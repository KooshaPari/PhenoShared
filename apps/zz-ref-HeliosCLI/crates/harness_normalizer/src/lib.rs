// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Normalizer module - Data normalization for heliosHarness

use std::collections::HashMap;
use thiserror::Error;
use tracing::{debug, instrument};

/// Errors that can be produced by normalization.
///
/// Traces to: FR-HELIOS-NORM-001
#[derive(Debug, Error)]
pub enum NormalizerError {
    /// The JSON input is empty or whitespace-only.
    #[error("empty JSON input")]
    Empty,

    /// The JSON input could not be parsed.
    #[error("invalid JSON: {0}")]
    InvalidJson(String),

    /// Underlying I/O failure (e.g. reading input from disk).
    ///
    /// Traces to: FR-HELIOS-IO-012
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Normalization result
#[derive(Debug, Clone)]
pub struct NormalizedData {
    pub value: String,
    pub normalized: bool,
    pub metadata: HashMap<String, String>,
}

impl NormalizedData {
    pub fn new(value: String) -> Self {
        Self { value, normalized: false, metadata: HashMap::new() }
    }

    pub fn with_metadata(mut self, key: &str, val: &str) -> Self {
        self.metadata.insert(key.to_string(), val.to_string());
        self
    }
}

/// Normalizer for different data types
pub struct Normalizer {
    trim: bool,
    lowercase: bool,
    remove_special: bool,
}

impl Normalizer {
    pub fn new() -> Self {
        Self { trim: true, lowercase: false, remove_special: false }
    }

    pub fn with_trim(mut self, enabled: bool) -> Self {
        self.trim = enabled;
        self
    }
    pub fn with_lowercase(mut self, enabled: bool) -> Self {
        self.lowercase = enabled;
        self
    }
    pub fn with_remove_special(mut self, enabled: bool) -> Self {
        self.remove_special = enabled;
        self
    }

    pub fn normalize(&self, input: &str) -> NormalizedData {
        let mut result = input.to_string();

        if self.trim {
            result = result.trim().to_string();
        }
        if self.lowercase {
            result = result.to_lowercase();
        }
        if self.remove_special {
            result = result.chars().filter(|c| c.is_alphanumeric() || c.is_whitespace()).collect();
        }

        NormalizedData::new(result).with_metadata("normalizer", "default")
    }

    /// Traces to: FR-HELIOS-NORM-001
    /// Validates and normalizes a JSON string by stripping whitespace.
    ///
    /// # Errors
    ///
    /// Returns [`NormalizerError::Empty`] if `json` is empty or
    /// contains only whitespace.
    #[instrument(skip(self, json), fields(input_len = json.len()))]
    pub fn normalize_json(&self, json: &str) -> Result<NormalizedData, NormalizerError> {
        let normalized: String = json.chars().filter(|c| !c.is_whitespace()).collect();
        if normalized.is_empty() {
            debug!("rejecting: empty input");
            return Err(NormalizerError::Empty);
        }
        // Sanity-check brace balance so we surface malformed inputs as InvalidJson
        // rather than silently passing them through.
        let opens = normalized.chars().filter(|c| *c == '{' || *c == '[').count();
        let closes = normalized.chars().filter(|c| *c == '}' || *c == ']').count();
        if opens != closes {
            debug!(opens, closes, "rejecting: unbalanced braces");
            return Err(NormalizerError::InvalidJson("unbalanced braces".into()));
        }
        debug!(output_len = normalized.len(), "normalized JSON");
        Ok(NormalizedData::new(normalized).with_metadata("type", "json"))
    }

    pub fn normalize_url(&self, url: &str) -> NormalizedData {
        let normalized = url.trim().to_lowercase();
        NormalizedData::new(normalized).with_metadata("type", "url")
    }

    pub fn normalize_path(&self, path: &str) -> NormalizedData {
        let normalized = path.replace("\\", "/");
        NormalizedData::new(normalized).with_metadata("type", "path")
    }
}

impl Default for Normalizer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_normalization() {
        let n = Normalizer::new().with_lowercase(true);
        let result = n.normalize("  HELLO  ");
        assert_eq!(result.value, "hello");
    }

    #[test]
    fn test_url_normalization() {
        let n = Normalizer::new();
        let result = n.normalize_url("HTTP://Example.COM/Path ");
        assert_eq!(result.value, "http://example.com/path");
    }

    /// Traces to: FR-HELIOS-NORM-001
    #[test]
    fn test_normalize_json_strips_whitespace() {
        let n = Normalizer::new();
        let result = n.normalize_json("{ \"a\" : 1 }").unwrap();
        assert_eq!(result.value, "{\"a\":1}");
    }

    /// Traces to: FR-HELIOS-NORM-001
    #[test]
    fn test_normalize_json_empty_returns_err() {
        let n = Normalizer::new();
        let result = n.normalize_json("   \n\t  ");
        assert!(matches!(result, Err(NormalizerError::Empty)));
    }

    /// Traces to: FR-HELIOS-NORM-001
    #[test]
    fn test_normalize_json_unbalanced_returns_err() {
        let n = Normalizer::new();
        let result = n.normalize_json("{ \"a\": 1");
        assert!(matches!(result, Err(NormalizerError::InvalidJson(_))));
    }

    /// Traces to: FR-HELIOS-IO-012
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("normalizer read failed");
        let err: NormalizerError = io_err.into();
        assert!(matches!(err, NormalizerError::Io(_)));
        assert!(err.to_string().contains("normalizer read failed"));
    }
}
