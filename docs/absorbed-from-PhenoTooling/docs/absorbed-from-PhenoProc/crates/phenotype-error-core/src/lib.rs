//! Error core types for Phenotype

use thiserror::Error;

/// Core error type for Phenotype
#[derive(Error, Debug, Clone)]
pub enum PhenotypeError {
    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),
    /// IO error
    #[error("IO error: {0}")]
    Io(String),
    /// Validation error
    #[error("Validation error: {0}")]
    Validation(String),
    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// API error type
#[derive(Error, Debug, Clone)]
pub enum ApiError {
    #[error("Not found: {resource} (id: {id})")]
    NotFound { resource: String, id: String },
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("API error: {0}")]
    Other(String),
}

impl ApiError {
    /// HTTP status code for this error
    pub fn status_code(&self) -> u16 {
        match self {
            ApiError::NotFound { .. } => 404,
            ApiError::Validation(_) => 422,
            ApiError::Other(_) => 500,
        }
    }
}

/// Config error type
#[derive(Error, Debug, Clone)]
#[error("Config error: {0}")]
pub struct ConfigError(pub String);

/// Domain error type
#[derive(Error, Debug, Clone)]
pub enum DomainError {
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("Domain error: {0}")]
    Other(String),
}

/// Error envelope type
#[derive(Debug, Clone)]
pub struct ErrorEnvelope {
    pub message: String,
    pub code: u32,
}

/// Repository error type
#[derive(Error, Debug, Clone)]
#[error("Repository error: {0}")]
pub struct RepositoryError(pub String);

/// Storage error type
#[derive(Error, Debug, Clone)]
#[error("Storage error: {0}")]
pub struct StorageError(pub String);

/// Result type alias
pub type Result<T> = std::result::Result<T, PhenotypeError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phenotype_error_display() {
        assert_eq!(
            PhenotypeError::Config("oops".into()).to_string(),
            "Configuration error: oops"
        );
        assert_eq!(
            PhenotypeError::Io("disk".into()).to_string(),
            "IO error: disk"
        );
        assert_eq!(
            PhenotypeError::Validation("bad".into()).to_string(),
            "Validation error: bad"
        );
        assert_eq!(
            PhenotypeError::Unknown("?".into()).to_string(),
            "Unknown error: ?"
        );
    }

    #[test]
    fn api_error_status_code() {
        assert_eq!(
            ApiError::NotFound {
                resource: "user".into(),
                id: "1".into()
            }
            .status_code(),
            404
        );
        assert_eq!(ApiError::Validation("x".into()).status_code(), 422);
        assert_eq!(ApiError::Other("x".into()).status_code(), 500);
    }

    #[test]
    fn api_error_display() {
        let e = ApiError::NotFound {
            resource: "user".into(),
            id: "42".into(),
        };
        assert_eq!(e.to_string(), "Not found: user (id: 42)");
        assert_eq!(ApiError::Validation("x".into()).to_string(), "Validation error: x");
        assert_eq!(ApiError::Other("x".into()).to_string(), "API error: x");
    }

    #[test]
    fn config_error_display() {
        let e = ConfigError("bad config".into());
        assert_eq!(e.to_string(), "Config error: bad config");
    }

    #[test]
    fn domain_error_display() {
        assert_eq!(
            DomainError::Validation("x".into()).to_string(),
            "validation failed: x"
        );
        assert_eq!(
            DomainError::Other("x".into()).to_string(),
            "Domain error: x"
        );
    }

    #[test]
    fn envelope_is_debug_and_clone() {
        let env = ErrorEnvelope {
            message: "msg".into(),
            code: 7,
        };
        let copy = env.clone();
        assert_eq!(copy.message, "msg");
        assert_eq!(copy.code, 7);
        let _ = format!("{:?}", env);
    }

    #[test]
    fn repository_error_display() {
        assert_eq!(
            RepositoryError("db down".into()).to_string(),
            "Repository error: db down"
        );
    }

    #[test]
    fn storage_error_display() {
        assert_eq!(
            StorageError("full".into()).to_string(),
            "Storage error: full"
        );
    }
}
