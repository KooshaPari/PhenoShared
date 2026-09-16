//! Anthropic provider implementation
//!
//! Provider for Anthropic's Claude API.

use crate::error::{Error, Result};
use crate::providers::{LLMProvider, StreamingProvider};
use crate::types::{
    ChatRequest, ChatResponse, EmbeddingRequest, EmbeddingResponse, Message, Model, ModelList,
    Role, StreamingChunk, Usage,
};
use async_trait::async_trait;
use futures::Stream;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::pin::Pin;
use std::time::Duration;

/// Anthropic API provider
#[derive(Debug)]
pub struct AnthropicProvider {
    client: Client,
    api_key: String,
    api_base: String,
}

impl AnthropicProvider {
    /// Create a new Anthropic provider
    pub fn new(config: crate::types::ProviderConfig) -> Result<Self> {
        let api_key = config.api_key.ok_or_else(|| {
            Error::Configuration("Anthropic API key is required".to_string())
        })?;

        let client = Client::builder()
            .timeout(Duration::from_secs(60))
            .build()
            .map_err(|e| Error::Configuration(format!("Failed to create HTTP client: {}", e)))?;

        Ok(Self {
            client,
            api_key,
            api_base: config
                .api_base
                .unwrap_or_else(|| "https://api.anthropic.com/v1".to_string()),
        })
    }

    fn build_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert("x-api-key", self.api_key.parse().unwrap());
        headers.insert(
            "anthropic-version",
            "2023-06-01".parse().unwrap(),
        );
        headers.insert(
            reqwest::header::CONTENT_TYPE,
            "application/json".parse().unwrap(),
        );

