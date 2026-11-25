// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `status` subcommand handler.

use anyhow::Result;

/// Show system status
pub fn cmd_status() -> Result<()> {
    println!("=== HeliosCLI Status ===");
    println!();
    println!("Crates:");
    println!("  helios_config:      {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_queue:      {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_runner:     {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_rollback:   {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_checkpoint: {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_spec:       {}", env!("CARGO_PKG_VERSION"));
    println!("  harness_verify:     {}", env!("CARGO_PKG_VERSION"));
    println!();

    let config_path =
        std::env::current_dir().ok().map(|d| d.join("helios.toml")).filter(|p| p.exists());

    match config_path {
        Some(path) => println!("Config: {}", path.display()),
        None => println!("Config: not found (using defaults)"),
    }

    println!();
    println!("Usage:");
    println!("  helios run <command>          Run a command through the harness");
    println!("  helios checkpoint --spec <s>  Create a git checkpoint");
    println!("  helios rollback <id>          Rollback to a checkpoint");
    println!("  helios status                 Show this status");
    println!("  helios enqueue <payload>      Enqueue a background task");
    println!("  helios record <script>        Record a terminal session (KLA)");
    println!("  helios exec <prompt>          Execute an agent task via AI");
    println!("  helios resume --last           Resume the most recent session");

    Ok(())
}
