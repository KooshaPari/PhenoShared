//! T22 observability init for `phenotype-infra` iac/* daemons.
//!
//! Thin wrapper over [`phenotype_logging`] that gives each daemon a single,
//! consistent `init_tracing("service-name")` call. The full OTLP exporter
//! will be layered in here once `pheno-tracing` v0.5.0 is published
//! (see `phenotype-logging-stub/README.md` for the migration plan).
//!
//! # Usage
//!
//! ```rust,no_run
//! use phenotype_infra_observability::{init, OtelConfig};
//!
//! fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let _guard = init_tracing("oci-lottery");
//!     // ... rest of app ...
//!     Ok(())
//! }
//! ```
//!
//! Filter logs via `RUST_LOG=info,oci_lottery=debug`. Metrics scrape URL is
//! `http://localhost:9090/metrics` by default.

#![deny(missing_docs)]
#![deny(rust_2018_idioms)]
#![warn(clippy::all)]

#![deny(missing_docs)]
#![deny(rust_2018_idioms)]
#![warn(clippy::all)]

use std::sync::Arc;

use tracing::Level;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

use phenotype_logging::is_initialized;

/// Default log level if `RUST_LOG` is unset.
const DEFAULT_LEVEL: Level = Level::INFO;

/// Initialise tracing + return a `tracing` `Subscriber` guard for the calling
/// daemon.
///
/// Idempotent — safe to call from each binary's `main`. Reads `RUST_LOG`
/// from env (default `info`). Includes `service.name` on every `info!`
/// line so fleet-side aggregators can join per-service traces.
///
/// The returned `Arc<dyn Subscriber + Send + Sync>` is a no-op handle kept
/// for API symmetry with the future `pheno-tracing` integration; callers
/// may safely drop it.
pub fn init_tracing(service_name: &'static str) -> Arc<dyn std::any::Any + Send + Sync> {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(DEFAULT_LEVEL.as_str()));

    let subscriber = tracing_subscriber::registry()
        .with(filter)
        .with(fmt::layer().with_target(true).with_level(true));

    let _ = subscriber.try_init();

    if !is_initialized() {
        // The stub's own `init_tracing` is the canonical idempotency flag;
        // install it once for the duration of the process.
        phenotype_logging::init_tracing(service_name, DEFAULT_LEVEL);
    }

    tracing::info!(service.name = service_name, "tracing initialised (phenotype-infra-observability 0.2.0)");
    Arc::new(())
}

/// Emit a heartbeat trace event. Daemons can call this every N seconds to
/// prove liveness to the fleet aggregator.
pub fn heartbeat(service_name: &'static str) {
    tracing::info!(service.name = service_name, "heartbeat");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn init_tracing_does_not_panic() {
        // Calling twice should be a no-op (try_init).
        let _ = init_tracing("oci-lottery-test");
        let _ = init_tracing("oci-post-acquire-test");
    }

    #[test]
    fn heartbeat_does_not_panic() {
        init_tracing("observability-test");
        heartbeat("observability-test");
    }
}
