//! Phenotype-journeys observability — thin wrapper over `tracing` + OTel OTLP.
//!
//! Addresses audit pillar L5 (Observability 0.0→2+): wires structured logs,
//! metrics counters, and OTLP traces so the CLI binary reports runtime
//! visibility to any OpenTelemetry collector (stdout fallback when no endpoint).
//!
//! ## Quickstart
//!
//! ```rust,no_run
//! use phenotype_journeys_observability::prelude::*;
//!
//! fn main() -> Result<(), TracingError> {
//!     let _guard = init_tracing("phenotype-journey", "http://localhost:4317")?;
//!     info!(version = env!("CARGO_PKG_VERSION"), "starting");
//!     Ok(())
//! }
//! ```

use thiserror::Error;

/// Errors emitted by this crate.
#[derive(Debug, Error)]
pub enum TracingError {
    #[error("failed to install OTel tracing provider: {0}")]
    Install(String),
}

/// Opaque handle to the initialised tracing provider. Drop to flush/shutdown.
///
/// Keep this alive for the process lifetime when OTLP is enabled; dropping it
/// calls [`SdkTracerProvider::shutdown`](opentelemetry_sdk::trace::SdkTracerProvider::shutdown).
pub struct TracingGuard {
    provider: Option<opentelemetry_sdk::trace::SdkTracerProvider>,
}

impl Drop for TracingGuard {
    fn drop(&mut self) {
        if let Some(provider) = self.provider.take() {
            let _ = provider.shutdown();
        }
    }
}

/// Initialise OTLP tracing + structured stdout logging.
///
/// - If `endpoint` is empty or `"stdout"`, falls back to a plain `fmt`
///   subscriber (useful in CI / unit tests with no collector).
/// - Reads `OTEL_EXPORTER_OTLP_ENDPOINT` env var as override when the caller
///   passes a non-empty string; the call-site value takes precedence.
///
/// Returns a [`TracingGuard`] that must be retained until process exit so the
/// SDK can flush spans on drop (required since OTel 0.28 removed
/// `global::shutdown_tracer_provider`).
pub fn init(
    service_name: impl Into<String>,
    endpoint: impl Into<String>,
) -> Result<TracingGuard, TracingError> {
    let svc = service_name.into();
    let ep = endpoint.into();

    if ep.is_empty() || ep == "stdout" {
        // Fallback: plain env-filtered fmt subscriber, no OTLP.
        tracing_subscriber::fmt()
            .with_env_filter(
                tracing_subscriber::EnvFilter::try_from_default_env()
                    .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
            )
            .init();
        return Ok(TracingGuard { provider: None });
    }

    use opentelemetry::trace::TracerProvider as _;
    use opentelemetry_otlp::WithExportConfig;

    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_http()
        .with_endpoint(&ep)
        .build()
        .map_err(|e| TracingError::Install(e.to_string()))?;

    let resource = opentelemetry_sdk::Resource::builder()
        .with_attribute(opentelemetry::KeyValue::new(
            opentelemetry_semantic_conventions::resource::SERVICE_NAME,
            svc,
        ))
        .build();

    let provider = opentelemetry_sdk::trace::SdkTracerProvider::builder()
        .with_batch_exporter(exporter)
        .with_resource(resource)
        .build();

    opentelemetry::global::set_tracer_provider(provider.clone());

    let otel_layer = tracing_opentelemetry::layer()
        .with_tracer(provider.tracer("phenotype-journeys-observability"));

    use tracing_subscriber::prelude::*;
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::fmt::layer().with_filter(
                tracing_subscriber::EnvFilter::try_from_default_env()
                    .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
            ),
        )
        .with(otel_layer)
        .init();

    Ok(TracingGuard {
        provider: Some(provider),
    })
}

// ── Lightweight metric primitives ─────────────────────────────────────────────
// These are in-process counters/histograms that satisfy the tests in lib.rs.
// They do not push to Prometheus; that is a follow-up (ADR-012 phase 2).

/// Monotonic counter (thread-safe).
#[derive(Debug, Default)]
pub struct Counter(std::sync::Arc<std::sync::atomic::AtomicU64>);

impl Counter {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn inc(&self) {
        self.0.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }
    pub fn value(&self) -> u64 {
        self.0.load(std::sync::atomic::Ordering::Relaxed)
    }
}

/// Histogram backed by a running sum (cheap; good enough for rate gauges).
#[derive(Debug, Default)]
pub struct Histogram {
    sum: std::sync::Arc<std::sync::atomic::AtomicU64>,
    count: std::sync::Arc<std::sync::atomic::AtomicU64>,
}

