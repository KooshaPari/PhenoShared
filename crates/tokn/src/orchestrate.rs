use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, Datelike, Utc};
use serde::Serialize;
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::hash::{Hash, Hasher};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use crate::analytics::*;
use crate::bench::{execute_bench, load_bench_report, load_perf_gate_config, PERF_GATES_PATH};
use crate::cli::{
    BenchArgs, BenchScenario, IngestArgs, IngestProvider, OnUnpricedAction, OrchestrateArgs,
    OutputMode, PricingAuditArgs, PricingLintArgs, PricingReconcileArgs, QueryArgs, UiSnapshotMode,
};
use crate::ingest::{
    discover_provider_sources, ingest_provider_name, run_ingest, source_mtime_unix,
};
use crate::models::*;
use crate::pricing::{execute_pricing_reconcile, run_pricing_audit, run_pricing_lint};
use crate::utils::*;

pub const ORCHESTRATE_PIPELINE_SUMMARY_SCHEMA_VERSION: u32 = 1;
pub const ORCHESTRATE_INGEST_CACHE_VERSION: u8 = 1;
pub const ORCHESTRATE_AGGREGATE_CACHE_VERSION: u8 = 1;
pub const UI_SNAPSHOT_SCHEMA_VERSION: u32 = 1;

pub fn run_orchestrate(args: OrchestrateArgs) -> Result<()> {
    let orchestrate_started = Instant::now();
    let mut ingest_stage = OrchestrateIngestStageSummary {
        skipped: args.skip_ingest,
        cache_enabled: args.ingest_cache_path.is_some(),
        cache_hit: false,
        cache_path: args
            .ingest_cache_path
            .as_ref()
            .map(|path| path.display().to_string()),
        duration_ms: 0,
        summary_json_path: args
            .summary_json_path
            .as_ref()
            .map(|path| path.display().to_string()),
        summary: None,
    };
    let mut reconcile_stage = OrchestratePricingReconcileStageSummary {
        skipped: args.skip_pricing_reconcile,
        duration_ms: 0,
        run_summary_path: None,
        latest_summary_path: None,
        summary: None,
    };
    let mut monthly_stage = OrchestrateStageSummary {
        skipped: false,
        duration_ms: 0,
    };
    let mut daily_stage = OrchestrateStageSummary {
        skipped: false,
        duration_ms: 0,
    };
    let mut aggregate_cache = OrchestrateAggregateCacheMetrics {
        enabled: args.aggregate_cache_path.is_some(),
        cache_path: args
            .aggregate_cache_path
            .as_ref()
            .map(|path| path.display().to_string()),
        hit_count: 0,
        miss_count: 0,
        invalidate_count: 0,
    };
    let mut bench_stage = OrchestrateBenchStageSummary {
        skipped: args.skip_bench,
        duration_ms: 0,
        latest_summary_path: None,
        baseline_used: false,
        report: None,
    };
    let mut perf_gate_stage = OrchestrateStageSummary {
        skipped: args.skip_bench || args.skip_gate,
        duration_ms: 0,
    };

    if !args.skip_ingest {
        let ingest_timer = Instant::now();
        let providers = resolve_ingest_providers(&args.providers);
        let mut skipped_by_cache = false;
        if let Some(cache_path) = args.ingest_cache_path.as_ref() {
            let cache_key = build_orchestrate_ingest_cache(&providers, &args);
            if orchestrate_ingest_cache_hit(cache_path, &cache_key, &args.events_out)? {
                skipped_by_cache = true;
                ingest_stage.cache_hit = true;
                eprintln!(
                    "orchestrate ingest cache hit: reusing existing output {}",
                    args.events_out.display()
                );
            }
        }

        if !skipped_by_cache {
            let ingest_args = IngestArgs {
                providers: args.providers.clone(),
                output: args.events_out.clone(),
                append: false,
                since: args.since,
                limit: args.limit,
                state_file: args.state_file.clone(),
                incremental: false,
                summary_json_path: args.summary_json_path.clone(),
                dedupe_by_request: true,
            };
            run_ingest(ingest_args)?;
            if let Some(cache_path) = args.ingest_cache_path.as_ref() {
                let cache_key = build_orchestrate_ingest_cache(&providers, &args);
                write_orchestrate_ingest_cache(cache_path, &cache_key)?;
            }
        }

        ingest_stage.duration_ms = ingest_timer.elapsed().as_millis();
        ingest_stage.skipped = skipped_by_cache;
        if let Some(path) = args.summary_json_path.as_ref() {
            ingest_stage.summary = load_ingest_summary(path).ok();
        }
    }

    if args.pricing_lint {
        run_pricing_lint(PricingLintArgs {
            pricing: args.pricing.clone(),
            allow_placeholders: false,
        })?;
    }

    if args.pricing_audit {
        run_pricing_audit(PricingAuditArgs {
            pricing: args.pricing.clone(),
            max_age_days: args.pricing_max_age_days,
            allow_stale: false,
            allow_missing_source: false,
            json_output: false,
        })?;
    }

    if !args.skip_pricing_reconcile {
        let reconcile_timer = Instant::now();
        let reconcile_workdir = orchestrate_reconcile_workdir(
            &args.pricing_reconcile_workdir,
            args.pricing_reconcile_static_artifacts,
            Utc::now(),
        );
        let reconcile_allow_unpriced = orchestrate_reconcile_allow_unpriced(
            args.pricing_reconcile_allow_unpriced,
            args.on_unpriced,
        );
        let outcome = execute_pricing_reconcile(PricingReconcileArgs {
            events: vec![args.events_out.clone()],
            pricing: args.pricing.clone(),
            month: args.month.clone(),
            workdir: reconcile_workdir,
            allow_unpriced: reconcile_allow_unpriced,
            dry_run: args.pricing_reconcile_dry_run,
            write_backup: args.pricing_reconcile_write_backup,
            allow_overwrite_model_rates: args.pricing_reconcile_allow_overwrite_model_rates,
        })?;
        println!("{}", serde_json::to_string_pretty(&outcome.summary)?);
        let reconcile_paths = write_orchestrate_reconcile_summaries(
            &outcome.summary,
            &args.pricing_reconcile_workdir,
            args.pricing_reconcile_static_artifacts,
        )?;
        reconcile_stage.duration_ms = reconcile_timer.elapsed().as_millis();
        reconcile_stage.run_summary_path = Some(reconcile_paths.run_summary_path);
        reconcile_stage.latest_summary_path = reconcile_paths.latest_summary_path;
        reconcile_stage.summary = Some(outcome.summary.clone());
        if outcome.fail_for_unpriced {
            return Err(anyhow!(
                "orchestrate pricing-reconcile failed: unpriced events remain after apply; re-run with --pricing-reconcile-allow-unpriced or --on-unpriced skip to continue"
            ));
        }
    }

    let query = QueryArgs {
        events: vec![args.events_out.clone()],
        pricing: args.pricing.clone(),
        providers: Vec::new(),
        models: Vec::new(),
        top_models: Some(5),
        top_providers: Some(5),
        output: OutputMode::Table,
        on_unpriced: args.on_unpriced,
    };
    if let Some(cache_path) = args.aggregate_cache_path.as_ref() {
        let key = build_orchestrate_aggregate_cache_key(&query, args.month.as_deref())?;
        let (mut cache, lookup) = orchestrate_aggregate_cache_lookup(cache_path, &key)?;
        match lookup {
            OrchestrateAggregateCacheLookup::Hit(entry) => {
                aggregate_cache.hit_count += 1;
                let monthly_timer = Instant::now();
                render_cost_breakdown(
                    "Monthly",
                    &entry.monthly,
                    query.output,
                    query.top_providers,
                    query.top_models,
                )?;
                monthly_stage.duration_ms = monthly_timer.elapsed().as_millis();
                monthly_stage.skipped = true;
                let daily_timer = Instant::now();
                render_daily_report(
                    &entry.daily,
                    query.output,
                    query.top_providers,
                    query.top_models,
                )?;
                daily_stage.duration_ms = daily_timer.elapsed().as_millis();
                daily_stage.skipped = true;
                eprintln!(
                    "orchestrate aggregate cache hit: reusing monthly/daily outputs from {}",
                    cache_path.display()
                );
            }
            OrchestrateAggregateCacheLookup::Miss | OrchestrateAggregateCacheLookup::Invalidate => {
                match lookup {
                    OrchestrateAggregateCacheLookup::Miss => aggregate_cache.miss_count += 1,
                    OrchestrateAggregateCacheLookup::Invalidate => {
                        aggregate_cache.invalidate_count += 1;
                        aggregate_cache.miss_count += 1;
                    }
                    OrchestrateAggregateCacheLookup::Hit(_) => {}
                }
                let monthly_timer = Instant::now();
                let monthly_report = build_monthly_report(&query, args.month.as_deref())?;
                render_cost_breakdown(
                    "Monthly",
                    &monthly_report,
                    query.output,
                    query.top_providers,
                    query.top_models,
                )?;
                monthly_stage.duration_ms = monthly_timer.elapsed().as_millis();

                let daily_timer = Instant::now();
                let daily_report = build_daily_report(&query, args.month.as_deref())?;
                render_daily_report(
                    &daily_report,
                    query.output,
                    query.top_providers,
                    query.top_models,
                )?;
                daily_stage.duration_ms = daily_timer.elapsed().as_millis();

                let selector_id = orchestrate_aggregate_selector_id(&key.selector);
                cache.entries.insert(
                    selector_id,
                    OrchestrateAggregateCacheEntry {
                        selector: key.selector,
                        pricing_hash: key.pricing_hash,
                        events_fingerprint: key.events_fingerprint,
                        monthly: monthly_report,
                        daily: daily_report,
                    },
                );
                write_orchestrate_aggregate_cache(cache_path, &cache)?;
            }
        }
    } else {
        let monthly_timer = Instant::now();
        let monthly_report = build_monthly_report(&query, args.month.as_deref())?;
        render_cost_breakdown(
            "Monthly",
            &monthly_report,
            query.output,
            query.top_providers,
            query.top_models,
        )?;
        monthly_stage.duration_ms = monthly_timer.elapsed().as_millis();

        let daily_timer = Instant::now();
        let daily_report = build_daily_report(&query, args.month.as_deref())?;
        render_daily_report(
            &daily_report,
            query.output,
            query.top_providers,
            query.top_models,
        )?;
        daily_stage.duration_ms = daily_timer.elapsed().as_millis();
    }

    if let Some(snapshot_path) = args.ui_snapshot_path.as_ref() {
        let snapshot =
            build_orchestrate_ui_snapshot(args.month.as_deref(), &args.events_out, &args)?;
        write_ui_snapshot(snapshot_path, &snapshot)?;
    }

    if args.skip_bench {
        maybe_write_orchestrate_pipeline_summary(
            &args,
            orchestrate_started.elapsed().as_millis(),
            ingest_stage,
            reconcile_stage,
            monthly_stage,
            daily_stage,
            aggregate_cache,
            bench_stage,
            perf_gate_stage,
        )?;
        return Ok(());
    }

    let bench_timer = Instant::now();
    let latest_summary = PathBuf::from("benchmarks/results/latest-summary.json");
    let baseline_path = select_orchestrate_baseline(args.month.as_deref(), &latest_summary);
    let bench_args = BenchArgs {
        events: vec![args.events_out.clone()],
        pricing: args.pricing.clone(),
        scenario: BenchScenario::All,
        month: args.month.clone(),
        warm_iterations: 5,
        warm_tail_events: 10_000,
        burst_batch_events: 2_000,
        json_output: false,
        on_unpriced: args.on_unpriced,
        json_output_path: Some(latest_summary.clone()),
        baseline: baseline_path,
        golden: None,
        golden_epsilon: 0.0001,
        trend_dir: None,
        record: true,
        label: Some("orchestrate".to_string()),
        trend_fail_on_regression: false,
    };
    let bench_run = execute_bench(bench_args)?;
    print_bench_table(&bench_run.report);
    bench_stage.duration_ms = bench_timer.elapsed().as_millis();
    bench_stage.latest_summary_path = Some(latest_summary.display().to_string());
    bench_stage.baseline_used = bench_run.baseline_used;
    bench_stage.report = Some(bench_run.report.clone());

    if !args.skip_gate {
        let gate_timer = Instant::now();
        run_perf_gate_checks(
            &bench_run.report,
            &load_perf_gate_config(Path::new(PERF_GATES_PATH))?,
            false,
            bench_run.baseline_used,
        )?;
        perf_gate_stage.duration_ms = gate_timer.elapsed().as_millis();
    }

    maybe_write_orchestrate_pipeline_summary(
        &args,
        orchestrate_started.elapsed().as_millis(),
        ingest_stage,
        reconcile_stage,
        monthly_stage,
        daily_stage,
        aggregate_cache,
        bench_stage,
        perf_gate_stage,
    )?;

    Ok(())
}

