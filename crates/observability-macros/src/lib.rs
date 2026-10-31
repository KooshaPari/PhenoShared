//! Reconstruction of the unrecoverable `phenotype-observably-macros` crate.
//!
//! # Provenance (read this before trusting the macro)
//!
//! The original crate lived at
//! `PhenoObservability/crates/phenotype-observably-macros`, a path *outside*
//! this repository. `PhenoObservability` exists neither on disk nor on GitHub
//! (`gh repo view KooshaPari/PhenoObservability` does not resolve), so the
//! original source is unrecoverable from upstream.
//!
//! Because a missing path dependency makes `cargo metadata` fail for the whole
//! workspace (which in turn killed the `Cargo Deny (Advisories + Licenses)` CI
//! job), this crate is a minimal in-repo stand-in that keeps the original
//! package name so downstream `use phenotype_observably_macros::async_instrumented;`
//! imports keep compiling unchanged.
//!
//! # Honest status: this is a PASS-THROUGH NO-OP
//!
//! The original `async_instrumented` emitted tracing spans around async
//! functions. This reconstruction **emits no instrumentation at all**. It
//! returns the annotated item byte-for-byte unchanged.
//!
//! Consequences, stated plainly:
//!
//! - Call sites compile, but they are **not** instrumented.
//! - No span is created, entered, or closed; no fields are recorded; no timing
//!   is captured.
//! - Any dashboard, alert, or trace query that expects these spans will see
//!   nothing, and will see it silently rather than loudly.
//!
//! Do not read the presence of `#[async_instrumented]` in this workspace as
//! evidence that observability exists. It does not.
//!
//! # Future work
//!
//! A real implementation should parse the attribute arguments and the annotated
//! `async fn`, then wrap the body in a `tracing` span (for example
//! `tracing::info_span!`, `.instrument(...)` from `tracing-futures`, or
//! `tracing::Instrument`). Until that lands, this file is deliberately small
//! and deliberately inert.

use proc_macro::TokenStream;

/// No-op stand-in for the original tracing instrumentation attribute.
///
/// Returns the annotated item unchanged. See the crate-level docs: this
/// reconstruction performs **no** instrumentation.
///
/// Accepts and ignores any attribute arguments, so existing `#[async_instrumented]`
/// call sites keep compiling whether or not arguments are present.
#[proc_macro_attribute]
pub fn async_instrumented(_attr: TokenStream, item: TokenStream) -> TokenStream {
    item
}
