use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::code::ErrorCode;
use crate::layered::{ApiError, DomainError, RepositoryError};

/// Wire-format error envelope suitable for JSON APIs, logs, and RPC payloads.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEnvelope {
    pub code: ErrorCode,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<Map<String, Value>>,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub fatal: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub retryable: Option<bool>,
}

impl ErrorEnvelope {
    /// Build a non-fatal envelope with no details.
    pub fn new(code: ErrorCode, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            details: None,
            fatal: false,
            retryable: None,
        }
    }

    /// Add structured detail data.
    pub fn with_details(mut self, details: Map<String, Value>) -> Self {
        self.details = Some(details);
        self
    }

    /// Mark whether callers should retry.
    pub fn with_retryable(mut self, retryable: bool) -> Self {
        self.retryable = Some(retryable);
        self
    }

    /// Mark whether the error is fatal to the current workflow.
    pub fn with_fatal(mut self, fatal: bool) -> Self {
        self.fatal = fatal;
        self
    }
}

impl From<&ApiError> for ErrorEnvelope {
    fn from(err: &ApiError) -> Self {
        let envelope = match err {
            ApiError::NotFound { resource, id } => {
                Self::new(err.error_code(), format!("{resource} {id} not found")).with_details(
                    Map::from_iter([
                        ("resource".to_string(), Value::String(resource.clone())),
                        ("id".to_string(), Value::String(id.clone())),
                    ]),
                )
            }
            ApiError::Domain(DomainError::NotFound { entity, id })
            | ApiError::Repository(RepositoryError::NotFound { entity, id }) => {
                Self::new(err.error_code(), format!("{entity} {id} not found")).with_details(
                    Map::from_iter([
                        ("resource".to_string(), Value::String(entity.clone())),
                        ("id".to_string(), Value::String(id.clone())),
                    ]),
                )
            }
            _ => Self::new(err.error_code(), err.to_string()),
        };

        envelope.with_retryable(err.is_retryable())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn error_envelope_from_api_error() {
        let api_err = ApiError::NotFound {
            resource: "project".into(),
            id: "42".into(),
        };
        let envelope = ErrorEnvelope::from(&api_err);
        assert_eq!(envelope.code, ErrorCode::NotFound);
        assert_eq!(envelope.retryable, Some(false));
        assert!(envelope.message.contains("project"));
    }

    #[test]
    fn error_envelope_serialization_matches_fixture() {
        let envelope = ErrorEnvelope::new(ErrorCode::ValidationError, "Invalid lane name")
            .with_details(json!({"field": "lane.name"}).as_object().unwrap().clone())
            .with_retryable(false);
        let fixture = include_str!("../../../contracts/errors/fixtures/validation-error.json");
        let fixture_json: Value = serde_json::from_str(fixture).unwrap();
        let envelope_json = serde_json::to_value(envelope).unwrap();
        assert_eq!(envelope_json, fixture_json);
    }

    #[test]
    fn error_envelope_from_not_found_api_error_matches_fixture() {
        let api_err = ApiError::NotFound {
            resource: "project".into(),
            id: "42".into(),
        };
        let envelope = ErrorEnvelope::from(&api_err);
        let fixture = include_str!("../../../contracts/errors/fixtures/not-found.json");
        let fixture_json: Value = serde_json::from_str(fixture).unwrap();
        let envelope_json = serde_json::to_value(envelope).unwrap();
        assert_eq!(envelope_json, fixture_json);
    }
}
