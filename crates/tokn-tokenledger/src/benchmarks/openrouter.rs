//! OpenRouter API client.
//!
//! Fetches model data from: https://openrouter.ai/api/v1/models
//!
//! Provides: pricing, context length, modalities, provider info

use crate::benchmarks::{BenchmarkData, BenchmarkSource, BenchmarkStore};
use reqwest::Client;
use thiserror::Error;
use tracing::{info, warn};

#[derive(Error, Debug)]
pub enum OrError {
    #[error("API error: {0}")]
    Api(String),
    #[error("Request error: {0}")]
    Request(#[from] reqwest::Error),
}

const OPENROUTER_API_BASE: &str = "https://openrouter.ai/api/v1/models";

/// OpenRouter API response structures
mod response {
    use serde::Deserialize;

    #[derive(Debug, Deserialize)]
    pub struct ApiResponse {
        pub data: Vec<ModelEntry>,
    }

    #[derive(Debug, Deserialize)]
    pub struct ModelEntry {
        pub id: String,
        pub name: String,
        pub description: Option<String>,
        pub pricing: Option<Pricing>,
        pub context_length: Option<u64>,
        pub max_completion_tokens: Option<u64>,
        pub architecture: Option<Architecture>,
    }

    #[derive(Debug, Deserialize)]
    pub struct Pricing {
        /// Price per 1M prompt tokens
        #[serde(rename = "prompt")]
        pub price_prompt: Option<String>,
        /// Price per 1M completion tokens
        #[serde(rename = "completion")]
        pub price_completion: Option<String>,
    }

    #[derive(Debug, Deserialize)]
    pub struct Architecture {
        pub modality: Option<String>,
        pub input_modalities: Option<Vec<String>>,
        pub output_modalities: Option<Vec<String>>,
    }
}

/// OpenRouter API client
pub struct OpenRouterClient {
    http_client: Client,
    api_key: String,
}

impl OpenRouterClient {
    /// Create a new OpenRouter API client
    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            http_client: Client::new(),
            api_key: api_key.into(),
        }
    }

    /// Fetch all models from OpenRouter API
    pub async fn fetch_models(&self) -> Result<Vec<response::ModelEntry>, OrError> {
        info!("Fetching models from OpenRouter API");

        let response = self
            .http_client
            .get(OPENROUTER_API_BASE)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .send()
            .await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            warn!("OpenRouter API returned error: {} - {}", status, text);
            return Err(OrError::Api(format!("{} - {}", status, text)));
        }

        let data: response::ApiResponse = response.json().await?;

        info!("Fetched {} models from OpenRouter", data.data.len());
        Ok(data.data)
    }

    /// Convert OR model entry to unified BenchmarkData
    /// Note: OpenRouter doesn't provide quality/speed benchmarks, only pricing
    pub fn to_benchmark_data(entry: &response::ModelEntry) -> BenchmarkData {
        // Parse pricing strings to f64 (they come as "$0.00" format)
        let parse_price = |s: &Option<String>| -> Option<f64> {
            s.as_ref().and_then(|p| {
                p.trim_start_matches('$')
                    .trim_end_matches(" / 1M tokens")
                    .parse::<f64>()
                    .ok()
            })
        };

        // Extract provider from model ID (e.g., "openai/gpt-4o" -> "openai")
        let provider = entry.id.split('/').next().map(String::from);

        BenchmarkData {
            model_id: entry.id.clone(),
            provider,

            // Quality - NOT provided by OpenRouter
            intelligence_index: None,
            coding_index: None,
            agentic_index: None,

            // Performance - NOT provided by OpenRouter
            speed_tps: None,
            latency_ttft_ms: None,
            latency_e2e_ms: None,

            // Pricing
            price_input_per_1m: parse_price(
                &entry.pricing.as_ref().and_then(|p| p.price_prompt.clone()),
            ),
            price_output_per_1m: parse_price(
                &entry
                    .pricing
                    .as_ref()
                    .and_then(|p| p.price_completion.clone()),
            ),
            price_cache_read_per_1m: None,
            price_cache_write_per_1m: None,

            // Context
            context_window_tokens: entry.context_length,
            max_output_tokens: entry.max_completion_tokens,

            // Metadata
            source: BenchmarkSource::OpenRouter,
            confidence: 0.8, // High confidence for official API
            updated_at: chrono::Utc::now(),
        }
    }

    /// Fetch and store all benchmarks
    pub async fn fetch_and_store(&self, store: &BenchmarkStore) -> Result<usize, OrError> {
        let entries = self.fetch_models().await?;
        let count = entries.len();

        for entry in entries {
            let benchmark = Self::to_benchmark_data(&entry);
            store.merge(entry.id.clone(), benchmark).await;
        }

        info!("Stored {} benchmarks from OpenRouter", count);
        Ok(count)
    }
}

/// Fetch OpenRouter benchmarks and return as Vec
pub async fn fetch_benchmarks(api_key: &str) -> Result<Vec<BenchmarkData>, OrError> {
    let client = OpenRouterClient::new(api_key);
    let entries = client.fetch_models().await?;

    Ok(entries
        .iter()
        .map(OpenRouterClient::to_benchmark_data)
        .collect())
}

/// Normalize model ID for matching across sources
pub fn normalize_model_id(id: &str) -> String {
    // Remove common prefixes/suffixes and lowercase
    let normalized = id.to_lowercase();

    // Handle common patterns
    // "openai/gpt-4o" -> "gpt-4o"
    // "anthropic/claude-3-5-sonnet" -> "claude-3-5-sonnet"
    // "google/gemini-2-5-flash" -> "gemini-2-5-flash"

    if let Some(slash_pos) = normalized.find('/') {
        normalized[slash_pos + 1..].to_string()
    } else {
        normalized
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_model_id() {
        assert_eq!(normalize_model_id("openai/gpt-4o"), "gpt-4o");
        assert_eq!(
            normalize_model_id("anthropic/claude-3-5-sonnet"),
            "claude-3-5-sonnet"
        );
        assert_eq!(normalize_model_id("GPT-4O"), "gpt-4o");
    }

    #[test]
    fn test_parse_price() {
        let entry = response::ModelEntry {
            id: "openai/gpt-4o".to_string(),
            name: "GPT-4o".to_string(),
            description: None,
            pricing: Some(response::Pricing {
                price_prompt: Some("$2.50 / 1M tokens".to_string()),
                price_completion: Some("$10.00 / 1M tokens".to_string()),
            }),
            context_length: Some(128000),
            max_completion_tokens: Some(16384),
            architecture: None,
        };

        let data = OpenRouterClient::to_benchmark_data(&entry);

        assert_eq!(data.model_id, "openai/gpt-4o");
        assert_eq!(data.provider, Some("openai".to_string()));
        assert_eq!(data.price_input_per_1m, Some(2.50));
        assert_eq!(data.price_output_per_1m, Some(10.00));
        assert_eq!(data.context_window_tokens, Some(128000));
        assert_eq!(data.source, BenchmarkSource::OpenRouter);
    }
}