pub fn select_orchestrate_baseline(
    month_filter: Option<&str>,
    latest_summary: &Path,
) -> Option<PathBuf> {
    let expected_month = month_filter?;
    if !latest_summary.exists() {
        return None;
    }
    let report = load_bench_report(latest_summary).ok()?;
    (report.month == expected_month).then(|| latest_summary.to_path_buf())
}

pub fn orchestrate_reconcile_allow_unpriced(
    pricing_reconcile_allow_unpriced: bool,
    on_unpriced: OnUnpricedAction,
) -> bool {
    pricing_reconcile_allow_unpriced || matches!(on_unpriced, OnUnpricedAction::Skip)
}

pub fn orchestrate_reconcile_workdir(
    base_workdir: &Path,
    static_artifacts: bool,
    now: DateTime<Utc>,
) -> PathBuf {
    if static_artifacts {
        return base_workdir.to_path_buf();
    }
    let run_id = now.format("reconcile-%Y%m%d-%H%M%S").to_string();
    base_workdir.join(run_id)
}

pub fn write_orchestrate_reconcile_summaries(
    summary: &PricingReconcileSummary,
    base_workdir: &Path,
    static_artifacts: bool,
) -> Result<OrchestrateReconcileSummaryPaths> {
    let run_summary_path = PathBuf::from(&summary.workdir).join("reconcile-summary.json");
    write_json_file_pretty(&run_summary_path, summary)?;
    let mut latest_summary_path = None;
    if !static_artifacts {
        let path = base_workdir.join("reconcile-latest-summary.json");
        write_json_file_pretty(&path, summary)?;
        latest_summary_path = Some(path.display().to_string());
    }
    Ok(OrchestrateReconcileSummaryPaths {
        run_summary_path: run_summary_path.display().to_string(),
        latest_summary_path,
    })
}

