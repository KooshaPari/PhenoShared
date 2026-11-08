//! Proc macros for the Phenotype MCP Fast framework
//!
//! Provides `#[tool]`, `#[resource]`, and `#[prompt]` macros that
//! auto-generate MCP protocol boilerplate from function signatures.

use proc_macro::TokenStream;
use quote::{format_ident, quote};
use syn::{parse_macro_input, FnArg, ItemFn, Pat, PatIdent};

/// Register a function as an MCP tool.
///
/// The function must accept a single `params` argument that implements
/// `serde::Deserialize` and `schemars::JsonSchema`, and return a
/// `Result<T, String>` where `T` implements `serde::Serialize`.
///
/// # Example
///
/// ```rust,ignore
/// use phenotype_mcp_fast::tool;
/// use schemars::JsonSchema;
/// use serde::Deserialize;
///
/// #[derive(JsonSchema, Deserialize)]
/// struct AddParams {
///     a: i32,
///     b: i32,
/// }
///
/// #[tool]
/// fn add(params: AddParams) -> Result<i32, String> {
///     Ok(params.a + params.b)
/// }
/// ```
#[proc_macro_attribute]
pub fn tool(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let input_fn = parse_macro_input!(item as ItemFn);
    let fn_name = &input_fn.sig.ident;
    let tool_name = fn_name.to_string();
    let vis = &input_fn.vis;
    let inputs = &input_fn.sig.inputs;
    let output = &input_fn.sig.output;
    let block = &input_fn.block;
    let generics = &input_fn.sig.generics;
    let attrs = &input_fn.attrs;

    // Extract the params type and name from the first argument
    let (params_type, param_name) = match inputs.first() {
        Some(FnArg::Typed(pat_type)) => {
            let ty = &pat_type.ty;
            let name = match &*pat_type.pat {
                Pat::Ident(PatIdent { ident, .. }) => ident.clone(),
                _ => {
                    return syn::Error::new_spanned(
                        &pat_type.pat,
                        "#[tool] parameter must be a simple identifier",
                    )
                    .to_compile_error()
                    .into();
                }
            };
            (quote!(#ty), name)
        }
        _ => {
            return syn::Error::new_spanned(
                &input_fn.sig,
                "#[tool] functions must have exactly one parameter (the params struct)",
            )
            .to_compile_error()
            .into();
        }
    };

    // Generate the tool registration struct name
    let tool_struct_name = format_ident!("{}__Tool", fn_name);

    let result = quote! {
        #(#attrs)*
        #vis fn #fn_name #generics(#inputs) #output #block

        /// Auto-generated MCP tool metadata and call wrapper for #fn_name
        #[allow(non_camel_case_types)]
        #vis struct #tool_struct_name;

        impl #tool_struct_name {
            /// Get the Tool definition for MCP protocol registration
            pub fn tool_def() -> ::phenotype_mcp_fast::internal::Tool {
                let schema = ::phenotype_mcp_fast::internal::schema_for!(#params_type);
                ::phenotype_mcp_fast::internal::Tool::new(
                    #tool_name,
                    concat!("Tool: ", stringify!(#fn_name)),
                    ::phenotype_mcp_fast::internal::serde_json::to_value(schema).unwrap_or_default(),
                )
            }

            /// Call the tool with JSON-RPC params
            pub fn call(
                params: &::phenotype_mcp_fast::internal::serde_json::Value
            ) -> Result<::phenotype_mcp_fast::internal::serde_json::Value, String> {
                let #param_name: #params_type = ::phenotype_mcp_fast::internal::serde_json::from_value(params.clone())
                    .map_err(|e| format!("Invalid params: {}", e))?;
                let result = #fn_name(#param_name)?;
                ::phenotype_mcp_fast::internal::serde_json::to_value(result)
                    .map_err(|e| format!("Serialization error: {}", e))
            }
        }
    };

    result.into()
}

/// Register a function as an MCP resource.
///
/// Stub for future implementation. Currently generates a compile-time
/// reminder to implement the resource pattern.
#[proc_macro_attribute]
pub fn resource(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let input_fn = parse_macro_input!(item as ItemFn);
    let fn_name = &input_fn.sig.ident;
    let vis = &input_fn.vis;
    let inputs = &input_fn.sig.inputs;
    let output = &input_fn.sig.output;
    let block = &input_fn.block;
    let generics = &input_fn.sig.generics;
    let attrs = &input_fn.attrs;

    let result = quote! {
        #(#attrs)*
        #vis fn #fn_name #generics(#inputs) #output #block

        // TODO: resource pattern not yet implemented in phenotype-mcp-fast
        // Track: https://github.com/KooshaPari/McpKit/issues/XXX
    };

    result.into()
}

/// Register a function as an MCP prompt.
///
/// Stub for future implementation. Currently generates a compile-time
/// reminder to implement the prompt pattern.
#[proc_macro_attribute]
pub fn prompt(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let input_fn = parse_macro_input!(item as ItemFn);
    let fn_name = &input_fn.sig.ident;
    let vis = &input_fn.vis;
    let inputs = &input_fn.sig.inputs;
    let output = &input_fn.sig.output;
    let block = &input_fn.block;
    let generics = &input_fn.sig.generics;
    let attrs = &input_fn.attrs;

    let result = quote! {
        #(#attrs)*
        #vis fn #fn_name #generics(#inputs) #output #block

        // TODO: prompt pattern not yet implemented in phenotype-mcp-fast
        // Track: https://github.com/KooshaPari/McpKit/issues/XXX
    };

    result.into()
}
