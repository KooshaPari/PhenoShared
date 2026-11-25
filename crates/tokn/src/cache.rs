// Caching and aggregation logic for coverage reports and unpriced events

use std::collections::{BTreeMap, HashSet};
use std::path::Path;

use anyhow::Result;
use chrono::Datelike;

use crate::cli::IngestProvider;
use crate::models::*;

pub fn build_coverage_report(events: &[UsageEvent], pricing: &PricingBook) -> CoverageReport {
    let mut missing_providers = Vec::new();
    let mut missing_models_by_provider: BTreeMap<String, HashSet<String>> = BTreeMap::new();
    let mut model_counts_by_provider: BTreeMap<String, BTreeMap<String, usize>> = BTreeMap::new();
    let mut priced_count = 0;
    let mut unpriced_count = 0;

    for event in events {
        let provider_name = resolve_provider_alias(&event.provider, pricing);
        if !pricing.providers.contains_key(&provider_name) {
            if !missing_providers.contains(&provider_name) {
                missing_providers.push(provider_name.clone());
            }
            unpriced_count += 1;
            continue;
        }

        let provider = &pricing.providers[&provider_name];
        let model_name = resolve_model_alias(&provider_name, &event.model, pricing);
        if !provider.models.contains_key(&model_name) {
            missing_models_by_provider
                .entry(provider_name.clone())
                .or_insert_with(HashSet::new)
                .insert(model_name.clone());
            model_counts_by_provider
                .entry(provider_name.clone())
                .or_insert_with(BTreeMap::new)
                .entry(model_name)
                .and_modify(|count| *count += 1)
                .or_insert(1);
            unpriced_count += 1;
        } else {
            priced_count += 1;
        }
    }

    // Convert HashSets to sorted Vecs for missing_models_by_provider
    let missing_models_by_provider_vecs = missing_models_by_provider
        .into_iter()
        .map(|(k, v)| {
            let mut sorted: Vec<String> = v.into_iter().collect();
            sorted.sort();
            (k, sorted)
        })
        .collect();

    // Build suggested provider aliases for missing providers
    let mut suggested_provider_aliases: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for missing_provider in &missing_providers {
        let mut suggestions: Vec<String> = pricing.provider_aliases.keys().cloned().collect();
        if !suggestions.is_empty() {
            suggestions.sort();
            suggested_provider_aliases.insert(missing_provider.clone(), suggestions);
        }
    }

    // Build suggested model aliases by provider
    let suggested_model_aliases_by_provider: BTreeMap<String, Vec<UnknownModelSuggestion>> =
        model_counts_by_provider
            .into_iter()
            .map(|(provider, model_counts)| {
                let mut suggestions: Vec<UnknownModelSuggestion> = model_counts
                    .into_iter()
                    .map(|(model, count)| UnknownModelSuggestion { model, count })
                    .collect();
                suggestions.sort_by_key(|s| std::cmp::Reverse(s.count));
                (provider, suggestions)
            })
            .collect();

    let month = if events.is_empty() {
        "0000-00".to_string()
    } else {
        format!(
            "{:04}-{:02}",
            events[0].timestamp.year(),
            events[0].timestamp.month()
        )
    };

    let mut totals_tokens = 0u64;
    for event in events {
        totals_tokens += event.usage.total();
    }

    CoverageReport {
        month,
        totals: crate::models::CoverageTotals {
            events: events.len(),
            tokens: totals_tokens,
        },
        priced_count,
        unpriced_count,
        missing_providers,
        missing_models_by_provider: missing_models_by_provider_vecs,
        suggested_provider_aliases,
        suggested_model_aliases_by_provider,
    }
}

pub fn collect_unpriced_events(events: &[UsageEvent], pricing: &PricingBook) -> Vec<UsageEvent> {
    events
        .iter()
        .filter(|event| {
            let provider_name = resolve_provider_alias(&event.provider, pricing);
            if !pricing.providers.contains_key(&provider_name) {
                return true;
            }
            let provider = &pricing.providers[&provider_name];
            let model_name = resolve_model_alias(&provider_name, &event.model, pricing);
            !provider.models.contains_key(&model_name)
        })
        .cloned()
        .collect()
}

pub fn maybe_write_unpriced_outputs(
    _events: &[UsageEvent],
    _unpriced: &[UsageEvent],
    _pricing: &PricingBook,
    patch_path: Option<&Path>,
    unpriced_events_path: Option<&Path>,
) -> Result<()> {
    if patch_path.is_some() || unpriced_events_path.is_some() {
        // TODO: implement patch writing and unpriced events output
    }
    Ok(())
}

pub fn resolve_ingest_providers(
    providers: &[IngestProvider],
) -> Vec<IngestProvider> {
    if providers.is_empty() {
        vec![
            IngestProvider::Claude,
            IngestProvider::Codex,
            IngestProvider::Proxyapi,
            IngestProvider::Cursor,
            IngestProvider::Droid,
        ]
    } else {
        providers.to_vec()
    }
}

pub fn resolve_provider_alias(name: &str, pricing: &PricingBook) -> String {
    pricing
        .provider_aliases
        .get(name)
        .cloned()
        .unwrap_or_else(|| name.to_string())
}

