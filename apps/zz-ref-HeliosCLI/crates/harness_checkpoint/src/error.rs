// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Error types for checkpoint operations
//!
//! [`CheckpointError`] implements `From<std::io::Error>` so that filesystem
//! failures (e.g. config snapshot reads, store I/O) propagate cleanly via
//! `?` without a `.map_err` at every call site. Git-specific errors keep
//! their own `GitError` variant since they originate from `git2`.

use thiserror::Error;

/// Errors that can occur during checkpoint operations
#[derive(Error, Debug)]
pub enum CheckpointError {
    /// Git operation failed
    #[error("Git error: {0}")]
    GitError(String),

    /// Repository not found
    #[error("Repository not found: {0}")]
    RepositoryNotFound(String),

    /// Checkpoint not found
    #[error("Checkpoint not found: {0}")]
    CheckpointNotFound(String),

    /// Failed to create checkpoint
    #[error("Failed to create checkpoint: {0}")]
    CreateFailed(String),

    /// Failed to restore checkpoint
    #[error("Failed to restore checkpoint: {0}")]
    RestoreFailed(String),

    /// Storage error
    #[error("Storage error: {0}")]
    StorageError(String),

    /// Configuration error
    #[error("Configuration error: {0}")]
    ConfigError(String),

    /// I/O error during checkpoint operations
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Result type for checkpoint operations
pub type Result<T> = std::result::Result<T, CheckpointError>;

#[cfg(test)]
mod tests {
    use super::*;

    /// Traces to: FR-HELIOS-IO-005
    /// `From<io::Error>` must produce the `Io` variant.
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("disk full");
        let err: CheckpointError = io_err.into();
        assert!(matches!(err, CheckpointError::Io(_)));
    }

    /// Traces to: FR-HELIOS-IO-005
    /// Display must surface the underlying I/O message.
    #[test]
    fn io_error_display_includes_message() {
        let io_err = std::io::Error::other("permission denied");
        let err: CheckpointError = io_err.into();
        assert!(err.to_string().contains("permission denied"));
    }
}
