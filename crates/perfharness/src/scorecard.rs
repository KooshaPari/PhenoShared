//! Scorecard: machine-readable JSON + human markdown output.
//!
//! Mirrors the forgecode#74 profile format: per-regime tables, bottleneck
//! classification, and ranked hot-path suggestions with candidate tech.

use crate::profiler::ExternalProfiler;
use crate::regimes::{AccumulatedResult, IndividualResult, ScaledParallelResult};
use chrono::Utc;

/// Top-level bottleneck classification for a profiled target.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BottleneckClass {
    /// Process/binary startup dominates individual latency.
    Init,
    /// Thread/task creation overhead (tokio/rayon/OS threads) caps throughput.
    Thread,
    /// Lock contention (Mutex/RwLock) under parallelism.
    Lock,
    /// Allocator pressure — heap fragmentation or per-request alloc storms.
    Alloc,
    /// I/O bound — disk or network wait.
    Io,
    /// IPC overhead (Unix socket, pipe, shared memory).
    Ipc,
    /// External rate limit (API, upstream LLM) — unavoidable wait.
    RateLimit,
    /// Memory leak or unbounded growth over time (forgecode-class).
    MemoryGrowth,
    /// No clear single bottleneck; distributed across multiple categories.
    Mixed,
    /// Insufficient data to classify.
    Unknown,
}

/// A single optimizable hot path with a candidate-tech suggestion.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct OptHotPath {
    /// Human-readable description of the hot path.
    pub description: String,
    /// Estimated impact (0.0–1.0; higher = more impactful to fix).
    pub estimated_impact: f64,
    /// Suggested technology or technique.
    pub candidate_tech: String,
}

/// Per-regime result summary embedded in the scorecard.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RegimeResult {
    pub individual: Option<IndividualResult>,
    pub accumulated: Option<AccumulatedResult>,
    pub scaled_parallel: Option<ScaledParallelResult>,
}

/// Full scorecard for one harness run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Scorecard {
    /// Target command that was profiled.
    pub target: Vec<String>,
    /// ISO-8601 timestamp of the run.
    pub timestamp: String,
    /// External profiler used (or None).
    pub profiler: ExternalProfiler,
    /// Per-regime results.
    pub regimes: RegimeResult,
    /// Primary bottleneck classification.
    pub bottleneck: BottleneckClass,
    /// Ranked list of optimizable hot paths (highest impact first).
    pub hot_paths: Vec<OptHotPath>,
}

impl Scorecard {
    /// Build a scorecard from regime results and infer the bottleneck.
    pub fn build(
        target: Vec<String>,
        profiler: ExternalProfiler,
        individual: Option<IndividualResult>,
        accumulated: Option<AccumulatedResult>,
        scaled_parallel: Option<ScaledParallelResult>,
    ) -> Self {
        let bottleneck = infer_bottleneck(&individual, &accumulated, &scaled_parallel);
        let hot_paths = rank_hot_paths(&bottleneck, &individual, &accumulated, &scaled_parallel);

        Self {
            target,
            timestamp: Utc::now().to_rfc3339(),
            profiler,
            regimes: RegimeResult {
                individual,
                accumulated,
                scaled_parallel,
            },
            bottleneck,
            hot_paths,
        }
    }

