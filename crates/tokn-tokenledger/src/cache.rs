// Caching and aggregation logic for coverage reports and unpriced events

use std::collections::{BTreeMap, HashSet};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::Path;

use anyhow::{Context, Result};
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
                .or_default()
                .insert(model_name.clone());
            model_counts_by_provider
                .entry(provider_name.clone())
                .or_default()
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
    events: &[UsageEvent],
    unpriced: &[UsageEvent],
    _pricing: &PricingBook,
    patch_path: Option<&Path>,
    unpriced_events_path: Option<&Path>,
) -> Result<()> {
    if let Some(path) = unpriced_events_path {
        write_unpriced_jsonl(path, unpriced)?;
    }
    if let Some(path) = patch_path {
        write_unpriced_patch(path, events, unpriced)?;
    }
    Ok(())
}

fn write_unpriced_jsonl(path: &Path, events: &[UsageEvent]) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    let mut writer = BufWriter::new(file);
    for event in events {
        serde_json::to_writer(&mut writer, event)
            .with_context(|| format!("serializing event to {:?}", path))?;
        writer
            .write_all(b"\n")
            .with_context(|| format!("writing newline to {:?}", path))?;
    }
    writer
        .flush()
        .with_context(|| format!("flushing {:?}", path))?;
    Ok(())
}

fn write_unpriced_patch(path: &Path, events: &[UsageEvent], unpriced: &[UsageEvent]) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    // Build a minimal patch listing missing provider:model pairs with event counts
    let mut missing: BTreeMap<String, BTreeMap<String, usize>> = BTreeMap::new();
    for event in unpriced {
        *missing
            .entry(event.provider.clone())
            .or_default()
            .entry(event.model.clone())
            .or_default() += 1;
    }
    let patch = serde_json::json!({
        "generated_for_events": events.len(),
        "unpriced_event_count": unpriced.len(),
        "missing_providers": missing.keys().collect::<Vec<_>>(),
        "stub_rates": missing.iter().map(|(provider, models)| {
            (provider.clone(), serde_json::json!({
                "subscription_usd_month": 0.0,
                "models": models.keys().map(|m| (m.clone(), serde_json::json!({
                    "input_usd_per_mtok": 0.0,
                    "output_usd_per_mtok": 0.0,
                    "_observed_count": models[m],
                    "_note": "stub — fill in actual rates"
                }))).collect::<serde_json::Map<_, _>>()
            }))
        }).collect::<serde_json::Map<_, _>>()
    });
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, &patch)
        .with_context(|| format!("writing patch to {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing newline to {:?}", path))?;
    Ok(())
}

pub fn resolve_ingest_providers(providers: &[IngestProvider]) -> Vec<IngestProvider> {
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
    use chrono::Utc;

    #[test]
    fn test_resolve_provider_alias_no_alias() {
        let mut providers = std::collections::HashMap::new();
        providers.insert(
            "openai".to_string(),
            ProviderPricing {
                subscription_usd_month: 0.0,
                models: std::collections::HashMap::new(),
                model_aliases: std::collections::HashMap::new(),
            },
        );
        let pricing = PricingBook {
            providers,
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };

        let resolved = resolve_provider_alias("openai", &pricing);
        assert_eq!(resolved, "openai");
    }

    #[test]
    fn test_resolve_provider_alias_with_alias() {
        let mut providers = std::collections::HashMap::new();
        providers.insert(
            "openai".to_string(),
            ProviderPricing {
                subscription_usd_month: 0.0,
                models: std::collections::HashMap::new(),
                model_aliases: std::collections::HashMap::new(),
            },
        );
        let mut provider_aliases = std::collections::HashMap::new();
        provider_aliases.insert("oai".to_string(), "openai".to_string());
        let pricing = PricingBook {
            providers,
            provider_aliases,
            meta: None,
        };

        let resolved = resolve_provider_alias("oai", &pricing);
        assert_eq!(resolved, "openai");
    }

    #[test]
    fn test_resolve_model_alias_no_alias() {
        let mut models = std::collections::HashMap::new();
        models.insert(
            "gpt-4".to_string(),
            ModelRate {
                input_usd_per_mtok: 0.5,
                output_usd_per_mtok: 1.0,
                cache_write_usd_per_mtok: None,
                cache_read_usd_per_mtok: None,
                tool_input_usd_per_mtok: None,
                tool_output_usd_per_mtok: None,
            },
        );
        let mut providers = std::collections::HashMap::new();
        providers.insert(
            "openai".to_string(),
            ProviderPricing {
                subscription_usd_month: 0.0,
                models,
                model_aliases: std::collections::HashMap::new(),
            },
        );
        let pricing = PricingBook {
            providers,
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };

        let resolved = resolve_model_alias("openai", "gpt-4", &pricing);
        assert_eq!(resolved, "gpt-4");
    }

    #[test]
    fn test_resolve_model_alias_with_alias() {
        let mut models = std::collections::HashMap::new();
        models.insert(
            "gpt-4".to_string(),
            ModelRate {
                input_usd_per_mtok: 0.5,
                output_usd_per_mtok: 1.0,
                cache_write_usd_per_mtok: None,
                cache_read_usd_per_mtok: None,
                tool_input_usd_per_mtok: None,
                tool_output_usd_per_mtok: None,
            },
        );
        let mut model_aliases = std::collections::HashMap::new();
        model_aliases.insert("gpt-4-turbo".to_string(), "gpt-4".to_string());
        let mut providers = std::collections::HashMap::new();
        providers.insert(
            "openai".to_string(),
            ProviderPricing {
                subscription_usd_month: 0.0,
                models,
                model_aliases,
            },
        );
        let pricing = PricingBook {
            providers,
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };

        let resolved = resolve_model_alias("openai", "gpt-4-turbo", &pricing);
        assert_eq!(resolved, "gpt-4");
    }

    #[test]
    fn test_build_coverage_report_empty_events() {
        let pricing = PricingBook {
            providers: std::collections::HashMap::new(),
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };
        let events: Vec<UsageEvent> = vec![];

        let report = build_coverage_report(&events, &pricing);
        assert_eq!(report.priced_count, 0);
        assert_eq!(report.unpriced_count, 0);
        assert!(report.missing_providers.is_empty());
    }

    #[test]
    fn test_build_coverage_report_missing_provider() {
        let pricing = PricingBook {
            providers: std::collections::HashMap::new(),
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };
        let events = vec![UsageEvent {
            provider: "unknown".to_string(),
            model: "gpt-4".to_string(),
            session_id: "sess1".to_string(),
            timestamp: Utc::now(),
            usage: TokenUsage {
                input_tokens: 100,
                output_tokens: 100,
                cache_write_tokens: 0,
                cache_read_tokens: 0,
                tool_input_tokens: 0,
                tool_output_tokens: 0,
            },
            tenant_id: None,
        }];

        let report = build_coverage_report(&events, &pricing);
        assert_eq!(report.unpriced_count, 1);
        assert!(report.missing_providers.contains(&"unknown".to_string()));
    }

    #[test]
    fn test_resolve_ingest_providers_empty() {
        let resolved = resolve_ingest_providers(&[]);
        assert!(!resolved.is_empty());
        assert!(resolved.len() >= 5);
    }

    #[test]
    fn test_collect_unpriced_events_empty() {
        let pricing = PricingBook {
            providers: std::collections::HashMap::new(),
            provider_aliases: std::collections::HashMap::new(),
            meta: None,
        };
        let events: Vec<UsageEvent> = vec![];
        let unpriced = collect_unpriced_events(&events, &pricing);
        assert!(unpriced.is_empty());
    }
}
