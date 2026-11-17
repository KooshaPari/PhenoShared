// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Error types for specification parsing and validation
//!
//! All variants are constructed via thiserror, and [`SpecError`] implements
//! `From<std::io::Error>` so I/O failures during spec loading propagate without
//! a `.map_err(...)` at every call site.

use thiserror::Error;

/// Errors that can occur during specification processing
#[derive(Error, Debug)]
pub enum SpecError {
    /// Failed to parse YAML content
    #[error("Failed to parse YAML: {0}")]
    ParseError(String),

    /// Failed to parse JSON content
    #[error("Failed to parse JSON: {0}")]
    JsonParseError(String),

    /// Specification is missing required field
    #[error("Missing required field: {0}")]
    MissingField(String),

    /// Specification has invalid value
    #[error("Invalid value for {field}: {message}")]
    InvalidValue { field: String, message: String },

    /// Validation failed
    #[error("Validation error: {0}")]
    ValidationError(String),

    /// Version not found
    #[error("Version not found: {0}")]
    VersionNotFound(String),

    /// Unsupported format
    #[error("Unsupported format: {0}")]
    UnsupportedFormat(String),

    /// I/O error encountered while reading a specification file
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Result type for specification operations
pub type Result<T> = std::result::Result<T, SpecError>;

#[cfg(test)]
mod tests {
    use super::*;

    /// Traces to: FR-HELIOS-IO-001
    /// `From<io::Error>` must be implemented so `?` works when reading spec
    /// files from disk.
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "spec.yaml missing");
        let err: SpecError = io_err.into();
        match err {
            SpecError::Io(_) => {}
            other => panic!("expected SpecError::Io, got {:?}", other),
        }
    }

    /// Traces to: FR-HELIOS-IO-001
    /// The error message must preserve the inner I/O error text for debugging.
    #[test]
    fn io_error_display_includes_message() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "denied");
        let err: SpecError = io_err.into();
        let rendered = err.to_string();
        assert!(rendered.contains("denied"), "got: {}", rendered);
    }
}
