//! ParetoRs — pure pricing & routing engine.
//!
//! No I/O, no external API calls. Pure Pareto-optimal selection logic.

use crate::models::*;

// ─── Constants ────────────────────────────────────────────────────────────────

/// Fallback cost when no pricing data is available (per-call estimate).
pub const DEFAULT_CALL_COST: f64 = 0.002;

// ─── Pareto-Optimal Selection ─────────────────────────────────────────────────

/// Select the best provider using Pareto-optimal filtering.
///
/// Selects providers that are not dominated on all criteria:
///   - cost (lower is better)
///   - latency (lower is better)
///   - reliability (higher is better)
pub fn select_pareto_optimal(
    harnesses: &[ProviderHarness],
    criteria: RoutingCriteria,
) -> Vec<ProviderHarness> {
    if harnesses.is_empty() {
        return vec![];
    }

    // Step 1: Filter out dominated providers
    let mut pareto: Vec<&ProviderHarness> = harnesses.iter().collect();

    // Remove strictly dominated options
    pareto.retain(|h| !harnesses.iter().any(|other| dominates(other, h, criteria)));

    // Step 2: Score remaining options by routing criteria
    let scored: Vec<(ProviderHarness, f64)> = pareto
        .into_iter()
        .map(|h| {
            let score = compute_routing_score(h, criteria);
            (h.clone(), score)
        })
        .collect();

    // Step 3: Sort by score (best first)
    let mut sorted = scored;
    sorted.sort_by(|a, b| b.1.partial_cmp(&a.1).expect("NaN in routing score"));

    sorted.into_iter().map(|(h, _)| h).collect()
}

/// Returns true if `dominator` is strictly better than `dominated` on ALL
/// relevant criteria (cost, latency, reliability).
fn dominates(
    dominator: &ProviderHarness,
    dominated: &ProviderHarness,
    criteria: RoutingCriteria,
) -> bool {
    let cost_better =
        dominator.input_cost + dominator.output_cost < dominated.input_cost + dominated.output_cost;
    let latency_better = match (dominator.p95_latency_ms, dominated.p95_latency_ms) {
        (Some(d), Some(b)) => d < b,
        (Some(_), None) => true,
        _ => false,
    };
    let reliability_better = dominator.success_rate > dominated.success_rate;

    match criteria {
        RoutingCriteria::Cost => cost_better,
        RoutingCriteria::Latency => latency_better,
        RoutingCriteria::Balanced => cost_better && latency_better && reliability_better,
    }
}

/// Compute a composite routing score (higher = better).
pub fn compute_routing_score(h: &ProviderHarness, criteria: RoutingCriteria) -> f64 {
    match criteria {
        RoutingCriteria::Cost => {
            // Score = 1 / total_cost  (higher score = lower cost)
            let total_cost = h.input_cost + h.output_cost;
            if total_cost <= 0.0 {
                f64::INFINITY
            } else {
                1.0 / total_cost
            }
        }
        RoutingCriteria::Latency => {
            // Score = negative latency (lower latency = higher score)
            h.p95_latency_ms.map(|l| -l).unwrap_or(0.0)
        }
        RoutingCriteria::Balanced => {
            // Weighted composite: 40% cost, 30% latency, 30% reliability
            let total_cost = h.input_cost + h.output_cost;
            let cost_score = if total_cost > 0.0 {
                1.0 / total_cost
            } else {
                f64::INFINITY
            };
            let latency_score = h.p95_latency_ms.map(|l| 1.0 / (l.max(1.0))).unwrap_or(0.0);
            let reliability_score = h.success_rate;
            0.4 * cost_score + 0.3 * latency_score + 0.3 * reliability_score
        }
    }
}

// ─── Price Loading / Parsing (pure) ────────────────────────────────────────────

/// Parse a pricing YAML file into a price map.
pub fn parse_pricing_yaml(yaml_content: &str) -> Result<Vec<ModelPricing>, String> {
    serde_yaml_ng::from_str(yaml_content).map_err(|e| format!("YAML parse error: {e}"))
}

/// Serialize price map back to YAML.
pub fn serialize_pricing_yaml(prices: &[ModelPricing]) -> Result<String, String> {
    serde_yaml_ng::to_string(prices).map_err(|e| format!("YAML serialize error: {e}"))
}

// ─── Price Lookup ─────────────────────────────────────────────────────────────

/// Find pricing for a specific model, returns None if not found.
pub fn find_model_price<'a>(
    prices: &'a [ModelPricing],
    provider: &str,
    model: &str,
) -> Option<&'a ModelPricing> {
    prices
        .iter()
        .find(|p| p.provider == provider && p.model == model)
}

