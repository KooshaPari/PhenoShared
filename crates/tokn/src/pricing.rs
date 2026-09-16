use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Datelike, Utc};
use serde_json::Value;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use crate::cli::{
    PricingApplyArgs, PricingAuditArgs, PricingCheckArgs, PricingLintArgs, PricingReconcileArgs,
};
use crate::models::*;
use crate::utils::*;

pub fn run_pricing_check(args: PricingCheckArgs) -> Result<()> {
    let (report, check_result) = run_pricing_check_stage(
        &args.events,
        &args.pricing,
        args.month.as_deref(),
        args.allow_unpriced,
        args.write_patch.as_deref(),
        args.write_unpriced_events.as_deref(),
    )?;

    if check_result.unpriced_count == 0 {
        println!(
            "pricing-check passed: month={} events={} priced={} unpriced={}",
            report.month, report.totals.events, report.priced_count, report.unpriced_count
        );
        return Ok(());
    }

    let details = check_result.details.join(", ");

    if args.allow_unpriced {
        eprintln!(
            "pricing-check warning: month={} events={} priced={} unpriced={}: {}",
            report.month, report.totals.events, report.priced_count, report.unpriced_count, details
        );
        return Ok(());
    }

    Err(anyhow!(
        "pricing-check failed: month={} events={} priced={} unpriced={}: {}. Re-run with --allow-unpriced to continue",
        report.month, report.totals.events, report.priced_count, report.unpriced_count, details
    ))
}

pub fn run_pricing_apply(args: PricingApplyArgs) -> Result<()> {
    let apply_result = apply_pricing_patch_file(
        &args.pricing,
        &args.patch,
        args.dry_run,
        args.write_backup,
        args.allow_overwrite_model_rates,
    )?;
    println!("{}", serde_json::to_string_pretty(&apply_result.summary)?);
    Ok(())
}

pub fn run_pricing_reconcile(args: PricingReconcileArgs) -> Result<()> {
    let outcome = execute_pricing_reconcile(args)?;
    println!("{}", serde_json::to_string_pretty(&outcome.summary)?);
    if outcome.fail_for_unpriced {
        return Err(anyhow!(
            "pricing-reconcile failed: unpriced events remain after apply; re-run with --allow-unpriced to continue"
        ));
    }
    Ok(())
}

pub fn execute_pricing_reconcile(args: PricingReconcileArgs) -> Result<PricingReconcileOutcome> {
    fs::create_dir_all(&args.workdir)
        .with_context(|| format!("creating reconcile workdir {:?}", args.workdir))?;

    let patch_path = args.workdir.join("pricing-patch.reconcile.json");
    let unpriced_events_path = args.workdir.join("unpriced-events.reconcile.jsonl");

    let pricing = load_pricing(&args.pricing)?;
    let events = load_events(&args.events)?;
    let normalized = normalize_events(events.clone(), &pricing);
    let filtered = filter_month(normalized, args.month.as_deref())?;
    if filtered.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }

    let coverage_report = build_coverage_report(&filtered, &pricing);
    let unpriced_events = collect_unpriced_events(&filtered, &pricing);
    maybe_write_unpriced_outputs(
        &filtered,
        &unpriced_events,
        &pricing,
        Some(&patch_path),
        Some(&unpriced_events_path),
    )?;

    let apply_result = apply_pricing_patch_file(
        &args.pricing,
        &patch_path,
        args.dry_run,
        args.write_backup,
        args.allow_overwrite_model_rates,
    )?;
    let metadata_updated = if !args.dry_run && apply_result.wrote_pricing {
        stamp_reconcile_metadata(&args.pricing)?
    } else {
        false
    };

    let pricing_for_check = if args.dry_run {
        apply_result
            .pricing_after
            .as_ref()
            .unwrap_or(&pricing)
            .clone()
    } else {
        load_pricing(&args.pricing)?
    };
    let normalized_after = normalize_events(events, &pricing_for_check);
    let filtered_after = filter_month(normalized_after, args.month.as_deref())?;
    if filtered_after.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }
    let check_report = build_coverage_report(&filtered_after, &pricing_for_check);
    let check_details = summarize_unpriced_pairs(&collect_unpriced_events(
        &filtered_after,
        &pricing_for_check,
    ));
    let check_stage = PricingReconcileCheckResult {
        passed: check_report.unpriced_count == 0 || args.allow_unpriced,
        month: check_report.month.clone(),
        priced_count: check_report.priced_count,
        unpriced_count: check_report.unpriced_count,
        details: check_details,
    };

    let summary = PricingReconcileSummary {
        pricing: args.pricing.display().to_string(),
        month_filter: args.month.clone(),
        workdir: args.workdir.display().to_string(),
        allow_unpriced: args.allow_unpriced,
        dry_run: args.dry_run,
        write_backup: args.write_backup,
        allow_overwrite_model_rates: args.allow_overwrite_model_rates,
        artifacts: PricingReconcileArtifacts {
            patch_path: patch_path.display().to_string(),
            unpriced_events_path: unpriced_events_path.display().to_string(),
            backup_path: apply_result
                .backup_path
                .map(|path| path.display().to_string()),
        },
        coverage: coverage_report,
        pricing_apply: PricingReconcileApplyResult {
            changed: apply_result.changed,
            wrote_pricing: apply_result.wrote_pricing,
            metadata_updated,
            summary: apply_result.summary,
        },
        pricing_check: check_stage,
    };

    Ok(PricingReconcileOutcome {
        fail_for_unpriced: !summary.pricing_check.passed,
        summary,
    })
}

