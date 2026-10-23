//! `phenotype-observably-macros` v0.2.0 — real implementation.
//!
//! `#[async_instrumented]` wraps an `async fn` in a `tracing` span that
//! survives every `.await` point by attaching via `tracing::Instrument`.
//! The result is a non-async `fn` that returns
//! `impl ::core::future::Future<Output = T>` and runs the body inside
//! the span.
//!
//! ## Options
//!
//! | Option            | Meaning                                                      |
//! |-------------------|--------------------------------------------------------------|
//! | `name = "..."`    | span name (defaults to the function ident)                   |
//! | `level = "..."`   | `trace` / `debug` / `info` (default) / `warn` / `error`      |
//! | `skip(a, b, ...)` | function arguments to omit from the span field list         |
//!
//! When the `tracing` feature is enabled (default), the macro emits a
//! `tracing::Instrument`-wrapped future. When the feature is disabled
//! the macro degenerates to identity so the original `async fn` is
//! emitted unchanged.
//!
//! Sync fns are passed through unchanged regardless of feature state.
//!
//! ## Examples
//!
//! ```rust,ignore
//! use phenotype_observably_macros::async_instrumented;
//!
//! #[async_instrumented]
//! async fn fetch(url: &str) -> anyhow::Result<String> {
//!     // span `fetch` opens on entry, stays open across `.await`
//!     reqwest::get(url).await?.text().await
//! }
//!
//! #[async_instrumented(level = "warn", name = "ingest", skip(secret))]
//! async fn ingest(secret: &str, payload: Vec<u8>) -> Result<(), Error> {
//!     // span `ingest` at WARN level, `secret` excluded from fields
//!     Ok(())
//! }
//! ```

use proc_macro::TokenStream;
use proc_macro2::{self, Span};
use quote::{quote, ToTokens};
use syn::{
    parse::{Parse, ParseStream},
    FnArg, Ident, ItemFn, LitStr, Pat, ReturnType,
};

/// Parsed options passed to `#[async_instrumented(...)]`.
///
/// All fields are optional. Unspecified values fall back to the defaults
/// documented on `async_instrumented`.
#[derive(Default)]
struct MacroOptions {
    name: Option<String>,
    level: Option<String>,
    skip: Vec<Ident>,
}

impl Parse for MacroOptions {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let mut opts = MacroOptions::default();
        while !input.is_empty() {
            let key: Ident = input.parse()?;
            // `skip(...)` is a list of identifiers; everything else is `key = "value"`.
            if key == "skip" {
                let content;
                syn::parenthesized!(content in input);
                let punctuated = content.parse_terminated(Ident::parse, syn::Token![,])?;
                opts.skip.extend(punctuated);
            } else {
                let _eq: syn::Token![=] = input.parse()?;
                let lit: LitStr = input.parse()?;
                let value = lit.value();
                match key.to_string().as_str() {
                    "name" => opts.name = Some(value),
                    "level" => opts.level = Some(value),
                    other => {
                        return Err(syn::Error::new_spanned(
                            key,
                            format!(
                                "unknown option `{}`; expected one of: name, level, skip",
                                other
                            ),
                        ));
                    }
                }
            }
            if input.peek(syn::Token![,]) {
                let _comma: syn::Token![,] = input.parse()?;
            }
        }
        Ok(opts)
    }
}

