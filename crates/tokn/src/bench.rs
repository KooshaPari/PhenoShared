use anyhow::{anyhow, Context, Result};
use chrono::{Datelike, Utc};
use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

use crate::cli::{BenchArgs, BenchScenario, OnUnpricedAction};
use crate::ingest::source_mtime_unix;
use crate::models::*;
use crate::utils::*;

pub const PERF_GATES_PATH: &str = "benchmarks/perf-gates.json";

pub fn run_bench(args: BenchArgs) -> Result<()> {
    if let Some(trend_dir) = args.trend_dir.as_deref() {
        return run_bench_trend(
            trend_dir,
            args.json_output,
            args.json_output_path.as_deref(),
            args.label.as_deref(),
            args.trend_fail_on_regression,
        );
    }
    let json_output = args.json_output;
    let bench_run = execute_bench(args)?;
    if json_output {
        println!("{}", serde_json::to_string_pretty(&bench_run.report)?);
    } else {
        print_bench_table(&bench_run.report);
    }
    Ok(())
}

#[derive(Debug, Clone)]
pub struct BenchExecution {
    pub report: BenchReport,
    pub baseline_used: bool,
}

pub fn execute_bench(args: BenchArgs) -> Result<BenchExecution> {
    if args.events.is_empty() {
        return Err(anyhow!(
            "--events is required unless --trend-dir is provided"
        ));
    }
    let pricing = load_pricing(&args.pricing)?;

    let baseline_events = load_events(&args.events)?;
    let baseline_normalized = normalize_events(baseline_events, &pricing);
    let baseline_filtered = filter_month(baseline_normalized, args.month.as_deref())?;
    if baseline_filtered.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }
    let month = format!(
        "{:04}-{:02}",
        baseline_filtered[0].timestamp.year(),
        baseline_filtered[0].timestamp.month()
    );

    let mut results = Vec::new();
    match args.scenario {
        BenchScenario::ColdBackfill => {
            results.push(run_bench_cold_backfill(
                &args.events,
                &pricing,
                args.month.as_deref(),
                args.on_unpriced,
            )?);
        }
        BenchScenario::WarmTail => {
            results.push(run_bench_warm_tail(
                &baseline_filtered,
                &pricing,
                args.warm_iterations,
                args.warm_tail_events,
                args.on_unpriced,
            )?);
        }
        BenchScenario::Burst => {
            results.push(run_bench_burst(
                &baseline_filtered,
                &pricing,
                args.burst_batch_events,
                args.on_unpriced,
            )?);
        }
        BenchScenario::All => {
            results.push(run_bench_cold_backfill(
                &args.events,
                &pricing,
                args.month.as_deref(),
                args.on_unpriced,
            )?);
            results.push(run_bench_warm_tail(
                &baseline_filtered,
                &pricing,
                args.warm_iterations,
                args.warm_tail_events,
                args.on_unpriced,
            )?);
            results.push(run_bench_burst(
                &baseline_filtered,
                &pricing,
                args.burst_batch_events,
                args.on_unpriced,
            )?);
        }
    }

    let baseline_used = args.baseline.is_some();
    let report = BenchReport {
        scenario: bench_scenario_name(args.scenario).to_string(),
        month,
        generated_at: Utc::now(),
        label: args.label.clone(),
        results: apply_bench_baseline(results, args.baseline.as_deref())?,
    };

    if let Some(golden_path) = args.golden.as_deref() {
        verify_bench_golden(&report, golden_path, args.golden_epsilon)?;
    }

    if let Some(path) = args.json_output_path.as_ref() {
        write_bench_report(path, &report)?;
    }
    if args.record {
        let generated_at = report.generated_at;
        let ts = generated_at.format("%Y%m%d-%H%M%S");
        let dir = Path::new("benchmarks/results");
        let record_path = dir.join(format!("bench-{ts}.json"));
        let latest_path = dir.join("latest-summary.json");
        write_bench_report(&record_path, &report)?;
        write_bench_report(&latest_path, &report)?;
    }

    Ok(BenchExecution {
        report,
        baseline_used,
    })
}

pub fn write_bench_report(path: &Path, report: &BenchReport) -> Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("creating output directory {:?}", parent))?;
        }
    }
    let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
    serde_json::to_writer_pretty(&mut file, report)
        .with_context(|| format!("writing benchmark report {:?}", path))?;
    file.write_all(b"\n")
        .with_context(|| format!("writing benchmark newline {:?}", path))?;
    Ok(())
}

