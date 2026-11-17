// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Git-based checkpoint implementation

use crate::checkpoint::{Checkpoint, CheckpointOptions, CheckpointStatus};
use crate::error::{CheckpointError, Result};
use chrono::Utc;
use git2::{build::CheckoutBuilder, Repository, Signature, StatusOptions};
use std::path::Path;
use tracing::{debug, instrument};
use uuid::Uuid;

/// Create a git checkpoint
#[instrument(skip(repo_path, options), fields(spec_id = %spec_id))]
pub fn create_git_checkpoint(
    repo_path: &Path,
    spec_id: &str,
    options: &CheckpointOptions,
) -> Result<Checkpoint> {
    // Open or create repository
    let repo = Repository::open(repo_path)
        .or_else(|_| Repository::init(repo_path))
        .map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let mut checkpoint = Checkpoint {
        id: Uuid::new_v4(),
        spec_id: spec_id.to_string(),
        git_sha: None,
        git_message: None,
        config_snapshot: None,
        db_snapshot_id: None,
        metrics_baseline: None,
        created_at: Utc::now(),
        status: CheckpointStatus::Creating,
        metadata: std::collections::HashMap::new(),
    };

    // Stage all changes
    let mut index = repo.index().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    if options.include_uncommitted {
        // Add all files
        index
            .add_all(["*"].iter(), git2::IndexAddOption::DEFAULT, None)
            .map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

        index.write().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;
    }

    // Create commit
    let message =
        options.message.clone().unwrap_or_else(|| format!("Checkpoint for spec: {}", spec_id));

    let signature = Signature::now("heliosHarness", "checkpoint@helios.local")
        .unwrap_or_else(|_| Signature::now("heliosHarness", "checkpoint@helios.local").unwrap());

    let oid = index.write_tree().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let tree =
        repo.find_tree(oid).map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    // Get parent commit
    let parent_commit = repo.head().ok().and_then(|h| h.peel_to_commit().ok());

    let parents: Vec<&git2::Commit> = parent_commit.iter().collect();

    let commit_oid = repo
        .commit(Some("HEAD"), &signature, &signature, &message, &tree, &parents)
        .map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let commit = repo
        .find_commit(commit_oid)
        .map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    checkpoint.git_sha = Some(commit.id().to_string());
    checkpoint.git_message = Some(message);
    checkpoint.status = CheckpointStatus::Complete;

    debug!(sha = %checkpoint.git_sha.as_deref().unwrap_or(""), "git checkpoint created");
    Ok(checkpoint)
}

/// Restore from git checkpoint
#[instrument(skip(repo_path, git_sha), fields(git_sha = %git_sha))]
pub fn restore_git_checkpoint(repo_path: &Path, git_sha: &str) -> Result<()> {
    let repo = Repository::open(repo_path)
        .map_err(|e| CheckpointError::RepositoryNotFound(e.message().to_string()))?;

    // Parse the commit SHA
    let oid = git_sha
        .parse::<git2::Oid>()
        .map_err(|e| CheckpointError::GitError(format!("Invalid SHA: {}", e)))?;

    // Checkout the commit
    let mut checkout_builder = CheckoutBuilder::new();
    checkout_builder.force().allow_conflicts(true);

    let commit =
        repo.find_commit(oid).map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let tree = commit.tree().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    repo.checkout_tree(tree.as_object(), Some(&mut checkout_builder))
        .map_err(|e| CheckpointError::RestoreFailed(e.message().to_string()))?;

    // Reset HEAD to the commit
    repo.set_head_detached(oid)
        .map_err(|e| CheckpointError::RestoreFailed(e.message().to_string()))?;

    Ok(())
}

/// Get current git status
#[instrument(skip(repo_path))]
pub fn get_git_status(repo_path: &Path) -> Result<GitStatus> {
    let repo = Repository::open(repo_path)
        .map_err(|e| CheckpointError::RepositoryNotFound(e.message().to_string()))?;

    let mut opts = StatusOptions::new();
    opts.include_untracked(true);

    let statuses = repo
        .statuses(Some(&mut opts))
        .map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let mut modified = Vec::new();
    let mut staged = Vec::new();
    let mut untracked = Vec::new();

    for entry in statuses.iter() {
        let path = entry.path().unwrap_or("").to_string();

        let status = entry.status();

        if status.is_index_new() || status.is_index_modified() {
            staged.push(path.clone());
        }
        if status.is_wt_modified() {
            modified.push(path.clone());
        }
        if status.is_wt_new() {
            untracked.push(path);
        }
    }

    let is_clean = modified.is_empty() && staged.is_empty() && untracked.is_empty();

    Ok(GitStatus { modified, staged, untracked, is_clean })
}

