//! Core plugin traits for AgilePlus extensibility.
//!
//! These traits define the port interfaces that adapters must implement.
//! They follow the Hexagonal Architecture pattern where the core domain
//! defines the interfaces that adapters must satisfy.
//!
//! ## Dyn Compatibility
//!
//! These traits use `#[trait_variant]` to enable dynamic dispatch via `dyn Trait`.
//! This allows runtime plugin selection and swapping.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::PluginResult;

/// Configuration for a plugin adapter.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginConfig {
    /// Plugin name
    pub name: String,
    /// Plugin version
    pub version: String,
    /// Adapter-specific configuration (JSON)
    #[serde(default)]
    pub adapter_config: serde_json::Value,
}

/// Base trait for all AgilePlus plugins.
///
/// All adapters must implement this trait to be registered in the system.
/// It provides metadata and lifecycle management for plugins.
///
/// ## Example
///
/// ```rust,ignore
/// struct GitAdapter { /* ... */ }
///
/// impl AdapterPlugin for GitAdapter {
///     fn name(&self) -> &str { "git" }
///     fn version(&self) -> &str { "0.1.0" }
///     fn initialize(&self, config: PluginConfig) -> PluginResult<()> {
///         // Initialize adapter
///         Ok(())
///     }
/// }
/// ```
pub trait AdapterPlugin: Send + Sync {
    /// Returns the plugin name (e.g., "git", "sqlite", "ollama").
    fn name(&self) -> &str;

    /// Returns the plugin version.
    fn version(&self) -> &str;

    /// Initializes the plugin with configuration.
    ///
    /// This is called once when the plugin is registered.
    fn initialize(&self, config: PluginConfig) -> PluginResult<()>;

    /// Returns the plugin health status.
    ///
    /// Returns `Ok(())` if healthy, or an error describing the issue.
    fn health_check(&self) -> PluginResult<()> {
        Ok(())
    }
}

// ============================================================================
// VCS Plugin Trait
// ============================================================================

/// Metadata about an active git worktree.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorktreeInfo {
    pub path: PathBuf,
    pub branch: String,
    pub feature_slug: String,
    pub wp_id: String,
}

/// Result of a merge operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeResult {
    pub success: bool,
    pub conflicts: Vec<ConflictInfo>,
    pub merged_commit: Option<String>,
}

/// Description of a merge conflict in a single file.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictInfo {
    pub path: String,
    pub ours: Option<String>,
    pub theirs: Option<String>,
}

/// Collected feature artifacts discovered in the repository.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureArtifacts {
    pub meta_json: Option<String>,
    pub audit_chain: Option<String>,
    pub evidence_paths: Vec<String>,
}

/// VCS (Version Control System) plugin trait.
///
/// Abstracts git operations so tests can use in-memory mocks.
///
/// ## Dyn Compatibility
///
/// This trait uses `#[async_trait]` to support dynamic dispatch.
///
/// ## Implementations
///
/// - `agileplus-plugin-git`: Production git adapter using gitoxide
/// - Mock adapter: For testing without filesystem
#[async_trait::async_trait]
pub trait VcsPlugin: AdapterPlugin {
    // -- Worktree operations --

    /// Create a worktree for a feature work package.
    async fn create_worktree(&self, feature_slug: &str, wp_id: &str) -> PluginResult<PathBuf>;

    /// List all worktrees.
    async fn list_worktrees(&self) -> PluginResult<Vec<WorktreeInfo>>;

    /// Clean up (remove) a worktree.
    async fn cleanup_worktree(&self, worktree_path: &Path) -> PluginResult<()>;

    // -- Branch operations --

    /// Create a new branch.
    async fn create_branch(&self, branch_name: &str, base: &str) -> PluginResult<()>;

    /// Checkout a branch.
    async fn checkout_branch(&self, branch_name: &str) -> PluginResult<()>;

    // -- Merge operations --

    /// Merge source branch into target.
    async fn merge_to_target(&self, source: &str, target: &str) -> PluginResult<MergeResult>;

    /// Detect conflicts between branches.
    async fn detect_conflicts(&self, source: &str, target: &str)
        -> PluginResult<Vec<ConflictInfo>>;

    // -- Artifact operations --

    /// Read an artifact file.
    async fn read_artifact(&self, feature_slug: &str, relative_path: &str) -> PluginResult<String>;

    /// Write an artifact file.
    async fn write_artifact(
        &self,
        feature_slug: &str,
        relative_path: &str,
        content: &str,
    ) -> PluginResult<()>;

    /// Check if an artifact exists.
    async fn artifact_exists(&self, feature_slug: &str, relative_path: &str) -> PluginResult<bool>;

