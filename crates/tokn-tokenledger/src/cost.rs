// Cost calculation utilities

use std::collections::{BTreeMap, HashMap};
use std::hash::{Hash, Hasher};

use anyhow::{Result, anyhow};

use crate::format::{round2, round4};
use crate::models::*;
use pareto_rs::OnUnpricedAction;

pub const MTOK: f64 = 1_000_000.0;

pub fn compute_costs(
    events: &[UsageEvent],
    pricing: &PricingBook,
    on_unpriced: OnUnpricedAction,
) -> Result<CostBreakdown> {
    let mut global = Acc::default();
    let mut by_provider: BTreeMap<String, Acc> = BTreeMap::new();
    let mut by_model: BTreeMap<String, Acc> = BTreeMap::new();
    let mut provider_token_totals: HashMap<String, u64> = HashMap::new();
    let mut missing: BTreeMap<String, usize> = BTreeMap::new();

    for evt in events {
        if event_pricing(evt, pricing).is_some() {
            *provider_token_totals
                .entry(evt.provider.clone())
                .or_default() += evt.usage.total();
        } else {
            *missing
                .entry(format!("{}:{}", evt.provider, evt.model))
                .or_default() += 1;
        }
    }

    if on_unpriced == OnUnpricedAction::Error && !missing.is_empty() {
        let details = missing
            .iter()
            .map(|(key, count)| format!("{key} (events={count})"))
            .collect::<Vec<_>>()
            .join(", ");
        return Err(anyhow!(
            "unpriced events found: {}. Re-run with --on-unpriced skip to ignore them",
            details
        ));
    }

    for evt in events {
        let Some((provider, rate)) = event_pricing(evt, pricing) else {
            continue;
        };

        let variable_cost = calc_variable_cost(&evt.usage, rate);
        let provider_total_tokens = *provider_token_totals
            .get(&evt.provider)
            .ok_or_else(|| anyhow!("missing token totals for provider {}", evt.provider))?;
        let event_sub_alloc = allocate_subscription(
            evt.usage.total(),
            provider_total_tokens,
            provider.subscription_usd_month,
        );

        merge_acc(&mut global, evt, variable_cost, event_sub_alloc);
        merge_acc(
            by_provider.entry(evt.provider.clone()).or_default(),
            evt,
            variable_cost,
            event_sub_alloc,
        );
        merge_acc(
            by_model.entry(evt.model.clone()).or_default(),
            evt,
            variable_cost,
            event_sub_alloc,
        );
    }

    let total_subscription = global.subscription_allocated_usd;
    let provider_breakdown = build_breakdown(&by_provider);
    let model_breakdown = build_breakdown(&by_model);

    let sub_alloc = global.subscription_allocated_usd;
    let monthly_total = global.variable_cost_usd + sub_alloc;
    let mtok = global.tokens as f64 / MTOK;
    let blended = if mtok > 0.0 {
        monthly_total / mtok
    } else {
        0.0
    };

    Ok(CostBreakdown {
        variable_cost_usd: round2(global.variable_cost_usd),
        subscription_allocated_usd: round2(sub_alloc),
        monthly_total_usd: round2(monthly_total),
        blended_usd_per_mtok: round4(blended),
        total_tokens: global.tokens,
        total_mtok: round4(mtok),
        input_tokens: global.input_tokens,
        output_tokens: global.output_tokens,
        cache_write_tokens: global.cache_write_tokens,
        cache_read_tokens: global.cache_read_tokens,
        tool_input_tokens: global.tool_input_tokens,
        tool_output_tokens: global.tool_output_tokens,
        session_count: global.sessions.len(),
        skipped_unpriced_count: missing.values().copied().sum(),
        provider_breakdown,
        model_breakdown,
        suggestions: make_suggestions(&global, total_subscription),
    })
}

