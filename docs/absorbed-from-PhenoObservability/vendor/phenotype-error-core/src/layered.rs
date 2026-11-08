use std::path::PathBuf;

use thiserror::Error;

use crate::code::ErrorCode;

/// Errors originating from the HTTP / transport boundary.
#[derive(Error, Debug)]
pub enum ApiError {
    #[error("bad request: {0}")]
    BadRequest(String),
    #[error("unauthorized: {0}")]
    Unauthorized(String),
    #[error("forbidden: {0}")]
    Forbidden(String),
    #[error("not found: {resource} {id}")]
    NotFound { resource: String, id: String },
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("rate limited")]
    RateLimited,
    #[error("timeout")]
    Timeout,
    #[error("internal: {0}")]
    Internal(String),
    #[error(transparent)]
    Domain(#[from] DomainError),
    #[error(transparent)]
    Repository(#[from] RepositoryError),
}

impl ApiError {
    /// HTTP status code for this error.
    pub fn status_code(&self) -> u16 {
        match self {
            Self::BadRequest(_) => 400,
            Self::Unauthorized(_) => 401,
            Self::Forbidden(_) => 403,
            Self::NotFound { .. } => 404,
            Self::Conflict(_) => 409,
            Self::RateLimited => 429,
            Self::Timeout => 504,
            Self::Internal(_) => 500,
            Self::Domain(DomainError::NotFound { .. }) => 404,
            Self::Domain(DomainError::Duplicate { .. }) => 409,
            Self::Domain(DomainError::NotPermitted(_)) => 403,
            Self::Domain(_) => 422,
            Self::Repository(RepositoryError::NotFound { .. }) => 404,
            Self::Repository(RepositoryError::Duplicate { .. }) => 409,
            Self::Repository(_) => 500,
        }
    }

    /// Stable wire error code for API clients.
    pub fn error_code(&self) -> ErrorCode {
        match self {
            Self::BadRequest(_) => ErrorCode::InvalidArgument,
            Self::Unauthorized(_) => ErrorCode::Unauthenticated,
            Self::Forbidden(_) => ErrorCode::PermissionDenied,
            Self::NotFound { .. } => ErrorCode::NotFound,
            Self::Conflict(_) => ErrorCode::AlreadyExists,
            Self::RateLimited => ErrorCode::ResourceExhausted,
            Self::Timeout => ErrorCode::Timeout,
            Self::Internal(_) => ErrorCode::InternalError,
            Self::Domain(DomainError::Validation(_)) => ErrorCode::ValidationError,
            Self::Domain(DomainError::NotFound { .. }) => ErrorCode::NotFound,
            Self::Domain(DomainError::Duplicate { .. }) => ErrorCode::AlreadyExists,
            Self::Domain(DomainError::NotPermitted(_)) => ErrorCode::PermissionDenied,
            Self::Domain(_) => ErrorCode::InvalidArgument,
            Self::Repository(RepositoryError::NotFound { .. }) => ErrorCode::NotFound,
            Self::Repository(RepositoryError::Duplicate { .. }) => ErrorCode::AlreadyExists,
            Self::Repository(_) => ErrorCode::InternalError,
        }
    }

    /// Whether the caller should retry.
    pub fn is_retryable(&self) -> bool {
        matches!(self, Self::RateLimited | Self::Timeout | Self::Internal(_))
    }
}

/// Errors from domain logic: validation, invariant violations, state issues.
#[derive(Error, Debug)]
pub enum DomainError {
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("invariant violated: {0}")]
    InvariantViolation(String),
    #[error("entity not found: {entity} {id}")]
    NotFound { entity: String, id: String },
    #[error("duplicate entity: {entity} {id}")]
    Duplicate { entity: String, id: String },
    #[error("invalid state transition: {from} -> {to}")]
    InvalidStateTransition { from: String, to: String },
    #[error("operation not permitted: {0}")]
    NotPermitted(String),
    #[error("policy evaluation failed: {0}")]
    PolicyEvaluation(String),
    #[error("{0}")]
    Other(String),
}

/// Errors from persistence adapters.
#[derive(Error, Debug)]
pub enum RepositoryError {
    #[error("record not found: {entity} {id}")]
    NotFound { entity: String, id: String },
    #[error("duplicate record: {entity} {id}")]
    Duplicate { entity: String, id: String },
    #[error("connection error: {0}")]
    Connection(String),
    #[error("query error: {0}")]
    Query(String),
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("sequence gap: expected {expected}, got {actual}")]
    SequenceGap { expected: i64, actual: i64 },
    #[error("integrity error: {0}")]
    Integrity(String),
    #[error(transparent)]
    Storage(#[from] StorageError),
}

impl From<serde_json::Error> for RepositoryError {
    fn from(err: serde_json::Error) -> Self {
        Self::Serialization(err.to_string())
    }
}

/// Errors from configuration loading, parsing, and validation.
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("file not found: {}", path.display())]
    FileNotFound { path: PathBuf },
    #[error("file read error: {}: {reason}", path.display())]
    FileRead { path: PathBuf, reason: String },
    #[error("parse error ({format}): {reason}")]
    Parse { format: String, reason: String },
    #[error("deserialization error: {0}")]
    Deserialize(String),
    #[error("unsupported format: {0}")]
    UnsupportedFormat(String),
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("missing required field: {0}")]
    MissingRequired(String),
    #[error("environment error: {0}")]
    Environment(String),
    #[error("{0}")]
    Other(String),
}