/// Git status
#[derive(Debug, Clone)]
pub struct GitStatus {
    pub modified: Vec<String>,
    pub staged: Vec<String>,
    pub untracked: Vec<String>,
    pub is_clean: bool,
}

/// Get current HEAD SHA
#[instrument(skip(repo_path))]
pub fn get_current_sha(repo_path: &Path) -> Result<String> {
    let repo = Repository::open(repo_path)
        .map_err(|e| CheckpointError::RepositoryNotFound(e.message().to_string()))?;

    let head = repo.head().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    let oid =
        head.peel_to_commit().map_err(|e| CheckpointError::GitError(e.message().to_string()))?;

    Ok(oid.id().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::checkpoint::{CheckpointOptions, CheckpointStatus};
    use std::fs;
    use tempfile::TempDir;

    fn init_repo_with_commit(dir: &Path) {
        let repo = Repository::init(dir).expect("init repo");
        let file_path = dir.join("README.md");
        fs::write(&file_path, "init").expect("write readme");
        let mut index = repo.index().expect("index");
        index.add_path(Path::new("README.md")).expect("add readme");
        index.write().expect("write index");
        let oid = index.write_tree().expect("write tree");
        let tree = repo.find_tree(oid).expect("find tree");
        let sig = Signature::now("test", "test@example.com").expect("signature");
        repo.commit(Some("HEAD"), &sig, &sig, "init", &tree, &[]).expect("initial commit");
    }

    #[test]
    fn create_git_checkpoint_stages_uncommitted_changes() {
        let dir = TempDir::new().expect("tempdir");
        init_repo_with_commit(dir.path());
        fs::write(dir.path().join("change.txt"), "hello").expect("write change");

        let options = CheckpointOptions {
            include_uncommitted: true,
            message: Some("test checkpoint".to_string()),
            ..Default::default()
        };
        let checkpoint =
            create_git_checkpoint(dir.path(), "spec-1", &options).expect("create checkpoint");

        assert_eq!(checkpoint.status, CheckpointStatus::Complete);
        assert!(checkpoint.git_sha.is_some());
        assert!(checkpoint.git_message.is_some());
    }

    #[test]
    fn get_git_status_reports_untracked_files() {
        let dir = TempDir::new().expect("tempdir");
        init_repo_with_commit(dir.path());
        fs::write(dir.path().join("new.txt"), "x").expect("write untracked");

        let status = get_git_status(dir.path()).expect("git status");
        assert!(!status.is_clean);
        assert!(!status.untracked.is_empty());
    }

    #[test]
    fn get_current_sha_returns_head_commit() {
        let dir = TempDir::new().expect("tempdir");
        init_repo_with_commit(dir.path());

        let sha = get_current_sha(dir.path()).expect("current sha");
        assert_eq!(sha.len(), 40);
    }

    #[test]
    fn restore_git_checkpoint_reverts_worktree() {
        let dir = TempDir::new().expect("tempdir");
        init_repo_with_commit(dir.path());
        fs::write(dir.path().join("a.txt"), "v1").expect("write v1");

        let options = CheckpointOptions { include_uncommitted: true, ..Default::default() };
        let checkpoint =
            create_git_checkpoint(dir.path(), "spec-restore", &options).expect("checkpoint");
        fs::write(dir.path().join("a.txt"), "v2").expect("write v2");

        restore_git_checkpoint(dir.path(), checkpoint.git_sha.as_ref().unwrap())
            .expect("restore checkpoint");
        let content = fs::read_to_string(dir.path().join("a.txt")).expect("read restored");
        assert_eq!(content, "v1");
    }

    #[test]
    fn restore_git_checkpoint_rejects_invalid_sha() {
        let dir = TempDir::new().expect("tempdir");
        init_repo_with_commit(dir.path());

        let err = restore_git_checkpoint(dir.path(), "not-a-sha").unwrap_err();
        assert!(matches!(err, CheckpointError::GitError(_)));
    }
}
