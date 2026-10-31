//! `phenotype-observably-macros` — real instrumentation.
//!
//! `#[async_instrumented]` instruments an `async fn` with a `tracing` span
//! that stays entered across every `.await` point in the function body.
//!
//! # Provenance (read this before trusting the macro)
//!
//! The original crate lived at
//! `PhenoObservability/crates/phenotype-observably-macros`, a path *outside*
//! this repository. `PhenoObservability` is unreachable (`gh repo view
//! KooshaPari/PhenoObservability` does not resolve), so the original source
//! could not be recovered.
//!
//! The implementation here is reconstructed from an in-flight PR branch
//! (`chore/remove-dead-integration-crate`), which carried a real
//! `tracing::Instrument`-based implementation of the same package. That
//! implementation did not survive contact with the real call sites in this
//! workspace; see "Deviations" below. The option surface, level mapping,
//! `skip(...)` handling, and sync pass-through are preserved from it.
//!
//! Prior to this, the crate was a **pass-through no-op**: it returned the
//! annotated item byte-for-byte unchanged, so 44 `#[async_instrumented]`
//! call sites compiled while emitting no spans at all. That is no longer the
//! case.
//!
//! # Deviations from the PR-branch implementation
//!
//! 1. **Codegen wraps the body, not the signature.** The PR-branch version
//!    rewrote the function signature to drop `async` and return
//!    `impl Future<Output = T> + 'fn_lifetime`, injecting a synthetic
//!    lifetime and rewriting anonymous `&T` argument lifetimes to match.
//!    That approach cannot handle `&self` receivers — it only rewrote
//!    [`syn::FnArg::Typed`] arguments, so `&self` kept its own elided
//!    lifetime while the return type claimed `'fn_lifetime`. Real call sites
//!    in this workspace are dominated by `&self` methods, and it failed
//!    outright with "lifetime may not live long enough" on
//!    `focus-always-on`. Preserving the original signature and instrumenting
//!    the body instead works for `&self`, `&mut self`, generic functions,
//!    `where` clauses, and `impl Trait` returns, because nothing about the
//!    public signature changes.
//!
//! 2. **The feature gate is evaluated at expansion time, not emitted.**
//!    The PR-branch version emitted `#[cfg(feature = "tracing")]` /
//!    `#[cfg(not(feature = "tracing"))]` into the *consumer*. Those cfgs are
//!    resolved in the consumer's own feature space, so unless every consumer
//!    happened to declare and enable a `tracing` feature, the macro silently
//!    expanded to the pass-through branch — reproducing the exact silent
//!    no-op this crate exists to remove. (Only 2 of 12 dependents declare
//!    such a feature, and neither enables it by default.) The gate is now
//!    read with `cfg!` inside the macro crate, so the emitted code is
//!    unconditionally the chosen variant.
//!
//! # Options
//!
//! | Option            | Meaning                                                      |
//! |-------------------|--------------------------------------------------------------|
//! | `name = "..."`    | span name (defaults to the function ident)                   |
//! | `level = "..."`   | `trace` / `debug` / `info` (default) / `warn` / `error`      |
//! | `skip(a, b, ...)` | function arguments to omit from the span field list          |
//!
//! Fields for non-skipped arguments are declared as
//! `tracing::field::Empty`, matching `tracing::instrument`'s behaviour: the
//! field names appear on the span but carry no value unless the body records
//! them.
//!
//! Sync functions are passed through unchanged regardless of feature state.
//!
//! # Examples
//!
//! ```rust,ignore
//! use phenotype_observably_macros::async_instrumented;
//!
//! #[async_instrumented]
//! async fn fetch(url: &str) -> anyhow::Result<String> {
//!     // span `fetch` is entered across every await below
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
    FnArg, Ident, ItemFn, LitStr, Pat,
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

/// Bridge between `proc_macro` and `proc_macro2` so the body can be
/// unit-tested from outside the proc-macro bridge (`parse_macro_input!`
/// panics when invoked outside a proc-macro).
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

    // Feature gate is resolved HERE, in the macro crate, so the emitted code
    // is unconditionally one variant. Emitting `#[cfg(feature = "tracing")]`
    // would hand the decision to the consumer, where the feature usually does
    // not exist and the macro would silently expand to a pass-through.
    if !cfg!(feature = "tracing") {
        // `#input` already carries the user's `vis`, so do not prepend it.
        return input.into_token_stream();
    }

    let name_str = opts
        .name
        .clone()
        .unwrap_or_else(|| input.sig.ident.to_string());
    let level = level_tokens(&opts.level);
    let field_args = span_field_args(&input.sig.inputs, &opts.skip);

    let vis = &input.vis;
    let attrs = &input.attrs;
    let sig = &input.sig;
    let block = &input.block;
    let name_lit = LitStr::new(&name_str, input.sig.ident.span());

    // Signature is preserved verbatim; only the body is wrapped.
    //
    // `async move { #block }` moves the arguments into the inner future and
    // leaves the outer `async fn` signature untouched, which is what makes
    // this work for `&self` methods (the dominant shape in this workspace),
    // generics, `where` clauses, and `impl Trait` returns. `.instrument(span)`
    // enters the span on each poll of the inner future, so the span is open
    // across every `.await` point in the body.
    quote! {
        #(#attrs)*
        #vis #sig {
            use ::tracing::Instrument as _;
            ::tracing::Instrument::instrument(
                async move { #block },
                ::tracing::span!(#level, #name_lit, #(#field_args),*),
            )
            .await
        }
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

    /// Unit test: the signature must survive expansion untouched.
    ///
    /// This is the regression guard for the `&self` defect that broke the
    /// PR-branch implementation: the emitted code must still declare
    /// `async fn ... (&self, ...)` and must not mention any synthetic
    /// lifetime.
    #[test]
    fn signature_is_preserved_verbatim() {
        let item = quote::quote! {
            pub async fn tick(&self, now: u64) -> ::anyhow::Result<()> { Ok(()) }
        };
        let out = async_instrumented_impl(quote::quote! {}, item).to_string();
        assert!(
            out.contains("async fn tick"),
            "signature was rewritten: {out}"
        );
        assert!(
            out.contains("& self"),
            "receiver was rewritten/lost: {out}"
        );
        assert!(
            !out.contains("fn_lifetime"),
            "synthetic lifetime reintroduced: {out}"
        );
        assert!(
            out.contains("Instrument"),
            "no instrumentation emitted: {out}"
        );
    }

    /// Unit test: a sync fn is emitted unchanged.
    #[test]
    fn sync_fn_passes_through() {
        let item = quote::quote! { fn helper(x: u32) -> u32 { x + 1 } };
        let out = async_instrumented_impl(quote::quote! {}, item).to_string();
        assert!(!out.contains("Instrument"), "sync fn was instrumented: {out}");
        assert!(out.contains("fn helper"), "sync fn was mangled: {out}");
    }
}
