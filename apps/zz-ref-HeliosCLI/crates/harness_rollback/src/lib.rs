// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Rollback Engine - Integrated with harness_checkpoint
//!
//! When a `repo_path` is provided, `rollback()` performs real git restoration
//! via `harness_checkpoint::git::restore_git_checkpoint`. Without a repo path,
//! it records the intended action (useful for testing or non-git scenarios).

use chrono::{DateTime, Utc};
use harness_checkpoint::git::restore_git_checkpoint;
use harness_checkpoint::store::CheckpointStore;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tracing::{info, warn};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RollbackStatus {
    Pending,
    Started,
    Completed,
    Failed,
    Partial,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackRecord {
    pub id: Uuid,
    pub checkpoint_id: String,
    pub spec_id: String,
    pub status: RollbackStatus,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub restored_items: Vec<String>,
    pub failed_items: Vec<String>,
    pub error: Option<String>,
}

impl RollbackRecord {
    pub fn new(checkpoint_id: &str, spec_id: &str) -> Self {
        Self {
            id: Uuid::new_v4(),
            checkpoint_id: checkpoint_id.to_string(),
            spec_id: spec_id.to_string(),
            status: RollbackStatus::Pending,
            started_at: Utc::now(),
            completed_at: None,
            restored_items: vec![],
            failed_items: vec![],
            error: None,
        }
    }

    pub fn start(&mut self) {
        self.status = RollbackStatus::Started;
    }
    pub fn add_restored(&mut self, item: &str) {
        self.restored_items.push(item.to_string());
    }
    pub fn add_failed(&mut self, item: &str) {
        self.failed_items.push(item.to_string());
    }
    pub fn complete(&mut self) {
        self.status = if self.failed_items.is_empty() {
            RollbackStatus::Completed
        } else {
            RollbackStatus::Partial
        };
        self.completed_at = Some(Utc::now());
    }
    pub fn fail(&mut self, err: &str) {
        self.status = RollbackStatus::Failed;
        self.completed_at = Some(Utc::now());
        self.error = Some(err.to_string());
    }
}

pub struct RollbackEngine {
    records: Vec<RollbackRecord>,
    checkpoints: Vec<(String, String, String)>, // (checkpoint_id, git_sha, spec_id)
    repo_path: Option<PathBuf>,
    #[allow(dead_code)]
    store: Option<std::sync::Arc<CheckpointStore>>, // populated by callers via with_store()
}

impl Default for RollbackEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl RollbackEngine {
    pub fn new() -> Self {
        Self { records: vec![], checkpoints: vec![], repo_path: None, store: None }
    }

    /// Create engine with a git repo path for real restoration
    pub fn with_repo(repo_path: PathBuf) -> Self {
        Self { records: vec![], checkpoints: vec![], repo_path: Some(repo_path), store: None }
    }

    /// Create engine with a checkpoint store for lookup
    pub fn with_store(store: std::sync::Arc<CheckpointStore>) -> Self {
        Self { records: vec![], checkpoints: vec![], repo_path: None, store: Some(store) }
    }

    /// Create engine with both repo path and checkpoint store
    pub fn with_repo_and_store(repo_path: PathBuf, store: std::sync::Arc<CheckpointStore>) -> Self {
        Self {
            records: vec![],
            checkpoints: vec![],
            repo_path: Some(repo_path),
            store: Some(store),
        }
    }

    pub fn register(&mut self, checkpoint_id: &str, git_sha: &str, spec_id: &str) -> Uuid {
        let id = Uuid::new_v4();
        self.checkpoints.push((
            checkpoint_id.to_string(),
            git_sha.to_string(),
            spec_id.to_string(),
        ));
        id
    }

    /// Rollback to a checkpoint. When repo_path is set, performs real git restoration.
    pub fn rollback(&mut self, checkpoint_id: &str) -> Option<RollbackRecord> {
        let spec_id = self
            .checkpoints
            .iter()
            .find(|(id, _, _)| id == checkpoint_id)
            .map(|(_, _, sid)| sid.as_str())
            .unwrap_or("unknown");

        let mut record = RollbackRecord::new(checkpoint_id, spec_id);
        record.start();

        // Find the git SHA for this checkpoint
        let git_sha = self
            .checkpoints
            .iter()
            .find(|(id, _, _)| id == checkpoint_id)
            .map(|(_, sha, _)| sha.clone());

        if let Some(ref repo_path) = self.repo_path {
            if let Some(ref sha) = git_sha {
                match restore_git_checkpoint(repo_path, sha) {
                    Ok(()) => {
                        info!(checkpoint_id, sha = %sha, "git checkpoint restored");
                        record.add_restored(&format!("git:{}:restored", sha));
                    }
                    Err(e) => {
                        warn!(checkpoint_id, sha = %sha, error = %e, "git restore failed");
                        record.add_restored(&format!("git:{}:attempted", sha));
                        record.add_failed(&format!("git:{}:{}", sha, e));
                    }
                }
            } else {
                // git_sha not in local vec — try the store if one is configured
                let store_sha = self.store.as_ref().and_then(|store| {
                    store
                        .get_blocking(checkpoint_id)
                        .ok()
                        .flatten()
                        .and_then(|cp| cp.git_sha.clone())
                });
                if let Some(ref sha) = store_sha {
                    match restore_git_checkpoint(repo_path, sha) {
                        Ok(()) => {
                            info!(checkpoint_id, sha = %sha, source = "store", "git checkpoint restored from store");
                            record.add_restored(&format!("git:{}:restored:store", sha));
                        }
                        Err(e) => {
                            warn!(checkpoint_id, sha = %sha, error = %e, "git restore from store failed");
                            record.add_restored(&format!("git:{}:attempted:store", sha));
                            record.add_failed(&format!("git:{}:{}:store", sha, e));
                        }
                    }
                } else {
                    record.add_failed("no git SHA found for checkpoint");
                }
            }
        } else {
            // No repo path — record intended action
            record.add_restored(&format!("git:{}:recorded", checkpoint_id));
        }

        record.complete();
        self.records.push(record.clone());
        Some(record)
    }

    pub fn verify(&self, record: &RollbackRecord) -> bool {
        matches!(record.status, RollbackStatus::Completed)
    }

    pub fn history(&self) -> &[RollbackRecord] {
        &self.records
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rollback() {
        let mut engine = RollbackEngine::new();
        engine.register("chk-001", "abc123sha", "test-spec");
        let result = engine.rollback("chk-001");
        assert!(result.is_some());
        let result = engine.rollback("chk-001");
        assert!(result.is_some());
        let record = result.expect("rollback returned a record");
        assert!(engine.verify(&record));
    }

    #[test]
    fn rollback_record_partial_when_failures_present() {
        let mut record = RollbackRecord::new("chk-002", "spec");
        record.start();
        record.add_restored("file-a");
        record.add_failed("file-b");
        record.complete();
        assert_eq!(record.status, RollbackStatus::Partial);
    }

    // ------------------------------------------------------------------
    // Additional tests
    // ------------------------------------------------------------------

    /// RollbackRecord::new initializes with correct default state.
    #[test]
    fn rollback_record_new_defaults() {
        let record = RollbackRecord::new("cp-100", "my-spec");
        assert_eq!(record.checkpoint_id, "cp-100");
        assert_eq!(record.spec_id, "my-spec");
        assert_eq!(record.status, RollbackStatus::Pending);
        assert!(record.completed_at.is_none());
        assert!(record.restored_items.is_empty());
        assert!(record.failed_items.is_empty());
        assert!(record.error.is_none());
    }

    /// RollbackRecord::start transitions status to Started.
    #[test]
    fn rollback_record_start_transition() {
        let mut record = RollbackRecord::new("cp", "sp");
        assert_eq!(record.status, RollbackStatus::Pending);
        record.start();
        assert_eq!(record.status, RollbackStatus::Started);
    }

    /// RollbackRecord::fail records error and sets Failed status.
    #[test]
    fn rollback_record_fail_records_error() {
        let mut record = RollbackRecord::new("cp", "sp");
        record.start();
        record.fail("something went wrong");
        assert_eq!(record.status, RollbackStatus::Failed);
        assert_eq!(record.error.as_deref(), Some("something went wrong"));
        assert!(record.completed_at.is_some());
    }

    /// RollbackRecord: complete with no failures yields Completed.
    #[test]
    fn rollback_record_complete_no_failures() {
        let mut record = RollbackRecord::new("cp", "sp");
        record.start();
        record.add_restored("item-a");
        record.complete();
        assert_eq!(record.status, RollbackStatus::Completed);
        assert!(record.completed_at.is_some());
    }

    /// RollbackEngine: default creates empty engine.
    #[test]
    fn rollback_engine_default_empty() {
        let engine = RollbackEngine::default();
        assert!(engine.history().is_empty());
    }

    /// RollbackEngine: register stores checkpoint mapping.
    #[test]
    fn rollback_engine_register_checkpoint() {
        let mut engine = RollbackEngine::new();
        let id = engine.register("cp-a", "sha-abc123", "spec-a");
        // Register returns a valid UUID.
        assert!(!id.is_nil());
    }

    /// RollbackEngine: history tracks all rollback records.
    #[test]
    fn rollback_engine_history_tracking() {
        let mut engine = RollbackEngine::new();
        engine.rollback("cp-1");
        engine.rollback("cp-2");
        let history = engine.history();
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].checkpoint_id, "cp-1");
        assert_eq!(history[1].checkpoint_id, "cp-2");
    }

    /// RollbackEngine: verify fails on partial records.
    #[test]
    fn rollback_engine_verify_partial() {
        let engine = RollbackEngine::new();
        let mut record = RollbackRecord::new("cp", "spec");
        record.start();
        record.add_restored("ok-item");
        record.add_failed("bad-item");
        record.complete();
        assert!(!engine.verify(&record));
    }

    /// RollbackEngine: verify passes on completed records.
    #[test]
    fn rollback_engine_verify_completed() {
        let mut engine = RollbackEngine::new();
        let record = engine.rollback("cp-ok").unwrap();
        assert!(engine.verify(&record));
    }

    /// RollbackStatus: serialization round-trip.
    #[test]
    fn rollback_status_serialization_roundtrip() {
        let statuses = [
            RollbackStatus::Pending,
            RollbackStatus::Started,
            RollbackStatus::Completed,
            RollbackStatus::Failed,
            RollbackStatus::Partial,
        ];
        for s in &statuses {
            let json = serde_json::to_string(s).expect("serialize");
            let back: RollbackStatus = serde_json::from_str(&json).expect("deserialize");
            assert_eq!(&back, s);
        }
    }
}
