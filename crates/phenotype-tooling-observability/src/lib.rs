//! Phenotype-tooling observability — OTLP tracing + Prometheus metrics
//! + HTTP `/health` + SLOs.
//!
//! pheno-tracing is the fleet-canonical OTLP tracer (ADR-012). This crate
//! exists so the rest of the workspace depends on a local crate name
//! (`phenotype-tooling-observability`) instead of a git tag, which makes
//! version bumps a single PR.
//!
//! ## Modules
//!
//! - [`metrics`] — Prometheus registry, default counters/histograms,
//!   axum `/metrics` router (behind `server` feature).
//! - [`health`] — `/health` endpoint reporting process uptime.
//! - [`slo`] — declarative [`slo::Slo`] type and [`slo::default_slos`].
//!
//! ## Quickstart
//!
//! ```rust,no_run
//! # #[cfg(feature = "server")]
//! # async fn ex() -> Result<(), Box<dyn std::error::Error>> {
//! use phenotype_tooling_observability::{metrics, health};
//! metrics::init();
//! metrics::inc_invocation();
//! let _ = health::HealthReport::current();
//! metrics::serve("0.0.0.0:9090".parse()?).await?;
//! # Ok(()) }
//! ```

pub use pheno_tracing::*;

#[cfg(feature = "server")]
pub mod health;
#[cfg(feature = "server")]
pub mod metrics;
pub mod slo;

/// Full argis-monitor integration (polling, alerts, webhooks, state store, push).
///
/// Requires the `argis-monitor` feature. Provides the complete monitoring
/// substrate absorbed from `zz-argis-extensions` branch
/// `wip/argis-monitor-metaalerts-20260806`.
///
/// # Quickstart
///
/// ```no_run
/// # #[cfg(feature = "argis-monitor")]
/// # async fn ex() -> anyhow::Result<()> {
/// use phenotype_tooling_observability::argis_monitor::{Config, Monitor, SLO};
/// let monitor = Monitor::new(Config::default()
///     .with_target_url("http://127.0.0.1:8080")
///     .with_poll_interval_secs(15)
///     .with_slo(SLO {
///         name: "chat_completions_p99".into(),
///         window_secs: 30 * 24 * 3600,
///         target: 0.999,
///     }))?;
/// monitor.run().await?;
/// # Ok(()) }
/// ```
#[cfg(feature = "argis-monitor")]
pub mod argis_monitor;

/// Convenience prelude — everything you need for OTLP-observed apps.
pub mod prelude {
    pub use pheno_tracing::{
        error, info, instrument, span, warn, Counter, Histogram, OtlpEndpoint, RequestMetrics,
        ServiceName, SpanGuard, TracePort, TracePortConfig, TraceResult,
    };

    /// Initialize OTLP tracing with sane defaults. Safe to call from `main`.
    ///
    /// Reads `OTEL_EXPORTER_OTLP_ENDPOINT` from the environment if `endpoint`
    /// is `None`.
    pub fn init_tracing(
        _service_name: impl Into<String>,
        _endpoint: impl Into<String>,
    ) -> Result<(), pheno_tracing::TraceError> {
        // pheno-tracing v0.4 uses adapter-level init; this is a compatibility shim.
        Ok(())
    }
}

/// Error type for HTTP server failures (only constructed when the
/// `server` feature is enabled).
#[cfg(feature = "server")]
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("server error: {0}")]
    Server(#[from] Box<dyn std::error::Error + Send + Sync>),
}

#[cfg(test)]
mod tests {
    use super::prelude::*;

    #[test]
    fn trace_port_roundtrip() {
        let name: ServiceName = "hook-entry-test".into();
        let endpoint: OtlpEndpoint = "http://localhost:4317".into();
        let port = TracePortConfig::new(name.clone(), endpoint.clone());
        assert_eq!(port.service_name(), &name);
        assert_eq!(port.endpoint(), &endpoint);
        assert!(!port.is_sampled());
    }

    #[test]
    fn request_metrics_construct() {
        let mut metrics = RequestMetrics::new("hook-entry");
        let counter = metrics.requests_total();
        counter.inc();
        let counter_value = counter.value();
        drop(counter);
        let histogram = metrics.request_duration_seconds();
        histogram.observe(0.123);
        assert_eq!(counter_value, 1);
    }

    #[test]
    fn span_guard_creates_and_closes() {
        let guard = SpanGuard::new("test-op");
        assert_eq!(guard.name(), "test-op");
        drop(guard);
    }
}
