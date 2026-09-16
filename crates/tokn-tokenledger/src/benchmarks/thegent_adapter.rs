//! Thegent adapter for quality/speed/cost values.
//!
//! This module provides integration with thegent's Python-based quality, speed,
//! and cost values modules. Instead of rewriting Python to Rust, we use subprocess
//! to call thegent commands and parse results.
//!
//! The thegent provides:
//! - Quality indices based on Terminal Bench 2.0, SWE-Bench, AIME
//! - Speed indices based on TPS, latency, success rate
//! - Cost data from catalog
//!
//! This adapter is optional - if thegent is not available, we fall back to
//! other data sources (AA, OpenRouter, manual overrides).

use crate::benchmarks::BenchmarkStore;
use std::process::Command;
use tracing::info;

/// Thegent adapter configuration
#[derive(Debug, Clone, Default)]
pub struct ThegentAdapterConfig {
    /// Path to thegent binary or module
    pub thegent_path: Option<String>,
    /// Whether to enable thegent integration
    pub enabled: bool,
}

/// Thegent adapter for querying quality/speed/cost values
pub struct ThegentAdapter {
    config: ThegentAdapterConfig,
}

impl ThegentAdapter {
    pub fn new(config: ThegentAdapterConfig) -> Self {
        Self { config }
    }

    /// Check if thegent is available
    pub fn is_available(&self) -> bool {
        if !self.config.enabled {
            return false;
        }

        // Try to find thegent
        if let Some(ref path) = self.config.thegent_path {
            return std::path::Path::new(path).exists();
        }

        // Try which command
        Command::new("which")
            .arg("thegent")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    /// Query thegent for all quality indices
    /// This would call: thegent quality --format json
    pub fn get_quality_indices(&self) -> Result<Vec<ThegentQualityIndex>, ThegentError> {
        if !self.is_available() {
            return Err(ThegentError::NotAvailable);
        }

        // For now, this is a placeholder - we'd call thegent CLI
        // In practice, we'd spawn thegent process and parse JSON output

        info!("Thegent quality indices requested but adapter not fully implemented");
        Err(ThegentError::NotImplemented)
    }

    /// Query thegent for all speed indices
    pub fn get_speed_indices(&self) -> Result<Vec<ThegentSpeedIndex>, ThegentError> {
        if !self.is_available() {
            return Err(ThegentError::NotAvailable);
        }

        info!("Thegent speed indices requested but adapter not fully implemented");
        Err(ThegentError::NotImplemented)
    }

    /// Query thegent for all cost values
    pub fn get_cost_values(&self) -> Result<Vec<ThegentCostValue>, ThegentError> {
        if !self.is_available() {
            return Err(ThegentError::NotAvailable);
        }

        info!("Thegent cost values requested but adapter not fully implemented");
        Err(ThegentError::NotImplemented)
    }

    /// Fetch and store all thegent data into benchmark store
    pub async fn fetch_and_store(&self, _store: &BenchmarkStore) -> Result<usize, ThegentError> {
        if !self.is_available() {
            return Err(ThegentError::NotAvailable);
        }

        // Placeholder - would collect from all three methods
        info!("Thegent adapter fetch_and_store not fully implemented");
        Err(ThegentError::NotImplemented)
    }
}

/// Quality index from thegent
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ThegentQualityIndex {
    pub model_id: String,
    pub provider: String,
    pub quality_index: f64,
    pub task_type: Option<String>,
}

/// Speed index from thegent
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ThegentSpeedIndex {
    pub model_id: String,
    pub provider: String,
    pub speed_index: f64,
    pub tps: Option<f64>,
    pub latency_ms: Option<f64>,
}

/// Cost value from thegent
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ThegentCostValue {
    pub model_id: String,
    pub provider: String,
    pub cost_per_1k: f64,
}

/// Errors from thegent adapter
#[derive(Debug, thiserror::Error)]
pub enum ThegentError {
    #[error("Thegent is not available")]
    NotAvailable,

    #[error("Thegent adapter not implemented")]
    NotImplemented,

    #[error("Failed to execute thegent: {0}")]
    ExecutionError(String),

    #[error("Failed to parse thegent output: {0}")]
    ParseError(String),
}

impl From<std::io::Error> for ThegentError {
    fn from(e: std::io::Error) -> Self {
        ThegentError::ExecutionError(e.to_string())
    }
}

impl From<serde_json::Error> for ThegentError {
    fn from(e: serde_json::Error) -> Self {
        ThegentError::ParseError(e.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_adapter_disabled_by_default() {
        let config = ThegentAdapterConfig::default();
        let adapter = ThegentAdapter::new(config);
        assert!(!adapter.is_available());
    }
}