/// Map a level string (e.g. `"info"`) to the matching `tracing::Level` variant.
fn level_tokens(level: &Option<String>) -> proc_macro2::TokenStream {
    let variant = match level.as_deref().map(str::to_ascii_lowercase).as_deref() {
        Some("trace") => "TRACE",
        Some("debug") => "DEBUG",
        Some("info") => "INFO",
        Some("warn") => "WARN",
        Some("error") => "ERROR",
        _ => "INFO",
    };
    let ident = Ident::new(variant, Span::call_site());
    quote! { ::tracing::Level::#ident }
}

/// Collect `name = tracing::field::Empty` for every non-`self` argument
/// whose name is not in the `skip` set. `self` receivers are always
/// omitted (matching `tracing::instrument` defaults).
fn span_field_args(
    inputs: &syn::punctuated::Punctuated<FnArg, syn::Token![,]>,
    skip: &[Ident],
) -> Vec<proc_macro2::TokenStream> {
    inputs
        .iter()
        .filter_map(|arg| match arg {
            FnArg::Typed(pat_type) => {
                if let Pat::Ident(pat_ident) = &*pat_type.pat {
                    let name = &pat_ident.ident;
                    if !skip.iter().any(|s| s == name) {
                        return Some(quote! { #name = ::tracing::field::Empty });
                    }
                }
                None
            }
            FnArg::Receiver(_) => None,
        })
        .collect()
}

/// Render the function's return type as `impl ::core::future::Future<Output = T>`.
///
/// The trailing `+ 'fn_lifetime` is what allows the returned `impl Trait`
/// to borrow from the function's input parameters (e.g. `&str`). Without
/// it the compiler rejects the wrapper with E0700 "hidden type captures
/// lifetime that does not appear in bounds" because `impl Future<...>`
/// has no syntactic slot for the input lifetimes to flow through.
fn future_return_type(output: &ReturnType) -> proc_macro2::TokenStream {
    match output {
        ReturnType::Default => {
            quote! { impl ::core::future::Future<Output = ()> + 'fn_lifetime }
        }
        ReturnType::Type(arrow, ty) => {
            quote! { #arrow impl ::core::future::Future<Output = #ty> + 'fn_lifetime }
        }
    }
}

/// Walk a type and replace every anonymous lifetime `'_` with `target`.
/// Used to make `&str` arguments explicitly borrow from `'fn_lifetime`
/// so the generated `impl Future + 'fn_lifetime` wrapper compiles.
fn rewrite_anonymous_lifetimes(ty: &mut syn::Type, target: &syn::Lifetime) {
    match ty {
        syn::Type::Reference(r#ref) => {
            // If the reference has no lifetime or has an anonymous
            // lifetime `'_`, install the target.
            match &r#ref.lifetime {
                None => r#ref.lifetime = Some(target.clone()),
                Some(lt) if lt.ident == "_" => r#ref.lifetime = Some(target.clone()),
                _ => {}
            }
            rewrite_anonymous_lifetimes(&mut r#ref.elem, target);
        }
        syn::Type::Tuple(t) => {
            for elem in t.elems.iter_mut() {
                rewrite_anonymous_lifetimes(elem, target);
            }
        }
        syn::Type::Array(a) => {
            rewrite_anonymous_lifetimes(&mut a.elem, target);
        }
        syn::Type::Group(g) => {
            rewrite_anonymous_lifetimes(&mut g.elem, target);
        }
        syn::Type::Paren(p) => {
            rewrite_anonymous_lifetimes(&mut p.elem, target);
        }
        syn::Type::Slice(s) => {
            rewrite_anonymous_lifetimes(&mut s.elem, target);
        }
        _ => {}
    }
}

/// Real implementation: bridge between `proc_macro` and `proc_macro2`
/// so the body can be unit-tested from outside the proc-macro bridge
/// (`parse_macro_input!` panics when invoked outside a proc-macro).
#[proc_macro_attribute]
pub fn async_instrumented(attr: TokenStream, item: TokenStream) -> TokenStream {
    let out = async_instrumented_impl(
        proc_macro2::TokenStream::from(attr),
        proc_macro2::TokenStream::from(item),
    );
    TokenStream::from(out)
}

fn async_instrumented_impl(
    attr: proc_macro2::TokenStream,
    item: proc_macro2::TokenStream,
) -> proc_macro2::TokenStream {
    let opts = match syn::parse2::<MacroOptions>(attr) {
        Ok(opts) => opts,
        Err(err) => return err.to_compile_error(),
    };

    let input = match syn::parse2::<ItemFn>(item) {
        Ok(item) => item,
        Err(err) => return err.to_compile_error(),
    };

    // Sync fns are passed through unchanged regardless of feature state.
    if input.sig.asyncness.is_none() {
        return input.into_token_stream();
    }

    let name_str = opts
        .name
        .clone()
        .unwrap_or_else(|| input.sig.ident.to_string());
    let level = level_tokens(&opts.level);
    let field_args = span_field_args(&input.sig.inputs, &opts.skip);

    // Build the wrapped signature: drop `async`, return
    // `impl Future<Output = T>` so the body can be wrapped in
    // `.instrument(span)` and still be `Send` across `.await`.
    //
    // We inject a synthetic `'fn_lifetime` parameter at the front of
    // the function's generics so the returned `impl Future` can borrow
    // from the caller's input parameters (e.g. `&str`). Without this,
    // Rust rejects the wrapper with E0700 "hidden type captures
    // lifetime that does not appear in bounds".
    let mut wrapped_sig = input.sig.clone();
    wrapped_sig.asyncness = None;

    // Prepend `'fn_lifetime` to the existing generics (if any).
    let synthetic_lt: syn::GenericParam = syn::parse_quote! { 'fn_lifetime };
    wrapped_sig.generics.params.insert(0, synthetic_lt);

    // Rewrite every reference input type from the anonymous lifetime
    // `&'_ T` to `&'fn_lifetime T`. Without this rewrite, the original
    // `&str` arguments would still elide to a fresh anonymous lifetime
    // rather than the synthetic `'fn_lifetime` we just added — producing
    // E0621 "explicit lifetime required".
    let fn_lt: syn::Lifetime = syn::parse_quote! { 'fn_lifetime };
    for arg in wrapped_sig.inputs.iter_mut() {
        if let syn::FnArg::Typed(pat_type) = arg {
            rewrite_anonymous_lifetimes(&mut pat_type.ty, &fn_lt);
        }
    }

    let fut_ret = future_return_type(&input.sig.output);
    wrapped_sig.output = match syn::parse2::<ReturnType>(fut_ret) {
        Ok(rt) => rt,
        Err(_) => {
            return syn::Error::new_spanned(
                &input.sig.output,
                "async_instrumented: could not rewrite return type",
            )
            .to_compile_error();
        }
    };

    let vis = &input.vis;
    let block = &input.block;
    let attrs = &input.attrs;
    let name_lit = LitStr::new(&name_str, input.sig.ident.span());

    // With the `tracing` feature: emit a real Instrument-wrapped future.
    //
    // The synthetic `'fn_lifetime` parameter (prepended to the function's
    // generics, see `wrapped_sig` construction above) is what lets the
    // returned `impl Future<...> + 'fn_lifetime` borrow from the caller's
    // input parameters. Without it the wrapper fails to compile with
    // E0700 "hidden type captures lifetime that does not appear in bounds".
    let enabled = quote! {
        #(#attrs)*
        #vis #wrapped_sig {
            use ::tracing::Instrument as _;
            async move { #block }
                .instrument(::tracing::span!(#level, #name_lit, #(#field_args),*))
        }
    };

    // Without the `tracing` feature: pass-through (original async fn).
    // NB: `#input` already includes the user's `vis`, so do NOT prepend
    // `#vis` here — doing so would emit `pub pub async fn ...` for any
    // user-written `pub` input (see commit history; this was a real bug).
    let disabled = quote! {
        #(#attrs)*
        #input
    };

    quote! {
        #[cfg(feature = "tracing")]
        #enabled

        #[cfg(not(feature = "tracing"))]
        #disabled
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Unit test: option parser accepts `name`, `level`, `skip(...)`.
    #[test]
    fn parses_attr_options() {
        let attr: MacroOptions = syn::parse_quote! {
            name = "ingest", level = "warn", skip(secret, token)
        };
        assert_eq!(attr.name.as_deref(), Some("ingest"));
        assert_eq!(attr.level.as_deref(), Some("warn"));
        let skips: Vec<String> = attr.skip.iter().map(|i| i.to_string()).collect();
        assert_eq!(skips, vec!["secret", "token"]);
    }

    /// Unit test: option parser rejects unknown options.
    #[test]
    fn rejects_unknown_option() {
        let res: syn::Result<MacroOptions> = syn::parse2(quote::quote! { bogus = "x" });
        assert!(res.is_err(), "expected error for unknown option");
    }

    /// Unit test: `level = "..."` maps to the right `tracing::Level` variant.
    #[test]
    fn level_variant_mapping() {
        let cases: &[(Option<&str>, &str)] = &[
            (Some("trace"), "TRACE"),
            (Some("debug"), "DEBUG"),
            (Some("info"), "INFO"),
            (Some("warn"), "WARN"),
            (Some("error"), "ERROR"),
            (Some("WARN"), "WARN"), // case-insensitive
            (None, "INFO"),         // default
        ];
        for (input, expected) in cases {
            let owned = input.map(str::to_string);
            let ts = level_tokens(&owned).to_string();
            assert!(
                ts.contains(expected),
                "level_tokens({:?}) = {}, expected to contain {}",
                input,
                ts,
                expected
            );
        }
    }
}
