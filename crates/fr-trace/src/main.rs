//! fr-trace: Functional Requirement -> test traceability scanner.
//!
//! Replaces:
//! - repos/scripts/traceability-check.py
//! - repos/HexaKit/scripts/traceability-check.py
//! - repos/PhenoKits/HexaKit/scripts/traceability-check.py

use anyhow::Result;
use clap::Parser;
use serde::Serialize;
use std::path::PathBuf;

/// Scan a repo for FR-NNN references and map them to test coverage.
#[derive(Parser, Debug)]
#[command(version, about)]
struct Cli {
    /// Root directory to scan.
    #[arg(short, long, default_value = ".")]
    path: PathBuf,

    /// Path to FUNCTIONAL_REQUIREMENTS.md (defaults to <path>/FUNCTIONAL_REQUIREMENTS.md).
    #[arg(long)]
    fr_file: Option<PathBuf>,

    /// Emit JSON report to stdout.
    #[arg(long, default_value_t = true)]
    json: bool,
}

#[derive(Serialize)]
struct Report {
    root: PathBuf,
    fr_file: Option<PathBuf>,
    declared_frs: Vec<String>,
    referenced_frs: Vec<String>,
    uncovered_frs: Vec<String>,
    orphan_refs: Vec<String>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // TODO: parse FUNCTIONAL_REQUIREMENTS.md for FR-XXX-NNN identifiers.
    // TODO: walk src/ and tests/, regex-match `FR-[A-Z]+-\d+` references.
    // TODO: cross-reference declared vs referenced; emit gaps.
    // Source reference: repos/scripts/traceability-check.py.
    let report = Report {
        root: cli.path.clone(),
        fr_file: cli.fr_file.clone(),
        declared_frs: vec![],
        referenced_frs: vec![],
        uncovered_frs: vec![],
        orphan_refs: vec![],
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
