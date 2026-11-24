//! HTTP route handlers for OmniRoute Core
//!
//! Implements OpenAI-compatible API endpoints.

use crate::http::AppState;
use crate::types::{ChatRequest, EmbeddingRequest, ModelList};
use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use tracing::{error, info, instrument};

pub use super::streaming::chat_completions_stream;

/// Root endpoint - returns server info
pub async fn root() -> impl IntoResponse {
    Json(serde_json::json!({
        "name": "OmniRoute Core",
        "version": "0.1.0",
        "description": "Intelligent LLM request routing"
    }))
}

/// Health check endpoint
pub async fn health(State(state): State<AppState>) -> impl IntoResponse {
    let providers = state.router.provider_names();
    Json(serde_json::json!({
        "status": "healthy",
        "providers": providers,
        "provider_count": providers.len()
    }))
}

/// Chat completions endpoint - POST /v1/chat/completions
#[instrument(skip(state, request))]
pub async fn chat_completions(
    State(state): State<AppState>,
    Json(request): Json<ChatRequest>,
) -> Response {
    info!(model = %request.model, "Processing chat completion request");

    let provider = match state.router.get_provider_for_model(&request.model) {
        Ok(p) => p,
        Err(e) => return AppError::NoProvider(e.to_string()).into_response(),
    };

    match provider.chat_completions(request).await {
        Ok(response) => Json(response).into_response(),
        Err(e) => AppError::Provider(e.to_string()).into_response(),
    }
}

/// Embeddings endpoint - POST /v1/embeddings
#[instrument(skip(state, request))]
pub async fn embeddings(
    State(state): State<AppState>,
    Json(request): Json<EmbeddingRequest>,
) -> Response {
    info!(model = %request.model, "Processing embeddings request");

    let provider = match state.router.get_provider_for_model(&request.model) {
        Ok(p) => p,
        Err(e) => return AppError::NoProvider(e.to_string()).into_response(),
    };

    match provider.embeddings(request).await {
        Ok(response) => Json(response).into_response(),
        Err(e) => AppError::Provider(e.to_string()).into_response(),
    }
}

/// List models endpoint - GET /v1/models
#[instrument(skip(state))]
pub async fn list_models(State(state): State<AppState>) -> Response {
    info!("Listing all models");

    match state.router.list_all_models().await {
        Ok(all_models) => {
            let mut combined_data = Vec::new();
            for (_, model_list) in all_models {
                combined_data.extend(model_list.data);
            }

            let response = ModelList {
                object: "list".to_string(),
                data: combined_data,
            };

            Json(response).into_response()
        }
        Err(e) => AppError::Internal(e.to_string()).into_response(),
    }
}

/// Application error types
#[derive(Debug)]
pub enum AppError {
    /// No provider available for the requested model
    NoProvider(String),
    /// Provider returned an error
    Provider(String),
    /// Internal server error
    Internal(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NoProvider(model) => (
                StatusCode::NOT_FOUND,
                format!("No provider available for model: {}", model),
            ),
            AppError::Provider(msg) => (StatusCode::BAD_GATEWAY, msg.clone()),
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg.clone()),
        };

        error!(error = %message, "Request failed");

        let body = serde_json::json!({
            "error": {
                "message": message,
                "type": "invalid_request_error",
            }
        });

        (status, Json(body)).into_response()
    }
}
