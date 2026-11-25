//! Observability module for OmniRoute Core
//!
//! Provides OpenTelemetry integration for tracing, metrics, and logging.

pub mod metrics;
pub mod tracing;

pub use metrics::Metrics;
pub use tracing::init_tracing;

/// Configuration for observability
#[derive(Debug, Clone)]
pub struct ObservabilityConfig {
    /// Service name for tracing/metrics
    pub service_name: String,
    /// Enable tracing
    pub tracing_enabled: bool,
    /// Enable metrics
    pub metrics_enabled: bool,
    /// OTLP endpoint for exporting traces
    pub otlp_endpoint: Option<String>,
    /// Sample rate (0.0 - 1.0)
    pub sample_rate: f64,
}

impl Default for ObservabilityConfig {
    fn default() -> Self {
        Self {
            service_name: "omniroute-core".to_string(),
            tracing_enabled: true,
            metrics_enabled: true,
            otlp_endpoint: None,
            sample_rate: 1.0,
        }
    }
}
