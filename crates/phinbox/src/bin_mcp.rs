//! `phinbox-mcp` — MCP server entry point.
//!
//! Exposes a single tool, `phinbox_mcp`, over stdio JSON-RPC. Connects
//! to Forge, Codex, Cursor, Claude Code, or any MCP-compatible host.

use std::process::ExitCode;
use std::sync::Arc;
use std::time::Duration;

use clap::Parser;
use phinbox::mcp::shutdown::ShutdownCoordinator;
use phinbox::mcp::PhinboxMcp;
use rmcp::ServiceExt;

#[derive(Parser)]
#[command(name = "phinbox-mcp", version)]
struct Args {
    /// Timeout in seconds for draining in-flight requests on shutdown.
    #[arg(long, default_value = "5")]
    shutdown_timeout_secs: u64,
}

#[tokio::main]
async fn main() -> ExitCode {
    init_tracing();
    let args = Args::parse();

    let server = PhinboxMcp::new();
    let transport = rmcp::transport::io::stdio();

    let result: Result<(), Box<dyn std::error::Error>> = async {
        let coord = Arc::new(ShutdownCoordinator::new(Duration::from_secs(args.shutdown_timeout_secs)));
        let mut shutdown_rx = ShutdownCoordinator::install(Arc::clone(&coord));

        let server = server.serve(transport).await?;

        tokio::select! {
            r = server.waiting() => { r?; }
            _ = &mut shutdown_rx => {
                tracing::info!("shutdown signal received, draining in-flight requests");
                coord.cancel_all().await;
            }
        }

        Ok(())
    }
    .await;

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn init_tracing() {
    use tracing_subscriber::EnvFilter;
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));
    let _ = tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .with_writer(std::io::stderr) // never write to stdout — that's the JSON-RPC pipe
        .try_init();
}