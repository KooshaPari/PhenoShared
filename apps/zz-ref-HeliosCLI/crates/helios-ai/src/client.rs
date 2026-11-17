//! OpenAI-compatible AI client.

use super::types::*;
use anyhow::{Context, Result};
use reqwest::Client;
use tokio::sync::mpsc;
use tracing::{debug, info};

/// AI client for making requests to OpenAI-compatible APIs.
pub struct AiClient {
    http: Client,
    config: ProviderConfig,
}

impl AiClient {
    /// Create a new AI client with the given configuration.
    pub fn new(config: ProviderConfig) -> Result<Self> {
        let http = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_secs))
            .build()
            .context("Failed to build HTTP client")?;
        Ok(Self { http, config })
    }

    /// Send a chat completion request and get a full response.
    pub async fn chat(
        &self,
        messages: &[Message],
        max_tokens: Option<u32>,
        temperature: Option<f32>,
    ) -> Result<ChatResponse> {
        let url = format!("{}/chat/completions", self.config.base_url);
        let body = ChatRequest {
            model: self.config.model.clone(),
            messages: messages.to_vec(),
            max_tokens,
            temperature,
            stream: false,
        };

        debug!(url = %url, model = %self.config.model, "Sending chat completion request");

        let mut req = self.http.post(&url).json(&body);
        if !self.config.api_key.is_empty() {
            req = req.bearer_auth(&self.config.api_key);
        }

        let resp = req.send().await.context("Failed to send request")?;
        let status = resp.status();

        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("API error {status}: {text}");
        }

        let response: ChatResponse = resp.json().await.context("Failed to parse response")?;
        info!(
            prompt_tokens = response.usage.as_ref().map(|u| u.prompt_tokens).unwrap_or(0),
            completion_tokens = response.usage.as_ref().map(|u| u.completion_tokens).unwrap_or(0),
            "Chat completion received"
        );
        Ok(response)
    }

    /// Simple convenience: send a single user message and get the response text.
    pub async fn complete(&self, prompt: &str) -> Result<String> {
        let messages = vec![Message::user(prompt)];
        let resp = self.chat(&messages, None, None).await?;
        resp.choices.first().map(|c| c.message.content.clone()).context("No response from AI")
    }

    /// Send a system prompt + user message.
    pub async fn complete_with_system(&self, system: &str, user: &str) -> Result<String> {
        let messages = vec![Message::system(system), Message::user(user)];
        let resp = self.chat(&messages, None, None).await?;
        resp.choices.first().map(|c| c.message.content.clone()).context("No response from AI")
    }

    /// Get the current configuration.
    pub fn config(&self) -> &ProviderConfig {
        &self.config
    }

    /// Send a chat completion request with SSE streaming.
    pub async fn stream_chat(
        &self,
        messages: &[Message],
        max_tokens: Option<u32>,
        temperature: Option<f32>,
    ) -> Result<mpsc::Receiver<String>> {
        let url = format!("{}/chat/completions", self.config.base_url);
        let body = ChatRequest {
            model: self.config.model.clone(),
            messages: messages.to_vec(),
            max_tokens,
            temperature,
            stream: true,
        };

        debug!(url = %url, model = %self.config.model, "Sending streaming chat request");

        let mut req = self.http.post(&url).json(&body);
        if !self.config.api_key.is_empty() {
            req = req.bearer_auth(&self.config.api_key);
        }

        let resp = req.send().await.context("Failed to send streaming request")?;
        let status = resp.status();

        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("API error {status}: {text}");
        }

        let (tx, rx) = mpsc::channel(256);

        tokio::spawn(async move {
            use super::sse::{parse_sse_line, SseEvent};
            use futures::StreamExt;
            let mut buffer = String::new();
            let mut byte_stream = resp.bytes_stream();

            while let Some(chunk_result) = byte_stream.next().await {
                let chunk = match chunk_result {
                    Ok(c) => c,
                    Err(e) => {
                        debug!(error = %e, "Stream read error");
                        break;
                    }
                };

                buffer.push_str(&String::from_utf8_lossy(&chunk));

                while let Some(newline_pos) = buffer.find('\n') {
                    let line = buffer[..newline_pos].trim().to_string();
                    buffer = buffer[newline_pos + 1..].to_string();

                    if line.is_empty() {
                        continue;
                    }

                    match parse_sse_line(&line) {
                        Some(SseEvent::Token(text)) => {
                            if tx.send(text).await.is_err() {
                                return;
                            }
                        }
                        Some(SseEvent::Done) => {
                            debug!("SSE stream done");
                            return;
                        }
                        None => {}
                    }
                }
            }
        });

        Ok(rx)
    }
}