    /// Scan and collect all artifacts for a feature.
    async fn scan_feature_artifacts(&self, feature_slug: &str) -> PluginResult<FeatureArtifacts>;
}

// ============================================================================
// Storage Plugin Trait
// ============================================================================

/// Storage plugin trait.
///
/// Abstracts database operations for persistence.
///
/// ## Dyn Compatibility
///
/// This trait uses `#[async_trait]` to support dynamic dispatch.
///
/// ## Implementations
///
/// - `agileplus-plugin-sqlite`: SQLite adapter (rusqlite)
/// - `agileplus-plugin-postgres`: PostgreSQL adapter (sqlx) [future]
#[async_trait::async_trait]
pub trait StoragePlugin: AdapterPlugin {
    // -- Feature operations --

    /// Create a new feature.
    async fn create_feature(&self, feature: &serde_json::Value) -> PluginResult<i64>;

    /// Get a feature by slug.
    async fn get_feature_by_slug(&self, slug: &str) -> PluginResult<Option<serde_json::Value>>;

    /// Get a feature by ID.
    async fn get_feature_by_id(&self, id: i64) -> PluginResult<Option<serde_json::Value>>;

    /// Update feature state.
    async fn update_feature_state(&self, id: i64, state: &str) -> PluginResult<()>;

    /// List all features.
    async fn list_all_features(&self) -> PluginResult<Vec<serde_json::Value>>;

    // -- Work package operations --

    /// Create a work package.
    async fn create_work_package(&self, wp: &serde_json::Value) -> PluginResult<i64>;

    /// Get a work package by ID.
    async fn get_work_package(&self, id: i64) -> PluginResult<Option<serde_json::Value>>;

    /// Update work package state.
    async fn update_wp_state(&self, id: i64, state: &str) -> PluginResult<()>;

    // -- Audit operations --

    /// Append an audit entry.
    async fn append_audit_entry(&self, entry: &serde_json::Value) -> PluginResult<i64>;

    /// Get audit trail for a feature.
    async fn get_audit_trail(&self, feature_id: i64) -> PluginResult<Vec<serde_json::Value>>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_plugin_config_construction_and_clone() {
        let cfg = PluginConfig {
            name: "x".to_string(),
            version: "1.0".to_string(),
            adapter_config: serde_json::json!({}),
        };
        assert_eq!(cfg.name, "x");
        assert_eq!(cfg.version, "1.0");
        assert_eq!(cfg.adapter_config, serde_json::json!({}));

        let cloned = cfg.clone();
        assert_eq!(cloned.name, cfg.name);
        assert_eq!(cloned.version, cfg.version);
        assert_eq!(cloned.adapter_config, cfg.adapter_config);

        let dbg = format!("{:?}", cfg);
        assert!(
            dbg.contains("x"),
            "debug output should contain name 'x': {}",
            dbg
        );
        assert!(
            dbg.contains("1.0"),
            "debug output should contain version '1.0': {}",
            dbg
        );
    }

    #[test]
    fn test_plugin_config_serde_roundtrip() {
        let original = PluginConfig {
            name: "git".to_string(),
            version: "0.1.0".to_string(),
            adapter_config: serde_json::json!({"key": "value"}),
        };

        // Sanity-check that the JSON is valid by successfully serializing.
        let json_str = serde_json::to_string(&original).expect("serialize should succeed");
        assert!(!json_str.is_empty(), "serialized JSON should not be empty");
        // Re-parse to ensure the produced JSON is itself valid JSON.
        let reparsed: serde_json::Value =
            serde_json::from_str(&json_str).expect("serialized output should be valid JSON");
        assert_eq!(reparsed["name"], "git");
        assert_eq!(reparsed["version"], "0.1.0");
        assert_eq!(reparsed["adapter_config"]["key"], "value");

        let deserialized: PluginConfig =
            serde_json::from_str(&json_str).expect("deserialize should succeed");
        assert_eq!(deserialized.name, original.name);
        assert_eq!(deserialized.version, original.version);
        assert_eq!(deserialized.adapter_config, original.adapter_config);
    }

    #[test]
    fn test_plugin_config_default_adapter_config() {
        // JSON payload intentionally omits `adapter_config` to exercise `#[serde(default)]`.
        let json_str = r#"{"name":"x","version":"1.0"}"#;
        let cfg: PluginConfig = serde_json::from_str(json_str).expect("deserialize should succeed");

        assert_eq!(cfg.name, "x");
        assert_eq!(cfg.version, "1.0");
        assert!(
            cfg.adapter_config.is_null(),
            "adapter_config should default to Null when missing, got: {}",
            cfg.adapter_config
        );
    }

