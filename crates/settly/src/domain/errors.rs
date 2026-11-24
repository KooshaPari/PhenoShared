//! Domain errors.

/// Configuration errors.
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("Key not found: {0}")]
    KeyNotFound(String),

    #[error("Type mismatch for {key}: expected {expected}, got {actual}")]
    TypeMismatch { key: String, expected: String, actual: String },

    #[error("Validation failed: {validator}: {message}")]
    ValidationFailed { validator: String, message: String },

    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Source not available: {0}")]
    SourceNotAvailable(String),
}

impl serde::Serialize for ConfigError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}
