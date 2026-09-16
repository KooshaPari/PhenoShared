//! Streaming support for OmniRoute Core
//!
//! Provides SSE (Server-Sent Events) streaming for chat completions.

use crate::error::Result;
use crate::http::AppState;
use crate::types::{ChatRequest, StreamingChunk};
use axum::{
    extract::State,
    response::{sse, IntoResponse, Response},
    Json,
};
use futures::StreamExt;
use tracing::info;

/// Streaming chat completions endpoint - POST /v1/chat/completions/stream
pub async fn chat_completions_stream(
    State(state): State<AppState>,
    Json(request): Json<ChatRequest>,
) -> Response {
    info!(model = %request.model, "Processing streaming chat completion request");

    let _provider = match state.router.get_provider_for_model(&request.model) {
        Ok(p) => p,
        Err(e) => return super::routes::AppError::NoProvider(e.to_string()).into_response(),
    };

    // Streaming implementation placeholder
    // Full streaming requires provider-specific handling
    super::routes::AppError::Provider(
        "Streaming not yet implemented - use non-streaming endpoint".to_string(),
    )
    .into_response()
}

/// Transform a provider stream into an SSE event stream
#[allow(dead_code)]
pub fn to_sse_stream<S>(stream: S) -> impl futures::Stream<Item = sse::Event> + Send + 'static
where
    S: futures::Stream<Item = Result<StreamingChunk>> + Send + 'static,
{
    stream.map(|result| match result {
        Ok(chunk) => {
            let data = serde_json::to_string(&chunk).unwrap_or_default();
            sse::Event::default()
                .event("chunk")
                .data(data)
        }
        Err(e) => {
            let error_data = serde_json::json!({
                "error": { "message": e.to_string() }
            });
            sse::Event::default()
                .event("error")
                .data(error_data.to_string())
        }
    })
}

/// SSE encoder for streaming responses
#[allow(dead_code)]
pub struct SseEncoder;

impl SseEncoder {
    /// Encode a streaming chunk as SSE data
    pub fn encode_chunk(chunk: &StreamingChunk) -> Result<String> {
        serde_json::to_string(chunk)
            .map_err(|e| crate::error::Error::Serialization(e))
    }

    /// Encode an error as SSE data
    pub fn encode_error(error: &str) -> String {
        serde_json::json!({
            "error": { "message": error }
        })
        .to_string()
    }

    /// Create the SSE event format
    pub fn format_event(event_type: &str, data: &str) -> String {
        format!("event: {}\ndata: {}\n\n", event_type, data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_error() {
        let error = SseEncoder::encode_error("Test error");
        assert!(error.contains("Test error"));
    }

    #[test]
    fn test_format_event() {
        let event = SseEncoder::format_event("chunk", r#"{"test": true}"#);
        assert!(event.contains("event: chunk"));
        assert!(event.contains("data: "));
    }
}