        headers
    }

    /// Convert OmniRoute messages to Anthropic format
    fn convert_messages(&self, messages: Vec<Message>) -> Vec<AnthropicMessage> {
        messages
            .into_iter()
            .map(|m| AnthropicMessage {
                role: match m.role {
                    Role::System => "user".to_string(), // Anthropic uses system in separate field
                    Role::User => "user".to_string(),
                    Role::Assistant => "assistant".to_string(),
                    Role::Tool => "user".to_string(),
                },
                content: m.content,
            })
            .collect()
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct AnthropicMessage {
    role: String,
    content: String,
}

#[derive(Debug, Serialize)]
struct AnthropicChatRequest {
    model: String,
    messages: Vec<AnthropicMessage>,
    stream: bool,
    max_tokens: u32,
    system: Option<String>,
    temperature: Option<f32>,
    top_p: Option<f32>,
    stop_sequences: Option<Vec<String>>,
    metadata: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct AnthropicResponse {
    id: String,
    #[serde(rename = "type")]
    response_type: String,
    role: String,
    content: Vec<AnthropicContentBlock>,
    model: String,
    stop_reason: Option<String>,
    stop_sequence: Option<String>,
    usage: AnthropicUsage,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
struct AnthropicUsage {
    input_tokens: u32,
    output_tokens: u32,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
#[allow(dead_code)]
enum AnthropicContentBlock {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "tool_use")]
    ToolUse {
        id: String,
        name: String,
        input: serde_json::Value,
    },
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct AnthropicStreamEvent {
    #[serde(rename = "type")]
    event_type: String,
    index: Option<u32>,
    delta: Option<AnthropicDelta>,
    content_block: Option<AnthropicContentBlock>,
    usage: Option<AnthropicUsage>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct AnthropicDelta {
    #[serde(rename = "type")]
    delta_type: String,
    text: Option<String>,
    partial_json: Option<String>,
}

#[async_trait]
impl LLMProvider for AnthropicProvider {
    fn name(&self) -> &str {
        "anthropic"
    }

    fn supports_model(&self, model: &str) -> bool {
        model.starts_with("claude-")
            || model == "claude-opus-4-5"
            || model == "claude-sonnet-4-7"
    }

    async fn list_models(&self) -> Result<ModelList> {
        // Anthropic doesn't have a list models endpoint, so we return known models
        let models = vec![
            Model {
                id: "claude-opus-4-20250514".to_string(),
                object: "model".to_string(),
                created: 1700000000,
                owned_by: Some("anthropic".to_string()),
                display_name: Some("Claude Opus 4".to_string()),
            },
            Model {
                id: "claude-sonnet-4-20250514".to_string(),
                object: "model".to_string(),
                created: 1700000000,
                owned_by: Some("anthropic".to_string()),
                display_name: Some("Claude Sonnet 4".to_string()),
            },
            Model {
                id: "claude-3-5-haiku-20241022".to_string(),
                object: "model".to_string(),
                created: 1700000000,
                owned_by: Some("anthropic".to_string()),
                display_name: Some("Claude 3.5 Haiku".to_string()),
            },
        ];

        Ok(ModelList {
            object: "list".to_string(),
            data: models,
        })
    }

    async fn chat_completions(&self, request: ChatRequest) -> Result<ChatResponse> {
        let url = format!("{}/messages", self.api_base);

        // Extract system message
        let (system_messages, other_messages): (Vec<_>, Vec<_>) = request
            .messages
            .into_iter()
            .partition(|m| m.role == Role::System);

        let system = system_messages.first().map(|m| m.content.clone());

        let anthropic_request = AnthropicChatRequest {
            model: request.model.clone(),
            messages: self.convert_messages(other_messages),
            stream: false,
            max_tokens: request.max_tokens.unwrap_or(4096),
            system,
            temperature: request.temperature,
            top_p: request.top_p,
            stop_sequences: request.stop,
            metadata: None,
        };

        let response = self
            .client
            .post(&url)
            .headers(self.build_headers())
            .json(&anthropic_request)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await?;
            return Err(Error::Provider(format!(
                "Anthropic API error: {} - {}",
                status,
                error_text
            )));
        }

        let data: AnthropicResponse = response.json().await?;

        let content = data
            .content
            .iter()
            .filter_map(|c| match c {
                AnthropicContentBlock::Text { text } => Some(text.clone()),
                _ => None,
            })
            .collect::<Vec<_>>()
            .join("");

        Ok(ChatResponse {
            id: data.id,
            object: "chat.completion".to_string(),
            created: 0, // Anthropic doesn't provide this
            model: data.model,
            choices: vec![crate::types::Choice {
                index: 0,
                message: Message::assistant(content),
                finish_reason: data.stop_reason,
            }],
            usage: Some(Usage::new(data.usage.input_tokens, data.usage.output_tokens)),
            service_tier: None,
            system_fingerprint: None,
        })
    }

    async fn embeddings(&self, _request: EmbeddingRequest) -> Result<EmbeddingResponse> {
        // Anthropic doesn't support embeddings
        Err(Error::Provider(
            "Anthropic does not support embeddings API".to_string(),
        ))
    }
}

#[async_trait]
impl StreamingProvider for AnthropicProvider {
    async fn chat_completions_stream(
        &self,
        request: ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<StreamingChunk>> + Send>>> {
        use futures::StreamExt;

        let url = format!("{}/messages", self.api_base);

        let (system_messages, other_messages): (Vec<_>, Vec<_>) = request
            .messages
            .into_iter()
            .partition(|m| m.role == Role::System);

        let system = system_messages.first().map(|m| m.content.clone());

        let anthropic_request = AnthropicChatRequest {
            model: request.model.clone(),
            messages: self.convert_messages(other_messages),
            stream: true,
            max_tokens: request.max_tokens.unwrap_or(4096),
            system,
            temperature: request.temperature,
            top_p: request.top_p,
            stop_sequences: request.stop,
            metadata: None,
        };

        let response = self
            .client
            .post(&url)
            .headers(self.build_headers())
            .json(&anthropic_request)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await?;
            return Err(Error::Provider(format!(
                "Anthropic API error: {} - {}",
                status,
                error_text
            )));
        }

        let model = request.model.clone();
        let stream = response.bytes_stream().map(move |chunk_result| {
            let bytes = chunk_result.map_err(|e| Error::Streaming(e.to_string()))?;
            let text = String::from_utf8_lossy(&bytes);

            for line in text.lines() {
                if let Some(data) = line.strip_prefix("data: ") {
                    if data == "[DONE]" {
                        continue;
                    }
                    match serde_json::from_str::<AnthropicStreamEvent>(data) {
                        Ok(event) => {
                            if event.event_type == "content_block_delta" {
                                if let Some(delta) = event.delta {
                                    if delta.delta_type == "text_delta" {
                                        if let Some(text) = delta.text {
                                            return Ok(StreamingChunk {
                                                id: format!("anthropic-{}", uuid_simple()),
                                                object: "chat.completion.chunk"
                                                    .to_string(),
                                                created: 0,
                                                model: model.clone(),
                                                choices: vec![crate::types::StreamingChoice {
                                                    index: event.index.unwrap_or(0),
                                                    delta: crate::types::Delta {
                                                        content: text,
                                                        role: None,
                                                        tool_calls: None,
                                                    },
                                                    finish_reason: None,
                                                }],
                                            });
                                        }
                                    }
                                }
                            }
                        }
                        Err(e) => {
                            tracing::debug!("Failed to parse stream event: {}", e);
                        }
                    }
                }
            }

            Err(Error::Streaming("No valid chunk in response".to_string()))
        });

        Ok(Box::pin(stream))
    }
}

fn uuid_simple() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{:016x}", nanos)
}
