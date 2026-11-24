//! Validation module for phenotype-sentinel
//! Provides configuration validation for circuit breaker, rate limiter, and bulkhead.

use serde::{Deserialize, Serialize};

/// Validation result type
pub type Result<T> = std::result::Result<T, ValidationError>;

/// Validation errors
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
    pub error_type: String,
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.field, self.message)
    }
}

impl std::error::Error for ValidationError {}

/// Validation result
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ValidationResult {
    pub is_valid: bool,
    pub errors: Vec<ValidationError>,
}

impl ValidationResult {
    /// Create a valid result
    pub fn valid() -> Self {
        Self { is_valid: true, errors: Vec::new() }
    }

    /// Create an invalid result
    pub fn invalid(errors: Vec<ValidationError>) -> Self {
        Self { is_valid: false, errors }
    }

    /// Add an error
    pub fn add_error(&mut self, error: ValidationError) {
        self.is_valid = false;
        self.errors.push(error);
    }

    /// Merge another result into this one
    pub fn merge(&mut self, other: Self) {
        if !other.is_valid {
            self.is_valid = false;
            self.errors.extend(other.errors);
        }
    }
}

/// Validator for configuration validation
#[derive(Debug, Clone, Default)]
pub struct Validator;

impl Validator {
    /// Create a new validator
    pub fn new() -> Self {
        Self
    }

    /// Add integer field validation (no-op, kept for API compatibility)
    /// Requires `validation-extended` feature.
    #[cfg(feature = "validation-extended")]
    pub fn integer(self, _field: &str) -> Self {
        self
    }

    /// Add minimum value constraint (no-op, kept for API compatibility)
    /// Requires `validation-extended` feature.
    #[cfg(feature = "validation-extended")]
    pub fn min(self, _min_val: f64) -> Self {
        self
    }

    /// Add maximum value constraint (no-op, kept for API compatibility)
    /// Requires `validation-extended` feature.
    #[cfg(feature = "validation-extended")]
    pub fn max(self, _max_val: f64) -> Self {
        self
    }

    /// Validate a value
    /// No-op stub reserved for the JSON-schema validator milestone.
    /// Requires `validation-extended` feature.
    #[cfg(feature = "validation-extended")]
    pub fn validate(&self, _value: &serde_json::Value) -> Result<ValidationResult> {
        Ok(ValidationResult::valid())
    }
}

/// Simple validation helper for field validation
/// Used by downstream sentinel consumers for range checking.
pub fn validate_field(
    field: &str,
    value: f64,
    min: Option<f64>,
    max: Option<f64>,
) -> Option<ValidationError> {
    if let Some(min_val) = min {
        if value < min_val {
            return Some(ValidationError {
                field: field.to_string(),
                message: format!("must be >= {}", min_val),
                error_type: "range".to_string(),
            });
        }
    }
    if let Some(max_val) = max {
        if value > max_val {
            return Some(ValidationError {
                field: field.to_string(),
                message: format!("must be <= {}", max_val),
                error_type: "range".to_string(),
            });
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_result_valid() {
        let result = ValidationResult::valid();
        assert!(result.is_valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validation_result_invalid() {
        let errors = vec![ValidationError {
            field: "test".to_string(),
            message: "error".to_string(),
            error_type: "test".to_string(),
        }];
        let result = ValidationResult::invalid(errors);
        assert!(!result.is_valid);
    }

    #[test]
    fn test_validate_field_min() {
        let result = validate_field("count", 0.0, Some(1.0), None);
        assert!(result.is_some());
        assert!(result.unwrap().message.contains(">="));
    }

    #[test]
    fn test_validate_field_max() {
        let result = validate_field("count", 100.0, None, Some(50.0));
        assert!(result.is_some());
        assert!(result.unwrap().message.contains("<="));
    }

    #[test]
    fn test_validate_field_ok() {
        let result = validate_field("count", 50.0, Some(1.0), Some(100.0));
        assert!(result.is_none());
    }
}
