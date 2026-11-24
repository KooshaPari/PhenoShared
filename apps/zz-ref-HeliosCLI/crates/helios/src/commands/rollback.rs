// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `rollback` subcommand handler.

use anyhow::Result;
use std::path::PathBuf;

/// Rollback to a checkpoint
pub fn cmd_rollback(checkpoint_id: String, repo: Option<PathBuf>) -> Result<()> {
    use harness_rollback::RollbackEngine;

    let repo_path = repo.unwrap_or_else(|| std::env::current_dir().expect("failed to get cwd"));

    println!("[helios] Rolling back to checkpoint: {}", checkpoint_id);
    println!("[helios] Repository: {}", repo_path.display());

    let mut engine = RollbackEngine::with_repo(repo_path);
    engine.register(&checkpoint_id, &checkpoint_id, "cli");

    match engine.rollback(&checkpoint_id) {
        Some(record) => {
            println!("[helios] Rollback completed:");
            println!("  Status:  {:?}", record.status);
            println!("  Restored: {:?}", record.restored_items);
            if !record.failed_items.is_empty() {
                eprintln!("  Failed: {:?}", record.failed_items);
            }
            if !engine.verify(&record) {
                anyhow::bail!("Rollback verification failed (partial or failed status)");
            }
            Ok(())
        }
        None => {
            anyhow::bail!("Rollback returned no record \u{2014} checkpoint may not exist");
        }
    }
}