    #[test]
    fn test_worktree_info_construction() {
        let info = WorktreeInfo {
            path: PathBuf::from("/tmp/x"),
            branch: "main".to_string(),
            feature_slug: "f".to_string(),
            wp_id: "w".to_string(),
        };
        assert_eq!(info.path, PathBuf::from("/tmp/x"));
        assert_eq!(info.branch, "main");
        assert_eq!(info.feature_slug, "f");
        assert_eq!(info.wp_id, "w");
    }

    #[test]
    fn test_merge_result_construction() {
        // Empty conflicts case.
        let ok = MergeResult {
            success: true,
            conflicts: vec![],
            merged_commit: Some("abc123".to_string()),
        };
        assert!(ok.success);
        assert!(ok.conflicts.is_empty());
        assert_eq!(ok.merged_commit.as_deref(), Some("abc123"));

        // With a single conflict and no merged commit.
        let conflict = ConflictInfo {
            path: "x.rs".to_string(),
            ours: Some("a".to_string()),
            theirs: Some("b".to_string()),
        };
        let failed = MergeResult {
            success: false,
            conflicts: vec![conflict],
            merged_commit: None,
        };
        assert!(!failed.success);
        assert_eq!(failed.conflicts.len(), 1);
        assert_eq!(failed.conflicts[0].path, "x.rs");
        assert_eq!(failed.conflicts[0].ours.as_deref(), Some("a"));
        assert_eq!(failed.conflicts[0].theirs.as_deref(), Some("b"));
        assert!(failed.merged_commit.is_none());
    }

    #[test]
    fn test_worktree_info_debug_format() {
        let w = WorktreeInfo {
            path: PathBuf::from("/tmp/wt"),
            branch: "main".to_string(),
            feature_slug: "feat-1".to_string(),
            wp_id: "WP-1".to_string(),
        };
        let dbg = format!("{:?}", w);
        assert!(
            dbg.contains("WorktreeInfo"),
            "debug output should contain 'WorktreeInfo': {}",
            dbg
        );
        assert!(
            dbg.contains("/tmp/wt"),
            "debug output should contain path '/tmp/wt': {}",
            dbg
        );
        assert!(
            dbg.contains("main"),
            "debug output should contain branch 'main': {}",
            dbg
        );
        assert!(
            dbg.contains("WP-1"),
            "debug output should contain wp_id 'WP-1': {}",
            dbg
        );
    }

    #[test]
    fn test_worktree_info_clone() {
        let original = WorktreeInfo {
            path: PathBuf::from("/tmp/wt"),
            branch: "main".to_string(),
            feature_slug: "feat-1".to_string(),
            wp_id: "WP-1".to_string(),
        };
        let cloned = original.clone();
        assert_eq!(cloned.path, original.path);
        assert_eq!(cloned.branch, original.branch);
        assert_eq!(cloned.feature_slug, original.feature_slug);
        assert_eq!(cloned.wp_id, original.wp_id);
    }

    #[test]
    fn test_merge_result_debug_format() {
        let m = MergeResult {
            success: true,
            conflicts: vec![],
            merged_commit: Some("abc".to_string()),
        };
        let dbg = format!("{:?}", m);
        assert!(
            dbg.contains("MergeResult"),
            "debug output should contain 'MergeResult': {}",
            dbg
        );
        assert!(
            dbg.contains("true"),
            "debug output should contain 'true': {}",
            dbg
        );
        assert!(
            dbg.contains("abc"),
            "debug output should contain merged_commit 'abc': {}",
            dbg
        );
    }

    #[test]
    fn test_merge_result_clone() {
        let conflict = ConflictInfo {
            path: "src/lib.rs".to_string(),
            ours: Some("ours-content".to_string()),
            theirs: Some("theirs-content".to_string()),
        };
        let original = MergeResult {
            success: false,
            conflicts: vec![conflict],
            merged_commit: None,
        };
        let cloned = original.clone();
        assert_eq!(cloned.success, original.success);
        assert_eq!(cloned.conflicts.len(), original.conflicts.len());
        assert_eq!(cloned.conflicts[0].path, original.conflicts[0].path);
        assert_eq!(cloned.conflicts[0].ours, original.conflicts[0].ours);
        assert_eq!(cloned.conflicts[0].theirs, original.conflicts[0].theirs);
        assert_eq!(cloned.merged_commit, original.merged_commit);
    }

