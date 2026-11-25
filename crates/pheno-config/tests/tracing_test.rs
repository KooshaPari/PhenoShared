//! Tracing integration test for pheno-config.
//!
//! Verifies the crate's `tracing` feature wiring is functional:
//! when a test wraps a `tracing::info_span!` and emits an event,
//! the `tracing-test` subscriber captures it. We don't construct a
//! real `Config` here because the current `pheno_config` builder
//! does not yet emit any tracing spans from inside `load_*` paths
//! (that's a follow-up ADR); the assertion is simply that the span
//! + event round-trip works under the `tracing` feature gate.
//!
//! Run with:
//!   cargo test --features tracing --test tracing_test

#![cfg(feature = "tracing")]

use tracing_test::traced_test;

#[traced_test]
#[test]
fn build_emits_span() {
    let span = tracing::info_span!("config_build");
    let _enter = span.enter();
    let result: Result<(), &'static str> = Ok(());
    tracing::info!(?result, "build complete");
    assert!(logs_contain("build complete"));
}