#[derive(Debug, Clone)]
pub struct OrchestrateReconcileSummaryPaths {
    run_summary_path: String,
    latest_summary_path: Option<String>,
}

pub fn maybe_write_orchestrate_pipeline_summary(
    args: &OrchestrateArgs,
    duration_ms: u128,
    ingest: OrchestrateIngestStageSummary,
    pricing_reconcile: OrchestratePricingReconcileStageSummary,
    monthly: OrchestrateStageSummary,
    daily: OrchestrateStageSummary,
    aggregate_cache: OrchestrateAggregateCacheMetrics,
    bench: OrchestrateBenchStageSummary,
    perf_gate: OrchestrateStageSummary,
) -> Result<()> {
    let Some(path) = args.pipeline_summary_path.as_ref() else {
        return Ok(());
    };
    let summary = OrchestratePipelineSummary {
        schema_version: ORCHESTRATE_PIPELINE_SUMMARY_SCHEMA_VERSION,
        generated_at: Utc::now(),
        month_filter: args.month.clone(),
        events_out: args.events_out.display().to_string(),
        pricing: args.pricing.display().to_string(),
        on_unpriced: on_unpriced_to_str(args.on_unpriced).to_string(),
        duration_ms,
        ingest,
        pricing_reconcile,
        monthly,
        daily,
        aggregate_cache,
        bench,
        perf_gate,
        ui_snapshot_path: args
            .ui_snapshot_path
            .as_ref()
            .map(|value| value.display().to_string()),
    };
    write_json_file_pretty(path, &summary)?;
    let latest_path = path
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join("orchestrate-latest-summary.json");
    write_json_file_pretty(&latest_path, &summary)?;
    Ok(())
}

