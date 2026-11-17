// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Verification error types
//!
//! [`VerifyError`] implements `From<std::io::Error>` (and `From<tokio::task::JoinError>`
//! where applicable) so verification runs can propagate filesystem and
//! process failures without per-call `.map_err(...)` shims.

use thiserror::Error;

/// Errors that can occur during verification
#[derive(Error, Debug)]
pub enum VerifyError {
    /// Test runner failed
    #[error("Test runner failed: {0}")]
    TestRunnerError(String),

    /// Security scan failed
    #[error("Security scan failed: {0}")]
    SecurityScanError(String),

    /// Performance benchmark failed
    #[error("Performance benchmark failed: {0}")]
    PerformanceError(String),

    /// Verification timeout
    #[error("Verification timeout: {0}")]
    Timeout(String),

    /// Verification failed
    #[error("Verification failed: {0}")]
    Failed(String),

    /// Invalid configuration
    #[error("Invalid configuration: {0}")]
    ConfigError(String),

    /// IO error
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Result type for verification operations
pub type Result<T> = std::result::Result<T, VerifyError>;

#[cfg(test)]
mod tests {
    use super::*;

    /// Traces to: FR-HELIOS-IO-008
    /// `From<io::Error>` must map to the `IoError` variant.
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("spec store closed");
        let err: VerifyError = io_err.into();
        assert!(matches!(err, VerifyError::IoError(_)));
    }

    /// Traces to: FR-HELIOS-IO-008
    /// Display must surface the underlying I/O message.
    #[test]
    fn io_error_display_includes_message() {
        let io_err = std::io::Error::other("spec store closed");
        let err: VerifyError = io_err.into();
        assert!(err.to_string().contains("spec store closed"));
    }
}