pub fn build_breakdown(items: &BTreeMap<String, Acc>) -> Vec<NamedMetric> {
    items
        .iter()
        .map(|(name, acc)| {
            let sub = acc.subscription_allocated_usd;
            let total = acc.variable_cost_usd + sub;
            let mtok = acc.tokens as f64 / MTOK;
            let tool_tokens = acc.tool_input_tokens + acc.tool_output_tokens;
            let tool_share = if acc.tokens == 0 {
                0.0
            } else {
                tool_tokens as f64 / acc.tokens as f64
            };
            NamedMetric {
                name: name.clone(),
                tokens: acc.tokens,
                mtok: round4(mtok),
                variable_cost_usd: round2(acc.variable_cost_usd),
                subscription_allocated_usd: round2(sub),
                total_cost_usd: round2(total),
                blended_usd_per_mtok: round4(if mtok > 0.0 { total / mtok } else { 0.0 }),
                session_count: acc.sessions.len(),
                tool_share: round4(tool_share),
            }
        })
        .collect()
}

pub fn merge_acc(acc: &mut Acc, evt: &UsageEvent, variable_cost: f64, sub_alloc: f64) {
    acc.tokens += evt.usage.total();
    acc.input_tokens += evt.usage.input_tokens;
    acc.output_tokens += evt.usage.output_tokens;
    acc.cache_write_tokens += evt.usage.cache_write_tokens;
    acc.cache_read_tokens += evt.usage.cache_read_tokens;
    acc.tool_input_tokens += evt.usage.tool_input_tokens;
    acc.tool_output_tokens += evt.usage.tool_output_tokens;
    acc.variable_cost_usd += variable_cost;
    acc.subscription_allocated_usd += sub_alloc;
    acc.sessions
        .insert(session_hash(&evt.provider, &evt.session_id));
}

pub fn session_hash(provider: &str, session_id: &str) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    provider.hash(&mut hasher);
    session_id.hash(&mut hasher);
    hasher.finish()
}

pub fn calc_variable_cost(usage: &TokenUsage, rate: &ModelRate) -> f64 {
    let cache_write = rate
        .cache_write_usd_per_mtok
        .unwrap_or(rate.input_usd_per_mtok);
    let cache_read = rate
        .cache_read_usd_per_mtok
        .unwrap_or(rate.input_usd_per_mtok * 0.1);
    let tool_in = rate
        .tool_input_usd_per_mtok
        .unwrap_or(rate.input_usd_per_mtok);
    let tool_out = rate
        .tool_output_usd_per_mtok
        .unwrap_or(rate.output_usd_per_mtok);

    (usage.input_tokens as f64 / MTOK) * rate.input_usd_per_mtok
        + (usage.output_tokens as f64 / MTOK) * rate.output_usd_per_mtok
        + (usage.cache_write_tokens as f64 / MTOK) * cache_write
        + (usage.cache_read_tokens as f64 / MTOK) * cache_read
        + (usage.tool_input_tokens as f64 / MTOK) * tool_in
        + (usage.tool_output_tokens as f64 / MTOK) * tool_out
}

pub fn allocate_subscription(item_tokens: u64, total_tokens: u64, subscription: f64) -> f64 {
    if total_tokens == 0 {
        0.0
    } else {
        subscription * (item_tokens as f64 / total_tokens as f64)
    }
}

pub fn make_suggestions(global: &Acc, total_subscription: f64) -> Vec<String> {
    let mut tips = Vec::new();
    let total_tokens = global.tokens as f64;
    if total_tokens > 0.0 {
        let tool_share =
            (global.tool_input_tokens + global.tool_output_tokens) as f64 / total_tokens;
        if tool_share > 0.35 {
            tips.push("Tool-token share is high (>35%): add per-tool budgets and short-circuit low-value tool calls.".to_string());
        }
        let cache_share = global.cache_read_tokens as f64 / total_tokens;
        if cache_share < 0.10 {
            tips.push("Cache-read share is low (<10%): improve prompt prefix reuse and session stickiness for Claude-style caching.".to_string());
        }
        let var_per_mtok = global.variable_cost_usd / (total_tokens / MTOK);
        if var_per_mtok > 12.0 {
            tips.push("Blended variable $/MTok is high: route low-complexity jobs to cheaper models/providers via policy rules.".to_string());
        }
    }
    let total_monthly = global.variable_cost_usd + total_subscription;
    if total_monthly > 0.0 && total_subscription / total_monthly > 0.7 {
        tips.push("Subscriptions dominate monthly cost (>70%): consolidate seats/plans or increase utilization with shared routing.".to_string());
    }
    if tips.is_empty() {
        tips.push("No obvious anomalies detected; keep collecting session-level data and compare 4-week trend deltas.".to_string());
    }
    tips
}

