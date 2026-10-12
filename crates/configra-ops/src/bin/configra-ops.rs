//! Configra operations CLI — health probes and version introspection.

use std::process::ExitCode;

use clap::{Parser, Subcommand};
use configra_ops::{
    init_logging, liveness, readiness, HealthCheck, LoggingConfig, WorkspaceCheck, VERSION,
};

#[derive(Debug, Parser)]
#[command(name = "configra-ops", version = VERSION, about = "Configra observability + ops CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Liveness probe (process up).
    Health {
        /// Readiness mode — run dependency checks.
        #[arg(long)]
        ready: bool,
        /// Emit JSON (default when CONFIGRA_LOG_FORMAT=json).
        #[arg(long)]
        json: bool,
    },
    /// Print build / crate version.
    Version,
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let _ = init_logging(&LoggingConfig::default());

    match cli.command {
        Command::Health { ready, json } => {
            let report = if ready {
                let workspace = WorkspaceCheck;
                let checks: Vec<&dyn HealthCheck> = vec![&workspace];
                readiness(VERSION, &checks)
            } else {
                liveness(VERSION)
            };

            let emit_json = json
                || std::env::var("CONFIGRA_LOG_FORMAT")
                    .map(|v| v == "json")
                    .unwrap_or(false);
            if emit_json {
                println!("{}", report.to_json().expect("serialize health report"));
            } else if report.status == configra_ops::HealthStatus::Healthy {
                println!("ok");
            } else {
                eprintln!("unhealthy");
                for check in &report.checks {
                    if check.status != configra_ops::HealthStatus::Healthy {
                        eprintln!(
                            "  {}: {}",
                            check.name,
                            check.message.as_deref().unwrap_or("failed")
                        );
                    }
                }
            }

            ExitCode::from(report.exit_code() as u8)
        },
        Command::Version => {
            println!("configra-ops {VERSION}");
            ExitCode::SUCCESS
        },
    }
}
