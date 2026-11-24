//! OpenAI-compatible AI client types.

use serde::{Deserialize, Serialize};

/// Configuration for an AI provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderConfig {
    /// API base URL
    pub base_url: String,
    /// API key (or empty for local providers)
    pub api_key: String,
    /// Default model to use
    pub model: String,
    /// Request timeout in seconds
    #[serde(default = "default_timeout")]
    pub timeout_secs: u64,
}

fn default_timeout() -> u64 {
    120
}

impl ProviderConfig {
    pub fn openai(api_key: impl Into<String>, model: impl Into<String>) -> Self {
        Self {
            base_url: "https://api.openai.com/v1".into(),
            api_key: api_key.into(),
            model: model.into(),
            timeout_secs: 120,
        }
    }

    pub fn ollama(model: impl Into<String>) -> Self {
        Self {
            base_url: "http://localhost:11434/v1".into(),
            api_key: "".into(),
            model: model.into(),
            timeout_secs: 300,
        }
    }

    pub fn lm_studio(model: impl Into<String>) -> Self {
        Self {
            base_url: "http://localhost:1234/v1".into(),
            api_key: "".into(),
            model: model.into(),
            timeout_secs: 300,
        }
    }
}

/// A message in a conversation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
}

impl Message {
    pub fn user(content: impl Into<String>) -> Self {
        Self { role: "user".into(), content: content.into() }
    }

    pub fn assistant(content: impl Into<String>) -> Self {
        Self { role: "assistant".into(), content: content.into() }
    }

    pub fn system(content: impl Into<String>) -> Self {
        Self { role: "system".into(), content: content.into() }
    }
}

/// Request body for the chat completions API.
#[derive(Debug, Serialize)]
pub struct ChatRequest {
    pub model: String,
    pub messages: Vec<Message>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    pub stream: bool,
}

/// Response from the chat completions API.
#[derive(Debug, Deserialize)]
pub struct ChatResponse {
    pub choices: Vec<Choice>,
    pub usage: Option<Usage>,
}

#[derive(Debug, Deserialize)]
pub struct Choice {
    pub message: Message,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Usage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

/// Streaming chunk from the chat completions API.
#[derive(Debug, Deserialize)]
pub struct StreamChunk {
    pub choices: Vec<StreamChoice>,
}

#[derive(Debug, Deserialize)]
pub struct StreamChoice {
    pub delta: Option<Delta>,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Delta {
    pub content: Option<String>,
    pub role: Option<String>,
}