pub fn resolve_model_alias(provider: &str, model: &str, pricing: &PricingBook) -> String {
    pricing
        .providers
        .get(provider)
        .and_then(|p| p.model_aliases.get(model).cloned())
        .unwrap_or_else(|| model.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::*;
    use std::collections::HashMap;

    fn test_pricing() -> PricingBook {
        let mut models = HashMap::new();
        models.insert(
            "gpt-4o".to_string(),
            ModelRate {
                input_usd_per_mtok: 2.5,
                output_usd_per_mtok: 10.0,
                cache_write_usd_per_mtok: None,
                cache_read_usd_per_mtok: None,
                tool_input_usd_per_mtok: None,
                tool_output_usd_per_mtok: None,
            },
        );
        let mut model_aliases = HashMap::new();
        model_aliases.insert("gpt-4o-2024-08-06".to_string(), "gpt-4o".to_string());
        let mut providers = HashMap::new();
        providers.insert(
            "openai".to_string(),
            ProviderPricing {
                subscription_usd_month: 5.0,
                models,
                model_aliases,
            },
        );
        let mut provider_aliases = HashMap::new();
        provider_aliases.insert("claude".to_string(), "anthropic".to_string());
        PricingBook {
            providers,
            provider_aliases,
            meta: None,
        }
    }

    fn test_event(provider: &str, model: &str) -> UsageEvent {
        UsageEvent {
            provider: provider.to_string(),
            model: model.to_string(),
            session_id: "sess-1".to_string(),
            timestamp: chrono::Utc::now(),
            usage: TokenUsage {
                input_tokens: 1000,
                output_tokens: 500,
                cache_write_tokens: 0,
                cache_read_tokens: 0,
                tool_input_tokens: 0,
                tool_output_tokens: 0,
            },
        }
    }

    #[test]
    fn test_resolve_provider_alias_found() {
        let pricing = test_pricing();
        assert_eq!(resolve_provider_alias("claude", &pricing), "anthropic");
    }

    #[test]
    fn test_resolve_provider_alias_not_found() {
        let pricing = test_pricing();
        assert_eq!(resolve_provider_alias("openai", &pricing), "openai");
    }

    #[test]
    fn test_resolve_model_alias_found() {
        let pricing = test_pricing();
        assert_eq!(
            resolve_model_alias("openai", "gpt-4o-2024-08-06", &pricing),
            "gpt-4o"
        );
    }

    #[test]
    fn test_resolve_model_alias_not_found() {
        let pricing = test_pricing();
        assert_eq!(
            resolve_model_alias("openai", "gpt-4o", &pricing),
            "gpt-4o"
        );
    }

    #[test]
    fn test_resolve_model_alias_unknown_provider() {
        let pricing = test_pricing();
        assert_eq!(
            resolve_model_alias("unknown", "some-model", &pricing),
            "some-model"
        );
    }

    #[test]
    fn test_resolve_ingest_providers_empty() {
        let result = resolve_ingest_providers(&[]);
        assert_eq!(result.len(), 5);
        assert!(result.contains(&IngestProvider::Claude));
        assert!(result.contains(&IngestProvider::Codex));
        assert!(result.contains(&IngestProvider::Proxyapi));
        assert!(result.contains(&IngestProvider::Cursor));
        assert!(result.contains(&IngestProvider::Droid));
    }

    #[test]
    fn test_resolve_ingest_providers_explicit() {
        let providers = vec![IngestProvider::Claude];
        let result = resolve_ingest_providers(&providers);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0], IngestProvider::Claude);
    }

    #[test]
    fn test_collect_unpriced_events_none() {
        let pricing = test_pricing();
        let events = vec![test_event("openai", "gpt-4o")];
        let unpriced = collect_unpriced_events(&events, &pricing);
        assert!(unpriced.is_empty());
    }

    #[test]
    fn test_collect_unpriced_events_all() {
        let pricing = test_pricing();
        let events = vec![test_event("openai", "unknown-model")];
        let unpriced = collect_unpriced_events(&events, &pricing);
        assert_eq!(unpriced.len(), 1);
    }

    #[test]
    fn test_collect_unpriced_events_mixed() {
        let pricing = test_pricing();
        let events = vec![
            test_event("openai", "gpt-4o"),
            test_event("openai", "unknown-model"),
            test_event("unknown-provider", "gpt-4o"),
        ];
        let unpriced = collect_unpriced_events(&events, &pricing);
        assert_eq!(unpriced.len(), 2);
    }

    #[test]
    fn test_build_coverage_report_basic() {
        let pricing = test_pricing();
        let events = vec![test_event("openai", "gpt-4o")];
        let report = build_coverage_report(&events, &pricing);
        assert_eq!(report.totals.events, 1);
        assert_eq!(report.priced_count, 1);
        assert_eq!(report.unpriced_count, 0);
        assert!(report.missing_providers.is_empty());
    }

    #[test]
    fn test_build_coverage_report_unpriced() {
        let pricing = test_pricing();
        let events = vec![
            test_event("openai", "unknown-model"),
            test_event("openai", "unknown-model-2"),
        ];
        let report = build_coverage_report(&events, &pricing);
        assert_eq!(report.unpriced_count, 2);
        assert_eq!(report.priced_count, 0);
    }

    #[test]
    fn test_build_coverage_report_missing_provider() {
        let pricing = test_pricing();
        let events = vec![test_event("new-provider", "some-model")];
        let report = build_coverage_report(&events, &pricing);
        assert_eq!(report.missing_providers.len(), 1);
        assert_eq!(report.missing_providers[0], "new-provider");
    }
}