/// Build a lookup map from (provider, model) -> ModelPricing.
pub fn build_price_map(
    prices: &[ModelPricing],
) -> std::collections::HashMap<(String, String), ModelPricing> {
    prices
        .iter()
        .map(|p| ((p.provider.clone(), p.model.clone()), p.clone()))
        .collect()
}

// ─── Price Comparison / Reconciliation ─────────────────────────────────────────

/// Diff two pricing maps and return models that are missing, changed, or removed.
pub fn diff_pricing(
    old_prices: &[ModelPricing],
    new_prices: &[ModelPricing],
    threshold_pct: f64,
) -> PricingDiff {
    let old_map = build_price_map(old_prices);
    let new_map = build_price_map(new_prices);

    let mut added = Vec::new();
    let mut changed = Vec::new();
    let mut removed = Vec::new();

    for (key, new_p) in &new_map {
        match old_map.get(key) {
            Some(old_p) => {
                let input_changed = pct_diff(old_p.input_per_m, new_p.input_per_m) > threshold_pct;
                let output_changed =
                    pct_diff(old_p.output_per_m, new_p.output_per_m) > threshold_pct;
                if input_changed || output_changed {
                    changed.push(PriceChange {
                        provider: new_p.provider.clone(),
                        model: new_p.model.clone(),
                        old_input: old_p.input_per_m,
                        new_input: new_p.input_per_m,
                        old_output: old_p.output_per_m,
                        new_output: new_p.output_per_m,
                        input_pct_change: pct_diff(old_p.input_per_m, new_p.input_per_m),
                        output_pct_change: pct_diff(old_p.output_per_m, new_p.output_per_m),
                    });
                }
            }
            None => {
                added.push(new_p.clone());
            }
        }
    }

    for (key, old_p) in &old_map {
        if !new_map.contains_key(key) {
            removed.push(old_p.clone());
        }
    }

    PricingDiff {
        added,
        changed,
        removed,
    }
}

/// Percentage difference: |new - old| / old * 100.
pub fn pct_diff(old: f64, new: f64) -> f64 {
    if old.abs() < 1e-10 {
        0.0
    } else {
        ((new - old).abs() / old) * 100.0
    }
}

