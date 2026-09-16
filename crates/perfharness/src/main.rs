//! perfharness CLI — reusable 3-regime profiling harness.
//!
//! Usage:
//!   perfharness run --cmd "echo hello" --regime all --out scorecard.json
//!   perfharness run --cmd "./my-binary --flag" --regime individual
//!   perfharness selftest

use anyhow::Result;
use clap::{Parser, Subcommand, ValueEnum};
use perfharness::{
    profiler::ExternalProfiler,
    regimes::{accumulated, individual, scaled_parallel},
    scorecard::Scorecard,
    HarnessConfig,
};
use tracing::info;

#[derive(Parser)]
#[command(name = "perfharness")]
#[command(about = "Reusable 3-regime profiling harness for Phenotype perf-critical projects")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Profile a target command across the configured regimes.
    Run {
        /// Command to profile (shell-split, e.g. `echo hello` or `./binary --flag`).
        #[arg(long, required = true)]
        cmd: String,

        /// Regimes to run.
        #[arg(long, default_value = "all")]
        regime: RegimeArg,

        /// Sequential runs for the accumulated regime.
        #[arg(long, default_value_t = 20)]
        runs: usize,

        /// Concurrency ladder (comma-separated), e.g. `1,4,8,16,32`.
        #[arg(long, default_value = "1,4,8,16,32")]
        ladder: String,

        /// Long-running seconds for RSS profiling (0 = skip).
        #[arg(long, default_value_t = 0)]
        rss_secs: u64,

        /// Per-run timeout in seconds.
        #[arg(long, default_value_t = 30)]
        timeout: u64,

        /// Output JSON scorecard to this file (stdout if omitted).
        #[arg(long)]
        out: Option<String>,

        /// Also write a markdown report alongside the JSON (replaces .json → .md).
        #[arg(long, default_value_t = false)]
        markdown: bool,

        /// Use an external profiler (samply / cargo-flamegraph / xctrace) for regime 1.
        #[arg(long, default_value_t = false)]
        external_profiler: bool,
    },

    /// Run a self-test against a trivial known target and validate the 3 regimes.
    Selftest,
}

#[derive(Clone, ValueEnum)]
enum RegimeArg {
    All,
    Individual,
    Accumulated,
    ScaledParallel,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_env("PERFHARNESS_LOG")
                .add_directive("perfharness=info".parse()?),
        )
        .init();

    let cli = Cli::parse();

    match cli.command {
        Cmd::Run {
            cmd,
            regime,
            runs,
            ladder,
            rss_secs,
            timeout,
            out,
            markdown,
            external_profiler,
        } => {
            let command = shell_split(&cmd)?;
            let parallel_ladder = parse_ladder(&ladder)?;

            let cfg = HarnessConfig {
                command,
                accumulated_runs: runs,
                parallel_ladder,
                long_running_secs: rss_secs,
                run_timeout_secs: timeout,
                use_external_profiler: external_profiler,
                ..Default::default()
            };

            let profiler = if external_profiler {
                ExternalProfiler::detect()
            } else {
                ExternalProfiler::None
            };

            let ind = match regime {
                RegimeArg::All | RegimeArg::Individual => {
                    info!("running regime 1: individual");
                    Some(individual::run(&cfg).await?)
                }
                _ => None,
            };

            let acc = match regime {
                RegimeArg::All | RegimeArg::Accumulated => {
                    info!(
                        "running regime 2: accumulated ({} runs, rss_secs={})",
                        runs, rss_secs
                    );
                    Some(accumulated::run(&cfg).await?)
                }
                _ => None,
            };

            let sp = match regime {
                RegimeArg::All | RegimeArg::ScaledParallel => {
                    info!("running regime 3: scaled-parallel ladder={}", ladder);
                    Some(scaled_parallel::run(&cfg).await?)
                }
                _ => None,
            };

            let scorecard = Scorecard::build(cfg.command, profiler, ind, acc, sp);
            let json = scorecard.to_json()?;

            match out {
                None => println!("{json}"),
                Some(ref path) => {
                    std::fs::write(path, &json)?;
                    info!("scorecard written to {path}");

                    if markdown {
                        let md_path = path.replace(".json", ".md");
                        std::fs::write(&md_path, scorecard.to_markdown())?;
                        info!("markdown report written to {md_path}");
                    }
                }
            }
        }

        Cmd::Selftest => {
            run_selftest().await?;
        }
    }

    Ok(())
}

