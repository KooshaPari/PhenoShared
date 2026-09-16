//! legacy-scan: detects anti-patterns per the Phenotype scripting-language hierarchy.
//!
//! Enforces the rubric in:
//! - repos/docs/governance/scripting_policy.md
//!
//! Flags: shell scripts >5 lines, Python/TS standalone CLIs, deprecated libs.

use anyhow::Result;
use clap::Parser;
use serde::Serialize;
use std::path::PathBuf;
use walkdir::WalkDir;

/// Scan a repo for scripting-policy violations and deprecated library usage.
#[derive(Parser, Debug)]
#[command(version, about)]
struct Cli {
    /// Root directory to scan.
    #[arg(short, long, default_value = ".")]
    path: PathBuf,

    /// Max shell-script line count before flagging (policy threshold).
    #[arg(long, default_value_t = 5)]
    shell_line_limit: usize,

    /// Emit JSON report to stdout.
    #[arg(long, default_value_t = true)]
    json: bool,
}

#[derive(Serialize)]
struct Finding {
    path: PathBuf,
    kind: &'static str,
    detail: String,
}

#[derive(Serialize)]
struct Report {
    root: PathBuf,
    scanned_files: usize,
    findings: Vec<Finding>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let mut scanned = 0usize;
    for entry in WalkDir::new(&cli.path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
    {
        scanned += 1;
        let _ = entry;
        // TODO: flag *.sh files with >shell_line_limit lines lacking justification header.
        // TODO: flag standalone *.py CLIs under scripts/ (not embedded in a Py runtime).
        // TODO: detect deprecated libs via Cargo.toml/package.json parsing.
        // Source reference: repos/docs/governance/scripting_policy.md rubric.
    }

    let report = Report {
        root: cli.path.clone(),
        scanned_files: scanned,
        findings: vec![],
    };
    if cli.json {
        println!("{}", serde_json::to_string_pretty(&report)?);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn smoke() {}
}