pub fn run_pricing_lint(args: PricingLintArgs) -> Result<()> {
    let pricing = load_pricing(&args.pricing)?;
    let mut violations = collect_pricing_placeholder_violations(&pricing);
    violations.sort();

    let summary = PricingLintSummary {
        pricing: args.pricing.display().to_string(),
        alias_integrity_ok: true,
        placeholder_violations: violations.clone(),
        allow_placeholders: args.allow_placeholders,
    };
    println!("{}", serde_json::to_string_pretty(&summary)?);

    if !violations.is_empty() && !args.allow_placeholders {
        return Err(anyhow!(
            "pricing-lint failed: found {} placeholder violation(s); re-run with --allow-placeholders to continue",
            violations.len()
        ));
    }
    Ok(())
}

pub fn run_pricing_audit(args: PricingAuditArgs) -> Result<()> {
    let report = execute_pricing_audit(&args)?;
    if args.json_output {
        println!("{}", serde_json::to_string_pretty(&report)?);
    } else {
        print_pricing_audit_report(&report);
    }

    if !report.pass {
        return Err(anyhow!(
            "pricing-audit failed with {} violation(s)",
            report.violations.len()
        ));
    }
    Ok(())
}

pub fn execute_pricing_audit(args: &PricingAuditArgs) -> Result<PricingAuditReport> {
    if args.max_age_days < 0 {
        return Err(anyhow!("--max-age-days must be >= 0"));
    }

    let pricing_text =
        fs::read_to_string(&args.pricing).with_context(|| format!("reading {:?}", args.pricing))?;
    let pricing_json: Value =
        serde_json::from_str(&pricing_text).context("parsing pricing json")?;
    load_pricing(&args.pricing)?;

    let checked_at = Utc::now();
    let meta = pricing_json.get("meta").and_then(Value::as_object);
    let metadata_present = meta.is_some();

    let source_value = meta
        .and_then(|m| m.get("source"))
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);
    let source_present = source_value.is_some();

    let updated_at_value = meta
        .and_then(|m| m.get("updated_at"))
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);
    let updated_at_present = updated_at_value.is_some();

    let mut age_days = None;
    let mut stale = false;
    let mut violations = Vec::new();
    let mut warnings = Vec::new();

    if !metadata_present {
        violations.push("missing metadata block `meta`".to_string());
    }
    if !source_present {
        let message = "missing metadata source `meta.source`".to_string();
        if args.allow_missing_source {
            warnings.push(message);
        } else {
            violations.push(message);
        }
    }
    match updated_at_value.as_deref() {
        Some(updated_at_raw) => {
            let parsed =
                DateTime::parse_from_rfc3339(updated_at_raw).map(|ts| ts.with_timezone(&Utc));
            match parsed {
                Ok(updated_at) => {
                    let days = checked_at.signed_duration_since(updated_at).num_days();
                    age_days = Some(days);
                    stale = days > args.max_age_days;
                    if stale {
                        let message = format!(
                            "stale pricing metadata: age_days={} exceeds max_age_days={}",
                            days, args.max_age_days
                        );
                        if args.allow_stale {
                            warnings.push(message);
                        } else {
                            violations.push(message);
                        }
                    }
                }
                Err(_) => violations.push(
                    "invalid metadata timestamp `meta.updated_at` (expected RFC3339)".to_string(),
                ),
            }
        }
        None => violations.push("missing metadata timestamp `meta.updated_at`".to_string()),
    }

    Ok(PricingAuditReport {
        pricing_path: args.pricing.display().to_string(),
        checked_at: checked_at.to_rfc3339(),
        metadata_present,
        source_present,
        updated_at_present,
        age_days,
        stale,
        pass: violations.is_empty(),
        violations,
        warnings,
    })
}