async fn run_selftest() -> Result<()> {
    info!("perfharness self-test: validating 3 regimes against `echo selftest`");

    let cfg = HarnessConfig {
        command: vec!["echo".into(), "selftest".into()],
        accumulated_runs: 5,
        parallel_ladder: vec![1, 2, 4],
        long_running_secs: 0,
        run_timeout_secs: 10,
        use_external_profiler: false,
        ..Default::default()
    };

    // Regime 1: Individual.
    let ind = individual::run(&cfg).await?;
    assert!(
        ind.total_wall_ms > 0.0,
        "individual: total_wall_ms must be positive"
    );
    assert_eq!(ind.exit_code, Some(0), "individual: exit_code must be 0");
    info!("regime 1 OK — total_wall_ms={:.1}", ind.total_wall_ms);

    // Regime 2: Accumulated.
    let acc = accumulated::run(&cfg).await?;
    assert_eq!(acc.sequential_runs, 5, "accumulated: expected 5 runs");
    assert!(
        acc.throughput_rps > 0.0,
        "accumulated: throughput_rps must be positive"
    );
    assert!(
        acc.rss_samples.is_empty(),
        "accumulated: rss_samples must be empty (long_running=0)"
    );
    info!(
        "regime 2 OK — throughput_rps={:.2} mean_ms={:.1}",
        acc.throughput_rps,
        acc.sequential_total_ms / acc.sequential_runs as f64
    );

    // Regime 3: Scaled-parallel.
    let sp = scaled_parallel::run(&cfg).await?;
    assert_eq!(
        sp.curve.len(),
        3,
        "scaled-parallel: expected 3 curve points"
    );
    for pt in &sp.curve {
        assert!(
            pt.throughput_rps > 0.0,
            "scaled-parallel: throughput must be positive at M={}",
            pt.concurrency
        );
    }
    info!(
        "regime 3 OK — plateau at M={} ({:.2} rps), degrades past M={}",
        sp.plateau_concurrency, sp.plateau_throughput_rps, sp.degradation_concurrency
    );

    // Build scorecard and validate serialisation.
    let scorecard = Scorecard::build(
        cfg.command.clone(),
        ExternalProfiler::None,
        Some(ind),
        Some(acc),
        Some(sp),
    );
    let json = scorecard.to_json()?;
    let reparsed: serde_json::Value = serde_json::from_str(&json)?;
    assert!(
        reparsed["bottleneck"].is_string(),
        "scorecard: bottleneck must be a string"
    );
    let md = scorecard.to_markdown();
    assert!(
        md.contains("Regime 1"),
        "markdown must contain regime headers"
    );

    info!("self-test PASSED — all 3 regimes produced sane numbers, scorecard serialises correctly");
    println!("{json}");

    Ok(())
}

/// Shell-split a command string into argv (handles quoted args naively).
fn shell_split(s: &str) -> Result<Vec<String>> {
    // Simple whitespace split; for complex quoting users should use --cmd with shell quoting.
    let parts: Vec<String> = s.split_whitespace().map(str::to_owned).collect();
    if parts.is_empty() {
        anyhow::bail!("--cmd must be a non-empty command string");
    }
    Ok(parts)
}

fn parse_ladder(s: &str) -> Result<Vec<usize>> {
    s.split(',')
        .map(|p| {
            p.trim()
                .parse::<usize>()
                .map_err(|e| anyhow::anyhow!("bad ladder value: {e}"))
        })
        .collect()
}