    /// Serialise to compact JSON string.
    pub fn to_json(&self) -> anyhow::Result<String> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    /// Render as human-readable markdown (mirrors forgecode#74 table format).
    pub fn to_markdown(&self) -> String {
        let mut out = String::new();

        out.push_str("# Perfharness Scorecard\n\n");
        out.push_str(&format!("**Target:** `{}`  \n", self.target.join(" ")));
        out.push_str(&format!("**Timestamp:** {}  \n", self.timestamp));
        out.push_str(&format!("**Profiler:** {}  \n\n", self.profiler.name()));

        // --- Regime 1: Individual ---
        out.push_str("## Regime 1 — Individual\n\n");
        if let Some(ref r) = self.regimes.individual {
            out.push_str("| Phase | Duration (ms) | Note |\n");
            out.push_str("|---|---|---|\n");
            out.push_str(&format!(
                "| spawn | {:.1} | process creation overhead |\n",
                r.spawn_ms
            ));
            out.push_str(&format!(
                "| init | {:.1} | binary startup to first work |\n",
                r.init_ms
            ));
            out.push_str(&format!(
                "| work | {:.1} | optimizable compute |\n",
                r.work_ms
            ));
            out.push_str(&format!(
                "| wait | {:.1} | unavoidable LLM/network wait |\n",
                r.unavoidable_wait_ms
            ));
            out.push_str(&format!("| teardown | {:.1} | cleanup |\n", r.teardown_ms));
            out.push_str(&format!(
                "| **total** | **{:.1}** | wall-clock |\n\n",
                r.total_wall_ms
            ));
        } else {
            out.push_str("_skipped_\n\n");
        }

        // --- Regime 2: Accumulated ---
        out.push_str("## Regime 2 — Accumulated\n\n");
        if let Some(ref r) = self.regimes.accumulated {
            out.push_str("### Sequential throughput\n\n");
            out.push_str("| Metric | Value |\n|---|---|\n");
            out.push_str(&format!("| runs | {} |\n", r.sequential_runs));
            out.push_str(&format!("| total_ms | {:.1} |\n", r.sequential_total_ms));
            out.push_str(&format!(
                "| mean_ms | {:.1} |\n",
                r.sequential_total_ms / r.sequential_runs as f64
            ));
            out.push_str(&format!("| throughput_rps | {:.2} |\n\n", r.throughput_rps));

            out.push_str("### Long-running memory\n\n");
            if r.rss_samples.is_empty() {
                out.push_str("_skipped (long_running_secs = 0)_\n\n");
            } else {
                let rss_mb: Vec<f64> = r
                    .rss_samples
                    .iter()
                    .map(|s| s.rss_kb as f64 / 1024.0)
                    .collect();
                let min = rss_mb.iter().cloned().fold(f64::INFINITY, f64::min);
                let max = rss_mb.iter().cloned().fold(0.0_f64, f64::max);
                let growth = max - min;
                out.push_str("| Metric | Value |\n|---|---|\n");
                out.push_str(&format!("| rss_min_mb | {:.1} |\n", min));
                out.push_str(&format!("| rss_max_mb | {:.1} |\n", max));
                out.push_str(&format!("| rss_growth_mb | {:.1} |\n", growth));
                out.push_str(&format!(
                    "| leak_flag | {} |\n\n",
                    if r.memory_leak_flag {
                        "**YES — investigate**"
                    } else {
                        "no"
                    }
                ));
            }
        } else {
            out.push_str("_skipped_\n\n");
        }

        // --- Regime 3: Scaled-parallel ---
        out.push_str("## Regime 3 — Scaled-parallel\n\n");
        if let Some(ref r) = self.regimes.scaled_parallel {
            out.push_str("| Concurrency (M) | Throughput (rps) | Efficiency |\n");
            out.push_str("|---|---|---|\n");
            let baseline = r.curve.first().map(|p| p.throughput_rps).unwrap_or(1.0);
            for point in &r.curve {
                let eff = if baseline > 0.0 {
                    (point.throughput_rps / baseline) / point.concurrency as f64
                } else {
                    0.0
                };
                out.push_str(&format!(
                    "| {} | {:.2} | {:.2} |\n",
                    point.concurrency, point.throughput_rps, eff
                ));
            }
            out.push_str(&format!(
                "\n**Plateau at M={}** ({:.2} rps), degrades past M={}\n\n",
                r.plateau_concurrency, r.plateau_throughput_rps, r.degradation_concurrency
            ));
        } else {
            out.push_str("_skipped_\n\n");
        }

        // --- Bottleneck & hot paths ---
        out.push_str("## Bottleneck & Optimizations\n\n");
        out.push_str(&format!(
            "**Primary bottleneck:** `{:?}`\n\n",
            self.bottleneck
        ));
        if self.hot_paths.is_empty() {
            out.push_str("_No hot paths identified._\n");
        } else {
            out.push_str("| Rank | Description | Impact | Candidate Tech |\n");
            out.push_str("|---|---|---|---|\n");
            for (i, hp) in self.hot_paths.iter().enumerate() {
                out.push_str(&format!(
                    "| {} | {} | {:.0}% | {} |\n",
                    i + 1,
                    hp.description,
                    hp.estimated_impact * 100.0,
                    hp.candidate_tech
                ));
            }
        }

        out
    }
}

// --- Internal inference helpers ---

fn infer_bottleneck(
    individual: &Option<IndividualResult>,
    accumulated: &Option<AccumulatedResult>,
    scaled_parallel: &Option<ScaledParallelResult>,
) -> BottleneckClass {
    // Memory growth check (forgecode-class 3GB pattern).
    if let Some(acc) = accumulated {
        if acc.memory_leak_flag {
            return BottleneckClass::MemoryGrowth;
        }
    }

    // Scaled-parallel plateau vs linear-ideal.
    if let Some(sp) = scaled_parallel {
        if sp.plateau_concurrency <= 8 && sp.curve.len() > 2 {
            // Plateaus very early → thread/lock bottleneck.
            return BottleneckClass::Thread;
        }
    }

    // Init-dominated: spawn+init > 60% of total.
    if let Some(ind) = individual {
        let init_frac = (ind.spawn_ms + ind.init_ms) / ind.total_wall_ms.max(1.0);
        if init_frac > 0.6 {
            return BottleneckClass::Init;
        }
        // Rate-limit dominated: unavoidable wait > 50%.
        let wait_frac = ind.unavoidable_wait_ms / ind.total_wall_ms.max(1.0);
        if wait_frac > 0.5 {
            return BottleneckClass::RateLimit;
        }
    }

    BottleneckClass::Unknown
}

