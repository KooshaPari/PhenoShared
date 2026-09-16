// @trace QG-CLI-001: qgate CLI entry point
//
// Usage:
//   qgate [OPTIONS]
//   qgate coverage --report coverage/lcov.info --format lcov
//   qgate checks
//   qgate run     (full gate: coverage + all checks)
//
// JSON report goes to stdout; human tree summary goes to stderr.
// Exit code: 0 = PASS, 1 = FAIL.

use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};

use qgate::config::QGateConfig;
use qgate::coverage::{parse_cobertura, parse_json_coverage, parse_lcov, CoverageTree};
use qgate::report::GateReport;
use qgate::runner::run_all_checks;

/// qgate — granular-recursive quality gate CLI for the Phenotype org.
///
/// Enforces ≥threshold% coverage on EVERY module recursively, plus all
/// check-type categories (unit, integration, e2e, chaos, perf, property,
/// mutation, static-analysis, security, a11y).
///
/// JSON report → stdout. Human tree summary → stderr.
/// Exit 0 = PASS, exit 1 = FAIL.
#[derive(Parser, Debug)]
#[command(
    name = "qgate",
    version,
    about = "Granular-recursive quality gate: 85%+ per-module coverage + all check types",
    long_about = None,
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Project root directory (default: current directory).
    #[arg(short, long, default_value = ".", global = true)]
    path: PathBuf,

    /// Exit with non-zero status on any failure.
    #[arg(long, default_value_t = true, global = true)]
    fail: bool,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Run the full quality gate: coverage + all check types.
    Run {
        /// Coverage report file (overrides .qgate.toml).
        #[arg(long)]
        coverage_report: Option<PathBuf>,
        /// Coverage format: lcov | cobertura | json.
        #[arg(long)]
        coverage_format: Option<String>,
        /// Coverage threshold (default from .qgate.toml or 85.0).
        #[arg(long)]
        threshold: Option<f64>,
    },
    /// Evaluate coverage only and print the module tree.
    Coverage {
        /// Coverage report file.
        #[arg(long)]
        report: PathBuf,
        /// Format: lcov | cobertura | json.
        #[arg(long, default_value = "lcov")]
        format: String,
        /// Minimum threshold (0–100, default 85).
        #[arg(long, default_value_t = 85.0)]
        threshold: f64,
    },
    /// Run all check-type categories and report results.
    Checks,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let root = cli.path.canonicalize().unwrap_or_else(|_| cli.path.clone());
    let cfg = QGateConfig::load(&root);

    let (coverage, checks) = match &cli.command {
        Some(Commands::Coverage {
            report,
            format,
            threshold,
        }) => {
            let content = std::fs::read_to_string(report)?;
            let tree = parse_coverage(&content, format, *threshold)?;
            eprint!("{}", tree.render_tree());
            let exit = if tree.all_pass() { 0 } else { 1 };
            std::process::exit(exit);
        }
        Some(Commands::Checks) => {
            let matrix = run_all_checks(&root, &cfg).await?;
            let empty_cov = CoverageTree {
                threshold: cfg.coverage_threshold,
                nodes: vec![],
            };
            (empty_cov, matrix)
        }
        Some(Commands::Run {
            coverage_report,
            coverage_format,
            threshold,
        }) => {
            let threshold = threshold.unwrap_or(cfg.coverage_threshold);
            let cov_format = coverage_format.as_deref().unwrap_or(&cfg.coverage_format);
            let cov_path = coverage_report
                .clone()
                .unwrap_or_else(|| root.join(&cfg.coverage_path));

            let tree = if cov_path.exists() {
                let content = std::fs::read_to_string(&cov_path)?;
                parse_coverage(&content, cov_format, threshold)?
            } else {
                eprintln!(
                    "[qgate] Warning: coverage report not found at {}",
                    cov_path.display()
                );
                eprintln!("[qgate] Run tests with coverage enabled first.");
                CoverageTree {
                    threshold,
                    nodes: vec![],
                }
            };

            let matrix = run_all_checks(&root, &cfg).await?;
            (tree, matrix)
        }
        None => {
            // Default: same as `run` with no overrides
            let threshold = cfg.coverage_threshold;
            let cov_path = root.join(&cfg.coverage_path);
            let tree = if cov_path.exists() {
                let content = std::fs::read_to_string(&cov_path)?;
                parse_coverage(&content, &cfg.coverage_format, threshold)?
            } else {
                eprintln!(
                    "[qgate] Warning: coverage report not found at {}",
                    cov_path.display()
                );
                eprintln!("[qgate] Run tests with coverage enabled first.");
                CoverageTree {
                    threshold,
                    nodes: vec![],
                }
            };
            let matrix = run_all_checks(&root, &cfg).await?;
            (tree, matrix)
        }
    };

    let report = GateReport::new(coverage, checks);
    report.emit_all()?;

    if cli.fail && report.status == qgate::report::GateStatus::Fail {
        std::process::exit(1);
    }

    Ok(())
}

/// Parse a coverage report given its content, format string, and threshold.
fn parse_coverage(content: &str, format: &str, threshold: f64) -> Result<CoverageTree> {
    match format.to_ascii_lowercase().as_str() {
        "cobertura" | "xml" => parse_cobertura(content, threshold),
        "json" => parse_json_coverage(content, threshold),
        _ => parse_lcov(content, threshold),
    }
}