pub fn on_unpriced_to_str(action: OnUnpricedAction) -> &'static str {
    match action {
        OnUnpricedAction::Error => "error",
        OnUnpricedAction::Skip => "skip",
    }
}

pub fn resolve_ingest_providers(selected: &[IngestProvider]) -> Vec<IngestProvider> {
    if selected.is_empty() {
        return vec![
            IngestProvider::Claude,
            IngestProvider::Codex,
            IngestProvider::Proxyapi,
            IngestProvider::Cursor,
            IngestProvider::Droid,
        ];
    }
    selected.to_vec()
}

pub fn build_orchestrate_ingest_cache(
    providers: &[IngestProvider],
    args: &OrchestrateArgs,
) -> OrchestrateIngestCache {
    let mut source_mtimes = BTreeMap::new();
    let mut provider_names = Vec::new();
    for provider in providers {
        provider_names.push(ingest_provider_name(*provider).to_string());
        for source in discover_provider_sources(*provider) {
            if let Some(mtime) = source_mtime_unix(&source) {
                source_mtimes.insert(source.display().to_string(), mtime);
            }
        }
    }
    provider_names.sort();
    provider_names.dedup();

    OrchestrateIngestCache {
        version: ORCHESTRATE_INGEST_CACHE_VERSION,
        providers: provider_names,
        since: args.since.as_ref().map(|since| since.to_rfc3339()),
        limit: args.limit,
        events_out: args.events_out.display().to_string(),
        source_mtimes,
    }
}

