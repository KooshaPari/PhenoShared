use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::io::Write;

use crate::cli::UiSnapshotMode;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenUsage {
    #[serde(default)]
    pub input_tokens: u64,
    #[serde(default)]
    pub output_tokens: u64,
    #[serde(default)]
    pub cache_write_tokens: u64,
    #[serde(default)]
    pub cache_read_tokens: u64,
    #[serde(default)]
    pub tool_input_tokens: u64,
    #[serde(default)]
    pub tool_output_tokens: u64,
}

impl TokenUsage {
    pub fn total(&self) -> u64 {
        self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
            + self.tool_input_tokens
            + self.tool_output_tokens
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageEvent {
    pub provider: String,
    pub model: String,
    pub session_id: String,
    pub timestamp: DateTime<Utc>,
    pub usage: TokenUsage,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ModelRate {
    pub input_usd_per_mtok: f64,
    pub output_usd_per_mtok: f64,
    #[serde(default)]
    pub cache_write_usd_per_mtok: Option<f64>,
    #[serde(default)]
    pub cache_read_usd_per_mtok: Option<f64>,
    #[serde(default)]
    pub tool_input_usd_per_mtok: Option<f64>,
    #[serde(default)]
    pub tool_output_usd_per_mtok: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderPricing {
    #[serde(default)]
    pub subscription_usd_month: f64,
    pub models: HashMap<String, ModelRate>,
    #[serde(default)]
    pub model_aliases: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PricingBook {
    pub providers: HashMap<String, ProviderPricing>,
    #[serde(default)]
    pub provider_aliases: HashMap<String, String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<PricingMeta>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PricingMeta {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct PricingPatch {
    #[serde(default)]
    pub missing_providers: HashMap<String, MissingProviderPatch>,
    #[serde(default)]
    pub missing_models_by_provider: HashMap<String, HashMap<String, ModelRate>>,
    #[serde(default)]
    pub suggested_aliases: SuggestedAliasesPatch,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct MissingProviderPatch {
    #[serde(default)]
    pub subscription_usd_month: f64,
    #[serde(default)]
    pub models: HashMap<String, ModelRate>,
    #[serde(default)]
    pub model_aliases: HashMap<String, String>,
    #[serde(default)]
    pub suggested_provider_aliases: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SuggestedAliasesPatch {
    #[serde(default)]
    pub provider_aliases: HashMap<String, Vec<String>>,
    #[serde(default)]
    pub model_aliases_by_provider: HashMap<String, HashMap<String, Vec<String>>>,
}

#[derive(Debug, Clone, Default, Serialize, PartialEq, Eq)]
pub struct PricingApplySummary {
    pub providers_added: usize,
    pub models_added: usize,
    pub aliases_added: usize,
    pub models_skipped_existing: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingReconcileSummary {
    pub pricing: String,
    pub month_filter: Option<String>,
    pub workdir: String,
    pub allow_unpriced: bool,
    pub dry_run: bool,
    pub write_backup: bool,
    pub allow_overwrite_model_rates: bool,
    pub artifacts: PricingReconcileArtifacts,
    pub coverage: CoverageReport,
    pub pricing_apply: PricingReconcileApplyResult,
    pub pricing_check: PricingReconcileCheckResult,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingReconcileArtifacts {
    pub patch_path: String,
    pub unpriced_events_path: String,
    pub backup_path: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingReconcileApplyResult {
    pub changed: bool,
    pub wrote_pricing: bool,
    pub metadata_updated: bool,
    pub summary: PricingApplySummary,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingReconcileCheckResult {
    pub passed: bool,
    pub month: String,
    pub priced_count: usize,
    pub unpriced_count: usize,
    pub details: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingLintSummary {
    pub pricing: String,
    pub alias_integrity_ok: bool,
    pub placeholder_violations: Vec<String>,
    pub allow_placeholders: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct PricingAuditReport {
    pub pricing_path: String,
    pub checked_at: String,
    pub metadata_present: bool,
    pub source_present: bool,
    pub updated_at_present: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub age_days: Option<i64>,
    pub stale: bool,
    pub pass: bool,
    pub violations: Vec<String>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct PricingReconcileOutcome {
    pub summary: PricingReconcileSummary,
    pub fail_for_unpriced: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostBreakdown {
    pub variable_cost_usd: f64,
    pub subscription_allocated_usd: f64,
    pub monthly_total_usd: f64,
    pub blended_usd_per_mtok: f64,
    pub total_tokens: u64,
    pub total_mtok: f64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cache_write_tokens: u64,
    pub cache_read_tokens: u64,
    pub tool_input_tokens: u64,
    pub tool_output_tokens: u64,
    pub session_count: usize,
    pub skipped_unpriced_count: usize,
    pub provider_breakdown: Vec<NamedMetric>,
    pub model_breakdown: Vec<NamedMetric>,
    pub suggestions: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct CoverageReport {
    pub month: String,
    pub totals: CoverageTotals,
    pub priced_count: usize,
    pub unpriced_count: usize,
    pub missing_providers: Vec<String>,
    pub missing_models_by_provider: BTreeMap<String, Vec<String>>,
    pub suggested_provider_aliases: BTreeMap<String, Vec<String>>,
    pub suggested_model_aliases_by_provider: BTreeMap<String, Vec<UnknownModelSuggestion>>,
}

#[derive(Debug, Clone, Serialize)]
pub struct CoverageTotals {
    pub events: usize,
    pub tokens: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct UnknownModelSuggestion {
    pub model: String,
    pub count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyReport {
    pub month: String,
    pub totals: CostBreakdown,
    pub days: Vec<DailyEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyEntry {
    pub day: String,
    pub breakdown: CostBreakdown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NamedMetric {
    pub name: String,
    pub tokens: u64,
    pub mtok: f64,
    pub variable_cost_usd: f64,
    pub subscription_allocated_usd: f64,
    pub total_cost_usd: f64,
    pub blended_usd_per_mtok: f64,
    pub session_count: usize,
    pub tool_share: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiSnapshot {
    pub schema_version: u32,
    pub generated_at: DateTime<Utc>,
    pub month: String,
    pub mode: UiSnapshotMode,
    pub totals: UiSnapshotTotals,
    pub top_providers: Vec<UiSnapshotMetric>,
    pub top_models: Vec<UiSnapshotMetric>,
    pub suggestions: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reconcile_latest_summary_path: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiSnapshotTotals {
    pub cost_usd: f64,
    pub tokens: u64,
    pub blended_usd_per_mtok: f64,
    pub session_count: usize,
    pub skipped_unpriced_count: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiSnapshotMetric {
    pub name: String,
    pub tokens: u64,
    pub total_cost_usd: f64,
    pub blended_usd_per_mtok: f64,
    pub session_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct OrchestrateIngestCache {
    pub version: u8,
    pub providers: Vec<String>,
    pub since: Option<String>,
    pub limit: Option<usize>,
    pub events_out: String,
    pub source_mtimes: BTreeMap<String, u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrateAggregateCache {
    pub version: u8,
    #[serde(default)]
    pub entries: BTreeMap<String, OrchestrateAggregateCacheEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrateAggregateCacheEntry {
    pub selector: OrchestrateAggregateCacheSelector,
    pub pricing_hash: String,
    pub events_fingerprint: String,
    pub monthly: CostBreakdown,
    pub daily: DailyReport,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct OrchestrateAggregateCacheSelector {
    pub month_filter: Option<String>,
    pub providers: Vec<String>,
    pub models: Vec<String>,
    pub on_unpriced: String,
}

#[derive(Debug, Clone)]
pub struct OrchestrateAggregateCacheKey {
    pub selector: OrchestrateAggregateCacheSelector,
    pub pricing_hash: String,
    pub events_fingerprint: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestrateAggregateCacheMetrics {
    pub enabled: bool,
    pub cache_path: Option<String>,
    pub hit_count: u64,
    pub miss_count: u64,
    pub invalidate_count: u64,
}

pub enum OrchestrateAggregateCacheLookup {
    Hit(OrchestrateAggregateCacheEntry),
    Miss,
    Invalidate,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestratePipelineSummary {
    pub schema_version: u32,
    pub generated_at: DateTime<Utc>,
    pub month_filter: Option<String>,
    pub events_out: String,
    pub pricing: String,
    pub on_unpriced: String,
    pub duration_ms: u128,
    pub ingest: OrchestrateIngestStageSummary,
    pub pricing_reconcile: OrchestratePricingReconcileStageSummary,
    pub monthly: OrchestrateStageSummary,
    pub daily: OrchestrateStageSummary,
    pub aggregate_cache: OrchestrateAggregateCacheMetrics,
    pub bench: OrchestrateBenchStageSummary,
    pub perf_gate: OrchestrateStageSummary,
    pub ui_snapshot_path: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestrateStageSummary {
    pub skipped: bool,
    pub duration_ms: u128,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestrateIngestStageSummary {
    pub skipped: bool,
    pub cache_enabled: bool,
    pub cache_hit: bool,
    pub cache_path: Option<String>,
    pub duration_ms: u128,
    pub summary_json_path: Option<String>,
    pub summary: Option<IngestSummary>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestratePricingReconcileStageSummary {
    pub skipped: bool,
    pub duration_ms: u128,
    pub run_summary_path: Option<String>,
    pub latest_summary_path: Option<String>,
    pub summary: Option<PricingReconcileSummary>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OrchestrateBenchStageSummary {
    pub skipped: bool,
    pub duration_ms: u128,
    pub latest_summary_path: Option<String>,
    pub baseline_used: bool,
    pub report: Option<BenchReport>,
}

#[derive(Default, Debug, Clone)]
pub struct Acc {
    pub tokens: u64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cache_write_tokens: u64,
    pub cache_read_tokens: u64,
    pub tool_input_tokens: u64,
    pub tool_output_tokens: u64,
    pub variable_cost_usd: f64,
    pub subscription_allocated_usd: f64,
    pub sessions: HashSet<u64>,
}

#[derive(Default, Debug, Clone)]
pub struct BenchCorrectnessAccumulator {
    pub variable_cost_usd: f64,
    pub subscription_allocated_usd: f64,
    pub monthly_total_usd: f64,
    pub total_tokens: u64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cache_write_tokens: u64,
    pub cache_read_tokens: u64,
    pub tool_input_tokens: u64,
    pub tool_output_tokens: u64,
    pub skipped_unpriced_count: usize,
}

// Ingest-related types (used by multiple modules)
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct IngestStats {
    pub scanned: usize,
    pub emitted: usize,
    pub skipped: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestSummary {
    pub providers: BTreeMap<String, IngestStats>,
    pub incremental_sources_skipped: usize,
    pub emitted_total: usize,
    pub deduped_total: usize,
    pub output: String,
    pub started_at: DateTime<Utc>,
    pub finished_at: DateTime<Utc>,
    pub duration_ms: u128,
}

#[derive(Debug, Clone, Eq, PartialEq, Hash)]
pub struct IngestDedupeKey {
    pub provider: String,
    pub session_id: String,
    pub timestamp_millis: i64,
    pub model: String,
    pub token_total: u64,
}

pub struct IngestEmitCtx<'a> {
    pub since: Option<DateTime<Utc>>,
    pub limit: Option<usize>,
    pub total_emitted: &'a mut usize,
    pub deduped_total: &'a mut usize,
    pub dedupe_seen: Option<&'a mut HashSet<IngestDedupeKey>>,
    pub writer: &'a mut std::io::BufWriter<std::fs::File>,
    pub stats: &'a mut IngestStats,
}

impl IngestEmitCtx<'_> {
    pub fn limit_reached(&self) -> bool {
        self.limit.is_some_and(|max| *self.total_emitted >= max)
    }

    pub fn emit_event(&mut self, event: &UsageEvent) -> anyhow::Result<()> {
        if let Some(seen) = self.dedupe_seen.as_mut() {
            let dedupe_key = IngestDedupeKey {
                provider: event.provider.clone(),
                session_id: event.session_id.clone(),
                timestamp_millis: event.timestamp.timestamp_millis(),
                model: event.model.clone(),
                token_total: event.usage.total(),
            };
            if !seen.insert(dedupe_key) {
                *self.deduped_total += 1;
                return Ok(());
            }
        }
        serde_json::to_writer(&mut *self.writer, event)?;
        self.writer.write_all(b"\n")?;
        *self.total_emitted += 1;
        self.stats.emitted += 1;
        Ok(())
    }
}

// Benchmark report structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchReport {
    pub scenario: String,
    pub month: String,
    #[serde(default = "default_generated_at")]
    pub generated_at: DateTime<Utc>,
    #[serde(default)]
    pub label: Option<String>,
    pub results: Vec<BenchScenarioResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchScenarioResult {
    pub scenario: String,
    pub elapsed_ms: f64,
    pub events_processed: usize,
    pub events_per_sec: f64,
    #[serde(default)]
    pub correctness: Option<BenchScenarioCorrectness>,
    pub elapsed_ms_delta: Option<f64>,
    pub events_per_sec_delta: Option<f64>,
    pub elapsed_regression: Option<bool>,
    pub events_per_sec_regression: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BenchScenarioCorrectness {
    pub variable_cost_usd: f64,
    pub subscription_allocated_usd: f64,
    pub monthly_total_usd: f64,
    pub blended_usd_per_mtok: f64,
    pub total_tokens: u64,
    pub total_mtok: f64,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cache_write_tokens: u64,
    pub cache_read_tokens: u64,
    pub tool_input_tokens: u64,
    pub tool_output_tokens: u64,
    pub skipped_unpriced_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchTrendReport {
    pub trend_dir: String,
    #[serde(default = "default_generated_at")]
    pub generated_at: DateTime<Utc>,
    #[serde(default)]
    pub label: Option<String>,
    pub scenarios: Vec<BenchTrendScenarioSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerfGateConfig {
    #[serde(default)]
    pub require_baseline_for_regression_checks: bool,
    pub scenarios: BTreeMap<String, PerfGateThreshold>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerfGateThreshold {
    pub max_ms: f64,
    pub min_events_per_sec: f64,
    #[serde(default)]
    pub max_elapsed_regression_pct: Option<f64>,
    #[serde(default)]
    pub max_eps_drop_pct: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchTrendScenarioSummary {
    pub scenario: String,
    pub run_count: usize,
    pub latest_elapsed_ms: f64,
    pub median_elapsed_ms: f64,
    pub p95_elapsed_ms: f64,
    pub latest_events_per_sec: f64,
    pub median_events_per_sec: f64,
}

#[derive(Debug, Clone)]
pub struct BenchTrendSample {
    pub source: String,
    pub collected_at_unix: u64,
    pub elapsed_ms: f64,
    pub events_per_sec: f64,
}

fn default_generated_at() -> DateTime<Utc> {
    Utc::now()
}
