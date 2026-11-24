//! Error types for OmniRoute Core

use thiserror::Error;

/// Main error type for OmniRoute operations
#[derive(Error, Debug)]
pub enum Error {
    #[error("Provider error: {0}")]
    Provider(String),

    #[error("Request error: {0}")]
    Request(#[from] reqwest::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Routing error: no provider available for model '{0}'")]
    NoProvider(String),

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Authentication error: {0}")]
    Authentication(String),

    #[error("Rate limit exceeded: {0}")]
    RateLimit(String),

    #[error("Streaming error: {0}")]
    Streaming(String),

    #[error("Internal error: {0}")]
    Internal(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Result type alias using OmniRoute's error type
pub type Result<T> = std::result::Result<T, Error>;
