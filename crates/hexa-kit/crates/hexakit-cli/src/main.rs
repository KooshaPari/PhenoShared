//! HexaKit CLI — fleet repo bootstrap.

mod boundary;
mod gateway;
mod init;
mod lang;
mod lint;
mod manifest;
mod registry;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "hexakit",
    version,
    about = "HexaKit — Phenotype fleet scaffolding"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Bootstrap a new fleet repository (boundary, hooks, CI docs).
    Init(init::InitArgs),
    /// Validate BOUNDARY.md structure for a fleet repo.
    Boundary {
        #[command(subcommand)]
        command: BoundaryCommands,
    },
    /// Manage the phenotype-router HTTP delegate (replaces H10 gateway surface).
    Gateway(gateway::GatewayArgs),
}

#[derive(Subcommand)]
enum BoundaryCommands {
    Lint(lint::LintArgs),
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Init(args) => init::run(args),
        Commands::Boundary { command } => match command {
            BoundaryCommands::Lint(args) => lint::run(args),
        },
        Commands::Gateway(args) => gateway::run(args),
    }
}
