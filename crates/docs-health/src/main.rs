//! docs-health: Markdown compliance + broken link scanner.
//!
//! Replaces:
//! - repos/phenodocs/.airlock/lint.sh
//! - repos/phenodocs/scripts/check_docs_links.py

use anyhow::Result;
use clap::Parser;
use serde::Serialize;
use std::path::PathBuf;
use walkdir::WalkDir;

/// Scan markdown files for vale/markdownlint compliance and broken links.
#[derive(Parser, Debug)]
#[command(version, about)]
struct Cli {
    /// Root directory to scan.
    #[arg(short, long, default_value = ".")]
    path: PathBuf,

    /// Emit JSON report to stdout.
    #[arg(long, default_value_t = true)]
    json: bool,
}

#[derive(Serialize)]
struct Report {
    root: PathBuf,
    markdown_files: usize,
    vale_findings: Vec<String>,
    markdownlint_findings: Vec<String>,
    broken_links: Vec<String>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let mut md_files = 0usize;
    for entry in WalkDir::new(&cli.path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
    {
        if entry.path().extension().and_then(|s| s.to_str()) == Some("md") {
            md_files += 1;
        }
    }

    // TODO: implement vale subprocess wrapper (see phenodocs/.airlock/lint.sh).
    // TODO: implement markdownlint-cli2 subprocess wrapper.
    // TODO: implement broken-link detection (port check_docs_links.py).
    let report = Report {
        root: cli.path.clone(),
        markdown_files: md_files,
        vale_findings: vec![],
        markdownlint_findings: vec![],
        broken_links: vec![],
    };

    if cli.json {
        println!("{}", serde_json::to_string_pretty(&report)?);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn smoke() {
        // Scaffolding smoke test; real assertions arrive with implementation.
    }
}
