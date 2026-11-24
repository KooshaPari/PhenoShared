use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{self, File};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::{Path, PathBuf};

use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Datelike, Utc};

use crate::cli::{BenchScenario, OutputMode};
use crate::models::*;

// Re-export from specialized modules for backwards compatibility
pub use crate::cache::{
    build_coverage_report, collect_unpriced_events, maybe_write_unpriced_outputs,
    resolve_ingest_providers, resolve_model_alias, resolve_provider_alias,
};
pub use crate::cost::{
    allocate_subscription, build_breakdown, calc_variable_cost, compute_costs,
    event_pricing, make_suggestions, merge_acc, session_hash,
};
pub use crate::format::{
    default_generated_at, print_coverage_table, print_daily_markdown, print_daily_table,
    print_markdown, print_pricing_audit_report, print_table, round2, round4, top_rows,
};

pub const MTOK: f64 = 1_000_000.0;

// Performance gate checks
pub fn run_perf_gate_checks(
    report: &BenchReport,
    config: &PerfGateConfig,
    strict_mode: bool,
    baseline_used: bool,
) -> Result<()> {
    let mut failures = Vec::new();
    let has_regression_thresholds = config.scenarios.values().any(|threshold| {
        threshold.max_elapsed_regression_pct.is_some() || threshold.max_eps_drop_pct.is_some()
    });
    if strict_mode
        && (config.require_baseline_for_regression_checks || has_regression_thresholds)
        && !baseline_used
    {
        failures
            .push("strict mode requires baseline-backed deltas for regression checks".to_string());
    }

    let results_by_scenario: HashMap<&str, &BenchScenarioResult> = report
        .results
        .iter()
        .map(|result| (result.scenario.as_str(), result))
        .collect();

    for (scenario, gate) in &config.scenarios {
        let Some(result) = results_by_scenario.get(scenario.as_str()) else {
            failures.push(format!("{scenario}: missing benchmark result"));
            continue;
        };

        if result.elapsed_ms > gate.max_ms {
            failures.push(format!(
                "{scenario}: elapsed_ms {:.4} > max_ms {:.4}",
                result.elapsed_ms, gate.max_ms
            ));
        }
        if result.events_per_sec < gate.min_events_per_sec {
            failures.push(format!(
                "{scenario}: events_per_sec {:.4} < min_events_per_sec {:.4}",
                result.events_per_sec, gate.min_events_per_sec
            ));
        }

        if let (Some(delta), Some(max_pct)) =
            (result.elapsed_ms_delta, gate.max_elapsed_regression_pct)
        {
            if delta > 0.0 {
                let baseline_elapsed = result.elapsed_ms - delta;
                if baseline_elapsed > 0.0 {
                    let pct = (delta / baseline_elapsed) * 100.0;
                    if pct > max_pct {
                        failures.push(format!(
                            "{scenario}: elapsed regression {:.2}% > max_elapsed_regression_pct {:.2}%",
                            pct, max_pct
                        ));
                    }
                }
            }
        }

        if let (Some(delta), Some(max_pct)) = (result.events_per_sec_delta, gate.max_eps_drop_pct) {
            if delta < 0.0 {
                let baseline_eps = result.events_per_sec - delta;
                if baseline_eps > 0.0 {
                    let pct = ((-delta) / baseline_eps) * 100.0;
                    if pct > max_pct {
                        failures.push(format!(
                            "{scenario}: events/sec drop {:.2}% > max_eps_drop_pct {:.2}%",
                            pct, max_pct
                        ));
                    }
                }
            }
        }
    }

    if failures.is_empty() {
        eprintln!("performance gate passed");
        return Ok(());
    }

    Err(anyhow!(
        "performance gate FAILED\n{}",
        failures.join("\n")
    ))
}

