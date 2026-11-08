//! `pheno-tracing` stub crate — re-exports the canonical `tracing` crate
//! to unblock offline / CI builds while the real private `pheno-tracing`
//! git-dep (ADR-012) cannot be resolved.
//!
//! ## When to delete
//!
//! Delete this stub and the `[patch.crates-io]` redirect in
//! `Cargo.toml` once `pheno-tracing` v0.4.0 is either:
//! 1. Published to crates.io, OR
//! 2. Vendored into `vendor/pheno-tracing` with a `[patch.crates-io]`
//!    path redirect.
//!
//! ## API surface (subset)
//!
//! The real `pheno-tracing` crate exposes a fleet-canonical OTLP tracer
//! plus a `prelude` module. This stub mirrors the public symbols that
//! downstream consumers actually call.

pub use tracing::{debug, error, info, instrument, span, trace, warn, Level, Span};

pub mod prelude {
    pub use tracing::{debug, error, info, instrument, span, trace, warn, Level, Span};
    pub use tracing_subscriber::EnvFilter;
}

/// Process-level tracer initialiser (stub — does nothing).
pub fn init_tracing() {
    // No-op: the real pheno-tracing wires an OTLP exporter here.
}

/// Top-level `init(service, endpoint)` shape used by `prelude::init_tracing`.
pub fn init<S: Into<String>, E: Into<String>>(_service: S, _endpoint: E) -> Result<(), TracingError> {
    Ok(())
}

/// Error type returned by [`init`].
#[derive(Debug, thiserror::Error)]
pub enum TracingError {
    #[error("tracing error: {0}")]
    Other(String),
}

// ---------------------------------------------------------------------------
// ServiceName
// ---------------------------------------------------------------------------

/// Service name used as a tracer attribute (stub).
#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ServiceName(pub String);

impl ServiceName {
    pub fn new(name: impl Into<String>) -> Self {
        Self(name.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for ServiceName {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

impl From<String> for ServiceName {
    fn from(s: String) -> Self {
        Self(s)
    }
}

// ---------------------------------------------------------------------------
// OtlpEndpoint
// ---------------------------------------------------------------------------

/// OTLP endpoint configuration (stub).
#[derive(Debug, Clone, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct OtlpEndpoint {
    pub url: String,
}

impl OtlpEndpoint {
    pub fn new(url: impl Into<String>) -> Self {
        Self { url: url.into() }
    }

    pub fn as_str(&self) -> &str {
        &self.url
    }
}

impl From<&str> for OtlpEndpoint {
    fn from(s: &str) -> Self {
        Self { url: s.to_string() }
    }
}

impl From<String> for OtlpEndpoint {
    fn from(s: String) -> Self {
        Self { url: s }
    }
}

// ---------------------------------------------------------------------------
// Metrics primitives
// ---------------------------------------------------------------------------

/// Counter metric (stub — wraps a `tracing::event`).
#[derive(Debug, Clone, Default)]
pub struct Counter {
    pub name: String,
    value: u64,
}

impl Counter {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            value: 0,
        }
    }
    pub fn inc(&mut self) {
        self.value += 1;
        tracing::trace!(counter = %self.name, value = self.value, "inc");
    }
    pub fn value(&self) -> u64 {
        self.value
    }
}

/// Histogram metric (stub).
#[derive(Debug, Clone, Default)]
pub struct Histogram {
    pub name: String,
    count: u64,
    sum: f64,
}

impl Histogram {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            count: 0,
            sum: 0.0,
        }
    }
    pub fn observe(&mut self, value: f64) {
        self.count += 1;
        self.sum += value;
        tracing::trace!(histogram = %self.name, value, "observe");
    }
    pub fn count(&self) -> u64 {
        self.count
    }
    pub fn sum(&self) -> f64 {
        self.sum
    }
}

/// Per-request metrics bundle (stub).
#[derive(Debug)]
pub struct RequestMetrics {
    service: String,
    requests_total: Counter,
    request_duration_seconds: Histogram,
}

impl RequestMetrics {
    pub fn new(service: impl Into<String>) -> Self {
        let svc = service.into();
        Self {
            requests_total: Counter::new(format!("{svc}_requests_total")),
            request_duration_seconds: Histogram::new(format!("{svc}_request_duration_seconds")),
            service: svc,
        }
    }
    pub fn service(&self) -> &str {
        &self.service
    }
    pub fn requests_total(&mut self) -> &mut Counter {
        &mut self.requests_total
    }
    pub fn request_duration_seconds(&mut self) -> &mut Histogram {
        &mut self.request_duration_seconds
    }
}

// ---------------------------------------------------------------------------
// TracePort
// ---------------------------------------------------------------------------

/// Trace port identifier (stub).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TracePort {
    service: ServiceName,
    endpoint: OtlpEndpoint,
    sampled: bool,
}

impl TracePort {
    pub fn new(service: ServiceName, endpoint: OtlpEndpoint) -> Self {
        Self {
            service,
            endpoint,
            sampled: false,
        }
    }
    pub fn service_name(&self) -> &ServiceName {
        &self.service
    }
    pub fn endpoint(&self) -> &OtlpEndpoint {
        &self.endpoint
    }
    pub fn is_sampled(&self) -> bool {
        self.sampled
    }
}

impl Default for TracePort {
    fn default() -> Self {
        Self {
            service: ServiceName::default(),
            endpoint: OtlpEndpoint::default(),
            sampled: false,
        }
    }
}

// ---------------------------------------------------------------------------
// Misc
// ---------------------------------------------------------------------------

/// Result type alias for tracing-port operations.
pub type TraceResult<T> = Result<T, TracingError>;

/// Legacy error alias kept for backwards compat with the real crate.
#[derive(Debug, thiserror::Error)]
pub enum TraceError {
    #[error("tracing error: {0}")]
    Other(String),
}

/// Span guard for `instrument`-style scope tracking (stub).
pub struct SpanGuard {
    name: String,
    _span: tracing::Span,
}

impl SpanGuard {
    pub fn new(name: impl Into<String>) -> Self {
        let n = name.into();
        Self {
            name: n.clone(),
            _span: tracing::info_span!("guard", name = %n),
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }
}

impl Drop for SpanGuard {
    fn drop(&mut self) {
        tracing::trace!("span guard dropped");
    }
}