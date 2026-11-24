use chrono::{DateTime, Utc};
use clap::{Args, Parser, Subcommand, ValueEnum};
use serde::Serialize;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "tokenledger")]
#[command(about = "Fast token/session usage and blended cost analytics")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand, Debug)]
pub enum Command {
    Monthly(MonthlyArgs),
    Daily(DailyArgs),
    Coverage(CoverageArgs),
    PricingCheck(PricingCheckArgs),
    PricingApply(PricingApplyArgs),
    PricingReconcile(PricingReconcileArgs),
    PricingLint(PricingLintArgs),
    PricingAudit(PricingAuditArgs),
    Ingest(IngestArgs),
    Bench(BenchArgs),
    Orchestrate(OrchestrateArgs),
}

#[derive(Args, Debug, Clone)]
pub struct QueryArgs {
    #[arg(long = "events", required = true)]
    pub events: Vec<PathBuf>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long = "provider")]
    pub providers: Vec<String>,
    #[arg(long = "model")]
    pub models: Vec<String>,
    #[arg(long, help = "Limit rows for per-model output in table/markdown")]
    pub top_models: Option<usize>,
    #[arg(long, help = "Limit rows for per-provider output in table/markdown")]
    pub top_providers: Option<usize>,
    #[arg(long, default_value = "table")]
    pub output: OutputMode,
    #[arg(
        long,
        value_enum,
        default_value_t = OnUnpricedAction::Error,
        help = "Behavior when events reference provider/model entries missing from pricing"
    )]
    pub on_unpriced: OnUnpricedAction,
}

#[derive(Parser, Debug)]
pub struct MonthlyArgs {
    #[command(flatten)]
    pub query: QueryArgs,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
}

#[derive(Parser, Debug)]
pub struct DailyArgs {
    #[command(flatten)]
    pub query: QueryArgs,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
}

#[derive(Parser, Debug)]
pub struct CoverageArgs {
    #[arg(long = "events", required = true)]
    pub events: Vec<PathBuf>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
    #[arg(long, default_value_t = false)]
    pub json_output: bool,
    #[arg(long, help = "Write suggested pricing patch JSON to this path")]
    pub write_patch: Option<PathBuf>,
    #[arg(long, help = "Write unpriced events JSONL to this path")]
    pub write_unpriced_events: Option<PathBuf>,
}

#[derive(Parser, Debug)]
pub struct PricingCheckArgs {
    #[arg(long = "events", required = true)]
    pub events: Vec<PathBuf>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
    #[arg(
        long,
        default_value_t = false,
        help = "Return success even when unpriced events are found"
    )]
    pub allow_unpriced: bool,
    #[arg(long, help = "Write suggested pricing patch JSON to this path")]
    pub write_patch: Option<PathBuf>,
    #[arg(long, help = "Write unpriced events JSONL to this path")]
    pub write_unpriced_events: Option<PathBuf>,
}

#[derive(Parser, Debug)]
pub struct PricingApplyArgs {
    #[arg(long, required = true, help = "Pricing JSON file to update")]
    pub pricing: PathBuf,
    #[arg(long, required = true, help = "Pricing patch JSON to merge")]
    pub patch: PathBuf,
    #[arg(long, default_value_t = false)]
    pub dry_run: bool,
    #[arg(long, default_value_t = false)]
    pub write_backup: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Allow overwriting existing model rates/alias mappings"
    )]
    pub allow_overwrite_model_rates: bool,
}

#[derive(Parser, Debug)]
pub struct PricingReconcileArgs {
    #[arg(long = "events", required = true)]
    pub events: Vec<PathBuf>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
    #[arg(long, default_value = "./benchmarks/results")]
    pub workdir: PathBuf,
    #[arg(
        long,
        default_value_t = false,
        help = "Return success even when unpriced events are found after reconcile"
    )]
    pub allow_unpriced: bool,
    #[arg(long, default_value_t = false)]
    pub dry_run: bool,
    #[arg(long, default_value_t = false)]
    pub write_backup: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Allow overwriting existing model rates/alias mappings"
    )]
    pub allow_overwrite_model_rates: bool,
}

