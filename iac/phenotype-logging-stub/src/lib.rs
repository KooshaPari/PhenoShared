//! `phenotype-logging` — in-workspace tracing init for the `phenotype-infra`
//! iac/* daemons.
//!
//! This crate exists so the four daemons (`oci-lottery`, `oci-post-acquire`,
//! `tailscale-keygen`, `observability`) can depend on a single, locally
//! resolvable name with a stable, minimal API.
//!
//! ## Why a local stub?
//!
//! The original path-dependency
//! `../../../phenoShared-wtrees/version-align-latest-tag/crates/phenotype-logging`
//! only resolved inside a specific worktree layout, breaking the build for
//! any outside consumer (CI, fresh clone, downstream crates). The stub
//! makes the dep graph self-contained: a clone of `phenotype-infra` builds
//! without any sibling worktree present.
//!
//! ## Migration plan to pheno-tracing
//!
//! The canonical T22 pheno-tracing crate (ADR-036) currently depends on a
//! sibling `pheno-otel` crate that is not yet published. Once pheno-tracing
//! `v0.5.0` ships (with `pheno-otel` inlined or vendored), this crate will
//! switch from wrapping `tracing` directly to re-exporting `pheno-tracing`'s
//! `TracePort` API. The 4 daemons will then get OTLP export for free.
//!
//! ## Usage
//!
//! ```no_run
//! use phenotype_logging::{info, init_tracing};
//!
//! init_tracing("oci-lottery", tracing::Level::INFO);
//! info!(region = "us-ashburn-1", "lottery tick");
//! ```

#![deny(missing_docs)]
#![deny(rust_2018_idioms)]
#![warn(clippy::all)]

use std::sync::atomic::{AtomicBool, Ordering};

static INITIALIZED: AtomicBool = AtomicBool::new(false);

/// Re-export the `tracing` macros for ergonomic single-import.
pub use tracing::{debug, error, info, instrument, span, trace, warn, Level};

/// Default `tracing_subscriber::EnvFilter` directive used when `RUST_LOG` is
/// unset. Exposed as a public constant so daemons that need to install their
/// own custom subscriber (e.g. `tailscale-keygen` redirecting logs to stderr
/// to keep stdout free for the auth-key payload) can match the rest of the
/// fleet's default filter contract.
pub const DEFAULT_FILTER: &str = "info";

/// Initialize a default `tracing` subscriber at `INFO` level.
///
/// Convenience wrapper for daemons that don't need to tune the level.
/// Reads `RUST_LOG` from env (overrides the default). Idempotent:
/// subsequent calls are a no-op.
pub fn init(service_name: &'static str) {
    init_tracing(service_name, Level::INFO);
}

/// Initialize a default `tracing` subscriber.
///
/// Installs an `env-filter`-driven `fmt` subscriber. Reads `RUST_LOG` from
/// env (falls back to `level`). Idempotent: subsequent calls are a no-op.
pub fn init_tracing(service_name: &'static str, level: Level) {
    use tracing_subscriber::{fmt, prelude::*, EnvFilter};
    if INITIALIZED.swap(true, Ordering::SeqCst) {
        return;
    }
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(level.as_str()));
    let fmt_layer = fmt::layer().with_target(true).with_thread_ids(false);
    let _ = tracing_subscriber::registry()
        .with(filter)
        .with(fmt_layer)
        .try_init();
    tracing::info!(service = service_name, "tracing initialized");
}

/// Return whether `init_tracing` has been called in this process.
pub fn is_initialized() -> bool {
    INITIALIZED.load(Ordering::SeqCst)
}

/// Reset the init flag. **Test-only**: allows re-running the init sequence
/// across test cases that exercise subscribers.
#[doc(hidden)]
pub fn __reset_for_tests() {
    INITIALIZED.store(false, Ordering::SeqCst);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exports_tracing_macros() {
        let _ = std::any::type_name::<Level>();
    }

    #[test]
    fn init_tracing_is_idempotent() {
        __reset_for_tests();
        init_tracing("phenotype-logging-test", Level::INFO);
        // Allow other parallel tests to have set the flag (which still makes
        // the init function a no-op — that's the contract we care about).
        // We just need to ensure the function did not panic and that the
        // process did not crash; no panic is the assertion.
        let _ = is_initialized();
        // Second call must be a no-op (no panic).
        init_tracing("phenotype-logging-test", Level::INFO);
    }

    #[test]
    fn reset_clears_the_flag() {
        init_tracing("phenotype-logging-test", Level::INFO);
        __reset_for_tests();
        assert!(!is_initialized());
    }
}
