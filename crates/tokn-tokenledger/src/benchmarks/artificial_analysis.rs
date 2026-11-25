//! Artificial Analysis API client.
//!
//! Fetches benchmark data from: https://artificialanalysis.ai/api/v2/data/llms/models
//!
//! Requires API key (free tier: 1000 requests/day)

use crate::benchmarks::{BenchmarkData, BenchmarkSource, BenchmarkStore};
use reqwest::Client;
use thiserror::Error;
use tracing::{info, warn};

#[derive(Error, Debug)]
pub enum AaError {
    #[error("API error: {0}")]
    Api(String),
    #[error("Request error: {0}")]
    Request(#[from] reqwest::Error),
}

const AA_API_BASE: &str = "https://artificialanalysis.ai/api/v2/data/llms/models";

/// Artificial Analysis API response structures
mod response {
    use serde::Deserialize;

    #[derive(Debug, Deserialize)]
    pub struct ApiResponse {
        #[allow(dead_code)]
        pub status: u16,
        pub data: Vec<ModelEntry>,
    }

    #[derive(Debug, Deserialize)]
    pub struct ModelEntry {
        pub id: String,
        pub name: String,
        pub slug: String,
        pub model_creator: ModelCreator,
        pub evaluations: Option<Evaluations>,
        pub pricing: Option<Pricing>,
        #[serde(rename = "median_output_tokens_per_second")]
        pub speed_tps: Option<f64>,
        #[serde(rename = "median_time_to_first_token_seconds")]
        pub ttft_seconds: Option<f64>,
    }

    #[derive(Debug, Deserialize)]
    pub struct ModelCreator {
        pub id: String,
        pub name: String,
        pub slug: String,
    }

    #[derive(Debug, Deserialize)]
    pub struct Evaluations {
        #[serde(rename = "artificial_analysis_intelligence_index")]
        pub intelligence_index: Option<f64>,
        #[serde(rename = "artificial_analysis_coding_index")]
        pub coding_index: Option<f64>,
    }

    #[derive(Debug, Deserialize)]
    pub struct Pricing {
        #[serde(rename = "price_1m_input_tokens")]
        pub input_per_1m: Option<f64>,
        #[serde(rename = "price_1m_output_tokens")]
        pub output_per_1m: Option<f64>,
    }
}

/// Artificial Analysis API client
pub struct ArtificialAnalysisClient {
    http_client: Client,
    api_key: String,
}

impl ArtificialAnalysisClient {
    /// Create a new AA API client
    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            http_client: Client::new(),
            api_key: api_key.into(),
        }
    }

    /// Fetch all models from AA API
    pub async fn fetch_models(&self) -> Result<Vec<response::ModelEntry>, AaError> {
        info!("Fetching models from Artificial Analysis API");

        let response = self
            .http_client
            .get(AA_API_BASE)
            .header("x-api-key", &self.api_key)
            .send()
            .await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            warn!("AA API returned error: {} - {}", status, text);
            return Err(AaError::Api(format!("{} - {}", status, text)));
        }

        let data: response::ApiResponse = response.json().await?;

        info!(
            "Fetched {} models from Artificial Analysis",
            data.data.len()
        );
        Ok(data.data)
    }

    /// Convert AA model entry to unified BenchmarkData
    pub fn to_benchmark_data(entry: &response::ModelEntry) -> BenchmarkData {
        BenchmarkData {
            model_id: entry.slug.clone(),
            provider: Some(entry.model_creator.slug.clone()),

            // Quality
            intelligence_index: entry
                .evaluations
                .as_ref()
                .and_then(|e| e.intelligence_index),
            coding_index: entry.evaluations.as_ref().and_then(|e| e.coding_index),
            agentic_index: None, // Not in AA API

            // Performance
            speed_tps: entry.speed_tps,
            latency_ttft_ms: entry.ttft_seconds.map(|s| s * 1000.0),
            latency_e2e_ms: None, // Not directly available

            // Pricing
            price_input_per_1m: entry.pricing.as_ref().and_then(|p| p.input_per_1m),
            price_output_per_1m: entry.pricing.as_ref().and_then(|p| p.output_per_1m),
            price_cache_read_per_1m: None,
            price_cache_write_per_1m: None,

            // Context - not in this endpoint
            context_window_tokens: None,
            max_output_tokens: None,

            // Metadata
            source: BenchmarkSource::ArtificialAnalysis,
            confidence: 0.9, // High confidence for official API
            updated_at: chrono::Utc::now(),
        }
    }

    /// Fetch and store all benchmarks
    pub async fn fetch_and_store(&self, store: &BenchmarkStore) -> Result<usize, AaError> {
        let entries = self.fetch_models().await?;
        let count = entries.len();

        for entry in entries {
            let benchmark = Self::to_benchmark_data(&entry);
            store.merge(entry.slug, benchmark).await;
        }

        info!("Stored {} benchmarks from Artificial Analysis", count);
        Ok(count)
    }
}

/// Fetch AA benchmarks and return as Vec
pub async fn fetch_benchmarks(api_key: &str) -> Result<Vec<BenchmarkData>, AaError> {
    let client = ArtificialAnalysisClient::new(api_key);
    let entries = client.fetch_models().await?;

    Ok(entries
        .iter()
        .map(ArtificialAnalysisClient::to_benchmark_data)
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_to_benchmark_data() {
        let entry = response::ModelEntry {
            id: "test-id".to_string(),
            name: "Test Model".to_string(),
            slug: "test-model".to_string(),
            model_creator: response::ModelCreator {
                id: "openai".to_string(),
                name: "OpenAI".to_string(),
                slug: "openai".to_string(),
            },
            evaluations: Some(response::Evaluations {
                intelligence_index: Some(85.0),
                coding_index: Some(80.0),
            }),
            pricing: Some(response::Pricing {
                input_per_1m: Some(2.0),
                output_per_1m: Some(8.0),
            }),
            speed_tps: Some(100.0),
            ttft_seconds: Some(0.5),
        };

        let data = ArtificialAnalysisClient::to_benchmark_data(&entry);

        assert_eq!(data.model_id, "test-model");
        assert_eq!(data.provider, Some("openai".to_string()));
        assert_eq!(data.intelligence_index, Some(85.0));
        assert_eq!(data.speed_tps, Some(100.0));
        assert_eq!(data.price_input_per_1m, Some(2.0));
        assert_eq!(data.source, BenchmarkSource::ArtificialAnalysis);
    }
}
