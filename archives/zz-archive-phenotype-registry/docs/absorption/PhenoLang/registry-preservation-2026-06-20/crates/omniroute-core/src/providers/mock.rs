//! Mock provider implementation for testing
//!
//! This module provides a mock LLM provider that returns predefined responses.
//! Useful for testing, development, and prototyping without requiring API keys.

use crate::error::{Error, Result};
use crate::providers::{LLMProvider, StreamingProvider};
use crate::types::{
    ChatRequest, ChatResponse, Choice, Delta, Embedding, EmbeddingInput, EmbeddingRequest,
    EmbeddingResponse, Message, Model, ModelList, StreamingChunk, StreamingChoice, Usage,
};
use async_trait::async_trait;
use futures::Stream;
use std::pin::Pin;
use tokio::time::{sleep, Duration};

/// Configuration for the mock provider
#[derive(Debug, Clone)]
pub struct MockConfig {
    /// Simulated response delay in milliseconds
    pub delay_ms: u64,
    /// Whether to simulate streaming
    pub stream_delay_ms: u64,
    /// Number of chunks to generate for streaming
    pub stream_chunks: usize,
    /// Whether to return errors (for testing error handling)
    pub should_error: bool,
    /// Error message if should_error is true
    pub error_message: String,
}

impl Default for MockConfig {
    fn default() -> Self {
        Self {
            delay_ms: 100,
            stream_delay_ms: 50,
            stream_chunks: 5,
            should_error: false,
            error_message: "Mock error".to_string(),
        }
    }
}

impl MockConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_delay(mut self, ms: u64) -> Self {
        self.delay_ms = ms;
        self
    }

    pub fn with_stream_config(mut self, delay_ms: u64, chunks: usize) -> Self {
        self.stream_delay_ms = delay_ms;
        self.stream_chunks = chunks;
        self
    }

    pub fn with_error(mut self, message: impl Into<String>) -> Self {
        self.should_error = true;
        self.error_message = message.into();
        self
    }
}

/// Mock provider for testing
pub struct MockProvider {
    config: MockConfig,
    supported_models: Vec<String>,
}

impl MockProvider {
    /// Create a new mock provider with default configuration
    pub fn new() -> Self {
        Self {
            config: MockConfig::new(),
            supported_models: vec![
                "mock-gpt-4".to_string(),
                "mock-gpt-3.5-turbo".to_string(),
                "mock-claude-3".to_string(),
                "mock-embedding-model".to_string(),
            ],
        }
    }

    /// Create a new mock provider with custom configuration
    pub fn with_config(config: MockConfig) -> Self {
        Self {
            config,
            supported_models: vec![
                "mock-gpt-4".to_string(),
                "mock-gpt-3.5-turbo".to_string(),
                "mock-claude-3".to_string(),
                "mock-embedding-model".to_string(),
            ],
        }
    }

    /// Add additional supported models
    pub fn with_models(mut self, models: Vec<String>) -> Self {
        self.supported_models.extend(models);
        self
    }

    fn generate_response_text(&self, request: &ChatRequest) -> String {
        let last_message = request
            .messages
            .iter()
            .rev()
            .find(|m| m.role == crate::types::Role::User);

        match last_message {
            Some(msg) => format!(
                "Mock response to: {} (model: {})",
                msg.content,
                request.model
            ),
            None => format!("Mock response from {}", request.model),
        }
    }

    fn generate_embedding(&self, input: &str) -> Vec<f32> {
        (0..128)
            .map(|i| ((input.len().saturating_mul(i)) % 100) as f32 / 100.0)
            .collect()
    }

    fn stream_chunks_for_text(&self, text: &str) -> usize {
        let base_chunks = self.config.stream_chunks;
        if text.len() < 50 {
            2
        } else if text.len() < 200 {
            4
        } else {
            base_chunks
        }
    }
}

impl Default for MockProvider {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl LLMProvider for MockProvider {
    fn name(&self) -> &str {
        "mock"
    }

    fn supports_model(&self, model: &str) -> bool {
        self.supported_models.iter().any(|m| m == model)
    }

    async fn list_models(&self) -> Result<ModelList> {
        sleep(Duration::from_millis(self.config.delay_ms)).await;

        let models: Vec<Model> = self
            .supported_models
            .iter()
            .enumerate()
            .map(|(i, name)| {
                Model {
                    id: name.clone(),
                    object: "model".to_string(),
                    created: 1000 + i as u64,
                    owned_by: Some("mock-provider".to_string()),
                    display_name: Some(name.replace("mock-", "Mock ")),
                }
            })
            .collect();

        Ok(ModelList {
            object: "list".to_string(),
            data: models,
        })
    }