pub fn run_bench_trend(
    trend_dir: &Path,
    json_output: bool,
    json_output_path: Option<&Path>,
    label: Option<&str>,
    fail_on_regression: bool,
) -> Result<()> {
    if !trend_dir.exists() {
        return Err(anyhow!("trend directory does not exist: {:?}", trend_dir));
    }
    if !trend_dir.is_dir() {
        return Err(anyhow!("trend path is not a directory: {:?}", trend_dir));
    }

    let mut report_paths = Vec::new();
    for entry in walkdir::WalkDir::new(trend_dir)
        .into_iter()
        .filter_map(Result::ok)
    {
        if !entry.file_type().is_file() {
            continue;
        }
        if !entry
            .path()
            .extension()
            .and_then(|s| s.to_str())
            .is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
        {
            continue;
        }
        report_paths.push(entry.path().to_path_buf());
    }
    report_paths.sort();

    let mut by_scenario: BTreeMap<String, Vec<BenchTrendSample>> = BTreeMap::new();
    let mut loaded_reports = 0usize;
    for path in report_paths {
        let report = match load_bench_report(&path) {
            Ok(report) => report,
            Err(_) => continue,
        };
        loaded_reports += 1;
        let collected_at_unix = source_mtime_unix(&path).unwrap_or(0);
        let source = path.display().to_string();
        for result in report.results {
            by_scenario
                .entry(result.scenario.clone())
                .or_default()
                .push(BenchTrendSample {
                    source: source.clone(),
                    collected_at_unix,
                    elapsed_ms: result.elapsed_ms,
                    events_per_sec: result.events_per_sec,
                });
        }
    }
    if loaded_reports == 0 || by_scenario.is_empty() {
        return Err(anyhow!(
            "no valid benchmark JSON reports found under {:?}",
            trend_dir
        ));
    }

    let mut scenarios = Vec::with_capacity(by_scenario.len());
    for (scenario, samples) in by_scenario {
        let run_count = samples.len();
        let latest = samples
            .iter()
            .max_by(|a, b| {
                a.collected_at_unix
                    .cmp(&b.collected_at_unix)
                    .then_with(|| a.source.cmp(&b.source))
            })
            .ok_or_else(|| anyhow!("missing samples for scenario {}", scenario))?;

        let mut elapsed_values: Vec<f64> = samples.iter().map(|item| item.elapsed_ms).collect();
        elapsed_values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
        let mut eps_values: Vec<f64> = samples.iter().map(|item| item.events_per_sec).collect();
        eps_values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));

        scenarios.push(BenchTrendScenarioSummary {
            scenario,
            run_count,
            latest_elapsed_ms: round4(latest.elapsed_ms),
            median_elapsed_ms: round4(sorted_median(&elapsed_values)),
            p95_elapsed_ms: round4(sorted_percentile_95(&elapsed_values)),
            latest_events_per_sec: round4(latest.events_per_sec),
            median_events_per_sec: round4(sorted_median(&eps_values)),
        });
    }

    let report = BenchTrendReport {
        trend_dir: trend_dir.display().to_string(),
        generated_at: Utc::now(),
        label: label.map(str::to_string),
        scenarios,
    };

    if let Some(path) = json_output_path {
        if let Some(parent) = path.parent() {
            if !parent.as_os_str().is_empty() {
                fs::create_dir_all(parent)
                    .with_context(|| format!("creating output directory {:?}", parent))?;
            }
        }
        let mut file = File::create(path).with_context(|| format!("creating {:?}", path))?;
        serde_json::to_writer_pretty(&mut file, &report)
            .with_context(|| format!("writing benchmark trend report {:?}", path))?;
        file.write_all(b"\n")
            .with_context(|| format!("writing benchmark trend newline {:?}", path))?;
    }

    if json_output {
        println!("{}", serde_json::to_string_pretty(&report)?);
    } else {
        print_bench_trend_table(&report);
    }

    if fail_on_regression {
        fail_on_bench_trend_regressions(&report)?;
    }

    Ok(())
}

pub fn sorted_median(sorted_values: &[f64]) -> f64 {
    if sorted_values.is_empty() {
        return 0.0;
    }
    let mid = sorted_values.len() / 2;
    if sorted_values.len() % 2 == 1 {
        sorted_values[mid]
    } else {
        (sorted_values[mid - 1] + sorted_values[mid]) / 2.0
    }
}

