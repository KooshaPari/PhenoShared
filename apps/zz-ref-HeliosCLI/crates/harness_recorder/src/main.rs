// Forward-declared public API surface (L5-200 integration pending).
#![allow(dead_code)]
#![allow(unused_imports)]

use clap::Parser;

// Import from the library crate to avoid duplicating module declarations.
use kla::cli::{self, Commands};

#[derive(Parser)]
#[command(name = "kla")]
#[command(about = "KLA - Kommand Line Automation")]
#[command(version = "0.1.0")]
#[command(author = "KLA Team")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Bootstrap structured tracing (RUST_LOG controls level; defaults to "warn").
    // tracing-subscriber installs the global logger bridge for log:: macros too.
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("warn")),
        )
        .init();

    let cli = Cli::parse();

    match cli::execute_command(cli.command).await {
        Ok(_) => Ok(()),
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
