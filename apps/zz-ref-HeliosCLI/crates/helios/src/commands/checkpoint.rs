// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `checkpoint` subcommand handler.

use anyhow::{Context, Result};
use std::path::PathBuf;

/// Create a git checkpoint
pub fn cmd_checkpoint(spec: String, message: Option<String>, repo: Option<PathBuf>) -> Result<()> {
    use harness_checkpoint::checkpoint::CheckpointOptions;
    use harness_checkpoint::git::create_git_checkpoint;

    let repo_path = repo.unwrap_or_else(|| std::env::current_dir().expect("failed to get cwd"));

    println!("[helios] Creating checkpoint for spec '{}' in {}", spec, repo_path.display());

    let options = CheckpointOptions {
        include_uncommitted: true,
        message: message.or_else(|| Some(format!("helios checkpoint for {}", spec))),
        ..Default::default()
    };

    let checkpoint = create_git_checkpoint(&repo_path, &spec, &options)
        .context("Failed to create checkpoint")?;

    println!("[helios] Checkpoint created:");
    println!("  ID:   {}", checkpoint.id);
    println!("  SHA:  {}", checkpoint.git_sha.as_deref().unwrap_or("none"));
    println!("  Msg:  {}", checkpoint.git_message.as_deref().unwrap_or("none"));
    println!("  Spec: {}", checkpoint.spec_id);

    Ok(())
}