pub fn fail_on_bench_trend_regressions(report: &BenchTrendReport) -> Result<()> {
    let mut failures = Vec::new();

    for scenario in &report.scenarios {
        let regress_pct = ((scenario.latest_elapsed_ms - scenario.median_elapsed_ms)
            / scenario.median_elapsed_ms)
            * 100.0;
        if regress_pct > 5.0 {
            failures.push(format!(
                "{}: latest {:.2}ms is {:.2}% slower than median {:.2}ms",
                scenario.scenario, scenario.latest_elapsed_ms, regress_pct, scenario.median_elapsed_ms
            ));
        }

        let eps_change_pct = ((scenario.latest_events_per_sec - scenario.median_events_per_sec)
            / scenario.median_events_per_sec)
            * 100.0;
        if eps_change_pct < -5.0 {
            failures.push(format!(
                "{}: latest {:.2} eps is {:.2}% slower than median {:.2} eps",
                scenario.scenario, scenario.latest_events_per_sec, -eps_change_pct, scenario.median_events_per_sec
            ));
        }
    }

    if failures.is_empty() {
        eprintln!("bench trend analysis passed");
        return Ok(());
    }

    Err(anyhow!(
        "bench trend analysis FAILED\n{}",
        failures.join("\n")
    ))
}

pub fn bench_scenario_name(scenario: BenchScenario) -> &'static str {
    match scenario {
        BenchScenario::ColdBackfill => "cold-backfill",
        BenchScenario::WarmTail => "warm-tail",
        BenchScenario::Burst => "burst",
        BenchScenario::All => "all",
    }
}

pub fn print_bench_table(report: &BenchReport) {
    // Check if any result has deltas
    let has_deltas = report.results.iter().any(|r| r.elapsed_ms_delta.is_some() || r.events_per_sec_delta.is_some());

    if has_deltas {
        println!("Benchmark Results with Deltas");
        println!(
            "  {:<15} {:>12} {:>18} {:>18} {:>12} {:>12} {:>10}",
            "Scenario", "Elapsed (ms)", "Events", "Events/sec", "Delta ms", "Delta eps", "Regress"
        );
        for result in &report.results {
            let regress_flag = if let Some(delta) = result.events_per_sec_delta {
                if delta < 0.0 {
                    "REGRESS"
                } else {
                    ""
                }
            } else {
                ""
            };
            println!(
                "  {:<15} {:>12.4} {:>18} {:>18.4} {:>12} {:>12} {:>10}",
                result.scenario,
                result.elapsed_ms,
                result.events_processed,
                result.events_per_sec,
                result
                    .elapsed_ms_delta
                    .map(|v| format!("{v:.4}"))
                    .unwrap_or_else(|| "-".to_string()),
                result
                    .events_per_sec_delta
                    .map(|v| format!("{v:.4}"))
                    .unwrap_or_else(|| "-".to_string()),
                regress_flag
            );
        }
    } else {
        println!(
            "  {:<15} {:>12} {:>18} {:>18}",
            "Scenario", "Elapsed (ms)", "Events", "Events/sec"
        );
        for result in &report.results {
            println!(
                "  {:<15} {:>12.4} {:>18} {:>18.4}",
                result.scenario, result.elapsed_ms, result.events_processed, result.events_per_sec
            );
        }
    }
}

pub fn print_bench_trend_table(report: &BenchTrendReport) {
    println!("Benchmark trend summary (dir={})", report.trend_dir);
    println!(
        "  {:<15} {:>10} {:>14} {:>14} {:>14} {:>18} {:>18}",
        "Scenario", "Runs", "Latest ms", "Median ms", "p95 ms", "Latest eps", "Median eps"
    );
    for scenario in &report.scenarios {
        println!(
            "  {:<15} {:>10} {:>14.4} {:>14.4} {:>14.4} {:>18.4} {:>18.4}",
            scenario.scenario,
            scenario.run_count,
            scenario.latest_elapsed_ms,
            scenario.median_elapsed_ms,
            scenario.p95_elapsed_ms,
            scenario.latest_events_per_sec,
            scenario.median_events_per_sec,
        );
    }
}

pub fn load_pricing(path: &Path) -> Result<PricingBook> {
    let pricing: PricingBook =
        serde_json::from_reader(File::open(path).with_context(|| format!("opening {:?}", path))?)
            .context("parsing pricing json")?;
    validate_aliases(&pricing)?;
    Ok(pricing)
}

pub fn load_pricing_patch(path: &Path) -> Result<PricingPatch> {
    let patch: PricingPatch =
        serde_json::from_reader(File::open(path).with_context(|| format!("opening {:?}", path))?)
            .context("parsing pricing patch json")?;
    Ok(patch)
}