#[derive(Parser, Debug)]
pub struct PricingLintArgs {
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(
        long,
        default_value_t = false,
        help = "Return success even when placeholder model rates are found"
    )]
    pub allow_placeholders: bool,
}

#[derive(Parser, Debug)]
pub struct PricingAuditArgs {
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, default_value_t = 30)]
    pub max_age_days: i64,
    #[arg(long, default_value_t = false)]
    pub allow_stale: bool,
    #[arg(long, default_value_t = false)]
    pub allow_missing_source: bool,
    #[arg(long, default_value_t = false)]
    pub json_output: bool,
}

#[derive(Parser, Debug)]
pub struct IngestArgs {
    #[arg(
        long = "provider",
        value_enum,
        help = "Provider adapter(s) to ingest from; repeatable. Defaults to all providers."
    )]
    pub providers: Vec<IngestProvider>,
    #[arg(long, help = "Output path for normalized JSONL")]
    pub output: PathBuf,
    #[arg(long, help = "Append to output JSONL instead of truncating file")]
    pub append: bool,
    #[arg(long, help = "Only include records at or after this RFC3339 timestamp")]
    pub since: Option<DateTime<Utc>>,
    #[arg(long, help = "Max number of normalized events to emit")]
    pub limit: Option<usize>,
    #[arg(
        long,
        help = "Checkpoint state file path (source path -> last_modified_unix)"
    )]
    pub state_file: Option<PathBuf>,
    #[arg(long, help = "Skip unchanged sources based on checkpoint state")]
    pub incremental: bool,
    #[arg(long, help = "Write structured ingest summary JSON to this path")]
    pub summary_json_path: Option<PathBuf>,
    #[arg(
        long,
        help = "Deduplicate emitted events by request key (provider, session, timestamp, model, token totals)"
    )]
    pub dedupe_by_request: bool,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Hash, ValueEnum)]
pub enum IngestProvider {
    Claude,
    Codex,
    Proxyapi,
    Cursor,
    Droid,
}

#[derive(Parser, Debug)]
pub struct BenchArgs {
    #[arg(long = "events")]
    pub events: Vec<PathBuf>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, default_value = "all")]
    pub scenario: BenchScenario,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
    #[arg(long, default_value_t = 5)]
    pub warm_iterations: usize,
    #[arg(long, default_value_t = 10_000)]
    pub warm_tail_events: usize,
    #[arg(long, default_value_t = 2_000)]
    pub burst_batch_events: usize,
    #[arg(long, default_value_t = false)]
    pub json_output: bool,
    #[arg(long, value_enum, default_value_t = OnUnpricedAction::Error)]
    pub on_unpriced: OnUnpricedAction,
    #[arg(long, help = "Write benchmark JSON report to this path")]
    pub json_output_path: Option<PathBuf>,
    #[arg(long, help = "Load baseline benchmark JSON and include deltas")]
    pub baseline: Option<PathBuf>,
    #[arg(
        long,
        help = "Load golden benchmark JSON and validate elapsed-independent correctness fields"
    )]
    pub golden: Option<PathBuf>,
    #[arg(
        long,
        default_value_t = 0.0001,
        help = "Absolute epsilon for floating-point golden correctness comparisons"
    )]
    pub golden_epsilon: f64,
    #[arg(
        long,
        help = "Aggregate benchmark JSON reports from this directory and print trend summary"
    )]
    pub trend_dir: Option<PathBuf>,
    #[arg(
        long,
        help = "Write benchmark report to benchmarks/results/bench-<timestamp>.json and update latest-summary.json"
    )]
    pub record: bool,
    #[arg(long, help = "Optional label metadata stored in benchmark report")]
    pub label: Option<String>,
    #[arg(
        long,
        help = "In trend mode, fail if latest vs median exceeds thresholds from benchmarks/perf-gates.json"
    )]
    pub trend_fail_on_regression: bool,
}

