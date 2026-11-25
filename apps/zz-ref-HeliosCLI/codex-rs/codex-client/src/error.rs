use http::HeaderMap;
use http::StatusCode;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum TransportError {
    #[error("failed to build request: {0}")]
    Build(String),
    #[error("request timed out")]
    Timeout,
    #[error("network error: {0}")]
    Network(String),
    #[error("HTTP {status}")]
    Http {
        status: StatusCode,
        url: Option<String>,
        headers: Option<HeaderMap>,
        body: Option<String>,
    },
    #[error("retry limit exceeded")]
    RetryLimit,
}

#[derive(Debug, Error)]
pub enum StreamError {
    #[error("stream error: {0}")]
    Stream(String),
    #[error("stream idle timeout")]
    Timeout,
}