#[derive(Debug, Clone)]
pub struct PricingApplyExecution {
    pub summary: PricingApplySummary,
    pub changed: bool,
    pub wrote_pricing: bool,
    pub backup_path: Option<PathBuf>,
    pub pricing_after: Option<PricingBook>,
}

pub fn apply_pricing_patch_file(
    pricing_path: &Path,
    patch_path: &Path,
    dry_run: bool,
    write_backup: bool,
    allow_overwrite_model_rates: bool,
) -> Result<PricingApplyExecution> {
    let mut pricing = load_pricing(pricing_path)?;
    let patch = load_pricing_patch(patch_path)?;
    let (summary, changed) = merge_pricing_patch(&mut pricing, &patch, allow_overwrite_model_rates);

    validate_aliases(&pricing)?;
    let merged_json = serde_json::to_string_pretty(&pricing)?;
    let reparsed: PricingBook =
        serde_json::from_str(&merged_json).context("parse validation for merged pricing json")?;
    validate_aliases(&reparsed)?;

    let mut backup_path = None;
    let wrote_pricing = !dry_run && changed;
    if wrote_pricing {
        if write_backup {
            let backup = backup_path_for(pricing_path, Utc::now());
            fs::copy(pricing_path, &backup).with_context(|| {
                format!(
                    "write backup of {:?} to {:?}",
                    pricing_path, backup
                )
            })?;
            backup_path = Some(backup);
        }
        let mut f = BufWriter::new(
            File::create(pricing_path)
                .with_context(|| format!("create {:?}", pricing_path))?,
        );
        let json = serde_json::to_string_pretty(&pricing)?;
        f.write_all(json.as_bytes())?;
        f.flush()?;
    }

    Ok(PricingApplyExecution {
        summary,
        changed,
        wrote_pricing,
        backup_path,
        pricing_after: if wrote_pricing {
            Some(pricing)
        } else {
            None
        },
    })
}

pub fn stamp_reconcile_metadata(pricing_path: &Path) -> Result<bool> {
    let mut pricing = load_pricing(pricing_path)?;
    let now = Utc::now();
    let timestamp_str = now.format("%Y-%m-%dT%H:%M:%SZ").to_string();

    let mut changed = false;

    if let Some(ref mut meta) = pricing.meta {
        if meta.updated_at.is_none() {
            changed = true;
        }
        meta.updated_at = Some(timestamp_str);
        if meta.source.is_none() {
            meta.source = Some("tokenledger".to_string());
            changed = true;
        }
    } else {
        pricing.meta = Some(crate::models::PricingMeta {
            updated_at: Some(timestamp_str),
            source: Some("tokenledger".to_string()),
            version: None,
        });
        changed = true;
    }

    if !changed {
        return Ok(false);
    }

    let mut f = BufWriter::new(
        File::create(pricing_path).with_context(|| format!("create {:?}", pricing_path))?,
    );
    let json = serde_json::to_string_pretty(&pricing)?;
    f.write_all(json.as_bytes())?;
    f.flush()?;

    Ok(true)
}

pub fn summarize_unpriced_pairs(unpriced_events: &[UsageEvent]) -> Vec<String> {
    let mut pairs: BTreeMap<String, usize> = BTreeMap::new();
    for evt in unpriced_events {
        *pairs
            .entry(format!("{}:{}", evt.provider, evt.model))
            .or_default() += 1;
    }
    pairs
        .into_iter()
        .map(|(pair, count)| format!("{} (events={})", pair, count))
        .collect()
}

pub fn collect_pricing_placeholder_violations(pricing: &PricingBook) -> Vec<String> {
    let mut violations = Vec::new();

    for (provider_name, provider) in &pricing.providers {
        for (model_name, rate) in &provider.models {
            if has_placeholder_marker(&rate.input_usd_per_mtok.to_string())
                || has_placeholder_marker(&rate.output_usd_per_mtok.to_string())
            {
                append_rate_violation(
                    &mut violations,
                    provider_name,
                    model_name,
                    "placeholder rate marker",
                );
            }
        }
        if provider.subscription_usd_month < 0.0 {
            violations.push(format!(
                "{}: subscription is negative (${:.4})",
                provider_name, provider.subscription_usd_month
            ));
        }
    }

    if violations.is_empty() {
        violations.push("(none)".to_string());
    }

    violations
}

