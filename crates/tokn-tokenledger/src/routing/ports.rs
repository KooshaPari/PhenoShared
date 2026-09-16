//! Ports (interfaces) for hexagonal architecture.
//!
//! These traits define the contracts for benchmark, metrics, routing, and model mapping.
//! Each adapter implements one or more of these ports.

use crate::benchmarks::BenchmarkData;
use async_trait::async_trait;

/// Error type for port operations
#[derive(Debug, thiserror::Error)]
pub enum PortError {
    #[error("Source not available: {0}")]
    NotAvailable(String),

    #[error("Data not found: {0}")]
    NotFound(String),

    #[error("Connection error: {0}")]
    ConnectionError(String),

    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("Timeout: {0}")]
    Timeout(String),

    /// Tenant resolution or authorization error.
    /// Addresses audit finding L4: surface auth failures as typed errors.
    #[error("Tenant error: {0}")]
    Tenant(#[from] crate::tenant::TenantError),
}

pub type PortResult<T> = Result<T, PortError>;

// =============================================================================
// BENCHMARK PORT
// =============================================================================

/// Port for accessing benchmark data from any source
#[async_trait]
pub trait BenchmarkPort: Send + Sync {
    /// Get benchmark data for a specific model
    async fn get_benchmark(&self, model_id: &str) -> PortResult<Option<BenchmarkData>>;

    /// Get all benchmarks
    async fn get_all_benchmarks(&self) -> PortResult<Vec<BenchmarkData>>;

    /// Refresh data from source
    async fn refresh(&self) -> PortResult<()>;

    /// Check if source is available
    async fn is_available(&self) -> bool;

    /// Source name for debugging
    fn source_name(&self) -> &str;
}

// =============================================================================
// METRICS PORT
// =============================================================================

use crate::benchmarks::cliproxy_metrics::{ModelMetrics, ProviderMetrics};

/// Port for accessing runtime metrics
#[async_trait]
pub trait MetricsPort: Send + Sync {
    /// Get provider-level metrics
    async fn get_provider_metrics(&self) -> PortResult<Vec<ProviderMetrics>>;

    /// Get model-level metrics
    async fn get_model_metrics(&self) -> PortResult<Vec<ModelMetrics>>;

    /// Get real-time metrics for a specific model
    async fn get_model_realtime(&self, model_id: &str) -> PortResult<Option<ModelMetrics>>;

    /// Check if metrics are available
    async fn is_available(&self) -> bool;

    /// Source name
    fn source_name(&self) -> &str;
}

// =============================================================================
// ROUTING PORT
// =============================================================================

use serde::{Deserialize, Serialize};

/// Routing decision result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingDecision {
    /// Selected model
    pub model: String,
    /// Selected provider
    pub provider: String,
    /// Routing strategy used
    pub strategy: String,
    /// Confidence score (0-1)
    pub confidence: f64,
    /// Reason for selection
    pub reason: String,
    /// Alternative options considered
    pub alternatives: Vec<RoutingAlternative>,
}

/// Alternative routing option
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingAlternative {
    pub model: String,
    pub provider: String,
    pub score: f64,
    pub reason: String,
}

/// Routing criteria from request
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RoutingCriteria {
    /// Preferred quality threshold (0-1)
    pub min_quality: Option<f64>,
    /// Maximum cost per request (USD)
    pub max_cost: Option<f64>,
    /// Maximum latency (ms)
    pub max_latency: Option<u32>,
    /// Preferred throughput (tokens/sec)
    pub min_throughput: Option<f64>,
    /// Required context window
    pub min_context: Option<u64>,
    /// Task type hint
    pub task_type: Option<String>,
    /// Whether agentic task
    pub is_agentic: Option<bool>,
    /// Prefer fallback providers
    pub allow_fallback: Option<bool>,
}

/// Port for routing decisions
#[async_trait]
pub trait RoutingPort: Send + Sync {
    /// Select best model/provider for criteria
    async fn select(&self, criteria: &RoutingCriteria) -> PortResult<RoutingDecision>;

    /// Get rankings
    async fn get_rankings(
        &self,
        category: Option<&str>,
        limit: Option<u32>,
    ) -> PortResult<Vec<RoutingAlternative>>;

    /// Check if routing is available
    async fn is_available(&self) -> bool;

    /// Source name
    fn source_name(&self) -> &str;
}

// =============================================================================
// MODEL MAPPING PORT
// =============================================================================

/// Model mapping entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMapping {
    /// Source model ID (as received)
    pub source_model: String,
    /// Resolved canonical model
    pub canonical_model: String,
    /// Provider (if known)
    pub provider: Option<String>,
    /// Harness (if known)
    pub harness: Option<String>,
    /// Mapping confidence (0-1)
    pub confidence: f64,
    /// Mapping rule used
    pub rule: String,
}

/// Port for model mapping/resolution
#[async_trait]
pub trait ModelMappingPort: Send + Sync {
    /// Map a source model to canonical form
    async fn map_model(&self, source_model: &str) -> PortResult<ModelMapping>;

    /// Resolve provider for model
    async fn resolve_provider(&self, model: &str) -> PortResult<Option<String>>;

    /// Resolve harness for model
    async fn resolve_harness(&self, model: &str) -> PortResult<Option<String>>;

    /// Get all known mappings
    async fn all_mappings(&self) -> PortResult<Vec<ModelMapping>>;

    /// Check if mapping is available
    async fn is_available(&self) -> bool;

    /// Source name
    fn source_name(&self) -> &str;
}

// =============================================================================
// PROVIDER-HARNESS-MODEL TRIO
// =============================================================================

/// Complete trio: provider + harness + model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderHarnessModel {
    /// Provider (openai, anthropic, google, etc.)
    pub provider: String,
    /// Harness (codex, litellm, claudecode, etc.)
    pub harness: String,
    /// Model (gpt-4o, claude-3-5-sonnet, etc.)
    pub model: String,

    // Derived metrics from all sources
    /// Quality score (0-1)
    pub quality_score: Option<f64>,
    /// Cost per 1K tokens
    pub cost_per_1k: Option<f64>,
    /// Latency (ms)
    pub latency_ms: Option<u32>,
    /// Throughput (tokens/sec)
    pub throughput_tps: Option<f64>,
    /// Context window
    pub context_window: Option<u64>,
    /// Success rate
    pub success_rate: Option<f64>,
}

/// Port for trio resolution
#[async_trait]
pub trait TrioPort: Send + Sync {
    /// Resolve provider-harness-model trio
    async fn resolve_trio(
        &self,
        provider: Option<&str>,
        harness: Option<&str>,
        model: &str,
    ) -> PortResult<ProviderHarnessModel>;

    /// Get all known trios
    async fn all_trios(&self) -> PortResult<Vec<ProviderHarnessModel>>;

    /// Check if trio resolution is available
    async fn is_available(&self) -> bool;

    /// Source name
    fn source_name(&self) -> &str;
}
