//! Unified benchmark store and data structures.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Source of benchmark data
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum BenchmarkSource {
    /// Artificial Analysis API
    ArtificialAnalysis,
    /// OpenRouter API
    OpenRouter,
    /// Manual override from config
    ManualOverride,
    /// Web scraping (future)
    WebScrape,
    /// Fallback/hardcoded values
    #[default]
    Fallback,
}

/// Unified benchmark data for a model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkData {
    /// Unique model identifier (canonical)
    pub model_id: String,

    /// Provider (if known)
    pub provider: Option<String>,

    // ===== QUALITY =====
    /// Artificial Analysis Intelligence Index (0-100+)
    pub intelligence_index: Option<f64>,
    /// Coding capability score
    pub coding_index: Option<f64>,
    /// Agentic capability score
    pub agentic_index: Option<f64>,

    // ===== PERFORMANCE =====
    /// Output tokens per second
    pub speed_tps: Option<f64>,
    /// Time to first token (ms)
    pub latency_ttft_ms: Option<f64>,
    /// End-to-end latency for 500 tokens (ms)
    pub latency_e2e_ms: Option<f64>,

    // ===== PRICING =====
    /// Input price per 1M tokens (USD)
    pub price_input_per_1m: Option<f64>,
    /// Output price per 1M tokens (USD)
    pub price_output_per_1m: Option<f64>,
    /// Cache read price per 1M tokens (USD)
    pub price_cache_read_per_1m: Option<f64>,
    /// Cache write price per 1M tokens (USD)
    pub price_cache_write_per_1m: Option<f64>,

    // ===== CONTEXT =====
    /// Maximum context window (tokens)
    pub context_window_tokens: Option<u64>,
    /// Maximum output tokens
    pub max_output_tokens: Option<u64>,

    // ===== METADATA =====
    /// Data source
    pub source: BenchmarkSource,
    /// Confidence score (0.0-1.0)
    pub confidence: f64,
    /// When this data was last updated
    pub updated_at: DateTime<Utc>,
}

impl Default for BenchmarkData {
    fn default() -> Self {
        Self {
            model_id: String::new(),
            provider: None,
            intelligence_index: None,
            coding_index: None,
            agentic_index: None,
            speed_tps: None,
            latency_ttft_ms: None,
            latency_e2e_ms: None,
            price_input_per_1m: None,
            price_output_per_1m: None,
            price_cache_read_per_1m: None,
            price_cache_write_per_1m: None,
            context_window_tokens: None,
            max_output_tokens: None,
            source: BenchmarkSource::Fallback,
            confidence: 0.0,
            updated_at: Utc::now(),
        }
    }
}

/// Priority resolution for benchmark sources
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SourcePriority {
    /// Highest priority - manual overrides
    Manual = 0,
    /// API sources
    Api = 1,
    /// Web scraping
    Scrape = 2,
    /// Fallback values
    Fallback = 3,
}

impl BenchmarkSource {
    pub fn priority(&self) -> SourcePriority {
        match self {
            BenchmarkSource::ManualOverride => SourcePriority::Manual,
            BenchmarkSource::ArtificialAnalysis | BenchmarkSource::OpenRouter => {
                SourcePriority::Api
            }
            BenchmarkSource::WebScrape => SourcePriority::Scrape,
            BenchmarkSource::Fallback => SourcePriority::Fallback,
        }
    }
}

/// In-memory benchmark store with TTL caching
pub struct BenchmarkStore {
    data: Arc<RwLock<HashMap<String, BenchmarkData>>>,
    ttl_seconds: u64,
}

impl BenchmarkStore {
    pub fn new(ttl_seconds: u64) -> Self {
        Self {
            data: Arc::new(RwLock::new(HashMap::new())),
            ttl_seconds,
        }
    }

    /// Get benchmark data for a model
    pub async fn get(&self, model_id: &str) -> Option<BenchmarkData> {
        let data = self.data.read().await;
        data.get(model_id).cloned()
    }

    /// Get all benchmark data
    pub async fn get_all(&self) -> Vec<BenchmarkData> {
        let data = self.data.read().await;
        data.values().cloned().collect()
    }

    /// Set benchmark data for a model
    pub async fn set(&self, model_id: String, benchmark: BenchmarkData) {
        let mut data = self.data.write().await;
        data.insert(model_id, benchmark);
    }