#[derive(Parser, Debug)]
pub struct OrchestrateArgs {
    #[arg(long, default_value = "./examples/ingested.sample.jsonl")]
    pub events_out: PathBuf,
    #[arg(long)]
    pub state_file: Option<PathBuf>,
    #[arg(long)]
    pub since: Option<DateTime<Utc>>,
    #[arg(long)]
    pub limit: Option<usize>,
    #[arg(long = "providers", value_enum)]
    pub providers: Vec<IngestProvider>,
    #[arg(long, help = "Month in YYYY-MM")]
    pub month: Option<String>,
    #[arg(long, default_value = "pricing.example.json")]
    pub pricing: PathBuf,
    #[arg(long, value_enum, default_value_t = OnUnpricedAction::Error)]
    pub on_unpriced: OnUnpricedAction,
    #[arg(long)]
    pub skip_ingest: bool,
    #[arg(long)]
    pub skip_bench: bool,
    #[arg(long)]
    pub skip_gate: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Skip pricing reconcile stage (coverage -> apply -> check)"
    )]
    pub skip_pricing_reconcile: bool,
    #[arg(
        long,
        default_value = "./benchmarks/results",
        help = "Workdir for pricing reconcile artifacts"
    )]
    pub pricing_reconcile_workdir: PathBuf,
    #[arg(
        long,
        default_value_t = false,
        help = "Use reconcile workdir as-is (disable per-run timestamped artifact subdirectories)"
    )]
    pub pricing_reconcile_static_artifacts: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Run pricing reconcile in dry-run mode"
    )]
    pub pricing_reconcile_dry_run: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Write pricing backup during reconcile apply stage"
    )]
    pub pricing_reconcile_write_backup: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Allow pricing reconcile to overwrite existing model rates/aliases"
    )]
    pub pricing_reconcile_allow_overwrite_model_rates: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Allow pricing reconcile to succeed even when unpriced events remain"
    )]
    pub pricing_reconcile_allow_unpriced: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Run pricing-lint before monthly/daily/bench stages"
    )]
    pub pricing_lint: bool,
    #[arg(
        long,
        default_value_t = false,
        help = "Run pricing-audit before monthly/daily/bench stages"
    )]
    pub pricing_audit: bool,
    #[arg(
        long,
        default_value_t = 30,
        help = "Maximum allowed age of pricing metadata in days for pricing-audit"
    )]
    pub pricing_max_age_days: i64,
    #[arg(long)]
    pub summary_json_path: Option<PathBuf>,
    #[arg(
        long,
        help = "Optional deterministic ingest cache metadata path; unchanged inputs reuse existing --events-out output"
    )]
    pub ingest_cache_path: Option<PathBuf>,
    #[arg(
        long,
        help = "Optional aggregate cache path for monthly/daily outputs keyed by month/filter/pricing/events fingerprint"
    )]
    pub aggregate_cache_path: Option<PathBuf>,
    #[arg(
        long,
        help = "Write compact JSON snapshot for menu/statusbar UIs (CodexBar/OpenCode style)"
    )]
    pub ui_snapshot_path: Option<PathBuf>,
    #[arg(
        long,
        value_enum,
        default_value_t = UiSnapshotMode::Compact,
        help = "UI snapshot verbosity mode: compact (top lists) or extended (full provider/model breakdowns)"
    )]
    pub ui_snapshot_mode: UiSnapshotMode,
    #[arg(long, help = "Write orchestrate pipeline summary JSON to this path")]
    pub pipeline_summary_path: Option<PathBuf>,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
pub enum BenchScenario {
    ColdBackfill,
    WarmTail,
    Burst,
    All,
}

#[derive(Copy, Clone, Debug, ValueEnum)]
pub enum OutputMode {
    Table,
    Markdown,
    Json,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, ValueEnum)]
pub enum OnUnpricedAction {
    Error,
    Skip,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, ValueEnum, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum UiSnapshotMode {
    Compact,
    Extended,
}
