//! `agileplus tracaera` command implementation.
//!
//! Exports an evidence-backed trace graph snapshot for Tracaera ingestion.
//! Traceability: AGP-REQ(FR-TRACE-EXPORT)

use std::path::PathBuf;

use agileplus_domain::ports::StoragePort;
use agileplus_events::EventStore;
use anyhow::{Context, Result};
use clap::Subcommand;

mod graph;

#[derive(Debug, clap::Args)]
pub struct TracaeraArgs {
    #[command(subcommand)]
    pub command: TracaeraCommand,
}

#[derive(Debug, Subcommand)]
pub enum TracaeraCommand {
    /// Export a feature trace graph snapshot as JSON.
    Export(TracaeraExportArgs),
}

#[derive(Debug, clap::Args)]
pub struct TracaeraExportArgs {
    /// Feature slug to export.
    #[arg(long)]
    pub feature: String,

    /// Write JSON to a file instead of stdout.
    #[arg(long)]
    pub output: Option<PathBuf>,
}

pub async fn run<S>(args: TracaeraArgs, storage: &S) -> Result<()>
where
    S: StoragePort + EventStore,
{
    match args.command {
        TracaeraCommand::Export(args) => run_export(args, storage).await,
    }
}

async fn run_export<S>(args: TracaeraExportArgs, storage: &S) -> Result<()>
where
    S: StoragePort + EventStore,
{
    let feature = storage
        .get_feature_by_slug(&args.feature)
        .await
        .context("looking up feature for Tracaera export")?
        .ok_or_else(|| anyhow::anyhow!("Feature '{}' not found", args.feature))?;
    let graph = graph::build_trace_graph(storage, feature).await?;
    let content = serde_json::to_string_pretty(&graph)?;

    if let Some(output_path) = args.output {
        if let Some(parent) = output_path.parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent)
                    .with_context(|| format!("creating directory {}", parent.display()))?;
            }
        }
        std::fs::write(&output_path, content)
            .with_context(|| format!("writing Tracaera export to {}", output_path.display()))?;
        println!("Tracaera export written to: {}", output_path.display());
    } else {
        println!("{content}");
    }

    Ok(())
}
