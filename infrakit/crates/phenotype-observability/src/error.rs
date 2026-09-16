//! Error types for observability operations

use thiserror::Error;

/// Result type for observability operations
pub type Result<T> = std::result::Result<T, ObservabilityError>;

/// Errors that can occur during observability operations
#[derive(Debug, Error)]
pub enum ObservabilityError {
    /// Invalid header format
    #[error("Invalid header format: {0}")]
    InvalidHeaderFormat(String),

    /// Invalid header value
    #[error("Invalid header value: {0}")]
    InvalidHeaderValue(String),

    /// Missing required header
    #[error("Missing required header: {0}")]
    MissingHeader(String),

    /// Telemetry serialization error
    #[error("Telemetry serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    /// Invalid cost value
    #[error("Invalid cost value: {0}")]
    InvalidCost(String),

    /// Invalid latency value
    #[error("Invalid latency value: {0}")]
    InvalidLatency(String),

    /// Invalid fallback step
    #[error("Invalid fallback step: {0}")]
    InvalidFallbackStep(String),
}