    #[test]
    fn test_plugin_config_debug_format() {
        let c = PluginConfig {
            name: "x".to_string(),
            version: "1.0.0".to_string(),
            adapter_config: serde_json::json!({}),
        };
        let dbg = format!("{:?}", c);
        assert!(
            dbg.contains("PluginConfig"),
            "debug output should contain 'PluginConfig': {}",
            dbg
        );
        assert!(
            dbg.contains("x"),
            "debug output should contain name 'x': {}",
            dbg
        );
        assert!(
            dbg.contains("1.0.0"),
            "debug output should contain version '1.0.0': {}",
            dbg
        );
    }

    #[test]
    fn test_feature_artifacts_default_or_empty() {
        // `FeatureArtifacts` does not derive `Default`, so build an "empty" instance
        // explicitly and assert that all fields are absent/empty.
        let a = FeatureArtifacts {
            meta_json: None,
            audit_chain: None,
            evidence_paths: Vec::new(),
        };
        assert!(a.meta_json.is_none());
        assert!(a.audit_chain.is_none());
        assert!(a.evidence_paths.is_empty());
    }

    #[test]
    fn test_feature_artifacts_debug_format() {
        let a = FeatureArtifacts {
            meta_json: Some(r#"{"slug":"f"}"#.to_string()),
            audit_chain: Some("audit-blob".to_string()),
            evidence_paths: vec![
                "evidence/a.txt".to_string(),
                "evidence/b.txt".to_string(),
            ],
        };
        let dbg = format!("{:?}", a);
        assert!(
            dbg.contains("FeatureArtifacts"),
            "debug output should contain 'FeatureArtifacts': {}",
            dbg
        );
        assert!(
            dbg.contains("meta_json"),
            "debug output should contain 'meta_json' field name: {}",
            dbg
        );
        assert!(
            dbg.contains("audit-blob"),
            "debug output should contain audit chain blob: {}",
            dbg
        );
        assert!(
            dbg.contains("evidence/a.txt"),
            "debug output should contain evidence path: {}",
            dbg
        );
        assert!(
            dbg.contains("evidence/b.txt"),
            "debug output should contain second evidence path: {}",
            dbg
        );
    }

    #[test]
    fn test_merge_result_field_accessors() {
        let conflict = ConflictInfo {
            path: "src/lib.rs".to_string(),
            ours: Some("ours-content".to_string()),
            theirs: Some("theirs-content".to_string()),
        };
        let m = MergeResult {
            success: true,
            conflicts: vec![conflict],
            merged_commit: Some("deadbeef".to_string()),
        };

        // Direct field accessors (`success`, `conflicts`, `merged_commit`).
        assert!(m.success);
        assert_eq!(m.conflicts.len(), 1);
        assert_eq!(m.conflicts[0].path, "src/lib.rs");
        assert_eq!(m.conflicts[0].ours.as_deref(), Some("ours-content"));
        assert_eq!(m.conflicts[0].theirs.as_deref(), Some("theirs-content"));
        assert_eq!(m.merged_commit.as_deref(), Some("deadbeef"));
    }

    #[test]
    fn test_worktree_info_partial_eq() {
        // `WorktreeInfo` does not derive `PartialEq`, so we exercise equality
        // by comparing each field manually. Two identical values compare equal.
        let a = WorktreeInfo {
            path: PathBuf::from("/tmp/wt"),
            branch: "main".to_string(),
            feature_slug: "feat-1".to_string(),
            wp_id: "WP-1".to_string(),
        };
        let b = WorktreeInfo {
            path: PathBuf::from("/tmp/wt"),
            branch: "main".to_string(),
            feature_slug: "feat-1".to_string(),
            wp_id: "WP-1".to_string(),
        };
        assert_eq!(a.path, b.path);
        assert_eq!(a.branch, b.branch);
        assert_eq!(a.feature_slug, b.feature_slug);
        assert_eq!(a.wp_id, b.wp_id);

        // Mutate one field of a clone and confirm that field no longer matches.
        let mut c = b.clone();
        c.wp_id = "WP-2".to_string();
        assert_ne!(c.wp_id, a.wp_id);
    }

    #[test]
    fn test_plugin_config_default_adapter_config_is_object() {
        let c = PluginConfig {
            name: "x".to_string(),
            version: "1.0.0".to_string(),
            adapter_config: serde_json::json!({}),
        };
        assert!(
            c.adapter_config.is_object(),
            "adapter_config should be a JSON object, got: {}",
            c.adapter_config
        );
        let obj = c
            .adapter_config
            .as_object()
            .expect("adapter_config should be a JSON object");
        assert!(
            obj.is_empty(),
            "expected empty JSON object, got: {}",
            c.adapter_config
        );
    }
}