pub fn sorted_percentile_95(sorted_values: &[f64]) -> f64 {
    if sorted_values.is_empty() {
        return 0.0;
    }
    let rank = ((sorted_values.len() as f64) * 0.95).ceil() as usize;
    let idx = rank.saturating_sub(1).min(sorted_values.len() - 1);
    sorted_values[idx]
}

pub fn run_bench_cold_backfill(
    paths: &[PathBuf],
    pricing: &PricingBook,
    month: Option<&str>,
    on_unpriced: OnUnpricedAction,
) -> Result<BenchScenarioResult> {
    let start = Instant::now();
    let events = load_events(paths)?;
    let normalized = normalize_events(events, pricing);
    let filtered = filter_month(normalized, month)?;
    if filtered.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }
    let breakdown = compute_costs(&filtered, pricing, on_unpriced)?;
    Ok(build_bench_result(
        BenchScenario::ColdBackfill,
        start.elapsed(),
        filtered.len(),
        bench_correctness_from_breakdown(&breakdown),
    ))
}

pub fn run_bench_warm_tail(
    events: &[UsageEvent],
    pricing: &PricingBook,
    iterations: usize,
    tail_size: usize,
    on_unpriced: OnUnpricedAction,
) -> Result<BenchScenarioResult> {
    let runs = iterations.max(1);
    let tail_len = tail_size.min(events.len()).max(1);
    let tail = &events[events.len() - tail_len..];

    let mut correctness_acc = BenchCorrectnessAccumulator::default();
    let start = Instant::now();
    for _ in 0..runs {
        let breakdown = compute_costs(tail, pricing, on_unpriced)?;
        bench_correctness_add_breakdown(&mut correctness_acc, &breakdown);
    }
    Ok(build_bench_result(
        BenchScenario::WarmTail,
        start.elapsed(),
        tail.len() * runs,
        bench_correctness_from_accumulator(&correctness_acc),
    ))
}

pub fn run_bench_burst(
    events: &[UsageEvent],
    pricing: &PricingBook,
    batch_size: usize,
    on_unpriced: OnUnpricedAction,
) -> Result<BenchScenarioResult> {
    let size = batch_size.max(1);
    let mut correctness_acc = BenchCorrectnessAccumulator::default();
    let start = Instant::now();
    for chunk in events.chunks(size) {
        let breakdown = compute_costs(chunk, pricing, on_unpriced)?;
        bench_correctness_add_breakdown(&mut correctness_acc, &breakdown);
    }
    Ok(build_bench_result(
        BenchScenario::Burst,
        start.elapsed(),
        events.len(),
        bench_correctness_from_accumulator(&correctness_acc),
    ))
}

pub fn build_bench_result(
    scenario: BenchScenario,
    elapsed: std::time::Duration,
    events_processed: usize,
    correctness: BenchScenarioCorrectness,
) -> BenchScenarioResult {
    let elapsed_s = elapsed.as_secs_f64();
    let events_per_sec = if elapsed_s > 0.0 {
        events_processed as f64 / elapsed_s
    } else {
        0.0
    };
    BenchScenarioResult {
        scenario: bench_scenario_name(scenario).to_string(),
        elapsed_ms: round4(elapsed_s * 1000.0),
        events_processed,
        events_per_sec: round4(events_per_sec),
        correctness: Some(correctness),
        elapsed_ms_delta: None,
        events_per_sec_delta: None,
        elapsed_regression: None,
        events_per_sec_regression: None,
    }
}

pub fn bench_correctness_from_breakdown(breakdown: &CostBreakdown) -> BenchScenarioCorrectness {
    bench_correctness_from_accumulator(&BenchCorrectnessAccumulator {
        variable_cost_usd: breakdown.variable_cost_usd,
        subscription_allocated_usd: breakdown.subscription_allocated_usd,
        monthly_total_usd: breakdown.monthly_total_usd,
        total_tokens: breakdown.total_tokens,
        input_tokens: breakdown.input_tokens,
        output_tokens: breakdown.output_tokens,
        cache_write_tokens: breakdown.cache_write_tokens,
        cache_read_tokens: breakdown.cache_read_tokens,
        tool_input_tokens: breakdown.tool_input_tokens,
        tool_output_tokens: breakdown.tool_output_tokens,
        skipped_unpriced_count: breakdown.skipped_unpriced_count,
    })
}

