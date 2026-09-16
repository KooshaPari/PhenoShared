//! Routing logic and model mapping utilities.

use super::ports::*;
use crate::benchmarks::BenchmarkData;
use async_trait::async_trait;

// =============================================================================
// PARETO ROUTER
// =============================================================================

/// Pareto router for model selection
pub struct ParetoRouter {
    store: crate::benchmarks::BenchmarkStore,
}

impl ParetoRouter {
    pub fn new(store: crate::benchmarks::BenchmarkStore) -> Self {
        Self { store }
    }

    /// Calculate Pareto score for a benchmark
    pub fn calculate_pareto_score(benchmark: &BenchmarkData) -> f64 {
        let quality = benchmark.intelligence_index.unwrap_or(0.0) / 100.0; // Normalize to 0-1
        let speed = benchmark.speed_tps.unwrap_or(0.0) / 200.0; // Normalize (200 tps = max)
        let cost = 1.0 - (benchmark.price_input_per_1m.unwrap_or(1.0) / 10.0).min(1.0); // Lower cost = higher score

        // Weighted combination
        (quality * 0.5) + (speed * 0.3) + (cost * 0.2)
    }

    /// Get Pareto-optimal models
    pub async fn get_pareto_frontier(&self) -> Vec<(String, f64)> {
        let benchmarks = self.store.get_all().await;

        let mut scored: Vec<(String, f64)> = benchmarks
            .iter()
            .map(|b| (b.model_id.clone(), Self::calculate_pareto_score(b)))
            .collect();

        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        scored
    }
}

#[async_trait]
impl RoutingPort for ParetoRouter {
    async fn select(&self, criteria: &RoutingCriteria) -> PortResult<RoutingDecision> {
        let benchmarks = self.store.get_all().await;

        // Filter and score
        let mut candidates: Vec<(BenchmarkData, f64)> = benchmarks
            .iter()
            .filter(|b| {
                // Apply criteria filters
                if let Some(min_q) = criteria.min_quality {
                    if b.intelligence_index.unwrap_or(0.0) < min_q * 100.0 {
                        return false;
                    }
                }
                if let Some(max_c) = criteria.max_cost {
                    let cost = b.price_input_per_1m.unwrap_or(f64::MAX);
                    if cost > max_c * 1_000_000.0 {
                        return false;
                    }
                }
                if let Some(max_lat) = criteria.max_latency {
                    if b.latency_ttft_ms.unwrap_or(u32::MAX as f64) > max_lat as f64 {
                        return false;
                    }
                }
                true
            })
            .map(|b| (b.clone(), Self::calculate_pareto_score(b)))
            .collect();

        candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        match candidates.first() {
            Some((best, score)) => Ok(RoutingDecision {
                model: best.model_id.clone(),
                provider: best.provider.clone().unwrap_or_default(),
                strategy: "pareto".to_string(),
                confidence: *score,
                reason: format!(
                    "Pareto optimal: quality={:?}, speed={:?}, cost={:?}",
                    best.intelligence_index, best.speed_tps, best.price_input_per_1m
                ),
                alternatives: candidates
                    .iter()
                    .skip(1)
                    .take(4)
                    .map(|(b, s)| RoutingAlternative {
                        model: b.model_id.clone(),
                        provider: b.provider.clone().unwrap_or_default(),
                        score: *s,
                        reason: "Pareto alternative".to_string(),
                    })
                    .collect(),
            }),
            None => Err(PortError::NotFound("No models match criteria".into())),
        }
    }

    async fn get_rankings(
        &self,
        _category: Option<&str>,
        limit: Option<u32>,
    ) -> PortResult<Vec<RoutingAlternative>> {
        let frontier = self.get_pareto_frontier().await;
        let limit = limit.unwrap_or(20) as usize;

        Ok(frontier
            .into_iter()
            .take(limit)
            .map(|(model, score)| RoutingAlternative {
                model,
                provider: "unknown".to_string(),
                score,
                reason: "Pareto ranking".to_string(),
            })
            .collect())
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "pareto-router"
    }
}

// =============================================================================
// MODEL MAPPING
// =============================================================================

/// Model mapping resolver
pub struct ModelMappingResolver {
    store: crate::benchmarks::BenchmarkStore,
}

impl ModelMappingResolver {
    pub fn new(store: crate::benchmarks::BenchmarkStore) -> Self {
        Self { store }
    }

    /// Resolve provider-harness-model trio
    pub async fn resolve_trio(
        &self,
        provider: Option<&str>,
        harness: Option<&str>,
        model: &str,
    ) -> PortResult<ProviderHarnessModel> {
        // Get benchmark data for this model
        let benchmark = self.store.get(model).await;

        let (quality, cost, latency, throughput) = match benchmark {
            Some(b) => (
                b.intelligence_index,
                b.price_input_per_1m,
                b.latency_ttft_ms.map(|l| l as u32),
                b.speed_tps,
            ),
            None => (None, None, None, None),
        };

        Ok(ProviderHarnessModel {
            provider: provider.unwrap_or("unknown").to_string(),
            harness: harness.unwrap_or("unknown").to_string(),
            model: model.to_string(),
            quality_score: quality,
            cost_per_1k: cost,
            latency_ms: latency,
            throughput_tps: throughput,
            context_window: None,
            success_rate: None,
        })
    }
}

#[async_trait]
impl TrioPort for ModelMappingResolver {
    async fn resolve_trio(
        &self,
        provider: Option<&str>,
        harness: Option<&str>,
        model: &str,
    ) -> PortResult<ProviderHarnessModel> {
        self.resolve_trio(provider, harness, model).await
    }

    async fn all_trios(&self) -> PortResult<Vec<ProviderHarnessModel>> {
        let benchmarks = self.store.get_all().await;

        Ok(benchmarks
            .into_iter()
            .map(|b| ProviderHarnessModel {
                provider: b.provider.unwrap_or_default(),
                harness: "unknown".to_string(),
                model: b.model_id,
                quality_score: b.intelligence_index,
                cost_per_1k: b.price_input_per_1m,
                latency_ms: b.latency_ttft_ms.map(|l| l as u32),
                throughput_tps: b.speed_tps,
                context_window: b.context_window_tokens,
                success_rate: None,
            })
            .collect())
    }

    async fn is_available(&self) -> bool {
        true
    }

    fn source_name(&self) -> &str {
        "mapping-resolver"
    }
}