    async fn chat_completions(&self, request: ChatRequest) -> Result<ChatResponse> {
        sleep(Duration::from_millis(self.config.delay_ms)).await;

        if self.config.should_error {
            return Err(Error::Provider(self.config.error_message.clone()));
        }

        let response_text = self.generate_response_text(&request);

        Ok(ChatResponse {
            id: format!("mock-{}", uuid_simple()),
            object: "chat.completion".to_string(),
            created: current_timestamp(),
            model: request.model.clone(),
            choices: vec![Choice {
                index: 0,
                message: Message::assistant(response_text),
                finish_reason: Some("stop".to_string()),
            }],
            usage: Some(Usage {
                prompt_tokens: 10,
                completion_tokens: 20,
                total_tokens: 30,
            }),
            service_tier: None,
            system_fingerprint: None,
        })
    }

    async fn embeddings(&self, request: EmbeddingRequest) -> Result<EmbeddingResponse> {
        sleep(Duration::from_millis(self.config.delay_ms)).await;

        let inputs = match &request.input {
            EmbeddingInput::String(s) => vec![s.clone()],
            EmbeddingInput::Strings(v) => v.clone(),
        };

        let embeddings: Vec<Embedding> = inputs
            .iter()
            .enumerate()
            .map(|(i, input)| Embedding {
                object: "embedding".to_string(),
                embedding: self.generate_embedding(input),
                index: i as u32,
            })
            .collect();

        let total_tokens = inputs.iter().map(|s| s.len() as u32).sum();

        Ok(EmbeddingResponse {
            object: "list".to_string(),
            data: embeddings,
            model: request.model.clone(),
            usage: Usage {
                prompt_tokens: total_tokens,
                completion_tokens: 0,
                total_tokens,
            },
        })
    }
}

#[async_trait]
impl StreamingProvider for MockProvider {
    async fn chat_completions_stream(
        &self,
        request: ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<StreamingChunk>> + Send>>> {
        if self.config.should_error {
            return Err(Error::Provider(self.config.error_message.clone()));
        }

        let response_text = self.generate_response_text(&request);
        let chunk_count = self.stream_chunks_for_text(&response_text);
        let model = request.model.clone();
        let stream_delay = self.config.stream_delay_ms;

        let stream = async_stream::stream! {
            for i in 0..chunk_count {
                let chunk_text = if i == chunk_count - 1 {
                    &response_text
                } else {
                    &response_text[..(response_text.len() / chunk_count * (i + 1)).min(response_text.len())]
                };

                yield Ok(StreamingChunk {
                    id: format!("mock-{}", uuid_simple()),
                    object: "chat.completion.chunk".to_string(),
                    created: current_timestamp(),
                    model: model.clone(),
                    choices: vec![StreamingChoice {
                        index: 0,
                        delta: Delta {
                            content: chunk_text.to_string(),
                            role: None,
                            tool_calls: None,
                        },
                        finish_reason: if i == chunk_count - 1 {
                            Some("stop".to_string())
                        } else {
                            None
                        },
                    }],
                });

                if i < chunk_count - 1 {
                    sleep(Duration::from_millis(stream_delay)).await;
                }
            }
        };

        Ok(Box::pin(stream))
    }
}

fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn uuid_simple() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{:016x}", nanos)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_provider_chat() {
        let provider = MockProvider::new();
        let request = ChatRequest {
            model: "mock-gpt-4".to_string(),
            messages: vec![Message::user("Hello!")],
            ..Default::default()
        };

        let response = provider.chat_completions(request).await.unwrap();
        assert!(!response.choices.is_empty());
        assert!(response.choices[0].message.content.contains("Hello"));
    }

    #[tokio::test]
    async fn test_mock_provider_supports_model() {
        let provider = MockProvider::new();
        assert!(provider.supports_model("mock-gpt-4"));
        assert!(!provider.supports_model("unknown-model"));
    }

    #[tokio::test]
    async fn test_mock_provider_stream() {
        let provider = MockProvider::with_config(MockConfig::default());
        let request = ChatRequest {
            model: "mock-gpt-4".to_string(),
            messages: vec![Message::user("Test streaming")],
            stream: true,
            ..Default::default()
        };

        let stream = provider.chat_completions_stream(request).await.unwrap();
        use futures::StreamExt;
        let chunks: Vec<_> = stream.take(10).collect().await;
        assert!(!chunks.is_empty());
    }

    #[tokio::test]
    async fn test_mock_provider_embeddings() {
        let provider = MockProvider::new();
        let request = EmbeddingRequest {
            model: "mock-embedding-model".to_string(),
            input: EmbeddingInput::String("Hello world".to_string()),
            encoding_format: None,
            dimensions: None,
            user: None,
        };

        let response = provider.embeddings(request).await.unwrap();
        assert!(!response.data.is_empty());
        assert_eq!(response.data[0].embedding.len(), 128);
    }

    #[tokio::test]
    async fn test_mock_provider_list_models() {
        let provider = MockProvider::new();
        let list = provider.list_models().await.unwrap();
        assert!(!list.data.is_empty());
    }
}