pub fn run_pricing_check_stage(
    events_paths: &[PathBuf],
    pricing_path: &Path,
    month: Option<&str>,
    allow_unpriced: bool,
    write_patch: Option<&Path>,
    write_unpriced_events: Option<&Path>,
) -> Result<(CoverageReport, PricingReconcileCheckResult)> {
    let pricing = load_pricing(pricing_path)?;
    let events = load_events(events_paths)?;
    let normalized = normalize_events(events, &pricing);
    let filtered = filter_month(normalized, month)?;
    if filtered.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }

    let report = build_coverage_report(&filtered, &pricing);
    let unpriced_events = collect_unpriced_events(&filtered, &pricing);
    maybe_write_unpriced_outputs(
        &filtered,
        &unpriced_events,
        &pricing,
        write_patch,
        write_unpriced_events,
    )?;

    Ok((
        report.clone(),
        PricingReconcileCheckResult {
            passed: report.unpriced_count == 0 || allow_unpriced,
            month: report.month,
            priced_count: report.priced_count,
            unpriced_count: report.unpriced_count,
            details: summarize_unpriced_pairs(&unpriced_events),
        },
    ))
}

pub fn build_coverage_report(events: &[UsageEvent], pricing: &PricingBook) -> CoverageReport {
    let month = format!(
        "{:04}-{:02}",
        events[0].timestamp.year(),
        events[0].timestamp.month()
    );

    let mut priced_count = 0usize;
    let mut unpriced_count = 0usize;
    let mut total_tokens = 0_u64;
    let mut missing_providers = HashSet::new();
    let mut missing_models_by_provider: BTreeMap<String, HashSet<String>> = BTreeMap::new();
    let mut unknown_model_counts_by_provider: BTreeMap<String, HashMap<String, usize>> =
        BTreeMap::new();

    for event in events {
        total_tokens += event.usage.total();
        if event_pricing(event, pricing).is_some() {
            priced_count += 1;
            continue;
        }
        unpriced_count += 1;

        if !pricing.providers.contains_key(&event.provider) {
            missing_providers.insert(event.provider.clone());
            continue;
        }

        missing_models_by_provider
            .entry(event.provider.clone())
            .or_default()
            .insert(event.model.clone());
        *unknown_model_counts_by_provider
            .entry(event.provider.clone())
            .or_default()
            .entry(event.model.clone())
            .or_default() += 1;
    }

    let mut missing_providers: Vec<String> = missing_providers.into_iter().collect();
    missing_providers.sort();
    let missing_models_by_provider: BTreeMap<String, Vec<String>> = missing_models_by_provider
        .into_iter()
        .map(|(provider, models)| {
            let mut models: Vec<String> = models.into_iter().collect();
            models.sort();
            (provider, models)
        })
        .collect();

    let suggested_provider_aliases: BTreeMap<String, Vec<String>> = missing_providers
        .iter()
        .map(|provider| {
            (
                provider.clone(),
                suggest_aliases(provider, pricing.provider_aliases.keys()),
            )
        })
        .collect();

    let suggested_model_aliases_by_provider: BTreeMap<String, Vec<UnknownModelSuggestion>> =
        unknown_model_counts_by_provider
            .into_iter()
            .map(|(provider, counts)| {
                let mut suggestions: Vec<UnknownModelSuggestion> = counts
                    .into_iter()
                    .map(|(model, count)| UnknownModelSuggestion { model, count })
                    .collect();
                suggestions
                    .sort_by(|a, b| b.count.cmp(&a.count).then_with(|| a.model.cmp(&b.model)));
                (provider, suggestions)
            })
            .collect();

    CoverageReport {
        month,
        totals: CoverageTotals {
            events: events.len(),
            tokens: total_tokens,
        },
        priced_count,
        unpriced_count,
        missing_providers,
        missing_models_by_provider,
        suggested_provider_aliases,
        suggested_model_aliases_by_provider,
    }
}

pub fn collect_unpriced_events(events: &[UsageEvent], pricing: &PricingBook) -> Vec<UsageEvent> {
    events
        .iter()
        .filter(|event| event_pricing(event, pricing).is_none())
        .cloned()
        .collect()
}

pub fn maybe_write_unpriced_outputs(
    events: &[UsageEvent],
    unpriced_events: &[UsageEvent],
    pricing: &PricingBook,
    patch_path: Option<&Path>,
    unpriced_events_path: Option<&Path>,
) -> Result<()> {
    if let Some(path) = unpriced_events_path {
        write_jsonl_events(path, unpriced_events)?;
    }
    if let Some(path) = patch_path {
        let patch = build_pricing_patch(events, unpriced_events, pricing);
        write_pricing_patch(path, &patch)?;
    }
    Ok(())
}

