use thiserror::Error;

/// Custom error types for the pareto-rs crate.
#[allow(clippy::enum_variant_names)]
#[derive(Error, Debug, Clone, PartialEq)]
pub enum Error {
    #[error("IO error: {0}")]
    IoError(String),

    #[error("Failed to parse data: {0}")]
    ParseError(String),

    #[error("Validation failed: {0}")]
    ValidationError(String),

    #[error("Resource not found: {0}")]
    NotFoundError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_io_error_display() {
        let err = Error::IoError("file not found".to_string());
        assert_eq!(err.to_string(), "IO error: file not found");
    }

    #[test]
    fn test_parse_error_display() {
        let err = Error::ParseError("invalid JSON".to_string());
        assert_eq!(err.to_string(), "Failed to parse data: invalid JSON");
    }

    #[test]
    fn test_validation_error_display() {
        let err = Error::ValidationError("missing field 'id'".to_string());
        assert_eq!(err.to_string(), "Validation failed: missing field 'id'");
    }

    #[test]
    fn test_not_found_error_display() {
        let err = Error::NotFoundError("user_id=123".to_string());
        assert_eq!(err.to_string(), "Resource not found: user_id=123");
    }

    #[test]
    fn test_config_error_display() {
        let err = Error::ConfigError("invalid API key".to_string());
        assert_eq!(err.to_string(), "Configuration error: invalid API key");
    }
}
