//! Procedural macros for Phenotype.
//!
//! This crate is intentionally minimal; it provides a stable home for
//! future derive/attribute macros used by the rest of the workspace.

/// Placeholder derive macro used by downstream test/example code.
///
/// The real macros will be added in subsequent PRs; for now this
/// keeps the crate buildable and discoverable.
#[proc_macro_derive(PhenotypePlaceholder, attributes(phenotype))]
pub fn phenotype_placeholder(_input: proc_macro::TokenStream) -> proc_macro::TokenStream {
    proc_macro::TokenStream::new()
}
