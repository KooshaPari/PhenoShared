//! API error type mapped to HTTP status codes.
//!
//! Traceability: WP15-T086

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
pub use phenotype_error_core::ApiError;
use phenotype_error_core::DomainError;
use serde_json::json;

/// Response wrapper for ApiError that implements axum's `IntoResponse`.
#[derive(Debug)]
pub struct ApiResponse(pub ApiError);

impl From<ApiError> for ApiResponse {
    fn from(err: ApiError) -> Self {
        ApiResponse(err)
    }
}

fn api_error_response(error: &ApiError) -> Response {
    let (status, message) = match error {
        ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
        ApiError::Unauthorized(msg) => (StatusCode::UNAUTHORIZED, msg.clone()),
        ApiError::Forbidden(msg) => (StatusCode::FORBIDDEN, msg.clone()),
        ApiError::NotFound { resource, id } => {
            (StatusCode::NOT_FOUND, format!("{resource} {id} not found"))
        }
        ApiError::Conflict(msg) => (StatusCode::CONFLICT, msg.clone()),
        ApiError::RateLimited => (StatusCode::TOO_MANY_REQUESTS, "rate limited".to_string()),
        ApiError::Timeout => (StatusCode::GATEWAY_TIMEOUT, "timeout".to_string()),
        ApiError::Internal(msg) => {
            tracing::error!("internal API error: {msg}");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "internal server error".to_string(),
            )
        }
        ApiError::Platform(msg) => {
            tracing::error!("platform error: {msg}");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "platform error".to_string(),
            )
        }
        ApiError::Domain(domain_err) => {
            tracing::error!("domain error: {domain_err}");
            (StatusCode::UNPROCESSABLE_ENTITY, domain_err.to_string())
        }
        ApiError::Repository(repo_err) => {
            tracing::error!("repository error: {repo_err}");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "data access error".to_string(),
            )
        }
    };
    (status, Json(json!({"error": message}))).into_response()
}

impl IntoResponse for ApiResponse {
    fn into_response(self) -> Response {
        api_error_response(&self.0)
    }
}

pub fn not_found(resource: impl Into<String>, id: impl Into<String>) -> ApiError {
    ApiError::NotFound {
        resource: resource.into(),
        id: id.into(),
    }
}

pub fn template_error(message: impl Into<String>) -> ApiError {
    ApiError::Internal(message.into())
}

pub fn domain_error(error: agileplus_domain::error::DomainError) -> ApiError {
    use agileplus_domain::error::DomainError as AgileDomainError;

    match error {
        AgileDomainError::NotFound(message) => not_found("entity", message),
        AgileDomainError::Conflict(message) => ApiError::Conflict(message),
        AgileDomainError::InvalidTransition { from, to, .. } => {
            ApiError::Domain(DomainError::InvalidStateTransition { from, to })
        }
        other => ApiError::Domain(DomainError::Other(other.to_string())),
    }
}
