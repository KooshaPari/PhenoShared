// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Checkpoint models

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Checkpoint record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Checkpoint {
    /// Unique checkpoint ID
    pub id: Uuid,

    /// Associated spec ID
    pub spec_id: String,

    /// Git SHA (if git checkpoint)
    pub git_sha: Option<String>,

    /// Git message
    pub git_message: Option<String>,

    /// Config snapshot (JSON)
    pub config_snapshot: Option<serde_json::Value>,

    /// Database snapshot ID
    pub db_snapshot_id: Option<String>,

    /// Metrics baseline
    pub metrics_baseline: Option<MetricsBaseline>,

    /// Created at
    pub created_at: DateTime<Utc>,

    /// Status
    pub status: CheckpointStatus,

    /// Metadata
    pub metadata: std::collections::HashMap<String, String>,
}

/// Checkpoint status
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CheckpointStatus {
    #[default]
    Pending,
    Creating,
    Complete,
    Failed,
}

/// Metrics baseline for rollback verification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsBaseline {
    /// Timestamp
    pub timestamp: DateTime<Utc>,

    /// CPU usage percent
    pub cpu_percent: Option<f64>,

    /// Memory usage MB
    pub memory_mb: Option<u64>,

    /// Latency baseline ms
    pub latency_ms: Option<u64>,

    /// Error rate baseline
    pub error_rate: Option<f64>,
}

/// Config snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigSnapshot {
    /// Files snapshot
    pub files: Vec<FileSnapshot>,

    /// Environment variables
    pub env_vars: std::collections::HashMap<String, String>,

    /// Created at
    pub created_at: DateTime<Utc>,
}

/// Individual file snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileSnapshot {
    /// File path
    pub path: String,

    /// Content hash
    pub content_hash: String,

    /// Size bytes
    pub size_bytes: u64,
}

/// Checkpoint options
#[derive(Debug, Clone)]
pub struct CheckpointOptions {
    /// Create git checkpoint
    pub git_checkpoint: bool,

    /// Snapshot config files
    pub config_snapshot: bool,

    /// Capture metrics baseline
    pub metrics_baseline: bool,

    /// Include uncommitted changes
    pub include_uncommitted: bool,

    /// Custom message
    pub message: Option<String>,
}

impl Default for CheckpointOptions {
    fn default() -> Self {
        Self {
            git_checkpoint: true,
            config_snapshot: true,
            metrics_baseline: true,
            include_uncommitted: true,
            message: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn checkpoint_options_default_flags_enabled() {
        let options = CheckpointOptions::default();
        assert!(options.git_checkpoint);
        assert!(options.config_snapshot);
        assert!(options.include_uncommitted);
    }

    #[test]
    fn checkpoint_status_roundtrip_serialization() {
        let checkpoint = Checkpoint {
            id: Uuid::new_v4(),
            spec_id: "spec".to_string(),
            git_sha: Some("abc".to_string()),
            git_message: None,
            config_snapshot: None,
            db_snapshot_id: None,
            metrics_baseline: Some(MetricsBaseline {
                timestamp: Utc::now(),
                cpu_percent: None,
                memory_mb: Some(128),
                latency_ms: None,
                error_rate: None,
            }),
            created_at: Utc::now(),
            status: CheckpointStatus::Complete,
            metadata: std::collections::HashMap::new(),
        };

        let json = serde_json::to_string(&checkpoint).expect("serialize");
        let decoded: Checkpoint = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(decoded.spec_id, "spec");
        assert_eq!(decoded.status, CheckpointStatus::Complete);
    }
}
