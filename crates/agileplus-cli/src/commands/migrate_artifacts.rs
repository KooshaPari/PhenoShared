//! `agileplus migrate-artifacts` command implementation.
//!
//! Normalizes brownfield AgilePlus artifacts into docs-native locations.
//! Traceability: AGP-REQ(FR-MIGRATE-ARTIFACTS)

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

#[derive(Debug, clap::Args)]
pub struct MigrateArtifactsArgs {
    /// Write the migration report to this path.
    #[arg(long, default_value = "docs/reports/artifact-migration-report.md")]
    pub report: PathBuf,
}

#[derive(Debug, Default)]
struct MigrationReport {
    copied: usize,
    skipped: usize,
    sources: Vec<String>,
    outputs: Vec<String>,
}

const MIGRATION_EXPORT_BASENAMES: &[&str] =
    &["events.json", "events.jsonl", "evidence_ledger.jsonl"];

pub async fn run_migrate_artifacts(args: MigrateArtifactsArgs) -> Result<()> {
    let mut report = MigrationReport::default();
    migrate_spec_roots(&mut report)?;
    migrate_root_exports(&mut report)?;
    write_report(&args.report, &report)?;

    println!("Artifact migration completed.");
    println!("  Copied:  {}", report.copied);
    println!("  Skipped: {}", report.skipped);
    println!("  Report:  {}", args.report.display());
    Ok(())
}

fn migrate_spec_roots(report: &mut MigrationReport) -> Result<()> {
    for source_root in ["specs", "plans"] {
        let root = Path::new(source_root);
        if !root.exists() {
            continue;
        }
        report.sources.push(source_root.to_string());
        copy_tree(root, Path::new("docs").join(source_root), report)?;
    }
    Ok(())
}

fn migrate_root_exports(report: &mut MigrationReport) -> Result<()> {
    let export_dir = Path::new(".agileplus").join("exports");
    for entry in std::fs::read_dir(".").context("reading repository root for export artifacts")? {
        let entry = entry?;
        let path = entry.path();
        if !path.is_file() {
            continue;
        }
        let Some(file_name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        if !is_root_export_candidate(file_name) {
            continue;
        }
        let Some(file_name) = path.file_name() else {
            continue;
        };
        report.sources.push(path.to_string_lossy().to_string());
        copy_file(&path, &export_dir.join(file_name), report)?;
    }
    Ok(())
}

fn is_root_export_candidate(file_name: &str) -> bool {
    let Some(ext) = file_name.rsplit('.').next() else {
        return false;
    };
    if !matches!(ext, "json" | "jsonl") {
        return false;
    }
    MIGRATION_EXPORT_BASENAMES.contains(&file_name)
}

fn copy_tree(source: &Path, target: PathBuf, report: &mut MigrationReport) -> Result<()> {
    for entry in std::fs::read_dir(source)
        .with_context(|| format!("reading artifact source {}", source.display()))?
    {
        let entry = entry?;
        let source_path = entry.path();
        let target_path = target.join(entry.file_name());
        if source_path.is_dir() {
            copy_tree(&source_path, target_path, report)?;
        } else if source_path.is_file() {
            copy_file(&source_path, &target_path, report)?;
        }
    }
    Ok(())
}

fn copy_file(source: &Path, target: &Path, report: &mut MigrationReport) -> Result<()> {
    let source_content =
        std::fs::read(source).with_context(|| format!("reading {}", source.display()))?;
    if target.exists() {
        let target_content =
            std::fs::read(target).with_context(|| format!("reading {}", target.display()))?;
        if target_content == source_content {
            report.skipped += 1;
            return Ok(());
        }
    }
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating artifact directory {}", parent.display()))?;
    }
    std::fs::write(target, source_content)
        .with_context(|| format!("writing {}", target.display()))?;
    report.copied += 1;
    report.outputs.push(target.to_string_lossy().to_string());
    Ok(())
}

fn write_report(path: &Path, report: &MigrationReport) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating report directory {}", parent.display()))?;
    }
    std::fs::write(path, render_report(report))
        .with_context(|| format!("writing migration report {}", path.display()))?;
    Ok(())
}

fn render_report(report: &MigrationReport) -> String {
    let mut lines = vec![
        "# Artifact Migration Report".to_string(),
        String::new(),
        format!("- Copied: {}", report.copied),
        format!("- Skipped unchanged: {}", report.skipped),
        String::new(),
        "## Sources".to_string(),
    ];
    if report.sources.is_empty() {
        lines.push("- none".to_string());
    } else {
        lines.extend(report.sources.iter().map(|source| format!("- `{source}`")));
    }
    lines.push(String::new());
    lines.push("## Outputs".to_string());
    if report.outputs.is_empty() {
        lines.push("- none".to_string());
    } else {
        lines.extend(report.outputs.iter().map(|output| format!("- `{output}`")));
    }
    lines.push(String::new());
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_report_includes_counts_sources_and_outputs() {
        let report = MigrationReport {
            copied: 1,
            skipped: 2,
            sources: vec!["specs".to_string()],
            outputs: vec!["docs/specs/demo/spec.md".to_string()],
        };
        let content = render_report(&report);

        assert!(content.contains("Copied: 1"));
        assert!(content.contains("Skipped unchanged: 2"));
        assert!(content.contains("`specs`"));
        assert!(content.contains("`docs/specs/demo/spec.md`"));
    }
}