pub fn bench_correctness_add_breakdown(
    accumulator: &mut BenchCorrectnessAccumulator,
    breakdown: &CostBreakdown,
) {
    accumulator.variable_cost_usd += breakdown.variable_cost_usd;
    accumulator.subscription_allocated_usd += breakdown.subscription_allocated_usd;
    accumulator.monthly_total_usd += breakdown.monthly_total_usd;
    accumulator.total_tokens += breakdown.total_tokens;
    accumulator.input_tokens += breakdown.input_tokens;
    accumulator.output_tokens += breakdown.output_tokens;
    accumulator.cache_write_tokens += breakdown.cache_write_tokens;
    accumulator.cache_read_tokens += breakdown.cache_read_tokens;
    accumulator.tool_input_tokens += breakdown.tool_input_tokens;
    accumulator.tool_output_tokens += breakdown.tool_output_tokens;
    accumulator.skipped_unpriced_count += breakdown.skipped_unpriced_count;
}

pub fn bench_correctness_from_accumulator(
    accumulator: &BenchCorrectnessAccumulator,
) -> BenchScenarioCorrectness {
    let total_mtok = accumulator.total_tokens as f64 / MTOK;
    BenchScenarioCorrectness {
        variable_cost_usd: round2(accumulator.variable_cost_usd),
        subscription_allocated_usd: round2(accumulator.subscription_allocated_usd),
        monthly_total_usd: round2(accumulator.monthly_total_usd),
        blended_usd_per_mtok: round4(if total_mtok > 0.0 {
            accumulator.monthly_total_usd / total_mtok
        } else {
            0.0
        }),
        total_tokens: accumulator.total_tokens,
        total_mtok: round4(total_mtok),
        input_tokens: accumulator.input_tokens,
        output_tokens: accumulator.output_tokens,
        cache_write_tokens: accumulator.cache_write_tokens,
        cache_read_tokens: accumulator.cache_read_tokens,
        tool_input_tokens: accumulator.tool_input_tokens,
        tool_output_tokens: accumulator.tool_output_tokens,
        skipped_unpriced_count: accumulator.skipped_unpriced_count,
    }
}

pub fn apply_bench_baseline(
    mut results: Vec<BenchScenarioResult>,
    baseline_path: Option<&Path>,
) -> Result<Vec<BenchScenarioResult>> {
    let Some(path) = baseline_path else {
        return Ok(results);
    };
    let baseline = load_bench_report(path)?;
    let baseline_by_scenario: HashMap<&str, &BenchScenarioResult> = baseline
        .results
        .iter()
        .map(|item| (item.scenario.as_str(), item))
        .collect();

    for result in &mut results {
        let Some(prev) = baseline_by_scenario.get(result.scenario.as_str()) else {
            continue;
        };
        let elapsed_delta = round4(result.elapsed_ms - prev.elapsed_ms);
        let eps_delta = round4(result.events_per_sec - prev.events_per_sec);
        result.elapsed_ms_delta = Some(elapsed_delta);
        result.events_per_sec_delta = Some(eps_delta);
        result.elapsed_regression = Some(elapsed_delta > 0.0);
        result.events_per_sec_regression = Some(eps_delta < 0.0);
    }

    Ok(results)
}

