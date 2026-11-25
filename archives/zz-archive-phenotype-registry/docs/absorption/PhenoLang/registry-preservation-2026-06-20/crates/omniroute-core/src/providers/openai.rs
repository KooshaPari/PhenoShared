//! OpenAI provider implementation
//!
//! Provider for OpenAI's API including GPT-4, GPT-3.5 Turbo, and embeddings.

use crate::error::{Error, Result};
use crate::providers::{LLMProvider, StreamingProvider};
use crate::types::{
    ChatRequest, ChatResponse, EmbeddingRequest, EmbeddingResponse, Model, ModelList,
    StreamingChunk,
};
use async_trait::async_trait;
use futures::Stream;
use reqwest::Client;
use serde_json::json;
use std::pin::Pin;
use std::time::Duration;

/// OpenAI API provider
#[derive(Debug)]
pub struct OpenAIProvider {
    client: Client,
    api_key: String,
    api_base: String,
    organization: Option<String>,
}

impl OpenAIProvider {
    /// Create a new OpenAI provider
    pub fn new(config: crate::types::ProviderConfig) -> Result<Self> {
        let api_key = config.api_key.ok_or_else(|| {
            Error::Configuration("OpenAI API key is required".to_string())
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
                .unwrap_or_else(|| "https://api.openai.com/v1".to_string()),
            organization: config.organization,
        })
    }

    fn build_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::AUTHORIZATION,
            format!("Bearer {}", self.api_key).parse().unwrap(),
        );
        headers.insert(
            reqwest::header::CONTENT_TYPE,
            "application/json".parse().unwrap(),
        );

        if let Some(ref org) = self.organization {
            headers.insert("OpenAI-Organization", org.parse().unwrap());
        }

        headers
    }

    async fn chat_completions_impl(
        &self,
        request: ChatRequest,
        stream: bool,
    ) -> Result<reqwest::Response> {
        let url = format!("{}/chat/completions", self.api_base);

        let mut body = serde_json::to_value(&request)?;
        body["stream"] = serde_json::Value::Bool(stream);

        let response = self
            .client
            .post(&url)
            .headers(self.build_headers())
            .json(&body)
            .send()
            .await?;

        Ok(response)
    }
}

#[async_trait]
impl LLMProvider for OpenAIProvider {
    fn name(&self) -> &str {
        "openai"
    }

    fn supports_model(&self, model: &str) -> bool {
        model.starts_with("gpt-")
            || model.starts_with("o1-")
            || model.starts_with("o3-")
            || model == "chatgpt-4o-latest"
            || model == "gpt-4o-realtime-preview"
    }

    async fn list_models(&self) -> Result<ModelList> {
        let url = format!("{}/models", self.api_base);

        let response = self
            .client
            .get(&url)
            .headers(self.build_headers())
            .send()
            .await?;

        let data: serde_json::Value = response.json().await?;

        let models: Vec<Model> = data["data"]
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .filter_map(|m| {
                let id = m["id"].as_str()?.to_string();
                if self.supports_model(&id) {
                    Some(Model {
                        id,
                        object: "model".to_string(),
                        created: m["created"].as_u64().unwrap_or(0),
                        owned_by: m["owned_by"].as_str().map(String::from),
                        display_name: None,
                    })
                } else {
                    None
                }
            })
            .collect();

        Ok(ModelList {
            object: "list".to_string(),
            data: models,
        })
    }

    async fn chat_completions(&self, request: ChatRequest) -> Result<ChatResponse> {
        let response = self.chat_completions_impl(request, false).await?;

        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await?;
            return Err(Error::Provider(format!(
                "OpenAI API error: {} - {}",
                status,
                error_text
            )));
        }

        let data: serde_json::Value = response.json().await?;
        let response = serde_json::from_value(data)?;

        Ok(response)
    }

    async fn embeddings(&self, request: EmbeddingRequest) -> Result<EmbeddingResponse> {
        let url = format!("{}/embeddings", self.api_base);

        let body = json!({
            "model": request.model,
            "input": request.input,
            "encoding_format": request.encoding_format.unwrap_or_else(|| "float".to_string()),
            "dimensions": request.dimensions,
            "user": request.user,
        });

        let response = self
            .client
            .post(&url)
            .headers(self.build_headers())
            .json(&body)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await?;
            return Err(Error::Provider(format!(
                "OpenAI API error: {} - {}",
                status,
                error_text
            )));
        }

        let data: serde_json::Value = response.json().await?;
        let response = serde_json::from_value(data)?;

        Ok(response)
    }
}

#[async_trait]
impl StreamingProvider for OpenAIProvider {
    async fn chat_completions_stream(
        &self,
        request: ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<StreamingChunk>> + Send>>> {
        use futures::StreamExt;

        let response = self.chat_completions_impl(request, true).await?;

        let status = response.status();
        if !status.is_success() {
            let error_text = response.text().await?;
            return Err(Error::Provider(format!(
                "OpenAI API error: {} - {}",
                status,
                error_text
            )));
        }

        let stream = response.bytes_stream().map(|chunk_result| {
            let bytes = chunk_result.map_err(|e| Error::Streaming(e.to_string()))?;
            let text = String::from_utf8_lossy(&bytes);

            // Parse SSE lines
            for line in text.lines() {
                if line.starts_with("data: ") {
                    let data = &line[6..];
                    if data == "[DONE]" {
                        continue;
                    }
                    match serde_json::from_str::<StreamingChunk>(data) {
                        Ok(chunk) => return Ok(chunk),
                        Err(e) => {
                            tracing::debug!("Failed to parse streaming chunk: {}", e);
                        }
                    }
                }
            }

            Err(Error::Streaming("No valid chunk in response".to_string()))
        });

        Ok(Box::pin(stream))
    }
}