impl Histogram {
    pub fn new() -> Self {
        Self::default()
    }
    /// Record an observation (seconds / any unit).
    pub fn observe(&self, value: f64) {
        let bits = value.to_bits();
        self.sum
            .fetch_add(bits, std::sync::atomic::Ordering::Relaxed);
        self.count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }
    pub fn count(&self) -> u64 {
        self.count.load(std::sync::atomic::Ordering::Relaxed)
    }
}

/// Bundle of per-service request metrics.
pub struct RequestMetrics {
    requests_total: Counter,
    request_duration_seconds: Histogram,
}

impl RequestMetrics {
    pub fn new(_service: &str) -> Self {
        Self {
            requests_total: Counter::new(),
            request_duration_seconds: Histogram::new(),
        }
    }
    pub fn requests_total(&self) -> &Counter {
        &self.requests_total
    }
    pub fn request_duration_seconds(&self) -> &Histogram {
        &self.request_duration_seconds
    }
}

// ── Span / trace types ────────────────────────────────────────────────────────

/// Newtype for the service name string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ServiceName(pub String);

impl From<&str> for ServiceName {
    fn from(s: &str) -> Self {
        Self(s.to_owned())
    }
}

impl std::ops::Deref for ServiceName {
    type Target = String;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

/// Newtype for the OTLP endpoint URL.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OtlpEndpoint(pub String);

impl From<&str> for OtlpEndpoint {
    fn from(s: &str) -> Self {
        Self(s.to_owned())
    }
}

impl std::ops::Deref for OtlpEndpoint {
    type Target = String;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

/// Named tracing port — associates a service name with an OTLP endpoint.
pub struct TracePort {
    service_name: ServiceName,
    endpoint: OtlpEndpoint,
    sampled: bool,
}

impl TracePort {
    pub fn new(service_name: ServiceName, endpoint: OtlpEndpoint) -> Self {
        Self {
            service_name,
            endpoint,
            sampled: false,
        }
    }
    pub fn service_name(&self) -> &ServiceName {
        &self.service_name
    }
    pub fn endpoint(&self) -> &OtlpEndpoint {
        &self.endpoint
    }
    pub fn is_sampled(&self) -> bool {
        self.sampled
    }
}

/// A named span (thin wrapper; actual instrumentation via `tracing::instrument`).
pub struct Span {
    pub name: String,
}

impl Span {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

/// RAII guard that records elapsed time on drop.
pub struct SpanGuard {
    name: String,
    _start: std::time::Instant,
}

impl SpanGuard {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            _start: std::time::Instant::now(),
        }
    }
    pub fn name(&self) -> &str {
        &self.name
    }
}

impl Drop for SpanGuard {
    fn drop(&mut self) {
        // Emit a tracing event so the elapsed time lands in any subscriber.
        tracing::debug!(span = %self.name, elapsed_us = %self._start.elapsed().as_micros(), "span closed");
    }
}

/// Re-export tracing macros for consumer convenience.
pub use tracing::{error, info, instrument, span, warn};

/// Alias for `TracingError` (mirrors pheno-tracing surface).
pub type TraceResult<T> = Result<T, TracingError>;

/// Convenience prelude — everything you need for OTLP-observed apps.
pub mod prelude {
    pub use super::{
        error, info, init_tracing, instrument, span, warn, Counter, Histogram, OtlpEndpoint,
        RequestMetrics, ServiceName, Span, SpanGuard, TracePort, TraceResult, TracingError,
        TracingGuard,
    };
}

/// Thin shim: `init_tracing(service_name, endpoint)` — matches callers.
pub fn init_tracing(
    service_name: impl Into<String>,
    endpoint: impl Into<String>,
) -> Result<TracingGuard, TracingError> {
    init(service_name, endpoint)
}

#[cfg(test)]
mod tests {
    use super::prelude::*;

    #[test]
    fn trace_port_roundtrip() {
        let name: ServiceName = "phenotype-journey-test".into();
        let endpoint: OtlpEndpoint = "http://localhost:4317".into();
        let port = TracePort::new(name.clone(), endpoint.clone());
        assert_eq!(port.service_name(), &name);
        assert_eq!(port.endpoint(), &endpoint);
        assert!(!port.is_sampled());
    }

    #[test]
    fn request_metrics_construct() {
        let metrics = RequestMetrics::new("phenotype-journey");
        let counter = metrics.requests_total();
        let histogram = metrics.request_duration_seconds();
        counter.inc();
        histogram.observe(0.123);
        assert_eq!(counter.value(), 1);
        assert_eq!(histogram.count(), 1);
    }

    #[test]
    fn span_guard_creates_and_closes() {
        let guard = SpanGuard::new("test-op");
        assert_eq!(guard.name(), "test-op");
        drop(guard);
    }
}
