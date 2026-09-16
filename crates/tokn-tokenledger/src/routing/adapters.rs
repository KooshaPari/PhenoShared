//! Adapters implementing the ports.
//!
//! Each adapter connects to a specific data source and implements the ports.

use super::ports::*;
use crate::benchmarks::cliproxy_metrics::{
    CLIProxyMetricsClient, CLIProxyMetricsConfig, ModelMetrics, ProviderMetrics,
};
use crate::benchmarks::{BenchmarkData, BenchmarkStore};
use async_trait::async_trait;

// =============================================================================
// UNIFIED ADAPTER (combines all sources)
// =============================================================================

/// Unified adapter that combines multiple sources with priority
pub struct UnifiedAdapter {
    store: BenchmarkStore,
    metrics_client: Option<CLIProxyMetricsClient>,
}

impl UnifiedAdapter {
    pub fn new(store: BenchmarkStore) -> Self {
        Self {
            store,
            metrics_client: None,
        }
    }

    pub fn with_metrics(config: CLIProxyMetricsConfig, store: BenchmarkStore) -> Self {
        let client = CLIProxyMetricsClient::new(config);
        Self {
            store,
            metrics_client: Some(client),
        }
    }
}

#[async_trait]
impl BenchmarkPort for UnifiedAdapter {
    async fn get_benchmark(&self, model_id: &str) -> PortResult<Option<BenchmarkData>> {
        Ok(self.store.get(model_id).await)
    }

    async fn get_all_benchmarks(&self) -> PortResult<Vec<BenchmarkData>> {
        Ok(self.store.get_all().await)
    }

    async fn refresh(&self) -> PortResult<()> {
        // Would trigger refresh from all configured sources
        Ok(())
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "unified"
    }
}

#[async_trait]
impl MetricsPort for UnifiedAdapter {
    async fn get_provider_metrics(&self) -> PortResult<Vec<ProviderMetrics>> {
        match &self.metrics_client {
            Some(client) => client
                .get_provider_metrics()
                .await
                .map_err(|e| PortError::ConnectionError(e.to_string())),
            None => Err(PortError::NotAvailable(
                "Metrics client not configured".into(),
            )),
        }
    }

    async fn get_model_metrics(&self) -> PortResult<Vec<ModelMetrics>> {
        match &self.metrics_client {
            Some(client) => client
                .get_model_metrics()
                .await
                .map_err(|e| PortError::ConnectionError(e.to_string())),
            None => Err(PortError::NotAvailable(
                "Metrics client not configured".into(),
            )),
        }
    }

    async fn get_model_realtime(&self, model_id: &str) -> PortResult<Option<ModelMetrics>> {
        let models = self.get_model_metrics().await?;
        Ok(models.into_iter().find(|m| m.model == model_id))
    }

    async fn is_available(&self) -> bool {
        self.metrics_client.is_some()
    }

    fn source_name(&self) -> &str {
        "unified-metrics"
    }
}

// =============================================================================
// CLIProxyAPI ADAPTER
// =============================================================================

/// CLIProxyAPI-specific adapter
pub struct CLIProxyAdapter {
    metrics_client: CLIProxyMetricsClient,
    store: BenchmarkStore,
}

impl CLIProxyAdapter {
    pub fn new(config: CLIProxyMetricsConfig, store: BenchmarkStore) -> Self {
        Self {
            metrics_client: CLIProxyMetricsClient::new(config),
            store,
        }
    }
}

#[async_trait]
impl BenchmarkPort for CLIProxyAdapter {
    async fn get_benchmark(&self, model_id: &str) -> PortResult<Option<BenchmarkData>> {
        Ok(self.store.get(model_id).await)
    }

    async fn get_all_benchmarks(&self) -> PortResult<Vec<BenchmarkData>> {
        Ok(self.store.get_all().await)
    }

    async fn refresh(&self) -> PortResult<()> {
        // Would fetch latest from CLIProxyAPI
        Ok(())
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "cliproxyapi"
    }
}

#[async_trait]
impl MetricsPort for CLIProxyAdapter {
    async fn get_provider_metrics(&self) -> PortResult<Vec<ProviderMetrics>> {
        self.metrics_client
            .get_provider_metrics()
            .await
            .map_err(|e| PortError::ConnectionError(e.to_string()))
    }

    async fn get_model_metrics(&self) -> PortResult<Vec<ModelMetrics>> {
        self.metrics_client
            .get_model_metrics()
            .await
            .map_err(|e| PortError::ConnectionError(e.to_string()))
    }

    async fn get_model_realtime(&self, model_id: &str) -> PortResult<Option<ModelMetrics>> {
        let models = self.get_model_metrics().await?;
        Ok(models.into_iter().find(|m| m.model == model_id))
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "cliproxyapi-metrics"
    }
}

// =============================================================================
// HELIOS HARNESS ADAPTER
// =============================================================================

/// HeliosHarness adapter for benchmark results
pub struct HeliosHarnessAdapter {
    /// Path to benchmark results
    results_path: Option<String>,
    store: BenchmarkStore,
}