impl From<std::io::Error> for ConfigError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => Self::FileNotFound {
                path: PathBuf::from("<unknown>"),
            },
            _ => Self::Other(err.to_string()),
        }
    }
}

impl From<serde_json::Error> for ConfigError {
    fn from(err: serde_json::Error) -> Self {
        Self::Parse {
            format: "json".into(),
            reason: err.to_string(),
        }
    }
}

/// Low-level storage errors for files, network, and cache adapters.
#[derive(Error, Debug)]
pub enum StorageError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("not found: {0}")]
    NotFound(String),
    #[error("permission denied: {0}")]
    PermissionDenied(String),
    #[error("capacity exceeded: {0}")]
    CapacityExceeded(String),
    #[error("connection error: {0}")]
    Connection(String),
    #[error("{0}")]
    Other(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn api_error_status_codes() {
        assert_eq!(ApiError::BadRequest("x".into()).status_code(), 400);
        assert_eq!(ApiError::Unauthorized("x".into()).status_code(), 401);
        assert_eq!(ApiError::Forbidden("x".into()).status_code(), 403);
        assert_eq!(
            ApiError::NotFound {
                resource: "user".into(),
                id: "1".into()
            }
            .status_code(),
            404
        );
        assert_eq!(ApiError::Conflict("x".into()).status_code(), 409);
        assert_eq!(ApiError::RateLimited.status_code(), 429);
        assert_eq!(ApiError::Timeout.status_code(), 504);
        assert_eq!(ApiError::Internal("x".into()).status_code(), 500);
    }

    #[test]
    fn api_error_codes_are_stable_wire_codes() {
        assert_eq!(
            ApiError::BadRequest("x".into()).error_code(),
            ErrorCode::InvalidArgument
        );
        assert_eq!(
            ApiError::Unauthorized("x".into()).error_code(),
            ErrorCode::Unauthenticated
        );
        assert_eq!(
            ApiError::Forbidden("x".into()).error_code(),
            ErrorCode::PermissionDenied
        );
        assert_eq!(
            ApiError::RateLimited.error_code(),
            ErrorCode::ResourceExhausted
        );
    }

    #[test]
    fn api_error_retryable() {
        assert!(ApiError::RateLimited.is_retryable());
        assert!(ApiError::Timeout.is_retryable());
        assert!(ApiError::Internal("boom".into()).is_retryable());
        assert!(!ApiError::BadRequest("nope".into()).is_retryable());
    }

    #[test]
    fn domain_error_display() {
        let err = DomainError::Validation("name required".into());
        assert_eq!(err.to_string(), "validation failed: name required");
    }

    #[test]
    fn domain_error_state_transition() {
        let err = DomainError::InvalidStateTransition {
            from: "draft".into(),
            to: "published".into(),
        };
        assert!(err.to_string().contains("draft"));
        assert!(err.to_string().contains("published"));
    }

    #[test]
    fn repository_error_from_serde() {
        let json_err = serde_json::from_str::<String>("not json").unwrap_err();
        let repo_err = RepositoryError::from(json_err);
        assert!(matches!(repo_err, RepositoryError::Serialization(_)));
    }

    #[test]
    fn repository_error_sequence_gap() {
        let err = RepositoryError::SequenceGap {
            expected: 5,
            actual: 7,
        };
        assert!(err.to_string().contains("expected 5"));
        assert!(err.to_string().contains("got 7"));
    }

    #[test]
    fn config_error_from_io_not_found() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "gone");
        let cfg_err = ConfigError::from(io_err);
        assert!(matches!(cfg_err, ConfigError::FileNotFound { .. }));
    }

    #[test]
    fn config_error_from_io_other() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "nope");
        let cfg_err = ConfigError::from(io_err);
        assert!(matches!(cfg_err, ConfigError::Other(_)));
    }

    #[test]
    fn config_error_from_serde_json() {
        let json_err = serde_json::from_str::<String>("bad").unwrap_err();
        let cfg_err = ConfigError::from(json_err);
        assert!(matches!(cfg_err, ConfigError::Parse { format, .. } if format == "json"));
    }

    #[test]
    fn storage_error_from_io() {
        let io_err = std::io::Error::new(std::io::ErrorKind::BrokenPipe, "pipe");
        let store_err = StorageError::from(io_err);
        assert!(matches!(store_err, StorageError::Io(_)));
    }

    #[test]
    fn api_error_from_domain() {
        let domain_err = DomainError::Validation("bad input".into());
        let api_err = ApiError::from(domain_err);
        assert_eq!(api_err.status_code(), 422);
        assert_eq!(api_err.error_code(), ErrorCode::ValidationError);
        assert!(api_err.to_string().contains("bad input"));
    }

    #[test]
    fn api_error_from_repository() {
        let repo_err = RepositoryError::Connection("db down".into());
        let api_err = ApiError::from(repo_err);
        assert_eq!(api_err.status_code(), 500);
        assert_eq!(api_err.error_code(), ErrorCode::InternalError);
    }

    #[test]
    fn repository_error_from_storage() {
        let store_err = StorageError::NotFound("file.dat".into());
        let repo_err = RepositoryError::from(store_err);
        assert!(matches!(repo_err, RepositoryError::Storage(_)));
    }

    #[test]
    fn anyhow_interop() {
        let domain_err = DomainError::Validation("test".into());
        let anyhow_err: anyhow::Error = domain_err.into();
        assert!(anyhow_err.to_string().contains("validation failed: test"));

        let api_err = ApiError::Internal("crash".into());
        let anyhow_err: anyhow::Error = api_err.into();
        assert!(anyhow_err.to_string().contains("crash"));
    }
}
