// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Error types for elicitation
//!
//! [`ElicitationError`] implements `From<std::io::Error>` so that
//! filesystem-backed intent sources (e.g. prompts loaded from disk) can
//! propagate failures without per-call `.map_err` shims.

use thiserror::Error;

/// Errors that can occur during elicitation
#[derive(Error, Debug)]
pub enum ElicitationError {
    /// Failed to parse intent
    #[error("Failed to parse intent: {0}")]
    ParseError(String),

    /// Ambiguous input - needs clarification
    #[error("Ambiguous input: {0}")]
    AmbiguousError(String),

    /// Invalid intent
    #[error("Invalid intent: {0}")]
    InvalidIntent(String),

    /// Generation failed
    #[error("Generation failed: {0}")]
    GenerationError(String),

    /// Classification failed
    #[error("Classification failed: {0}")]
    ClassificationError(String),

    /// I/O error reading intent source
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Result type for elicitation
pub type Result<T> = std::result::Result<T, ElicitationError>;

#[cfg(test)]
mod tests {
    use super::*;

    /// Traces to: FR-HELIOS-IO-004
    /// `From<io::Error>` must produce the `Io` variant.
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("prompt file missing");
        let err: ElicitationError = io_err.into();
        assert!(matches!(err, ElicitationError::Io(_)));
    }

    /// Traces to: FR-HELIOS-IO-004
    /// Display must surface the underlying I/O message.
    #[test]
    fn io_error_display_includes_message() {
        let io_err = std::io::Error::other("broken pipe");
        let err: ElicitationError = io_err.into();
        assert!(err.to_string().contains("broken pipe"));
    }
}
