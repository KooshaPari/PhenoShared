//! # perfharness
//!
//! Reusable 3-regime profiling harness for Phenotype perf-critical projects.
//!
//! ## Regimes
//!
//! 1. **Individual** — single run wall-clock + phase breakdown (spawn/init/work/teardown),
//!    separating unavoidable wait (LLM/network) from optimizable compute. Wraps samply,
//!    cargo-flamegraph, or Instruments when available; degrades gracefully.
//!
//! 2. **Accumulated** — (a) sequential N-runs throughput; (b) long-running RSS memory
//!    profile — leak/fragmentation/growth detection. Flags the forgecode-3GB-class growth
//!    pattern.
//!
//! 3. **Scaled-parallel** — M concurrent copies (configurable: 1/4/8/16/32/64), throughput
//!    vs M curve, plateau/degradation detection. The packing-density metric.
//!
//! ## Scorecard
//!
//! Each run emits a machine-readable [`Scorecard`] (JSON) plus a human-readable markdown
//! table with per-regime numbers, bottleneck classification, and ranked optimizable hot
//! paths with candidate-tech suggestions.

pub mod profiler;
pub mod regimes;
pub mod scorecard;

pub use profiler::ExternalProfiler;
pub use regimes::{AccumulatedResult, IndividualResult, ScaledParallelResult};
pub use scorecard::{BottleneckClass, OptHotPath, RegimeResult, Scorecard};

/// Configuration for a single harness run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct HarnessConfig {
    /// Command to profile, e.g. `["./my-binary", "--flag"]`.
    pub command: Vec<String>,

    /// Working directory for the command (defaults to cwd).
    pub workdir: Option<String>,

    /// Environment variables to inject into the child process.
    pub env: Vec<(String, String)>,

    /// Number of sequential runs for the accumulated regime.
    pub accumulated_runs: usize,

    /// RSS poll interval in milliseconds during long-running profiling.
    pub rss_poll_ms: u64,

    /// Duration (seconds) to hold one process alive for the long-running memory sub-regime.
    /// If 0, skipped.
    pub long_running_secs: u64,

    /// Parallelism ladder for the scaled-parallel regime, e.g. [1, 4, 8, 16, 32, 64].
    pub parallel_ladder: Vec<usize>,

    /// Timeout per individual run in seconds.
    pub run_timeout_secs: u64,

    /// Whether to invoke an external profiler (samply / cargo-flamegraph / instruments).
    pub use_external_profiler: bool,
}

impl Default for HarnessConfig {
    fn default() -> Self {
        Self {
            command: vec![],
            workdir: None,
            env: vec![],
            accumulated_runs: 20,
            rss_poll_ms: 500,
            long_running_secs: 0,
            parallel_ladder: vec![1, 4, 8, 16, 32, 64],
            run_timeout_secs: 30,
            use_external_profiler: false,
        }
    }
}
