//! `agileplus hooks` command implementation.
//!
//! Installs and verifies lightweight local hooks that enforce traceability.
//! Traceability: AGP-REQ(FR-HOOKS-TRACE)

use std::path::PathBuf;

use agileplus_domain::ports::VcsPort;
use anyhow::{Context, Result};
use clap::Subcommand;

use crate::commands::validate::evaluate_traceability;

#[derive(Debug, clap::Args)]
pub struct HooksArgs {
    #[command(subcommand)]
    pub command: HooksCommand,
}

#[derive(Debug, Subcommand)]
pub enum HooksCommand {
    /// Install a local pre-commit hook template.
    Install(HooksInstallArgs),
    /// Verify traceability for a feature and fail on broken links.
    Verify(HooksVerifyArgs),
    /// Remove a previously installed local hook template.
    Uninstall(HooksUninstallArgs),
}

#[derive(Debug, clap::Args)]
pub struct HooksInstallArgs {
    /// Hook script path to write.
    #[arg(long, default_value = ".agileplus/hooks/pre-commit")]
    pub output: PathBuf,
}

#[derive(Debug, clap::Args)]
pub struct HooksVerifyArgs {
    /// Feature slug to verify.
    #[arg(long)]
    pub feature: String,
}

#[derive(Debug, clap::Args)]
pub struct HooksUninstallArgs {
    /// Hook script path to remove.
    #[arg(long, default_value = ".agileplus/hooks/pre-commit")]
    pub path: PathBuf,
}

pub async fn run_hooks<V>(args: HooksArgs, vcs: &V) -> Result<()>
where
    V: VcsPort,
{
    match args.command {
        HooksCommand::Install(args) => install_hook(args),
        HooksCommand::Verify(args) => verify_hook(args, vcs).await,
        HooksCommand::Uninstall(args) => uninstall_hook(args),
    }
}

fn install_hook(args: HooksInstallArgs) -> Result<()> {
    if let Some(parent) = args.output.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating hook directory {}", parent.display()))?;
        }
    }
    std::fs::write(&args.output, pre_commit_hook_template())
        .with_context(|| format!("writing hook template to {}", args.output.display()))?;
    println!(
        "AgilePlus hook template written to: {}",
        args.output.display()
    );
    println!("Set AGILEPLUS_FEATURE before running the hook, or call `agileplus hooks verify --feature <slug>` directly.");
    Ok(())
}

async fn verify_hook<V>(args: HooksVerifyArgs, vcs: &V) -> Result<()>
where
    V: VcsPort,
{
    let issues = evaluate_traceability(vcs, &args.feature).await?;
    if !issues.is_empty() {
        for issue in &issues {
            eprintln!("{} {}: {}", issue.kind, issue.id, issue.message);
        }
        anyhow::bail!(
            "Traceability verification failed for feature '{}': {} issue(s)",
            args.feature,
            issues.len()
        );
    }
    println!(
        "Traceability verification passed for feature '{}'.",
        args.feature
    );
    Ok(())
}

fn uninstall_hook(args: HooksUninstallArgs) -> Result<()> {
    if args.path.exists() {
        std::fs::remove_file(&args.path)
            .with_context(|| format!("removing hook template {}", args.path.display()))?;
        println!("AgilePlus hook removed: {}", args.path.display());
    } else {
        println!("AgilePlus hook not present: {}", args.path.display());
    }
    Ok(())
}

fn pre_commit_hook_template() -> &'static str {
    r#"#!/usr/bin/env sh
set -eu

if [ -z "${AGILEPLUS_FEATURE:-}" ]; then
  echo "AGILEPLUS_FEATURE is required for AgilePlus traceability hook" >&2
  exit 2
fi

agileplus hooks verify --feature "$AGILEPLUS_FEATURE"
"#
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pre_commit_hook_runs_traceability_verify() {
        let hook = pre_commit_hook_template();

        assert!(hook.contains("AGILEPLUS_FEATURE"));
        assert!(hook.contains("agileplus hooks verify --feature"));
    }
}
