//! Multi-turn chat session.

use super::client::AiClient;
use super::types::*;
use anyhow::Result;
use tokio::sync::mpsc;

/// A multi-turn chat session that maintains conversation history.
pub struct ChatSession {
    client: AiClient,
    pub(crate) messages: Vec<Message>,
    max_history: usize,
}

impl ChatSession {
    /// Create a new chat session with an optional system prompt.
    pub fn new(config: ProviderConfig, system_prompt: Option<&str>) -> Result<Self> {
        let client = AiClient::new(config)?;
        let mut messages = Vec::new();
        if let Some(sys) = system_prompt {
            messages.push(Message::system(sys));
        }
        Ok(Self { client, messages, max_history: 50 })
    }

    /// Send a user message and get the assistant's response, maintaining history.
    pub async fn send(&mut self, user_message: &str) -> Result<String> {
        self.messages.push(Message::user(user_message));

        if self.messages.len() > self.max_history {
            let system_msg = self.messages.first().cloned();
            let drain_count = self.messages.len() - self.max_history + 1;
            self.messages.drain(1..drain_count + 1);
            if let Some(sys) = system_msg {
                self.messages.insert(0, sys);
            }
        }

        let response = self.client.chat(&self.messages, None, None).await?;
        let content =
            response.choices.first().map(|c| c.message.content.clone()).unwrap_or_default();

        self.messages.push(Message::assistant(&content));
        Ok(content)
    }

    /// Get the current conversation history.
    pub fn history(&self) -> &[Message] {
        &self.messages
    }

    /// Send a user message with SSE streaming, maintaining conversation history.
    pub async fn send_stream(&mut self, user_message: &str) -> Result<mpsc::Receiver<String>> {
        self.messages.push(Message::user(user_message));

        if self.messages.len() > self.max_history {
            let system_msg = self.messages.first().cloned();
            let drain_count = self.messages.len() - self.max_history + 1;
            self.messages.drain(1..drain_count + 1);
            if let Some(sys) = system_msg {
                self.messages.insert(0, sys);
            }
        }

        self.client.stream_chat(&self.messages, None, None).await
    }

    /// Record an assistant response in the conversation history.
    pub fn record_response(&mut self, content: &str) {
        self.messages.push(Message::assistant(content));
    }

    /// Get a reference to the inner AI client.
    pub fn client(&self) -> &AiClient {
        &self.client
    }

    /// Clear conversation history (preserves system prompt).
    pub fn clear(&mut self) {
        let system_msg = self.messages.first().cloned();
        self.messages.clear();
        if let Some(sys) = system_msg {
            self.messages.push(sys);
        }
    }
}