fn rank_hot_paths(
    bottleneck: &BottleneckClass,
    individual: &Option<IndividualResult>,
    _accumulated: &Option<AccumulatedResult>,
    scaled_parallel: &Option<ScaledParallelResult>,
) -> Vec<OptHotPath> {
    let mut paths = Vec::new();

    match bottleneck {
        BottleneckClass::Init => {
            if let Some(ind) = individual {
                paths.push(OptHotPath {
                    description: format!(
                        "Spawn+init takes {:.0}ms — reduce binary startup",
                        ind.spawn_ms + ind.init_ms
                    ),
                    estimated_impact: 0.7,
                    candidate_tech: "Zig daemon (posix_spawn + kqueue IPC); lazy init; \
                        pre-fork worker pool"
                        .into(),
                });
            }
        }
        BottleneckClass::Thread => {
            if let Some(sp) = scaled_parallel {
                paths.push(OptHotPath {
                    description: format!(
                        "Thread storm: throughput plateaus at M={} ({:.0} rps)",
                        sp.plateau_concurrency, sp.plateau_throughput_rps
                    ),
                    estimated_impact: 0.8,
                    candidate_tech: "Zig forge-daemon (lock-free SPSC ring + kqueue/kevent); \
                        reduce OS-thread count per process (tokio current_thread); io_uring"
                        .into(),
                });
            }
        }
        BottleneckClass::MemoryGrowth => {
            paths.push(OptHotPath {
                description: "RSS grows unboundedly over sequential runs — likely leak or \
                    cache bloat (SELECT * on large blob tables)"
                    .into(),
                estimated_impact: 0.9,
                candidate_tech: "heaptrack/massif; pagination + LIMIT on DB queries; \
                    mimalloc/jemalloc; arena allocators"
                    .into(),
            });
        }
        BottleneckClass::RateLimit => {
            paths.push(OptHotPath {
                description: "Majority of wall-clock is unavoidable upstream wait".into(),
                estimated_impact: 0.3,
                candidate_tech: "Request batching; streaming responses; speculative prefetch"
                    .into(),
            });
        }
        _ => {}
    }

    // Always suggest profiler if none available.
    paths.push(OptHotPath {
        description: "Install samply or cargo-flamegraph for flame graphs".into(),
        estimated_impact: 0.1,
        candidate_tech: "samply record <cmd>; cargo flamegraph".into(),
    });

    paths
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::regimes::{IndividualResult, RssSample};

    #[test]
    fn scorecard_serialises_to_valid_json() {
        let ind = IndividualResult {
            spawn_ms: 10.0,
            init_ms: 40.0,
            work_ms: 30.0,
            unavoidable_wait_ms: 5.0,
            teardown_ms: 2.0,
            total_wall_ms: 87.0,
            exit_code: Some(0),
            profiler_output: None,
        };
        let sc = Scorecard::build(
            vec!["echo".into(), "hello".into()],
            ExternalProfiler::None,
            Some(ind),
            None,
            None,
        );
        let json = sc.to_json().unwrap();
        let reparsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(reparsed["target"][0], "echo");
        assert!(reparsed["bottleneck"].is_string());
    }

    #[test]
    fn scorecard_markdown_contains_regime_headers() {
        let sc = Scorecard::build(
            vec!["true".into()],
            ExternalProfiler::None,
            None,
            None,
            None,
        );
        let md = sc.to_markdown();
        assert!(md.contains("Regime 1"));
        assert!(md.contains("Regime 2"));
        assert!(md.contains("Regime 3"));
    }

    #[test]
    fn memory_growth_flag_sets_bottleneck() {
        use crate::regimes::AccumulatedResult;
        let acc = AccumulatedResult {
            sequential_runs: 5,
            sequential_total_ms: 500.0,
            throughput_rps: 10.0,
            rss_samples: vec![
                RssSample {
                    elapsed_ms: 0,
                    rss_kb: 10_000,
                },
                RssSample {
                    elapsed_ms: 500,
                    rss_kb: 50_000,
                },
            ],
            memory_leak_flag: true,
        };
        let sc = Scorecard::build(
            vec!["test".into()],
            ExternalProfiler::None,
            None,
            Some(acc),
            None,
        );
        assert_eq!(sc.bottleneck, BottleneckClass::MemoryGrowth);
    }

    #[test]
    fn init_dominated_classifies_as_init() {
        let ind = IndividualResult {
            spawn_ms: 200.0,
            init_ms: 100.0,
            work_ms: 50.0,
            unavoidable_wait_ms: 0.0,
            teardown_ms: 10.0,
            total_wall_ms: 360.0,
            exit_code: Some(0),
            profiler_output: None,
        };
        let sc = Scorecard::build(
            vec!["test".into()],
            ExternalProfiler::None,
            Some(ind),
            None,
            None,
        );
        assert_eq!(sc.bottleneck, BottleneckClass::Init);
    }
}
