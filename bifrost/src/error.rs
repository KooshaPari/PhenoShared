//! Error types for the Bifrost-backed router adapter.

use std::fmt;

/// Errors produced by the Bifrost backend or the in-memory router.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// Bifrost gateway is configured but not reachable. v1 placeholder
    /// path should fall back to `omni-router`.
    #[error("bifrost backend unavailable: {0}")]
    BackendUnavailable(String),

    /// No route target matches the request shape.
    #[error("no route target matches: {0}")]
    NoMatch(String),

    /// Request was rejected by the dispatch contract (e.g. invalid model id).
    #[error("invalid request: {0}")]
    Invalid(String),

    /// Underlying I/O / HTTP failure.
    #[error("transport error: {0}")]
    Transport(String),
}

impl Error {
    /// True if the error is recoverable by retrying once.
    #[must_use]
    pub fn is_retryable(&self) -> bool {
        matches!(self, Error::Transport(_) | Error::BackendUnavailable(_))
    }
}

/// Result alias used throughout the crate.
pub type Result<T> = std::result::Result<T, Error>;

/// Convenience wrapper used by tests to build a `BackendUnavailable` error
/// with the standard formatting.
pub(crate) fn unavailable(extra: impl fmt::Display) -> Error {
    Error::BackendUnavailable(extra.to_string())
}

#[cfg(any(feature = "cache-sqlite", feature = "virtual-keys"))]
impl From<rusqlite::Error> for Error {
    fn from(err: rusqlite::Error) -> Self {
        Error::Transport(format!("sqlite: {err}"))
    }
}