pub fn write_jsonl_events(path: &Path, events: &[UsageEvent]) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    let mut writer = BufWriter::new(file);
    for event in events {
        serde_json::to_writer(&mut writer, event).with_context(|| format!("writing {:?}", path))?;
        writer
            .write_all(b"\n")
            .with_context(|| format!("writing newline {:?}", path))?;
    }
    writer
        .flush()
        .with_context(|| format!("flushing {:?}", path))?;
    Ok(())
}

pub fn write_pricing_patch(path: &Path, patch: &Value) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, patch)
        .with_context(|| format!("writing {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing newline {:?}", path))?;
    Ok(())
}

pub fn build_pricing_patch(
    events: &[UsageEvent],
    unpriced_events: &[UsageEvent],
    pricing: &PricingBook,
) -> Value {
    let month = format!(
        "{:04}-{:02}",
        events[0].timestamp.year(),
        events[0].timestamp.month()
    );
    let mut missing_providers: BTreeMap<String, BTreeMap<String, usize>> = BTreeMap::new();
    let mut missing_models_by_provider: BTreeMap<String, BTreeMap<String, usize>> = BTreeMap::new();

    for event in unpriced_events {
        if pricing.providers.contains_key(&event.provider) {
            *missing_models_by_provider
                .entry(event.provider.clone())
                .or_default()
                .entry(event.model.clone())
                .or_default() += 1;
        } else {
            *missing_providers
                .entry(event.provider.clone())
                .or_default()
                .entry(event.model.clone())
                .or_default() += 1;
        }
    }

    let missing_provider_entries = missing_providers
        .iter()
        .map(|(provider, models)| {
            let suggested_provider_aliases =
                suggest_aliases(provider, pricing.provider_aliases.keys());
            let observed_unpriced_models = models.keys().cloned().collect::<Vec<_>>();
            (
                provider.clone(),
                serde_json::json!({
                    "subscription_usd_month": 0.0,
                    "models": {},
                    "model_aliases": {},
                    "observed_unpriced_models": observed_unpriced_models,
                    "suggested_provider_aliases": suggested_provider_aliases
                }),
            )
        })
        .collect::<serde_json::Map<String, Value>>();

    let missing_models_entries = missing_models_by_provider
        .iter()
        .map(|(provider, models)| {
            (
                provider.clone(),
                Value::Object(
                    models
                        .keys()
                        .map(|model| {
                            (
                                model.clone(),
                                serde_json::json!({
                                    "input_usd_per_mtok": 0.0,
                                    "output_usd_per_mtok": 0.0,
                                    "cache_write_usd_per_mtok": Value::Null,
                                    "cache_read_usd_per_mtok": Value::Null,
                                    "tool_input_usd_per_mtok": Value::Null,
                                    "tool_output_usd_per_mtok": Value::Null
                                }),
                            )
                        })
                        .collect(),
                ),
            )
        })
        .collect::<serde_json::Map<String, Value>>();

    let suggested_provider_aliases = missing_providers
        .keys()
        .map(|provider| {
            let candidates = suggest_aliases(provider, pricing.provider_aliases.keys());
            (
                provider.clone(),
                Value::Array(candidates.into_iter().map(Value::String).collect()),
            )
        })
        .collect::<serde_json::Map<String, Value>>();

    let suggested_model_aliases_by_provider = missing_models_by_provider
        .iter()
        .map(|(provider, unknown_models)| {
            let Some(provider_pricing) = pricing.providers.get(provider) else {
                return (provider.clone(), Value::Object(serde_json::Map::new()));
            };
            let known_models = provider_pricing
                .models
                .keys()
                .chain(provider_pricing.model_aliases.keys())
                .cloned()
                .collect::<Vec<_>>();
            let model_suggestions = unknown_models
                .keys()
                .map(|unknown_model| {
                    let matches = suggest_aliases(unknown_model, known_models.iter());
                    (
                        unknown_model.clone(),
                        Value::Array(matches.into_iter().map(Value::String).collect()),
                    )
                })
                .collect::<serde_json::Map<String, Value>>();
            (provider.clone(), Value::Object(model_suggestions))
        })
        .collect::<serde_json::Map<String, Value>>();

    serde_json::json!({
        "metadata": {
            "generated_at": Utc::now(),
            "source_events_count": events.len(),
            "month": month
        },
        "missing_providers": missing_provider_entries,
        "missing_models_by_provider": missing_models_entries,
        "suggested_aliases": {
            "provider_aliases": suggested_provider_aliases,
            "model_aliases_by_provider": suggested_model_aliases_by_provider
        }
    })
}