// Helper function to get event pricing - uses utils functions
/// Filter usage events by an optional tenant_id.
/// Returns all events when `tenant_id` is `None`.
pub fn filter_tenant<'a>(events: &'a [UsageEvent], tenant_id: Option<&str>) -> Vec<&'a UsageEvent> {
    match tenant_id {
        None => events.iter().collect(),
        Some(tid) => events
            .iter()
            .filter(|e| e.tenant_id.as_deref() == Some(tid))
            .collect(),
    }
}

pub fn event_pricing<'a>(
    evt: &UsageEvent,
    pricing: &'a PricingBook,
) -> Option<(&'a ProviderPricing, &'a ModelRate)> {
    let provider_name = crate::utils::resolve_provider_alias(&evt.provider, pricing);
    let provider = pricing.providers.get(&provider_name)?;
    let model_name = crate::utils::resolve_model_alias(&provider_name, &evt.model, pricing);
    let rate = provider.models.get(&model_name)?;
    Some((provider, rate))
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[test]
    fn test_calc_variable_cost_basic() {
        let usage = TokenUsage {
            input_tokens: 1_000_000,
            output_tokens: 1_000_000,
            cache_write_tokens: 0,
            cache_read_tokens: 0,
            tool_input_tokens: 0,
            tool_output_tokens: 0,
        };
        let rate = ModelRate {
            input_usd_per_mtok: 0.5,
            output_usd_per_mtok: 1.0,
            cache_write_usd_per_mtok: None,
            cache_read_usd_per_mtok: None,
            tool_input_usd_per_mtok: None,
            tool_output_usd_per_mtok: None,
        };
        let cost = calc_variable_cost(&usage, &rate);
        assert!((cost - 1.5).abs() < 0.0001);
    }

    #[test]
    fn test_calc_variable_cost_with_cache() {
        let usage = TokenUsage {
            input_tokens: 1_000_000,
            output_tokens: 1_000_000,
            cache_write_tokens: 1_000_000,
            cache_read_tokens: 1_000_000,
            tool_input_tokens: 0,
            tool_output_tokens: 0,
        };
        let rate = ModelRate {
            input_usd_per_mtok: 0.5,
            output_usd_per_mtok: 1.0,
            cache_write_usd_per_mtok: Some(0.1),
            cache_read_usd_per_mtok: Some(0.05),
            tool_input_usd_per_mtok: None,
            tool_output_usd_per_mtok: None,
        };
        let cost = calc_variable_cost(&usage, &rate);
        // 0.5 (input) + 1.0 (output) + 0.1 (cache_write) + 0.05 (cache_read) = 1.65
        assert!((cost - 1.65).abs() < 0.0001);
    }

    #[test]
    fn test_allocate_subscription_full() {
        let allocated = allocate_subscription(1_000_000, 1_000_000, 100.0);
        assert!((allocated - 100.0).abs() < 0.01);
    }

    #[test]
    fn test_allocate_subscription_half() {
        let allocated = allocate_subscription(500_000, 1_000_000, 100.0);
        assert!((allocated - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_allocate_subscription_zero_total() {
        let allocated = allocate_subscription(1_000, 0, 100.0);
        assert_eq!(allocated, 0.0);
    }

    #[test]
    fn test_allocate_subscription_zero_monthly() {
        let allocated = allocate_subscription(1_000, 2_000, 0.0);
        assert_eq!(allocated, 0.0);
    }

    #[test]
    fn test_session_hash_consistency() {
        let provider = "openai";
        let session_id1 = "session123";
        let session_id2 = "session123";
        let session_id3 = "session456";

        let hash1 = session_hash(provider, session_id1);
        let hash2 = session_hash(provider, session_id2);
        let hash3 = session_hash(provider, session_id3);

        assert_eq!(hash1, hash2);
        assert_ne!(hash1, hash3);
    }

    #[test]
    fn test_session_hash_provider_affects_hash() {
        let session_id = "session123";
        let hash1 = session_hash("openai", session_id);
        let hash2 = session_hash("anthropic", session_id);
        assert_ne!(hash1, hash2);
    }

    #[test]
    fn test_calc_variable_cost_zero_tokens() {
        let usage = TokenUsage {
            input_tokens: 0,
            output_tokens: 0,
            cache_write_tokens: 0,
            cache_read_tokens: 0,
            tool_input_tokens: 0,
            tool_output_tokens: 0,
        };
        let rate = ModelRate {
            input_usd_per_mtok: 0.5,
            output_usd_per_mtok: 1.0,
            cache_write_usd_per_mtok: None,
            cache_read_usd_per_mtok: None,
            tool_input_usd_per_mtok: None,
            tool_output_usd_per_mtok: None,
        };
        let cost = calc_variable_cost(&usage, &rate);
        assert_eq!(cost, 0.0);
    }

    #[test]
    fn test_calc_variable_cost_tool_tokens() {
        let usage = TokenUsage {
            input_tokens: 1_000_000,
            output_tokens: 0,
            cache_write_tokens: 0,
            cache_read_tokens: 0,
            tool_input_tokens: 1_000_000,
            tool_output_tokens: 1_000_000,
        };
        let rate = ModelRate {
            input_usd_per_mtok: 0.5,
            output_usd_per_mtok: 1.0,
            cache_write_usd_per_mtok: None,
            cache_read_usd_per_mtok: None,
            tool_input_usd_per_mtok: Some(0.2),
            tool_output_usd_per_mtok: Some(0.3),
        };
        let cost = calc_variable_cost(&usage, &rate);
        // 0.5 (input) + 0.2 (tool_input) + 0.3 (tool_output) = 1.0
        assert!((cost - 1.0).abs() < 0.0001);
    }

    #[test]
    fn test_filter_tenant_none_returns_all() {
        let events = vec![
            UsageEvent {
                provider: "openai".into(),
                model: "gpt-4".into(),
                session_id: "s1".into(),
                timestamp: Utc::now(),
                usage: TokenUsage::default(),
                tenant_id: Some("acme".into()),
            },
            UsageEvent {
                provider: "anthropic".into(),
                model: "claude-3".into(),
                session_id: "s2".into(),
                timestamp: Utc::now(),
                usage: TokenUsage::default(),
                tenant_id: None,
            },
        ];
        let filtered = filter_tenant(&events, None);
        assert_eq!(filtered.len(), 2);
    }

    #[test]
    fn test_filter_tenant_matching() {
        let events = vec![
            UsageEvent {
                provider: "openai".into(),
                model: "gpt-4".into(),
                session_id: "s1".into(),
                timestamp: Utc::now(),
                usage: TokenUsage::default(),
                tenant_id: Some("acme".into()),
            },
            UsageEvent {
                provider: "anthropic".into(),
                model: "claude-3".into(),
                session_id: "s2".into(),
                timestamp: Utc::now(),
                usage: TokenUsage::default(),
                tenant_id: Some("globex".into()),
            },
        ];
        let filtered = filter_tenant(&events, Some("acme"));
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].tenant_id.as_deref(), Some("acme"));
    }

    #[test]
    fn test_filter_tenant_no_match() {
        let events = vec![UsageEvent {
            provider: "openai".into(),
            model: "gpt-4".into(),
            session_id: "s1".into(),
            timestamp: Utc::now(),
            usage: TokenUsage::default(),
            tenant_id: Some("acme".into()),
        }];
        let filtered = filter_tenant(&events, Some("nobody"));
        assert!(filtered.is_empty());
    }
}
