//! Error types for the Tracera sink.

use thiserror::Error;

/// Result alias for sink operations.
pub type SinkResult<T> = Result<T, SinkError>;

/// Errors that may arise when using a Tracera sink.
#[derive(Debug, Error)]
pub enum SinkError {
    /// Configuration is invalid (e.g. empty endpoint, bad URL).
    #[error("invalid config: {0}")]
    InvalidConfig(String),

    /// Auth configuration is invalid (e.g. empty bearer token).
    #[error("invalid auth: {0}")]
    InvalidAuth(String),

    /// HTTP transport failure.
    #[error("transport error: {0}")]
    Transport(String),

    /// Server returned a non-success status.
    #[error("server rejected batch: status={status} body={body}")]
    ServerRejected {
        /// HTTP status code.
        status: u16,
        /// Truncated response body.
        body: String,
    },

    /// Auth rejected (HTTP 401/403).
    #[error("auth rejected: status={status}")]
    AuthRejected {
        /// HTTP status code.
        status: u16,
    },

    /// Backpressure: store is full and `block_on_full` was false.
    #[error("store full (capacity={capacity}, dropped={dropped})")]
    StoreFull {
        /// Configured capacity.
        capacity: usize,
        /// Number of events that were dropped.
        dropped: usize,
    },

    /// Sink is shutting down / shut down.
    #[error("sink is shutdown")]
    Shutdown,

    /// JSON serialization / deserialization error.
    #[error("serde error: {0}")]
    Serde(String),
}

impl From<serde_json::Error> for SinkError {
    fn from(value: serde_json::Error) -> Self {
        Self::Serde(value.to_string())
    }
}
