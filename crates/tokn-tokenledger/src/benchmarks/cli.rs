//! CLI command handlers for benchmarks.

use crate::benchmarks::{artificial_analysis, openrouter, store::BenchmarkStore};
use crate::cli::BenchmarksArgs;
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

/// Main entry point for benchmarks CLI commands
pub fn run_benchmarks(args: BenchmarksArgs) -> Result<()> {
    match args.command {
        crate::cli::BenchmarksCommand::Refresh(args) => run_refresh(args),
        crate::cli::BenchmarksCommand::List(args) => run_list(args),
        crate::cli::BenchmarksCommand::Show(args) => run_show(args),
        crate::cli::BenchmarksCommand::Validate(args) => run_validate(args),
    }
}

/// Refresh benchmarks from configured sources
fn run_refresh(args: crate::cli::RefreshBenchmarksArgs) -> Result<()> {
    println!("Refreshing benchmarks...");

    let rt = tokio::runtime::Runtime::new()?;

    rt.block_on(async {
        let store = Arc::new(RwLock::new(BenchmarkStore::new(3600)));
        let mut total = 0;

        // Refresh from Artificial Analysis if API key provided
        if let Some(ref key) = args.aa_api_key {
            info!("Fetching benchmarks from Artificial Analysis...");
            match artificial_analysis::fetch_benchmarks(key).await {
                Ok(data) => {
                    for benchmark in &data {
                        store
                            .write()
                            .await
                            .merge(benchmark.model_id.clone(), benchmark.clone())
                            .await;
                    }
                    total += data.len();
                    println!("✓ Fetched {} models from Artificial Analysis", data.len());
                }
                Err(e) => {
                    println!("✗ Failed to fetch from Artificial Analysis: {}", e);
                }
            }
        }

        // Refresh from OpenRouter if API key provided
        if let Some(ref key) = args.openrouter_api_key {
            info!("Fetching benchmarks from OpenRouter...");
            match openrouter::fetch_benchmarks(key).await {
                Ok(data) => {
                    for benchmark in &data {
                        store
                            .write()
                            .await
                            .merge(benchmark.model_id.clone(), benchmark.clone())
                            .await;
                    }
                    total += data.len();
                    println!("✓ Fetched {} models from OpenRouter", data.len());
                }
                Err(e) => {
                    println!("✗ Failed to fetch from OpenRouter: {}", e);
                }
            }
        }

        // Output results
        if total > 0 {
            println!("\nTotal benchmarks: {}", total);

            if let Some(output_path) = &args.output {
                // Just print count to output file
                std::fs::write(output_path, format!("{{\"count\":{}}}", total))?;
                println!("✓ Written summary to: {}", output_path.display());
            }
        } else {
            println!("No benchmarks fetched. Provide API keys or use --no-fetch for cache.");
            println!("\nUsage:");
            println!("  tokenledger benchmarks refresh --aa-api-key YOUR_KEY");
            println!("  tokenledger benchmarks refresh --openrouter-api-key YOUR_KEY");
        }

        Ok(())
    })
}

/// List available benchmarks
fn run_list(args: crate::cli::ListBenchmarksArgs) -> Result<()> {
    println!("Listing benchmarks (limit: {})...", args.limit);
    // Placeholder - would load from store
    println!("Use 'tokenledger benchmarks refresh' first to fetch data.");
    Ok(())
}

/// Show specific model benchmark
fn run_show(args: crate::cli::ShowBenchmarkArgs) -> Result<()> {
    println!("Showing benchmark for: {}", args.model_id);
    // Placeholder - would lookup from store
    println!("Use 'tokenledger benchmarks refresh' first to fetch data.");
    Ok(())
}

/// Validate benchmark configuration
fn run_validate(args: crate::cli::ValidateBenchmarksArgs) -> Result<()> {
    println!("Validating benchmark configuration...");

    if let Some(config_path) = args.config {
        let content = std::fs::read_to_string(&config_path)?;
        let _config: serde_yaml_ng::Value = serde_yaml_ng::from_str(&content)?;
        println!("✓ Config is valid: {}", config_path.display());
    } else {
        println!("No config file provided. Checking default locations...");

        let default_paths = ["configs/benchmarks.yaml", "configs/benchmarks.example.yaml"];

        for path in default_paths {
            if std::path::Path::new(path).exists() {
                println!("✓ Found: {}", path);
            }
        }
    }

    Ok(())
}
