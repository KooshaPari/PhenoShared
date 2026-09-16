//! ParetoRs — pure cost calculation engine.
//!
//! No I/O, no external API calls. Pure functions only.

use crate::models::*;
use crate::pricing::DEFAULT_CALL_COST;
use crate::utils::RawHarnessRecord;

// ─── Core Cost Calculation ────────────────────────────────────────────────────

/// Calculate total cost for a call given token counts and pricing rates.
#[inline]
pub fn calc_total_cost(input_tokens: u64, output_tokens: u64, rate: PricingRate) -> f64 {
    if rate.use_default {
        return DEFAULT_CALL_COST;
    }
    let input_cost = (input_tokens as f64 / 1_000_000.0) * rate.input_per_m;
    let output_cost = (output_tokens as f64 / 1_000_000.0) * rate.output_per_m;
    input_cost + output_cost
}

/// Build a cost snapshot from raw call data and provider harness info.
#[allow(clippy::too_many_arguments)]
pub fn build_snapshot(
    id: String,
    provider: &str,
    model: &str,
    input_tokens: u64,
    output_tokens: u64,
    rate: PricingRate,
    latency_ms: Option<f64>,
    routing_criteria: Option<RoutingCriteria>,
    routing_score: Option<f64>,
    timestamp: chrono::DateTime<chrono::Utc>,
) -> CostSnapshot {
    let total_cost = calc_total_cost(input_tokens, output_tokens, rate);
    CostSnapshot {
        id,
        provider: provider.to_string(),
        model: model.to_string(),
        input_tokens,
        output_tokens,
        input_cost: if rate.use_default {
            0.0
        } else {
            (input_tokens as f64 / 1_000_000.0) * rate.input_per_m
        },
        output_cost: if rate.use_default {
            0.0
        } else {
            (output_tokens as f64 / 1_000_000.0) * rate.output_per_m
        },
        total_cost,
        latency_ms,
        timestamp,
        routing_criteria: routing_criteria.map(|r| r.to_string()),
        routing_score,
    }
}

/// Aggregate costs from a list of snapshots.
pub fn aggregate_costs(snapshots: &[CostSnapshot]) -> CostAggregate {
    if snapshots.is_empty() {
        return CostAggregate {
            total_input_tokens: 0,
            total_output_tokens: 0,
            total_input_cost: 0.0,
            total_output_cost: 0.0,
            total_cost: 0.0,
            call_count: 0,
        };
    }
    let total_input_tokens: u64 = snapshots.iter().map(|s| s.input_tokens).sum();
    let total_output_tokens: u64 = snapshots.iter().map(|s| s.output_tokens).sum();
    let total_input_cost: f64 = snapshots.iter().map(|s| s.input_cost).sum();
    let total_output_cost: f64 = snapshots.iter().map(|s| s.output_cost).sum();
    let total_cost: f64 = snapshots.iter().map(|s| s.total_cost).sum();
    CostAggregate {
        total_input_tokens,
        total_output_tokens,
        total_input_cost,
        total_output_cost,
        total_cost,
        call_count: snapshots.len(),
    }
}

/// Aggregate costs grouped by provider.
pub fn aggregate_by_provider(snapshots: &[CostSnapshot]) -> Vec<ProviderCostAggregate> {
    use std::collections::HashMap;
    let mut map: HashMap<String, Vec<&CostSnapshot>> = HashMap::new();
    for s in snapshots {
        map.entry(s.provider.clone()).or_default().push(s);
    }
    let mut result: Vec<ProviderCostAggregate> = map
        .into_iter()
        .map(|(provider, group)| {
            let total_input_tokens: u64 = group.iter().map(|s| s.input_tokens).sum();
            let total_output_tokens: u64 = group.iter().map(|s| s.output_tokens).sum();
            let total_input_cost: f64 = group.iter().map(|s| s.input_cost).sum();
            let total_output_cost: f64 = group.iter().map(|s| s.output_cost).sum();
            let total_cost: f64 = group.iter().map(|s| s.total_cost).sum();
            let latencies: Vec<f64> = group.iter().filter_map(|s| s.latency_ms).collect();
            let avg_latency_ms = if latencies.is_empty() {
                None
            } else {
                Some(latencies.iter().sum::<f64>() / latencies.len() as f64)
            };
            ProviderCostAggregate {
                provider,
                total_input_tokens,
                total_output_tokens,
                total_input_cost,
                total_output_cost,
                total_cost,
                call_count: group.len(),
                avg_latency_ms,
            }
        })
        .collect();
    result.sort_by(|a, b| b.total_cost.partial_cmp(&a.total_cost).unwrap());
    result
}