    /// Merge benchmark data with priority resolution
    pub async fn merge(&self, model_id: String, new_data: BenchmarkData) {
        let mut data = self.data.write().await;

        if let Some(existing) = data.get(&model_id) {
            // Resolve conflicts based on priority
            let merged = if new_data.source.priority() < existing.source.priority() {
                // New source has higher priority
                new_data
            } else {
                // Keep existing, merge non-None fields
                self.merge_benchmarks(existing, &new_data)
            };
            data.insert(model_id, merged);
        } else {
            data.insert(model_id, new_data);
        }
    }

    fn merge_benchmarks(&self, existing: &BenchmarkData, new: &BenchmarkData) -> BenchmarkData {
        // Take the higher confidence data for each field
        BenchmarkData {
            model_id: new.model_id.clone(),
            provider: new.provider.clone().or_else(|| existing.provider.clone()),

            intelligence_index: Self::merge_field(
                existing.intelligence_index,
                new.intelligence_index,
                new.confidence,
            ),
            coding_index: Self::merge_field(
                existing.coding_index,
                new.coding_index,
                new.confidence,
            ),
            agentic_index: Self::merge_field(
                existing.agentic_index,
                new.agentic_index,
                new.confidence,
            ),

            speed_tps: Self::merge_field(existing.speed_tps, new.speed_tps, new.confidence),
            latency_ttft_ms: Self::merge_field(
                existing.latency_ttft_ms,
                new.latency_ttft_ms,
                new.confidence,
            ),
            latency_e2e_ms: Self::merge_field(
                existing.latency_e2e_ms,
                new.latency_e2e_ms,
                new.confidence,
            ),

            price_input_per_1m: new.price_input_per_1m.or(existing.price_input_per_1m),
            price_output_per_1m: new.price_output_per_1m.or(existing.price_output_per_1m),
            price_cache_read_per_1m: new
                .price_cache_read_per_1m
                .or(existing.price_cache_read_per_1m),
            price_cache_write_per_1m: new
                .price_cache_write_per_1m
                .or(existing.price_cache_write_per_1m),

            context_window_tokens: new.context_window_tokens.or(existing.context_window_tokens),
            max_output_tokens: new.max_output_tokens.or(existing.max_output_tokens),

            source: if new.source.priority() < existing.source.priority() {
                new.source
            } else {
                existing.source
            },
            confidence: new.confidence.max(existing.confidence),
            updated_at: if new.source.priority() < existing.source.priority() {
                new.updated_at
            } else {
                existing.updated_at
            },
        }
    }

    fn merge_field(existing: Option<f64>, new: Option<f64>, new_confidence: f64) -> Option<f64> {
        match (existing, new) {
            (Some(_e), Some(n)) if new_confidence > 0.5 => Some(n),
            (Some(e), Some(_)) => Some(e),
            (Some(e), None) => Some(e),
            (None, Some(n)) => Some(n),
            _ => None,
        }
    }

    /// Clear expired entries
    pub async fn clear_expired(&self) {
        let now = Utc::now().timestamp();
        let mut data = self.data.write().await;
        data.retain(|_, v| {
            let age = now - v.updated_at.timestamp();
            age < self.ttl_seconds as i64
        });
    }
}

impl Default for BenchmarkStore {
    fn default() -> Self {
        Self::new(3600) // 1 hour default TTL
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_store_get_set() {
        let store = BenchmarkStore::new(3600);

        let data = BenchmarkData {
            model_id: "gpt-4o".to_string(),
            intelligence_index: Some(85.0),
            source: BenchmarkSource::ArtificialAnalysis,
            confidence: 0.9,
            ..Default::default()
        };

        store.set("gpt-4o".to_string(), data.clone()).await;

        let retrieved = store.get("gpt-4o").await;
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().intelligence_index, Some(85.0));
    }

    #[tokio::test]
    async fn test_priority_merge() {
        let store = BenchmarkStore::new(3600);

        // Low priority data
        let low_priority = BenchmarkData {
            model_id: "gpt-4o".to_string(),
            intelligence_index: Some(80.0),
            source: BenchmarkSource::Fallback,
            confidence: 0.3,
            ..Default::default()
        };

        // High priority data
        let high_priority = BenchmarkData {
            model_id: "gpt-4o".to_string(),
            intelligence_index: Some(85.0),
            source: BenchmarkSource::ArtificialAnalysis,
            confidence: 0.9,
            ..Default::default()
        };

        store.merge("gpt-4o".to_string(), low_priority).await;
        store.merge("gpt-4o".to_string(), high_priority).await;

        let result = store.get("gpt-4o").await.unwrap();
        assert_eq!(result.intelligence_index, Some(85.0));
    }
}
