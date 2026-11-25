// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Checkpoint storage

use crate::checkpoint::Checkpoint;
use crate::error::{CheckpointError, Result};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, instrument};

/// In-memory checkpoint store
pub struct CheckpointStore {
    checkpoints: RwLock<HashMap<String, Checkpoint>>,
    by_spec: RwLock<HashMap<String, Vec<String>>>,
}

impl Default for CheckpointStore {
    fn default() -> Self {
        Self::new()
    }
}

impl CheckpointStore {
    /// Create new store
    pub fn new() -> Self {
        Self { checkpoints: RwLock::new(HashMap::new()), by_spec: RwLock::new(HashMap::new()) }
    }

    /// Create new store with Arc for sharing
    pub fn new_arc() -> Arc<Self> {
        Arc::new(Self::new())
    }

    /// Save checkpoint
    #[instrument(skip(self, checkpoint), fields(checkpoint_id = %checkpoint.id, spec_id = %checkpoint.spec_id))]
    pub async fn save(&self, checkpoint: Checkpoint) -> Result<()> {
        let id = checkpoint.id.to_string();
        let spec_id = checkpoint.spec_id.clone();

        self.checkpoints.write().await.insert(id.clone(), checkpoint);

        // Update index
        let mut by_spec = self.by_spec.write().await;
        by_spec.entry(spec_id.clone()).or_insert_with(Vec::new).push(id);

        debug!("saved checkpoint");
        Ok(())
    }

    /// Looks up a checkpoint by ID (error if not found).
    #[instrument(skip(self, id))]
    pub async fn get(&self, id: &str) -> Result<Checkpoint> {
        self.checkpoints
            .read()
            .await
            .get(id)
            .cloned()
            .ok_or_else(|| CheckpointError::CheckpointNotFound(id.to_string()))
    }

    /// Looks up a checkpoint by ID in the store (async).  Returns Ok(None) if not found.
    pub async fn try_get(&self, id: &str) -> Result<Option<Checkpoint>> {
        Ok(self.checkpoints.read().await.get(id).cloned())
    }

    /// Looks up a checkpoint by ID (blocking).  Returns Ok(None) if not found.
    /// Panics if no Tokio runtime is active.
    pub fn get_blocking(&self, id: &str) -> Result<Option<Checkpoint>> {
        tokio::runtime::Handle::current().block_on(self.try_get(id))
    }

    /// Get latest checkpoint for spec
    #[instrument(skip(self, spec_id))]
    pub async fn get_latest(&self, spec_id: &str) -> Result<Checkpoint> {
        let checkpoints = self.get_by_spec(spec_id).await?;

        checkpoints.into_iter().max_by_key(|c| c.created_at).ok_or_else(|| {
            CheckpointError::CheckpointNotFound(format!("No checkpoints for spec: {}", spec_id))
        })
    }

    /// Delete checkpoint
    #[instrument(skip(self, id))]
    pub async fn delete(&self, id: &str) -> Result<()> {
        if self.checkpoints.write().await.remove(id).is_none() {
            return Err(CheckpointError::CheckpointNotFound(id.to_string()));
        }
        Ok(())
    }

    /// Get checkpoints by spec ID
    #[instrument(skip(self, spec_id))]
    pub async fn get_by_spec(&self, spec_id: &str) -> Result<Vec<Checkpoint>> {
        let ids = self.by_spec.read().await.get(spec_id).cloned().unwrap_or_default();
        let checkpoints = self.checkpoints.read().await;
        Ok(ids.iter().filter_map(|id| checkpoints.get(id).cloned()).collect())
    }

    /// List all checkpoints.
    pub async fn list(&self) -> Vec<Checkpoint> {
        self.checkpoints.read().await.values().cloned().collect()
    }

    /// List all checkpoints (blocking).
    pub fn list_blocking(&self) -> Vec<Checkpoint> {
        tokio::runtime::Handle::current().block_on(self.list())
    }

    /// Get count
    #[instrument(skip(self))]
    pub async fn count(&self) -> usize {
        self.checkpoints.read().await.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_store() {
        let store = CheckpointStore::new();

        let checkpoint = Checkpoint {
            id: uuid::Uuid::new_v4(),
            spec_id: "test-spec".to_string(),
            git_sha: Some("abc123".to_string()),
            git_message: None,
            config_snapshot: None,
            db_snapshot_id: None,
            metrics_baseline: None,
            created_at: chrono::Utc::now(),
            status: crate::checkpoint::CheckpointStatus::Complete,
            metadata: std::collections::HashMap::new(),
        };

        store.save(checkpoint.clone()).await.expect("save checkpoint should succeed");

        let retrieved =
            store.get(&checkpoint.id.to_string()).await.expect("get checkpoint returned none");
        assert_eq!(retrieved.spec_id, "test-spec");

        let by_spec = store.get_by_spec("test-spec").await.expect("get_by_spec failed");
        assert_eq!(by_spec.len(), 1);

        let latest = store.get_latest("test-spec").await.expect("latest");
        assert_eq!(latest.id, checkpoint.id);

        assert_eq!(store.count().await, 1);
        assert_eq!(store.list().await.len(), 1);

        store.delete(&checkpoint.id.to_string()).await.expect("delete");
        assert_eq!(store.count().await, 0);
        assert!(store.get(&checkpoint.id.to_string()).await.is_err());
    }
}
