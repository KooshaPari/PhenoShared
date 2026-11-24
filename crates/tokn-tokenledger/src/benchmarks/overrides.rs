//! Manual benchmark overrides from configuration.
//!
//! Allows users to override benchmark data via YAML/JSON config.
//! This has HIGHEST PRIORITY over all other sources.

use crate::benchmarks::{BenchmarkData, BenchmarkSource};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;
use tracing::info;

/// Manual benchmark override configuration
#[derive(Debug, Deserialize, Clone)]
pub struct ManualOverridesConfig {
    /// Map of model_id to override data
    pub overrides: HashMap<String, ModelOverride>,
}

/// Override data for a single model
#[derive(Debug, Deserialize, Clone, Default)]
pub struct ModelOverride {
    /// Override intelligence index
    #[serde(default)]
    pub intelligence_index: Option<f64>,
    /// Override coding index
    #[serde(default)]
    pub coding_index: Option<f64>,
    /// Override agentic index
    #[serde(default)]
    pub agentic_index: Option<f64>,
    /// Override speed (tokens per second)
    #[serde(default)]
    pub speed_tps: Option<f64>,
    /// Override latency TTFT (ms)
    #[serde(default)]
    pub latency_ms: Option<f64>,
    /// Override input price per 1M
    #[serde(default)]
    pub price_input: Option<f64>,
    /// Override output price per 1M
    #[serde(default)]
    pub price_output: Option<f64>,
    /// Override context window
    #[serde(default)]
    pub context_window: Option<u64>,
}

impl ModelOverride {
    /// Convert to BenchmarkData
    pub fn to_benchmark_data(&self, model_id: &str) -> BenchmarkData {
        BenchmarkData {
            model_id: model_id.to_string(),
            provider: None,

            intelligence_index: self.intelligence_index,
            coding_index: self.coding_index,
            agentic_index: self.agentic_index,

            speed_tps: self.speed_tps,
            latency_ttft_ms: self.latency_ms,
            latency_e2e_ms: None,

            price_input_per_1m: self.price_input,
            price_output_per_1m: self.price_output,
            price_cache_read_per_1m: None,
            price_cache_write_per_1m: None,

            context_window_tokens: self.context_window,
            max_output_tokens: None,

            source: BenchmarkSource::ManualOverride,
            confidence: 1.0, // Highest confidence for manual overrides
            updated_at: chrono::Utc::now(),
        }
    }
}

/// Manual overrides loader
#[derive(Default)]
pub struct ManualOverrides {
    overrides: HashMap<String, BenchmarkData>,
}

impl ManualOverrides {
    /// Load overrides from a YAML file
    pub fn from_yaml(path: impl AsRef<Path>) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: ManualOverridesConfig = serde_yaml_ng::from_str(&content)?;

        let mut overrides = HashMap::new();
        for (model_id, override_data) in config.overrides {
            let benchmark = override_data.to_benchmark_data(&model_id);
            overrides.insert(model_id, benchmark);
        }

        info!("Loaded {} manual benchmark overrides", overrides.len());

        Ok(Self { overrides })
    }

    /// Load overrides from a JSON file
    pub fn from_json(path: impl AsRef<Path>) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: ManualOverridesConfig = serde_json::from_slice(content.as_bytes())?;

        let mut overrides = HashMap::new();
        for (model_id, override_data) in config.overrides {
            let benchmark = override_data.to_benchmark_data(&model_id);
            overrides.insert(model_id, benchmark);
        }

        info!("Loaded {} manual benchmark overrides", overrides.len());

        Ok(Self { overrides })
    }

    /// Get override for a specific model
    pub fn get(&self, model_id: &str) -> Option<&BenchmarkData> {
        self.overrides.get(model_id)
    }

    /// Get all overrides
    pub fn get_all(&self) -> Vec<&BenchmarkData> {
        self.overrides.values().collect()
    }

    /// Get all model IDs with overrides
    pub fn model_ids(&self) -> Vec<&String> {
        self.overrides.keys().collect()
    }
}

/// Example configuration
pub const EXAMPLE_CONFIG: &str = r#"
# Manual benchmark overrides
# These have HIGHEST PRIORITY over all other data sources

overrides:
  gemini-3.1-pro:
    intelligence_index: 57.0
    speed_tps: 65
    latency_ms: 3990
    price_input: 2.00
    price_output: 12.00
    context_window: 1048576

  gpt-4o:
    intelligence_index: 85.0
    speed_tps: 120
    latency_ms: 1500

  claude-3-5-sonnet:
    intelligence_index: 88.0
    speed_tps: 80
    latency_ms: 2000
"#;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_override_to_benchmark() {
        let override_data = ModelOverride {
            intelligence_index: Some(57.0),
            speed_tps: Some(65.0),
            latency_ms: Some(3990.0),
            price_input: Some(2.0),
            price_output: Some(12.0),
            context_window: Some(1048576),
            ..Default::default()
        };

        let benchmark = override_data.to_benchmark_data("gemini-3.1-pro");

        assert_eq!(benchmark.model_id, "gemini-3.1-pro");
        assert_eq!(benchmark.intelligence_index, Some(57.0));
        assert_eq!(benchmark.speed_tps, Some(65.0));
        assert_eq!(benchmark.price_input_per_1m, Some(2.0));
        assert_eq!(benchmark.source, BenchmarkSource::ManualOverride);
        assert_eq!(benchmark.confidence, 1.0);
    }
}
