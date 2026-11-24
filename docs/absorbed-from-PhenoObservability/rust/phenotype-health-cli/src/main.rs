//! Phenotype Health CLI
//!
//! Command-line tool for unified project health scanning

use clap::{Parser, Subcommand, ValueEnum};
use clap_ext::prelude::*;
use phenotype_health_cli::{generate_json_report, generate_table_report, UnifiedHealthScanner};
use std::path::PathBuf;
use tracing::info;

#[derive(Parser)]
#[command(name = "phenotype-health")]
#[command(about = "Unified project health scanner for the Phenotype monorepo")]
#[command(version)]
struct Cli {
    /// Shared `-v/-q` verbosity flags (clap-ext `Verbosity`)
    #[command(flatten)]
    verbosity: Verbosity,

    /// Path to scan (defaults to current directory)
    #[arg(short, long, value_name = "PATH")]
    path: Option<PathBuf>,

    /// Output format
    #[arg(short, long, value_enum, default_value = "table")]
    format: OutputFormat,

    /// Subcommand to run
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    /// Scan entire workspace
    Scan {
        /// Specific project to check
        #[arg(short, long)]
        project: Option<String>,
    },
    /// Quick health check on a single project
    Check {
        /// Project path to check
        #[arg(value_name = "PATH")]
        path: PathBuf,
    },
    /// Generate health report
    Report {
        /// Output file path
        #[arg(short, long, value_name = "FILE")]
        output: Option<PathBuf>,
    },
    /// Start HTTP server for health dashboard
    Serve {
        /// Address to bind to
        #[arg(short, long, default_value = "127.0.0.1:8080")]
        addr: String,
        /// Enable file watching for auto-reload
        #[arg(short, long)]
        watch: bool,
    },
    /// Watch for changes and auto-reload
    Watch {
        /// Command to run on change
        #[arg(short, long, default_value = "scan")]
        command: String,
    },
    /// Initialize a new configuration file
    Init {
        /// Path to create config file
        #[arg(short, long, default_value = ".phenotype-health.toml")]
        config: PathBuf,
    },
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
enum OutputFormat {
    /// Human-readable table format
    Table,
    /// JSON format
    Json,
    /// Minimal output (just status)
    Minimal,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    // Initialize tracing via clap-ext (handles RUST_LOG + -v/-q mapping).
    setup_tracing(cli.verbosity.to_filter());

    // Determine the path to scan
    let scan_path = cli.path.unwrap_or_else(|| std::env::current_dir().unwrap());

    info!("Starting health scan at: {}", scan_path.display());

    let mut scanner = UnifiedHealthScanner::new();