pub fn append_rate_violation(violations: &mut Vec<String>, provider: &str, model: &str, reason: &str) {
    violations.push(format!("{provider} / {model}: {reason}"));
}

pub fn has_placeholder_marker(raw: &str) -> bool {
    raw.to_lowercase().contains("x") || raw.to_lowercase().contains("todo")
}

pub fn merge_pricing_patch(
    pricing: &mut PricingBook,
    patch: &PricingPatch,
    _allow_overwrite_model_rates: bool,
) -> (PricingApplySummary, bool) {
    let mut summary = PricingApplySummary::default();
    let mut changed = false;

    // Merge missing providers (providers suggested for unknown provider:model pairs)
    for (provider_name, missing_patch) in &patch.missing_providers {
        if !pricing.providers.contains_key(provider_name) {
            let new_provider = ProviderPricing {
                subscription_usd_month: missing_patch.subscription_usd_month,
                models: missing_patch.models.clone(),
                model_aliases: missing_patch.model_aliases.clone(),
            };
            pricing.providers.insert(provider_name.clone(), new_provider);
            summary.providers_added += 1;
            changed = true;
        }
    }

    // Merge missing models by provider
    for (provider_name, missing_models) in &patch.missing_models_by_provider {
        if let Some(provider) = pricing.providers.get_mut(provider_name) {
            for (model_name, model_rate) in missing_models {
                if !provider.models.contains_key(model_name) {
                    provider.models.insert(model_name.clone(), model_rate.clone());
                    summary.models_added += 1;
                    changed = true;
                } else {
                    summary.models_skipped_existing += 1;
                }
            }
        }
    }

    // Merge suggested aliases (provider aliases are Vec<String> of suggestions, skip for now as they're informational)
    // Model aliases by provider are also informational suggestions, not directly applied

    (summary, changed)
}


pub fn first_existing_provider_candidate<'a>(
    candidates: &'a [String],
    pricing: &'a PricingBook,
) -> Option<&'a str> {
    candidates
        .iter()
        .find(|c| pricing.providers.contains_key(*c))
        .map(|s| s.as_str())
}

pub fn first_existing_model_candidate<'a>(
    candidates: &'a [String],
    provider: &'a ProviderPricing,
) -> Option<&'a str> {
    candidates
        .iter()
        .find(|c| provider.models.contains_key(*c))
        .map(|s| s.as_str())
}

pub fn backup_path_for(pricing_path: &Path, now: DateTime<Utc>) -> PathBuf {
    let timestamp = now.format("%Y%m%d_%H%M%S").to_string();
    let stem = pricing_path.file_stem().unwrap_or_default().to_string_lossy();
    let parent = pricing_path.parent().unwrap_or_else(|| Path::new("."));
    parent.join(format!("{stem}.{timestamp}.bak"))
}

pub fn render_cost_breakdown(
    label: &str,
    report: &CostBreakdown,
    output: OutputMode,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) -> Result<()> {
    match output {
        OutputMode::Json => {
            let json = serde_json::json!({
                "variable_cost_usd": report.variable_cost_usd,
                "subscription_allocated_usd": report.subscription_allocated_usd,
                "monthly_total_usd": report.monthly_total_usd,
                "blended_usd_per_mtok": report.blended_usd_per_mtok,
                "total_tokens": report.total_tokens,
                "total_mtok": report.total_mtok,
                "session_count": report.session_count,
            });
            println!("{}", serde_json::to_string_pretty(&json)?);
        }
        OutputMode::Table => print_table(label, report, top_providers, top_models),
        OutputMode::Markdown => print_markdown(label, report, top_providers, top_models),
    }
    Ok(())
}

pub fn load_events(paths: &[PathBuf]) -> Result<Vec<UsageEvent>> {
    let mut events = Vec::new();
    for path in paths {
        parse_jsonl_file(path, &mut events)?;
    }
    Ok(events)
}

pub fn parse_jsonl_file(path: &Path, out: &mut Vec<UsageEvent>) -> Result<()> {
    let file = File::open(path).with_context(|| format!("opening {:?}", path))?;
    let reader = BufReader::new(file);

    for (line_no, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("reading line {} from {:?}", line_no + 1, path))?;
        if line.trim().is_empty() {
            continue;
        }
        let event: UsageEvent = serde_json::from_str(&line)
            .with_context(|| format!("parsing line {} in {:?}", line_no + 1, path))?;
        out.push(event);
    }

    Ok(())
}