/// Pricing diff result.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PricingDiff {
    pub added: Vec<ModelPricing>,
    pub changed: Vec<PriceChange>,
    pub removed: Vec<ModelPricing>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PriceChange {
    pub provider: String,
    pub model: String,
    pub old_input: f64,
    pub new_input: f64,
    pub old_output: f64,
    pub new_output: f64,
    pub input_pct_change: f64,
    pub output_pct_change: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_harness(
        provider: &str,
        model: &str,
        input_cost: f64,
        output_cost: f64,
        latency_ms: Option<f64>,
        success_rate: f64,
    ) -> ProviderHarness {
        ProviderHarness {
            provider: provider.to_string(),
            model: model.to_string(),
            input_cost,
            output_cost,
            p50_latency_ms: latency_ms,
            p95_latency_ms: latency_ms,
            success_rate,
        }
    }

    #[test]
    fn test_select_pareto_optimal_empty() {
        let result = select_pareto_optimal(&[], RoutingCriteria::Balanced);
        assert!(result.is_empty());
    }

    #[test]
    fn test_select_pareto_optimal_single() {
        let h = make_harness("openai", "gpt-4o", 0.01, 0.03, Some(100.0), 0.99);
        let result = select_pareto_optimal(std::slice::from_ref(&h), RoutingCriteria::Balanced);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].provider, "openai");
    }

    #[test]
    fn test_select_pareto_optimal_cost_dominance() {
        let cheap = make_harness("a", "m1", 0.01, 0.01, Some(200.0), 0.95);
        let expensive = make_harness("b", "m2", 0.05, 0.05, Some(100.0), 0.99);
        // Cost criteria: cheap dominates expensive on cost
        let result = select_pareto_optimal(&[cheap, expensive], RoutingCriteria::Cost);
        // The cheap one should rank first
        assert_eq!(result[0].provider, "a");
    }

    #[test]
    fn test_compute_routing_score_cost() {
        let h = make_harness("openai", "gpt-4o", 0.01, 0.03, Some(100.0), 0.99);
        let score = compute_routing_score(&h, RoutingCriteria::Cost);
        // total_cost = 0.04, score = 1/0.04 = 25.0
        assert!((score - 25.0).abs() < 0.01);
    }

    #[test]
    fn test_compute_routing_score_cost_zero() {
        let h = make_harness("free", "free-model", 0.0, 0.0, Some(100.0), 0.99);
        let score = compute_routing_score(&h, RoutingCriteria::Cost);
        assert!(score.is_infinite());
    }

    #[test]
    fn test_compute_routing_score_latency() {
        let h = make_harness("openai", "gpt-4o", 0.01, 0.03, Some(100.0), 0.99);
        let score = compute_routing_score(&h, RoutingCriteria::Latency);
        assert_eq!(score, -100.0);
    }

    #[test]
    fn test_compute_routing_score_latency_none() {
        let h = make_harness("openai", "gpt-4o", 0.01, 0.03, None, 0.99);
        let score = compute_routing_score(&h, RoutingCriteria::Latency);
        assert_eq!(score, 0.0);
    }

    #[test]
    fn test_compute_routing_score_balanced() {
        let h = make_harness("openai", "gpt-4o", 0.01, 0.03, Some(100.0), 0.99);
        let score = compute_routing_score(&h, RoutingCriteria::Balanced);
        // 0.4 * (1/0.04) + 0.3 * (1/100) + 0.3 * 0.99
        // = 0.4 * 25.0 + 0.3 * 0.01 + 0.3 * 0.99
        // = 10.0 + 0.003 + 0.297 = 10.3
        assert!((score - 10.3).abs() < 0.01);
    }

    #[test]
    fn test_pct_diff_basic() {
        let diff = pct_diff(100.0, 150.0);
        assert!((diff - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_pct_diff_zero_old() {
        let diff = pct_diff(0.0, 100.0);
        assert_eq!(diff, 0.0);
    }

    #[test]
    fn test_pct_diff_equal() {
        let diff = pct_diff(50.0, 50.0);
        assert_eq!(diff, 0.0);
    }

    #[test]
    fn test_find_model_price_found() {
        let prices = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let found = find_model_price(&prices, "openai", "gpt-4o");
        assert!(found.is_some());
        assert_eq!(found.unwrap().input_per_m, 2.5);
    }

    #[test]
    fn test_find_model_price_not_found() {
        let prices = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let found = find_model_price(&prices, "anthropic", "claude-3");
        assert!(found.is_none());
    }

    #[test]
    fn test_build_price_map() {
        let prices = vec![
            ModelPricing {
                provider: "openai".into(),
                model: "gpt-4o".into(),
                input_per_m: 2.5,
                output_per_m: 10.0,
            },
            ModelPricing {
                provider: "anthropic".into(),
                model: "claude-3".into(),
                input_per_m: 3.0,
                output_per_m: 15.0,
            },
        ];
        let map = build_price_map(&prices);
        assert_eq!(map.len(), 2);
        assert!(map.contains_key(&("openai".into(), "gpt-4o".into())));
        assert!(map.contains_key(&("anthropic".into(), "claude-3".into())));
    }

    #[test]
    fn test_diff_pricing_added() {
        let old: Vec<ModelPricing> = vec![];
        let new = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let diff = diff_pricing(&old, &new, 1.0);
        assert_eq!(diff.added.len(), 1);
        assert_eq!(diff.changed.len(), 0);
        assert_eq!(diff.removed.len(), 0);
    }

    #[test]
    fn test_diff_pricing_removed() {
        let old = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let new: Vec<ModelPricing> = vec![];
        let diff = diff_pricing(&old, &new, 1.0);
        assert_eq!(diff.added.len(), 0);
        assert_eq!(diff.removed.len(), 1);
    }

    #[test]
    fn test_diff_pricing_changed() {
        let old = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.0,
            output_per_m: 10.0,
        }];
        let new = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 3.0,
            output_per_m: 10.0,
        }];
        let diff = diff_pricing(&old, &new, 1.0);
        assert_eq!(diff.added.len(), 0);
        assert_eq!(diff.changed.len(), 1);
        assert_eq!(diff.removed.len(), 0);
        assert_eq!(diff.changed[0].model, "gpt-4o");
    }

    #[test]
    fn test_diff_pricing_no_change_below_threshold() {
        let old = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.0,
            output_per_m: 10.0,
        }];
        let new = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.01,
            output_per_m: 10.0,
        }];
        let diff = diff_pricing(&old, &new, 1.0);
        assert_eq!(diff.added.len(), 0);
        assert_eq!(diff.changed.len(), 0);
        assert_eq!(diff.removed.len(), 0);
    }

    #[test]
    fn test_serialize_pricing_yaml_roundtrip() {
        let prices = vec![ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let yaml = serialize_pricing_yaml(&prices).unwrap();
        let parsed = parse_pricing_yaml(&yaml).unwrap();
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].provider, "openai");
        assert_eq!(parsed[0].input_per_m, 2.5);
    }

    #[test]
    fn test_parse_pricing_yaml_invalid() {
        let result = parse_pricing_yaml("not: valid: yaml: [unclosed");
        assert!(result.is_err());
    }

    #[test]
    fn test_routing_criteria_display() {
        assert_eq!(RoutingCriteria::Cost.to_string(), "cost");
        assert_eq!(RoutingCriteria::Latency.to_string(), "latency");
        assert_eq!(RoutingCriteria::Balanced.to_string(), "balanced");
    }
}
