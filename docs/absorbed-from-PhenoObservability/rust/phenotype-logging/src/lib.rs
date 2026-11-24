//! Canonical `tracing` initialization for the Phenotype ecosystem.
//!
//! This crate exists so that downstream binaries and integration tests in
//! `PhenoRuntime`, `PhenoAgent`, `PhenoMCP-cheap`, `HeliosLab`, and any
//! other Phenotype polyrepo can call a single ergonomic helper instead of
//! hand-rolling the 7-line `tracing_subscriber::fmt().with_env_filter(...).init()`
//! block at the top of every `main.rs` and `tests/.../harness.rs`.
//!
//! The pattern honored here matches what already lives in those repos:
//!
//! ```text
//! tracing_subscriber::fmt()
//!     .with_env_filter(
//!         tracing_subscriber::EnvFilter::try_from_default_env()
//!             .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
//!     )
//!     .with_target(false)
//!     .init();
//! ```
//!
//! Two entry points are provided:
//!
//! - [`init_tracing`] / [`init_tracing_with_default`] — fire-and-forget for
//!   `fn main()`. Safe to call multiple times in the same process; the second
//!   call is a no-op rather than a panic.
//! - [`init_tracing_for_test`] — returns a [`tracing::subscriber::DefaultGuard`]
//!   tied to its scope, for use in tests and library contexts where the global
//!   subscriber must remain untouched.
//!
//! All public APIs are documented and every test references a Functional
//! Requirement in `FUNCTIONAL_REQUIREMENTS.md` (FR-LOG-001..003).

use tracing_subscriber::EnvFilter;

/// Default `EnvFilter` directive used when `RUST_LOG` is unset or invalid.
///
/// Matches the value used by the upstream callers in `PhenoRuntime`,
/// `PhenoAgent`, and `HeliosLab`.
pub const DEFAULT_FILTER: &str = "info";

/// Initialize the global `tracing` subscriber using the canonical
/// `EnvFilter`-from-`RUST_LOG` pattern.
///
/// Behavior:
///
/// - If `RUST_LOG` is set, its directives are honored (e.g.
///   `RUST_LOG=debug,sqlx=warn`).
/// - Otherwise, falls back to [`DEFAULT_FILTER`] (currently `"info"`).
/// - Subsequent calls in the same process are no-ops, so it is safe to call
///   from binaries, integration tests, and library entry points alike.
///
/// This is the **fire-and-forget** variant intended for `fn main()`. For
/// scoped setup in tests, prefer [`init_tracing_for_test`].
pub fn init_tracing() {
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(DEFAULT_FILTER));
    // Use `try_init` so a re-init in the same process (e.g. across multiple
    // integration test binaries linked into one test runner) is a no-op
    // rather than a panic. The canonical `.init()` form lives in the docs
    // and the in-tree PhenoRuntime/HeliosLab callers.
    let _ = tracing_subscriber::fmt().with_env_filter(filter).with_target(false).try_init();
}

/// Initialize the global `tracing` subscriber with a custom default filter
/// used when `RUST_LOG` is unset or invalid.
///
/// `RUST_LOG` still takes precedence when set. `default_filter` is parsed
/// via [`EnvFilter::new`], so it must be a valid directive (e.g. `"info"`,
/// `"debug"`, `"warn,sqlx=info"`).
///
/// # Examples
///
/// ```no_run
/// use phenotype_logging::init_tracing_with_default;
/// init_tracing_with_default("debug");
/// ```
pub fn init_tracing_with_default(default_filter: &str) {
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(default_filter));
    let _ = tracing_subscriber::fmt().with_env_filter(filter).with_target(false).try_init();
}

/// Scoped, guard-based variant for tests and library contexts where the
/// default global subscriber must remain untouched.
///
/// The supplied `filter_directive` is parsed via [`EnvFilter::new`] (not
/// `try_from_default_env`) so behavior is deterministic in tests. The
/// returned guard is `Drop`-able: dropping it restores the previous global
/// subscriber.
///
/// # Examples
///
/// ```no_run
/// use phenotype_logging::init_tracing_for_test;
///
/// let _guard = init_tracing_for_test("info");
/// tracing::info!("captured for the lifetime of `_guard`");
/// ```
pub fn init_tracing_for_test(filter_directive: &str) -> tracing::subscriber::DefaultGuard {
    let filter = EnvFilter::new(filter_directive);
    let subscriber = tracing_subscriber::fmt().with_env_filter(filter).with_target(false).finish();
    tracing::subscriber::set_default(subscriber)
}

#[cfg(test)]
mod tests {
    //! Inline tests, per the phenoShared convention. Each test references an
    //! FR ID in `FUNCTIONAL_REQUIREMENTS.md` so the FR-traceability matrix
    //! remains intact.

    use super::*;

    /// Traces to: FR-LOG-001
    ///
    /// `init_tracing` must be safe to call multiple times in the same process
    /// without panicking. This is the property that makes it usable in
    /// integration test binaries (one per test file) and `main()` shims
    /// alike.
    #[test]
    fn test_init_tracing_is_idempotent() {
        init_tracing();
        init_tracing();
        init_tracing_with_default("debug");
        init_tracing_with_default("trace");
    }

    /// Traces to: FR-LOG-002
    ///
    /// `init_tracing_with_default` must accept any string that
    /// [`EnvFilter::new`] accepts (e.g. `info`, `debug`, `warn,sqlx=info`)
    /// without panicking. We only assert the API surface here because the
    /// function uses `try_init` internally.
    #[test]
    fn test_init_tracing_with_default_accepts_known_directives() {
        init_tracing_with_default("info");
        init_tracing_with_default("debug");
        init_tracing_with_default("warn,sqlx=info");
    }

    /// Traces to: FR-LOG-003
    ///
    /// The scoped guard variant must construct successfully and be
    /// `Drop`-able. Dropping the guard restores the prior global
    /// subscriber, so this test runs in isolation.
    #[test]
    fn test_init_tracing_for_test_returns_droppable_guard() {
        let _guard = init_tracing_for_test("info");
        // Allow tracing macros to be used; they will be captured by `_guard`.
        tracing::info!("captured by init_tracing_for_test guard");
        // Drop happens at end of scope; no panic means the test passes.
    }
}
