//! Metrics and tracing configuration types for fleet-wide consumers.
//!
//! Provides the API surface that downstream crates (`phenotype-tooling-observability`,
//! `phenovcs-observability`, etc.) expect from `pheno-tracing` — including
//! `ServiceName`, `OtlpEndpoint`, `Counter`, `Histogram`, `RequestMetrics`,
//! and `SpanGuard`. These complement the core port/adapter types in `port.rs`
//! and the sampling types in `sampling.rs`.

use std::fmt;

// ---------------------------------------------------------------------------
// ServiceName
// ---------------------------------------------------------------------------

/// Service name used as a tracer attribute.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct ServiceName(pub String);

impl ServiceName {
    /// Create a new service name.
    pub fn new(name: impl Into<String>) -> Self {
        Self(name.into())
    }

    /// Borrow the inner string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for ServiceName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
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

/// OTLP endpoint configuration.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct OtlpEndpoint {
    /// The OTLP collector URL (e.g. `http://localhost:4317`).
    pub url: String,
}

impl OtlpEndpoint {
    /// Create a new endpoint.
    pub fn new(url: impl Into<String>) -> Self {
        Self { url: url.into() }
    }

    /// Borrow the URL string.
    pub fn as_str(&self) -> &str {
        &self.url
    }
}

impl fmt::Display for OtlpEndpoint {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.url)
    }
}

impl From<&str> for OtlpEndpoint {
    fn from(s: &str) -> Self {
        Self {
            url: s.to_string(),
        }
    }
}

impl From<String> for OtlpEndpoint {
    fn from(s: String) -> Self {
        Self { url: s }
    }
}

// ---------------------------------------------------------------------------
// Counter
// ---------------------------------------------------------------------------

/// Monotonic counter metric for fleet observability.
#[derive(Debug, Clone, Default)]
pub struct Counter {
    /// Metric name (e.g. `"cli_requests_total"`).
    pub name: String,
    value: u64,
}

impl Counter {
    /// Create a new counter at zero.
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            value: 0,
        }
    }

    /// Increment the counter by one.
    pub fn inc(&mut self) {
        self.value += 1;
        tracing::trace!(counter = %self.name, value = self.value, "inc");
    }

    /// Current counter value.
    pub fn value(&self) -> u64 {
        self.value
    }
}

// ---------------------------------------------------------------------------
// Histogram
// ---------------------------------------------------------------------------

/// Latency / duration histogram metric.
#[derive(Debug, Clone, Default)]
pub struct Histogram {
    /// Metric name (e.g. `"cli_request_duration_seconds"`).
    pub name: String,
    count: u64,
    sum: f64,
}

impl Histogram {
    /// Create a new empty histogram.
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            count: 0,
            sum: 0.0,
        }
    }

    /// Record an observation.
    pub fn observe(&mut self, value: f64) {
        self.count += 1;
        self.sum += value;
        tracing::trace!(histogram = %self.name, value, "observe");
    }

    /// Number of observations.
    pub fn count(&self) -> u64 {
        self.count
    }

    /// Sum of all observations.
    pub fn sum(&self) -> f64 {
        self.sum
    }
}

// ---------------------------------------------------------------------------
// RequestMetrics
// ---------------------------------------------------------------------------

/// Per-request metrics bundle (counter + histogram).
#[derive(Debug)]
pub struct RequestMetrics {
    service: String,
    requests_total: Counter,
    request_duration_seconds: Histogram,
}

impl RequestMetrics {
    /// Create a metrics bundle scoped to `service`.
    pub fn new(service: impl Into<String>) -> Self {
        let svc = service.into();
        Self {
            requests_total: Counter::new(format!("{svc}_requests_total")),
            request_duration_seconds: Histogram::new(format!("{svc}_request_duration_seconds")),
            service: svc,
        }
    }

    /// Service name this bundle is scoped to.
    pub fn service(&self) -> &str {
        &self.service
    }

    /// Mutable access to the request counter.
    pub fn requests_total(&mut self) -> &mut Counter {
        &mut self.requests_total
    }

    /// Mutable access to the duration histogram.
    pub fn request_duration_seconds(&mut self) -> &mut Histogram {
        &mut self.request_duration_seconds
    }
}

// ---------------------------------------------------------------------------
// TracePortConfig (concrete struct — different from the port::TracePort trait)
// ---------------------------------------------------------------------------

/// Concrete trace port configuration (service + endpoint).
///
/// This is a *configuration struct*, not to be confused with the
/// [`port::TracePort`] trait. Consumers use this to build a port config
/// and then pass it to an adapter that implements the trait.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct TracePortConfig {
    service: ServiceName,
    endpoint: OtlpEndpoint,
    sampled: bool,
}

impl TracePortConfig {
    /// Build a new port configuration.
    pub fn new(service: ServiceName, endpoint: OtlpEndpoint) -> Self {
        Self {
            service,
            endpoint,
            sampled: false,
        }
    }

    /// Borrow the service name.
    pub fn service_name(&self) -> &ServiceName {
        &self.service
    }

    /// Borrow the OTLP endpoint.
    pub fn endpoint(&self) -> &OtlpEndpoint {
        &self.endpoint
    }

    /// Whether this port is currently sampled.
    pub fn is_sampled(&self) -> bool {
        self.sampled
    }
}

// ---------------------------------------------------------------------------
// SpanGuard
// ---------------------------------------------------------------------------

/// Scope guard for `instrument`-style span tracking.
///
/// Creates an `info_span!` on construction and logs on drop. Useful for
/// bounding a span to a function scope without requiring the caller to
/// manually manage the span lifecycle.
pub struct SpanGuard {
    name: String,
    _span: tracing::Span,
}

impl SpanGuard {
    /// Create a new span guard with the given name.
    pub fn new(name: impl Into<String>) -> Self {
        let n = name.into();
        Self {
            name: n.clone(),
            _span: tracing::info_span!("guard", name = %n),
        }
    }

    /// Borrow the span name.
    pub fn name(&self) -> &str {
        &self.name
    }
}

impl Drop for SpanGuard {
    fn drop(&mut self) {
        tracing::trace!("span guard dropped");
    }
}