pub fn verify_bench_golden(report: &BenchReport, golden_path: &Path, epsilon: f64) -> Result<()> {
    if epsilon < 0.0 {
        return Err(anyhow!("golden epsilon must be >= 0"));
    }
    let golden = load_bench_report(golden_path)?;
    let golden_by_scenario: HashMap<&str, &BenchScenarioResult> = golden
        .results
        .iter()
        .map(|item| (item.scenario.as_str(), item))
        .collect();

    let mut mismatches = Vec::new();
    let actual_scenarios: HashSet<&str> = report
        .results
        .iter()
        .map(|result| result.scenario.as_str())
        .collect();
    for scenario in golden_by_scenario.keys() {
        if !actual_scenarios.contains(*scenario) {
            mismatches.push(format!(
                "{}: present in golden fixture but missing from current report",
                scenario
            ));
        }
    }
    for result in &report.results {
        let Some(expected) = golden_by_scenario.get(result.scenario.as_str()) else {
            mismatches.push(format!("{}: missing from golden fixture", result.scenario));
            continue;
        };

        if result.events_processed != expected.events_processed {
            mismatches.push(format!(
                "{}: events_processed {} != {}",
                result.scenario, result.events_processed, expected.events_processed
            ));
        }

        match (&result.correctness, &expected.correctness) {
            (Some(actual), Some(expected_correctness)) => {
                compare_golden_f64(
                    &mut mismatches,
                    &result.scenario,
                    "variable_cost_usd",
                    actual.variable_cost_usd,
                    expected_correctness.variable_cost_usd,
                    epsilon,
                );
                compare_golden_f64(
                    &mut mismatches,
                    &result.scenario,
                    "subscription_allocated_usd",
                    actual.subscription_allocated_usd,
                    expected_correctness.subscription_allocated_usd,
                    epsilon,
                );
                compare_golden_f64(
                    &mut mismatches,
                    &result.scenario,
                    "monthly_total_usd",
                    actual.monthly_total_usd,
                    expected_correctness.monthly_total_usd,
                    epsilon,
                );
                compare_golden_f64(
                    &mut mismatches,
                    &result.scenario,
                    "blended_usd_per_mtok",
                    actual.blended_usd_per_mtok,
                    expected_correctness.blended_usd_per_mtok,
                    epsilon,
                );
                compare_golden_f64(
                    &mut mismatches,
                    &result.scenario,
                    "total_mtok",
                    actual.total_mtok,
                    expected_correctness.total_mtok,
                    epsilon,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "total_tokens",
                    actual.total_tokens,
                    expected_correctness.total_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "input_tokens",
                    actual.input_tokens,
                    expected_correctness.input_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "output_tokens",
                    actual.output_tokens,
                    expected_correctness.output_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "cache_write_tokens",
                    actual.cache_write_tokens,
                    expected_correctness.cache_write_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "cache_read_tokens",
                    actual.cache_read_tokens,
                    expected_correctness.cache_read_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "tool_input_tokens",
                    actual.tool_input_tokens,
                    expected_correctness.tool_input_tokens,
                );
                compare_golden_u64(
                    &mut mismatches,
                    &result.scenario,
                    "tool_output_tokens",
                    actual.tool_output_tokens,
                    expected_correctness.tool_output_tokens,
                );
                compare_golden_usize(
                    &mut mismatches,
                    &result.scenario,
                    "skipped_unpriced_count",
                    actual.skipped_unpriced_count,
                    expected_correctness.skipped_unpriced_count,
                );
            }
            (None, _) => mismatches.push(format!(
                "{}: report is missing correctness payload",
                result.scenario
            )),
            (_, None) => mismatches.push(format!(
                "{}: golden fixture is missing correctness payload",
                result.scenario
            )),
        }
    }

    if mismatches.is_empty() {
        return Ok(());
    }
    Err(anyhow!(
        "benchmark golden correctness FAILED\n{}",
        mismatches
            .into_iter()
            .map(|item| format!("- {item}"))
            .collect::<Vec<_>>()
            .join("\n")
    ))
}

pub fn compare_golden_f64(
    mismatches: &mut Vec<String>,
    scenario: &str,
    field: &str,
    actual: f64,
    expected: f64,
    epsilon: f64,
) {
    if (actual - expected).abs() > epsilon {
        mismatches.push(format!(
            "{scenario}: {field} {} != {} (epsilon={})",
            round4(actual),
            round4(expected),
            epsilon
        ));
    }
}

pub fn compare_golden_u64(
    mismatches: &mut Vec<String>,
    scenario: &str,
    field: &str,
    actual: u64,
    expected: u64,
) {
    if actual != expected {
        mismatches.push(format!("{scenario}: {field} {} != {}", actual, expected));
    }
}

pub fn compare_golden_usize(
    mismatches: &mut Vec<String>,
    scenario: &str,
    field: &str,
    actual: usize,
    expected: usize,
) {
    if actual != expected {
        mismatches.push(format!("{scenario}: {field} {} != {}", actual, expected));
    }
}

pub fn load_bench_report(path: &Path) -> Result<BenchReport> {
    serde_json::from_reader(File::open(path).with_context(|| format!("opening {:?}", path))?)
        .with_context(|| format!("parsing benchmark report {:?}", path))
}

pub fn load_perf_gate_config(path: &Path) -> Result<PerfGateConfig> {
    serde_json::from_reader(File::open(path).with_context(|| format!("opening {:?}", path))?)
        .with_context(|| format!("parsing perf gate config {:?}", path))
}