    match cli.command {
        Some(Commands::Scan { project }) => {
            if let Some(project_name) = project {
                // Scan specific project
                let project_path = scan_path.join(&project_name);
                info!("Scanning specific project: {}", project_name);

                let result = scanner.quick_check(&project_path).await;
                print_project_result(&result, cli.format);
            } else {
                // Full workspace scan
                let report = scanner.scan_workspace(&scan_path).await;

                match cli.format {
                    OutputFormat::Table => {
                        print!("{}", generate_table_report(&report));
                    }
                    OutputFormat::Json => {
                        println!("{}", generate_json_report(&report));
                    }
                    OutputFormat::Minimal => {
                        println!("{:?}", report.status);
                    }
                }
            }
        }
        Some(Commands::Check { path }) => {
            info!("Quick check at: {}", path.display());
            let result = scanner.quick_check(&path).await;
            print_project_result(&result, cli.format);
        }
        Some(Commands::Report { output }) => {
            let report = scanner.scan_workspace(&scan_path).await;
            let output_str = match cli.format {
                OutputFormat::Json => generate_json_report(&report),
                _ => generate_table_report(&report),
            };

            if let Some(output_path) = output {
                std::fs::write(&output_path, output_str)?;
                info!("Report written to: {}", output_path.display());
            } else {
                println!("{}", output_str);
            }
        }
        Some(Commands::Serve { addr, watch: _ }) => {
            info!("Starting health server on {}", addr);

            use phenotype_health::http::health_routes;
            use phenotype_health::HealthRegistry;
            use std::sync::Arc;

            let registry = Arc::new(HealthRegistry::new());
            let app = health_routes(registry);

            let socket_addr: std::net::SocketAddr = addr
                .parse()
                .map_err(|e| anyhow::anyhow!("Invalid address: {}", e))?;

            info!("Health server running on http://{}", socket_addr);
            info!("Health endpoint: http://{}/health", socket_addr);

            let listener = tokio::net::TcpListener::bind(socket_addr)
                .await
                .map_err(|e| anyhow::anyhow!("Failed to bind: {}", e))?;

            axum::serve(listener, app)
                .await
                .map_err(|e| anyhow::anyhow!("Server error: {}", e))?;
        }
        Some(Commands::Watch { command }) => {
            info!("Starting file watcher with command: {}", command);
            println!("👁️  Watching for changes... (Press Ctrl+C to stop)");

            // Initial run
            run_watch_command(&command, &scan_path).await?;

            // Set up real file watching with notify crate
            use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
            use std::sync::mpsc::channel;

            let (tx, rx) = channel();

            let mut watcher = RecommendedWatcher::new(
                move |res: Result<Event, notify::Error>| {
                    if let Ok(event) = res {
                        let _ = tx.send(event);
                    }
                },
                Config::default(),
            )
            .map_err(|e| anyhow::anyhow!("Failed to create watcher: {}", e))?;

            // Watch the scan path
            watcher
                .watch(&scan_path, RecursiveMode::Recursive)
                .map_err(|e| anyhow::anyhow!("Failed to watch path: {}", e))?;

            println!("✅ Watching: {}", scan_path.display());
            println!("   Triggers: Cargo.toml, package.json, go.mod, pyproject.toml changes");

            loop {
                match rx.recv() {
                    Ok(event) => {
                        // Check if the event is relevant (config files, source files)
                        let should_trigger = event.paths.iter().any(|p| {
                            let path_str = p.to_string_lossy().to_lowercase();
                            path_str.ends_with("cargo.toml")
                                || path_str.ends_with("package.json")
                                || path_str.ends_with("go.mod")
                                || path_str.ends_with("pyproject.toml")
                                || path_str.ends_with(".rs")
                                || path_str.ends_with(".go")
                                || path_str.ends_with(".ts")
                                || path_str.ends_with(".js")
                                || path_str.ends_with(".py")
                        });

                        if should_trigger {
                            println!("\n🔄 Change detected: {:?}", event.paths);
                            if let Err(e) = run_watch_command(&command, &scan_path).await {
                                eprintln!("❌ Error running command: {}", e);
                            }
                            println!("\n👁️  Watching for changes... (Press Ctrl+C to stop)");
                        }
                    }
                    Err(e) => {
                        eprintln!("❌ Watch error: {}", e);
                        break;
                    }
                }
            }
        }
        Some(Commands::Init { config }) => {
            info!("Initializing configuration at: {}", config.display());

            use phenotype_health_cli::config::generate_default_config;

            if config.exists() {
                println!("Configuration file already exists at: {}", config.display());
                println!("Use --config to specify a different path.");
            } else {
                let content = generate_default_config();
                std::fs::write(&config, content)?;
                println!("Created configuration file: {}", config.display());
                println!("Edit this file to customize your health scanning preferences.");
            }
        }
        None => {
            let report = scanner.scan_workspace(&scan_path).await;

            match cli.format {
                OutputFormat::Table => {
                    print!("{}", generate_table_report(&report));
                }
                OutputFormat::Json => {
                    println!("{}", generate_json_report(&report));
                }
                OutputFormat::Minimal => {
                    println!("{:?}", report.status);
                }
            }
        }
    }

    Ok(())
}

fn print_project_result(result: &phenotype_health_cli::ProjectHealthResult, format: OutputFormat) {
    match format {
        OutputFormat::Table => {
            println!("\n{:=^50}", " PROJECT HEALTH ");
            println!("Path: {}", result.path);
            println!("Type: {:?}", result.project_type);
            println!("Status: {:?}", result.status);
            println!("Compliance Score: {:.1}%", result.compliance_score);
            println!("Findings: {}", result.findings_count);
            println!(
                "Health Config: {}",
                if result.has_health_config {
                    "Yes"
                } else {
                    "No"
                }
            );
            println!("{:=^50}\n", "");
        }
        OutputFormat::Json => {
            let json = serde_json::json!({
                "path": result.path,
                "type": format!("{:?}", result.project_type),
                "status": format!("{:?}", result.status),
                "compliance_score": result.compliance_score,
                "findings_count": result.findings_count,
                "has_health_config": result.has_health_config,
            });
            println!("{}", serde_json::to_string_pretty(&json).unwrap());
        }
        OutputFormat::Minimal => {
            println!("{:?}", result.status);
        }
    }
}

async fn run_watch_command(command: &str, scan_path: &std::path::Path) -> anyhow::Result<()> {
    use phenotype_health_cli::{generate_table_report, UnifiedHealthScanner};

    let mut scanner = UnifiedHealthScanner::new();

    match command {
        "scan" => {
            let report = scanner.scan_workspace(scan_path).await;
            println!("{}", generate_table_report(&report));
        }
        "check" => {
            // Quick check on each project
            // This would need project discovery first
            println!("Quick check mode not implemented yet");
        }
        _ => {
            println!("Unknown command: {}", command);
        }
    }

    Ok(())
}
