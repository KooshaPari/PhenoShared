//! `trace-gate` — CI coverage gate binary.
//!
//! Scans source for FR annotations, checks against a manifest, exits 0 on
//! full coverage or 1 if any FR is missing.
//!
//! ```text
//! USAGE:
//!     trace-gate [OPTIONS]
//!
//! OPTIONS:
//!     --manifest <FILE>   Path to trace-gate.toml  [default: trace-gate.toml]
//!     --src <DIR>         Source directory to scan  [default: src]
//!     --push <URL>        Push results to Tracera ingest (best-effort, no exit-code effect)
//!     --json              Emit JSON summary to stdout
//! ```

mod coverage;
mod manifest;
mod push;

use std::path::PathBuf;
use std::process;

use clap::Parser;
use traceability_core::CoverageState;
use traceability_decorators::{patterns::Patterns, scan_dir};

use coverage::CoverageSummary;
use manifest::Manifest;

// ── Terminal colour helpers ───────────────────────────────────────────────────

/// Returns `true` when ANSI colour / Unicode glyphs are acceptable on stderr.
///
/// Disabled when:
/// - `NO_COLOR` is set to any value (https://no-color.org)
/// - `CLICOLOR == 0` (https://bixense.com/clicolors)
/// - stderr is not a terminal and `FORCE_COLOR` is unset
fn use_color_on_stderr() -> bool {
    if std::env::var_os("NO_COLOR").is_some() {
        return false;
    }
    if let Some(v) = std::env::var_os("CLICOLOR") {
        if v == "0" {
            return false;
        }
    }
    // Default: only colour when stderr is a terminal
    is_terminal::IsTerminal::is_terminal(&std::io::stderr())
}

/// Return the pass/fail symbol: coloured glyph on terminal, ASCII label otherwise.
fn pass_fail_symbol(pass: bool) -> &'static str {
    if use_color_on_stderr() {
        if pass {
            "✓"
        } else {
            "✗"
        }
    } else if pass {
        "[PASS]"
    } else {
        "[FAIL]"
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "trace-gate",
    version,
    about = "CI gate: verify FR coverage via source annotations"
)]
struct Args {
    /// Path to the trace-gate.toml manifest.
    #[arg(long, default_value = "trace-gate.toml")]
    manifest: String,

    /// Source directory to scan for annotations.
    #[arg(long, default_value = "src")]
    src: String,

    /// POST coverage set to this Tracera ingest URL (best-effort, does not
    /// affect exit code).
    #[arg(long)]
    push: Option<String>,

    /// Emit full JSON summary to stdout in addition to human-readable output.
    #[arg(long)]
    json: bool,
}

// FR: FR-GATE-001
fn main() {
    // ── Initialise structured logging ──────────────────────────────────────
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_writer(std::io::stderr)
        .with_target(false)
        .without_time() // CLI output is ephemeral — no timestamps needed.
        .init();

    let args = Args::parse();

    // ── Load manifest ────────────────────────────────────────────────────────
    let manifest = match Manifest::load(&args.manifest) {
        Ok(m) => m,
        Err(e) => {
            tracing::error!("trace-gate: cannot load manifest — {e}");
            tracing::warn!("hint: check that '{}' exists and is valid TOML", args.manifest);
            process::exit(2);
        }
    };

    if manifest.requirement.is_empty() {
        tracing::warn!("trace-gate: manifest has no [[requirement]] entries — nothing to check.");
        process::exit(0);
    }

    // ── Scan source ──────────────────────────────────────────────────────────
    let patterns = Patterns::new();
    let src_path = PathBuf::from(&args.src);
    let scan_links = match scan_dir(&src_path, &patterns) {
        Ok(l) => l,
        Err(e) => {
            tracing::error!("trace-gate: scan error: {e}");
            tracing::warn!(
                "hint: check that the source directory '{}' exists and is readable",
                args.src
            );
            process::exit(2);
        }
    };

    // ── Build coverage summary ───────────────────────────────────────────────
    let summary = CoverageSummary::build(&manifest.requirement, &scan_links);

    // ── Human-readable report ────────────────────────────────────────────────
    let pass_sym = pass_fail_symbol(true);
    let fail_sym = pass_fail_symbol(false);

    println!(
        "\ntrace-gate: {} FR(s) checked — {} covered, {} missing\n",
        manifest.requirement.len(),
        summary.covered_count,
        summary.missing_count,
    );

    for req in &summary.requirements {
        match req.state {
            CoverageState::Covered => {
                println!(
                    "  {pass_sym} {} — covered at {} location(s)",
                    req.fr_id,
                    req.found_at.len()
                );
                for loc in &req.found_at {
                    let sym = if loc.symbol.is_empty() {
                        String::new()
                    } else {
                        format!(" ({})", loc.symbol)
                    };
                    println!("       {}:{}{}", loc.file, loc.line, sym);
                }
            }
            _ => {
                println!("  {fail_sym} {} — MISSING ({})", req.fr_id, req.description);
            }
        }
    }
    println!();

    // ── Optional JSON output ─────────────────────────────────────────────────
    if args.json {
        println!(
            "{}",
            serde_json::to_string_pretty(&summary).unwrap_or_default()
        );
    }

    // ── Optional push ────────────────────────────────────────────────────────
    // Support both --push <URL> and TRACE_GATE_PUSH_URL env var.
    // The env var path avoids leaking tokens in `ps` argv.
    let push_url = args
        .push
        .or_else(|| std::env::var("TRACE_GATE_PUSH_URL").ok());
    if let Some(url) = &push_url {
        push::push_to_tracera(url, &summary);
    }

    // ── Exit code ────────────────────────────────────────────────────────────
    if summary.all_covered {
        process::exit(0);
    } else {
        tracing::error!(
            "trace-gate: FAIL — {} FR(s) not covered in source",
            summary.missing_count
        );
        process::exit(1);
    }
}
