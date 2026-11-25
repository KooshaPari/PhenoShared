//! Provider implementations for OmniRoute Core

pub mod mock;
pub mod openai;
pub mod anthropic;

pub use mock::MockProvider;

use crate::error::Result;
use crate::types::{
    ChatRequest, ChatResponse, EmbeddingRequest, EmbeddingResponse, ModelList, StreamingChunk,
};
use std::pin::Pin;

/// Trait for LLM provider implementations
///
/// This trait defines the core interface that all LLM providers must implement.
/// Each provider can handle different models and has its own authentication
/// and API configuration.
///
/// Streaming support is provided via the [`StreamingProvider`] extension trait.
#[async_trait::async_trait]
pub trait LLMProvider: Send + Sync {
    /// Get the provider's unique identifier
    fn name(&self) -> &str;

    /// Check if this provider can handle the given model
    fn supports_model(&self, model: &str) -> bool;

    /// Get the list of models this provider supports
    async fn list_models(&self) -> Result<ModelList>;

    /// Send a chat completion request
    async fn chat_completions(&self, request: ChatRequest) -> Result<ChatResponse>;

    /// Generate embeddings for the given input
    async fn embeddings(&self, request: EmbeddingRequest) -> Result<EmbeddingResponse>;
}

/// Extension trait for providers that support streaming
///
/// This is a separate trait to maintain dyn compatibility in the main [`LLMProvider`] trait.
/// Providers that support streaming should also implement this trait.
#[async_trait::async_trait]
pub trait StreamingProvider: LLMProvider {
    /// Send a streaming chat completions request
    ///
    /// Returns a pinned boxed stream of chunks that can be processed incrementally.
    async fn chat_completions_stream(
        &self,
        request: ChatRequest,
    ) -> Result<Pin<Box<dyn futures::Stream<Item = Result<StreamingChunk>> + Send>>>;
}

/// Check if a provider supports streaming
#[allow(dead_code)]
pub fn supports_streaming<P: LLMProvider>(_provider: &P) -> bool {
    // This is a workaround since we can't use trait objects directly
    // In practice, we'd check at registration time or use Any
    false
}