pub fn orchestrate_ingest_cache_hit(
    cache_path: &Path,
    expected: &OrchestrateIngestCache,
    events_out: &Path,
) -> Result<bool> {
    let Some(cached) = load_orchestrate_ingest_cache(cache_path)? else {
        return Ok(false);
    };
    Ok(events_out.is_file() && cached == *expected)
}

pub fn load_orchestrate_ingest_cache(path: &Path) -> Result<Option<OrchestrateIngestCache>> {
    if !path.exists() {
        return Ok(None);
    }
    let file = File::open(path).with_context(|| format!("opening ingest cache {:?}", path))?;
    let cache: OrchestrateIngestCache = serde_json::from_reader(file)
        .with_context(|| format!("parsing ingest cache {:?}", path))?;
    if cache.version != ORCHESTRATE_INGEST_CACHE_VERSION {
        return Ok(None);
    }
    Ok(Some(cache))
}

pub fn write_orchestrate_ingest_cache(path: &Path, cache: &OrchestrateIngestCache) -> Result<()> {
    write_json_file_pretty(path, cache)
}

pub fn build_orchestrate_aggregate_cache_key(
    query: &QueryArgs,
    month: Option<&str>,
) -> Result<OrchestrateAggregateCacheKey> {
    let mut providers = query.providers.clone();
    providers.sort();
    let mut models = query.models.clone();
    models.sort();
    let selector = OrchestrateAggregateCacheSelector {
        month_filter: month.map(ToOwned::to_owned),
        providers,
        models,
        on_unpriced: on_unpriced_to_str(query.on_unpriced).to_string(),
    };
    Ok(OrchestrateAggregateCacheKey {
        selector,
        pricing_hash: file_content_fingerprint(&query.pricing)?,
        events_fingerprint: files_content_fingerprint(&query.events)?,
    })
}

pub fn files_content_fingerprint(paths: &[PathBuf]) -> Result<String> {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    for path in paths {
        path.display().to_string().hash(&mut hasher);
        file_content_fingerprint(path)?.hash(&mut hasher);
    }
    Ok(format!("{:016x}", hasher.finish()))
}

pub fn file_content_fingerprint(path: &Path) -> Result<String> {
    let file = File::open(path).with_context(|| format!("opening fingerprint input {:?}", path))?;
    let mut reader = BufReader::new(file);
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    let mut buf = [0_u8; 8192];
    loop {
        let read = reader
            .read(&mut buf)
            .with_context(|| format!("reading fingerprint input {:?}", path))?;
        if read == 0 {
            break;
        }
        hasher.write(&buf[..read]);
    }
    Ok(format!("{:016x}", hasher.finish()))
}

pub fn orchestrate_aggregate_selector_id(selector: &OrchestrateAggregateCacheSelector) -> String {
    let month = selector.month_filter.as_deref().unwrap_or("*");
    format!(
        "month={month}|providers={}|models={}|on_unpriced={}",
        selector.providers.join(","),
        selector.models.join(","),
        selector.on_unpriced
    )
}

pub fn orchestrate_aggregate_cache_lookup(
    cache_path: &Path,
    key: &OrchestrateAggregateCacheKey,
) -> Result<(OrchestrateAggregateCache, OrchestrateAggregateCacheLookup)> {
    let mut cache = load_orchestrate_aggregate_cache(cache_path)?;
    let selector_id = orchestrate_aggregate_selector_id(&key.selector);
    let Some(entry) = cache.entries.get(&selector_id).cloned() else {
        return Ok((cache, OrchestrateAggregateCacheLookup::Miss));
    };
    if entry.pricing_hash == key.pricing_hash && entry.events_fingerprint == key.events_fingerprint
    {
        return Ok((cache, OrchestrateAggregateCacheLookup::Hit(entry)));
    }
    cache.entries.remove(&selector_id);
    Ok((cache, OrchestrateAggregateCacheLookup::Invalidate))
}