impl HeliosHarnessAdapter {
    pub fn new(results_path: Option<String>, store: BenchmarkStore) -> Self {
        Self {
            results_path,
            store,
        }
    }
}

#[async_trait]
impl BenchmarkPort for HeliosHarnessAdapter {
    async fn get_benchmark(&self, model_id: &str) -> PortResult<Option<BenchmarkData>> {
        Ok(self.store.get(model_id).await)
    }

    async fn get_all_benchmarks(&self) -> PortResult<Vec<BenchmarkData>> {
        Ok(self.store.get_all().await)
    }

    async fn refresh(&self) -> PortResult<()> {
        // Would load from HeliosHarness results directory
        Ok(())
    }

    async fn is_available(&self) -> bool {
        self.results_path.is_some()
    }

    fn source_name(&self) -> &str {
        "helios-harness"
    }
}

// =============================================================================
// THEGENT ROUTING ADAPTER
// =============================================================================

/// Thegent adapter for routing decisions
pub struct ThegentRoutingAdapter {
    store: BenchmarkStore,
}

impl ThegentRoutingAdapter {
    pub fn new(store: BenchmarkStore) -> Self {
        Self { store }
    }
}

#[async_trait]
impl RoutingPort for ThegentRoutingAdapter {
    async fn select(&self, criteria: &RoutingCriteria) -> PortResult<RoutingDecision> {
        // Use store data to select best model
        let benchmarks = self.store.get_all().await;

        // Filter by criteria
        let mut candidates: Vec<(String, f64)> = benchmarks
            .iter()
            .filter(|b| {
                if let Some(min_q) = criteria.min_quality {
                    if b.intelligence_index.unwrap_or(0.0) < min_q {
                        return false;
                    }
                }
                if let Some(max_c) = criteria.max_cost {
                    if b.price_input_per_1m.unwrap_or(f64::MAX) > max_c {
                        return false;
                    }
                }
                true
            })
            .map(|b| {
                let score =
                    b.intelligence_index.unwrap_or(0.0) / b.price_input_per_1m.unwrap_or(1.0);
                (b.model_id.clone(), score)
            })
            .collect();

        candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        let top = candidates
            .first()
            .cloned()
            .unwrap_or_else(|| ("gpt-4o".to_string(), 0.5));

        Ok(RoutingDecision {
            model: top.0,
            provider: "openai".to_string(),
            strategy: "quality-cost".to_string(),
            confidence: top.1,
            reason: "Best quality/cost ratio".to_string(),
            alternatives: vec![],
        })
    }

    async fn get_rankings(
        &self,
        _category: Option<&str>,
        limit: Option<u32>,
    ) -> PortResult<Vec<RoutingAlternative>> {
        let benchmarks = self.store.get_all().await;
        let limit = limit.unwrap_or(20) as usize;

        let mut rankings: Vec<RoutingAlternative> = benchmarks
            .iter()
            .map(|b| RoutingAlternative {
                model: b.model_id.clone(),
                provider: b.provider.clone().unwrap_or_default(),
                score: b.intelligence_index.unwrap_or(0.0),
                reason: format!("Intelligence: {:?}", b.intelligence_index),
            })
            .take(limit)
            .collect();

        rankings.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());

        Ok(rankings)
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "thegent"
    }
}

// =============================================================================
// AGENTAPI ADAPTER
// =============================================================================

/// AgentAPI adapter for agent lifecycle events
pub struct AgentAPIAdapter {
    store: BenchmarkStore,
}

impl AgentAPIAdapter {
    pub fn new(store: BenchmarkStore) -> Self {
        Self { store }
    }
}

#[async_trait]
impl BenchmarkPort for AgentAPIAdapter {
    async fn get_benchmark(&self, model_id: &str) -> PortResult<Option<BenchmarkData>> {
        Ok(self.store.get(model_id).await)
    }

    async fn get_all_benchmarks(&self) -> PortResult<Vec<BenchmarkData>> {
        Ok(self.store.get_all().await)
    }

    async fn refresh(&self) -> PortResult<()> {
        Ok(())
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "agentapi"
    }
}

#[async_trait]
impl ModelMappingPort for AgentAPIAdapter {
    async fn map_model(&self, source_model: &str) -> PortResult<ModelMapping> {
        // Simple mapping - would be more sophisticated in production
        let parts: Vec<&str> = source_model.split('/').collect();

        Ok(ModelMapping {
            source_model: source_model.to_string(),
            canonical_model: parts.last().unwrap_or(&source_model).to_string(),
            provider: parts.first().copied().map(String::from),
            harness: None,
            confidence: 0.8,
            rule: "slash_split".to_string(),
        })
    }

    async fn resolve_provider(&self, model: &str) -> PortResult<Option<String>> {
        let mapping = self.map_model(model).await?;
        Ok(mapping.provider)
    }

    async fn resolve_harness(&self, _model: &str) -> PortResult<Option<String>> {
        Ok(None)
    }

    async fn all_mappings(&self) -> PortResult<Vec<ModelMapping>> {
        Ok(vec![])
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "agentapi-mapping"
    }
}