pub fn filter_month(events: Vec<UsageEvent>, month: Option<&str>) -> Result<Vec<UsageEvent>> {
    match month {
        None => Ok(events),
        Some(m) => {
            let (year, month_num) = parse_month(m)?;
            Ok(events
                .into_iter()
                .filter(|e| e.timestamp.year() == year && e.timestamp.month() == month_num)
                .collect())
        }
    }
}

pub fn filter_provider_model(
    events: Vec<UsageEvent>,
    pricing: &PricingBook,
    providers: &[String],
    models: &[String],
) -> Vec<UsageEvent> {
    let provider_filter = normalize_provider_filters(pricing, providers);
    let model_filter = normalize_model_filters(pricing, models);
    events
        .into_iter()
        .filter(|e| (provider_filter.is_empty() || provider_filter.contains(&e.provider)) &&
                     (model_filter.is_empty() || model_filter.contains(&e.model)))
        .collect()
}

pub fn normalize_events(events: Vec<UsageEvent>, pricing: &PricingBook) -> Vec<UsageEvent> {
    events
        .into_iter()
        .map(|mut e| {
            e.provider = resolve_provider_alias(&e.provider, pricing);
            e.model = resolve_model_alias(&e.provider, &e.model, pricing);
            e
        })
        .collect()
}

pub fn canonical_provider(pricing: &PricingBook, provider: &str) -> String {
    resolve_provider_alias(provider, pricing)
}

pub fn canonical_model<'a>(provider_pricing: &'a ProviderPricing, model: &'a str) -> &'a str {
    provider_pricing
        .model_aliases
        .get(model)
        .map(|s| s.as_str())
        .unwrap_or(model)
}

pub fn normalize_provider_filters(pricing: &PricingBook, providers: &[String]) -> HashSet<String> {
    providers
        .iter()
        .map(|p| resolve_provider_alias(p, pricing))
        .collect()
}

pub fn normalize_model_filters(pricing: &PricingBook, models: &[String]) -> HashSet<String> {
    let mut result = HashSet::new();
    for provider in pricing.providers.values() {
        for model in models {
            if let Some(canonical) = provider.model_aliases.get(model) {
                result.insert(canonical.clone());
            } else {
                result.insert(model.clone());
            }
        }
    }
    result
}


pub fn validate_aliases(pricing: &PricingBook) -> Result<()> {
    for (alias, provider) in &pricing.provider_aliases {
        if !pricing.providers.contains_key(provider) {
            return Err(anyhow!("provider_alias '{}' points to unknown provider '{}'", alias, provider));
        }
    }

    for (provider_name, provider) in &pricing.providers {
        for (alias, model) in &provider.model_aliases {
            if !provider.models.contains_key(model) {
                return Err(anyhow!("provider '{}' has model_alias '{}' pointing to unknown model '{}'", provider_name, alias, model));
            }
        }
    }

    Ok(())
}

pub fn parse_month(raw: &str) -> Result<(i32, u32)> {
    let parts: Vec<&str> = raw.split('-').collect();
    if parts.len() != 2 {
        return Err(anyhow!("invalid month format '{}', expected YYYY-MM", raw));
    }
    let year: i32 = parts[0].parse().context("parsing year")?;
    let month: u32 = parts[1].parse().context("parsing month")?;
    if !(1..=12).contains(&month) {
        return Err(anyhow!("invalid month '{}', must be 1-12", month));
    }
    Ok((year, month))
}

pub fn suggest_aliases<'a, I>(unknown: &str, candidates: I) -> Vec<String>
where
    I: IntoIterator<Item = &'a String>,
{
    let key = normalize_alias_key(unknown);
    let mut suggestions = Vec::new();

    for candidate in candidates {
        if normalize_alias_key(candidate).contains(&key) {
            suggestions.push(candidate.clone());
        }
    }

    suggestions
}

pub fn normalize_alias_key(raw: &str) -> String {
    raw.to_lowercase().replace("_", "").replace("-", "")
}