pub fn load_orchestrate_aggregate_cache(path: &Path) -> Result<OrchestrateAggregateCache> {
    if !path.exists() {
        return Ok(OrchestrateAggregateCache {
            version: ORCHESTRATE_AGGREGATE_CACHE_VERSION,
            entries: BTreeMap::new(),
        });
    }
    let file = File::open(path).with_context(|| format!("opening aggregate cache {:?}", path))?;
    let cache: OrchestrateAggregateCache = serde_json::from_reader(file)
        .with_context(|| format!("parsing aggregate cache {:?}", path))?;
    if cache.version != ORCHESTRATE_AGGREGATE_CACHE_VERSION {
        return Ok(OrchestrateAggregateCache {
            version: ORCHESTRATE_AGGREGATE_CACHE_VERSION,
            entries: BTreeMap::new(),
        });
    }
    Ok(cache)
}

pub fn write_orchestrate_aggregate_cache(
    path: &Path,
    cache: &OrchestrateAggregateCache,
) -> Result<()> {
    write_json_file_pretty(path, cache)
}

pub fn load_ingest_summary(path: &Path) -> Result<IngestSummary> {
    let file = File::open(path).with_context(|| format!("opening ingest summary {:?}", path))?;
    serde_json::from_reader(file).with_context(|| format!("parsing ingest summary {:?}", path))
}

pub fn build_orchestrate_ui_snapshot(
    month: Option<&str>,
    events_path: &Path,
    args: &OrchestrateArgs,
) -> Result<UiSnapshot> {
    let pricing = load_pricing(&args.pricing)?;
    let events = load_events(&[events_path.to_path_buf()])?;
    let normalized = normalize_events(events, &pricing);
    let month_filtered = filter_month(normalized, month)?;
    let filtered = filter_provider_model(month_filtered, &pricing, &[], &[]);
    if filtered.is_empty() {
        return Err(anyhow!(
            "no events matched selected month/provider/model filters"
        ));
    }
    let breakdown = compute_costs(&filtered, &pricing, args.on_unpriced)?;
    let snapshot_month = format!(
        "{:04}-{:02}",
        filtered[0].timestamp.year(),
        filtered[0].timestamp.month()
    );
    Ok(build_ui_snapshot_from_breakdown(
        Utc::now(),
        snapshot_month,
        args.ui_snapshot_mode,
        &breakdown,
        5,
        discover_reconcile_latest_summary_path(Path::new("benchmarks/results")),
    ))
}

pub fn discover_reconcile_latest_summary_path(results_dir: &Path) -> Option<String> {
    let path = results_dir.join("reconcile-latest-summary.json");
    path.is_file().then(|| path.display().to_string())
}

pub fn build_ui_snapshot_from_breakdown(
    generated_at: DateTime<Utc>,
    month: String,
    mode: UiSnapshotMode,
    breakdown: &CostBreakdown,
    top_n: usize,
    reconcile_latest_summary_path: Option<String>,
) -> UiSnapshot {
    let top_limit = match mode {
        UiSnapshotMode::Compact => Some(top_n),
        UiSnapshotMode::Extended => None,
    };
    UiSnapshot {
        schema_version: UI_SNAPSHOT_SCHEMA_VERSION,
        generated_at,
        month,
        mode,
        totals: UiSnapshotTotals {
            cost_usd: breakdown.monthly_total_usd,
            tokens: breakdown.total_tokens,
            blended_usd_per_mtok: breakdown.blended_usd_per_mtok,
            session_count: breakdown.session_count,
            skipped_unpriced_count: breakdown.skipped_unpriced_count,
        },
        top_providers: top_rows(&breakdown.provider_breakdown, top_limit)
            .into_iter()
            .map(ui_snapshot_metric_from_named)
            .collect(),
        top_models: top_rows(&breakdown.model_breakdown, top_limit)
            .into_iter()
            .map(ui_snapshot_metric_from_named)
            .collect(),
        suggestions: breakdown.suggestions.clone(),
        reconcile_latest_summary_path,
    }
}

pub fn ui_snapshot_metric_from_named(item: &NamedMetric) -> UiSnapshotMetric {
    UiSnapshotMetric {
        name: item.name.clone(),
        tokens: item.tokens,
        total_cost_usd: item.total_cost_usd,
        blended_usd_per_mtok: item.blended_usd_per_mtok,
        session_count: item.session_count,
    }
}

pub fn write_ui_snapshot(path: &Path, snapshot: &UiSnapshot) -> Result<()> {
    write_json_file_pretty(path, snapshot)
}

pub fn write_json_file_pretty<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, value)
        .with_context(|| format!("writing {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing newline {:?}", path))?;
    Ok(())
}
