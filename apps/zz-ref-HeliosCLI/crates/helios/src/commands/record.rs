// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `record` subcommand handler.

use anyhow::Result;
use std::path::PathBuf;

/// Record a terminal session using KLA
pub async fn cmd_record(script: PathBuf, output: PathBuf, format: String) -> Result<()> {
    println!("[helios] Recording session from: {}", script.display());
    println!("[helios] Output dir: {}", output.display());
    println!("[helios] Format: {}", format);

    kla::cli::commands::record_command(script, output, format).await
}