/// Build pricing audits from raw harness records.
pub fn build_pricing_audits(
    records: &[RawHarnessRecord],
    price_map: &[ModelPricing],
    on_unpriced: OnUnpricedAction,
) -> Vec<PricingAudit> {
    let price_lookup: std::collections::HashMap<(String, String), ModelPricing> = price_map
        .iter()
        .map(|p| ((p.provider.clone(), p.model.clone()), p.clone()))
        .collect();

    let mut audits = Vec::new();
    for record in records {
        let key = (record.provider.clone(), record.model.clone());
        let pricing = price_lookup.get(&key);
        let (total_cost, input_cost, output_cost) = match pricing {
            Some(p) => {
                let ic = (record.input_tokens as f64 / 1_000_000.0) * p.input_per_m;
                let oc = (record.output_tokens as f64 / 1_000_000.0) * p.output_per_m;
                (ic + oc, ic, oc)
            }
            None => match on_unpriced {
                OnUnpricedAction::Error => {
                    continue;
                }
                _ => (0.0, 0.0, 0.0),
            },
        };
        audits.push(PricingAudit {
            provider: record.provider.clone(),
            model: record.model.clone(),
            input_tokens: record.input_tokens,
            output_tokens: record.output_tokens,
            input_cost,
            output_cost,
            total_cost,
            latency_ms: record.latency_ms,
            timestamp: record.timestamp,
            provider_price_per_m: pricing.cloned(),
        });
    }
    audits
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    fn test_rate() -> PricingRate {
        PricingRate {
            input_per_m: 2.5,
            output_per_m: 10.0,
            use_default: false,
        }
    }

    #[test]
    fn test_calc_total_cost_basic() {
        let cost = calc_total_cost(1_000_000, 500_000, test_rate());
        assert!((cost - 7.5).abs() < 0.001, "Expected ~7.5, got {}", cost);
    }

    #[test]
    fn test_calc_total_cost_zero_tokens() {
        let cost = calc_total_cost(0, 0, test_rate());
        assert_eq!(cost, 0.0);
    }

    #[test]
    fn test_calc_total_cost_default() {
        let rate = PricingRate {
            input_per_m: 0.0,
            output_per_m: 0.0,
            use_default: true,
        };
        let cost = calc_total_cost(1_000_000, 500_000, rate);
        assert_eq!(cost, DEFAULT_CALL_COST);
    }

    #[test]
    fn test_build_snapshot_basic() {
        let ts = Utc::now();
        let rate = test_rate();
        let snapshot = build_snapshot(
            "id-1".to_string(),
            "openai",
            "gpt-4o",
            1_000_000,
            500_000,
            rate,
            Some(150.0),
            Some(RoutingCriteria::Cost),
            Some(0.95),
            ts,
        );
        assert_eq!(snapshot.id, "id-1");
        assert_eq!(snapshot.provider, "openai");
        assert_eq!(snapshot.model, "gpt-4o");
        assert_eq!(snapshot.input_tokens, 1_000_000);
        assert_eq!(snapshot.output_tokens, 500_000);
        assert!((snapshot.total_cost - 7.5).abs() < 0.001);
        assert_eq!(snapshot.latency_ms, Some(150.0));
        assert_eq!(snapshot.routing_criteria, Some("cost".to_string()));
        assert_eq!(snapshot.routing_score, Some(0.95));
    }

    #[test]
    fn test_build_snapshot_default_rate() {
        let ts = Utc::now();
        let rate = PricingRate {
            input_per_m: 0.0,
            output_per_m: 0.0,
            use_default: true,
        };
        let snapshot = build_snapshot(
            "id-2".to_string(),
            "openai",
            "gpt-4o",
            1_000_000,
            500_000,
            rate,
            None,
            None,
            None,
            ts,
        );
        assert_eq!(snapshot.total_cost, DEFAULT_CALL_COST);
        assert_eq!(snapshot.input_cost, 0.0);
        assert_eq!(snapshot.output_cost, 0.0);
    }

    #[test]
    fn test_aggregate_costs_empty() {
        let agg = aggregate_costs(&[]);
        assert_eq!(agg.call_count, 0);
        assert_eq!(agg.total_cost, 0.0);
        assert_eq!(agg.total_input_tokens, 0);
        assert_eq!(agg.total_output_tokens, 0);
    }

    #[test]
    fn test_aggregate_costs_single() {
        let ts = Utc::now();
        let snapshot = CostSnapshot {
            id: "s1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            input_cost: 2.5,
            output_cost: 5.0,
            total_cost: 7.5,
            latency_ms: Some(100.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let agg = aggregate_costs(&[snapshot]);
        assert_eq!(agg.call_count, 1);
        assert_eq!(agg.total_cost, 7.5);
        assert_eq!(agg.total_input_tokens, 1_000_000);
        assert_eq!(agg.total_output_tokens, 500_000);
    }

    #[test]
    fn test_aggregate_costs_multiple() {
        let ts = Utc::now();
        let s1 = CostSnapshot {
            id: "s1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            input_cost: 2.5,
            output_cost: 5.0,
            total_cost: 7.5,
            latency_ms: Some(100.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let s2 = CostSnapshot {
            id: "s2".to_string(),
            provider: "anthropic".to_string(),
            model: "claude-3".to_string(),
            input_tokens: 2_000_000,
            output_tokens: 1_000_000,
            input_cost: 6.0,
            output_cost: 12.0,
            total_cost: 18.0,
            latency_ms: Some(200.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let agg = aggregate_costs(&[s1, s2]);
        assert_eq!(agg.call_count, 2);
        assert_eq!(agg.total_cost, 25.5);
        assert_eq!(agg.total_input_tokens, 3_000_000);
        assert_eq!(agg.total_output_tokens, 1_500_000);
    }

    #[test]
    fn test_aggregate_by_provider_empty() {
        let result = aggregate_by_provider(&[]);
        assert!(result.is_empty());
    }

    #[test]
    fn test_aggregate_by_provider_single_provider() {
        let ts = Utc::now();
        let s1 = CostSnapshot {
            id: "s1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            input_cost: 2.5,
            output_cost: 5.0,
            total_cost: 7.5,
            latency_ms: Some(100.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let s2 = CostSnapshot {
            id: "s2".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 2_000_000,
            output_tokens: 1_000_000,
            input_cost: 5.0,
            output_cost: 10.0,
            total_cost: 15.0,
            latency_ms: Some(200.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let result = aggregate_by_provider(&[s1, s2]);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].provider, "openai");
        assert_eq!(result[0].call_count, 2);
        assert_eq!(result[0].total_cost, 22.5);
        assert_eq!(result[0].avg_latency_ms, Some(150.0));
    }

    #[test]
    fn test_aggregate_by_provider_multiple_providers() {
        let ts = Utc::now();
        let s1 = CostSnapshot {
            id: "s1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            input_cost: 2.5,
            output_cost: 5.0,
            total_cost: 7.5,
            latency_ms: Some(100.0),
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let s2 = CostSnapshot {
            id: "s2".to_string(),
            provider: "anthropic".to_string(),
            model: "claude-3".to_string(),
            input_tokens: 2_000_000,
            output_tokens: 1_000_000,
            input_cost: 6.0,
            output_cost: 12.0,
            total_cost: 18.0,
            latency_ms: None,
            timestamp: ts,
            routing_criteria: None,
            routing_score: None,
        };
        let result = aggregate_by_provider(&[s1, s2]);
        assert_eq!(result.len(), 2);
        // Sorted by total cost descending
        assert_eq!(result[0].provider, "anthropic");
        assert_eq!(result[0].total_cost, 18.0);
        assert_eq!(result[0].avg_latency_ms, None);
        assert_eq!(result[1].provider, "openai");
        assert_eq!(result[1].total_cost, 7.5);
        assert_eq!(result[1].avg_latency_ms, Some(100.0));
    }

    #[test]
    fn test_build_pricing_audits_with_prices() {
        let ts = Utc::now();
        let records = vec![RawHarnessRecord {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            latency_ms: Some(100.0),
            success: true,
            timestamp: ts,
        }];
        let prices = vec![ModelPricing {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        }];
        let audits = build_pricing_audits(&records, &prices, OnUnpricedAction::Warn);
        assert_eq!(audits.len(), 1);
        assert_eq!(audits[0].total_cost, 7.5);
        assert_eq!(audits[0].input_cost, 2.5);
        assert_eq!(audits[0].output_cost, 5.0);
    }

    #[test]
    fn test_build_pricing_audits_unpriced_warn() {
        let ts = Utc::now();
        let records = vec![RawHarnessRecord {
            provider: "unknown".to_string(),
            model: "unknown-model".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            latency_ms: Some(100.0),
            success: true,
            timestamp: ts,
        }];
        let prices = vec![];
        let audits = build_pricing_audits(&records, &prices, OnUnpricedAction::Warn);
        assert_eq!(audits.len(), 1);
        assert_eq!(audits[0].total_cost, 0.0);
        assert_eq!(audits[0].input_cost, 0.0);
        assert_eq!(audits[0].output_cost, 0.0);
    }

    #[test]
    fn test_build_pricing_audits_unpriced_error() {
        let ts = Utc::now();
        let records = vec![RawHarnessRecord {
            provider: "unknown".to_string(),
            model: "unknown-model".to_string(),
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            latency_ms: Some(100.0),
            success: true,
            timestamp: ts,
        }];
        let prices = vec![];
        let audits = build_pricing_audits(&records, &prices, OnUnpricedAction::Error);
        assert!(audits.is_empty());
    }
}
