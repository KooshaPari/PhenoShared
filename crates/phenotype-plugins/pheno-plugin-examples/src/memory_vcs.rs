//! Example: an in-memory VCS plugin.
//!
//! `MemoryVcsPlugin` stores branches, worktrees, and feature
//! artifacts in plain `HashMap`s. It implements every method of
//! [`VcsPlugin`] with the smallest amount of state needed for
//! realistic test scenarios.
//!
//! It is **not** a real version-control system: it does not track
//! history, resolve conflicts, or perform merges. It is a reference
//! for plugin authors, and a stable target for integration tests.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};

use async_trait::async_trait;
use pheno_plugin_core::capabilities::Capability;
use pheno_plugin_core::error::{PluginError, PluginResult};
use pheno_plugin_core::manifest::{PluginKind, PluginManifest};
use pheno_plugin_core::traits::{
    AdapterPlugin, ConflictInfo, FeatureArtifacts, MergeResult, PluginConfig, VcsPlugin,
    WorktreeInfo,
};

/// An in-memory VCS plugin.
///
/// All state lives in `Arc<RwLock<...>>` so the same instance can be
/// cloned (cheap) and shared between threads, matching the contract
/// of `dyn VcsPlugin` inside the registry.
#[derive(Clone, Default)]
pub struct MemoryVcsPlugin {
    inner: Arc<RwLock<MemoryVcsState>>,
}

#[derive(Default)]
struct MemoryVcsState {
    /// Logical branches known to the plugin.
    branches: HashMap<String, ()>,
    /// Active worktrees keyed by worktree path.
    worktrees: HashMap<PathBuf, WorktreeInfo>,
    /// Artifacts stored as `(feature_slug, relative_path) -> contents`.
    artifacts: HashMap<(String, String), String>,
}

impl MemoryVcsPlugin {
    /// Construct a fresh, empty in-memory VCS.
    pub fn new() -> Self {
        Self::default()
    }

    /// Build the canonical manifest for this plugin.
    pub fn manifest() -> PluginResult<PluginManifest> {
        let m = PluginManifest::new("memory-vcs", "0.1.0", PluginKind::Vcs)?
            .with_description("In-memory VCS plugin (for tests and SDK demos)".to_string())
            .with_capabilities(vec![
                Capability::Read,
                Capability::FilesystemRead,
                Capability::FilesystemWrite,
                Capability::WorkingTree,
            ]);
        m.validate()?;
        Ok(m)
    }
}

impl AdapterPlugin for MemoryVcsPlugin {
    fn name(&self) -> &str {
        "memory-vcs"
    }

    fn version(&self) -> &str {
        env!("CARGO_PKG_VERSION")
    }

    fn initialize(&self, _config: PluginConfig) -> PluginResult<()> {
        Ok(())
    }
}

#[async_trait]
impl VcsPlugin for MemoryVcsPlugin {
    async fn create_worktree(&self, feature_slug: &str, wp_id: &str) -> PluginResult<PathBuf> {
        if feature_slug.is_empty() || wp_id.is_empty() {
            return Err(PluginError::Validation(
                "feature_slug and wp_id must be non-empty".to_string(),
            ));
        }
        let path = PathBuf::from(format!("/mem-vcs/{}/{}", feature_slug, wp_id));
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        if state.worktrees.contains_key(&path) {
            return Err(PluginError::AlreadyExists(format!(
                "worktree already exists at {}",
                path.display()
            )));
        }
        let info = WorktreeInfo {
            path: path.clone(),
            branch: format!("feature/{}", feature_slug),
            feature_slug: feature_slug.to_string(),
            wp_id: wp_id.to_string(),
        };
        state.worktrees.insert(path.clone(), info);
        state
            .branches
            .insert(format!("feature/{}", feature_slug), ());
        Ok(path)
    }

    async fn list_worktrees(&self) -> PluginResult<Vec<WorktreeInfo>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state.worktrees.values().cloned().collect())
    }

    async fn cleanup_worktree(&self, worktree_path: &Path) -> PluginResult<()> {
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        state.worktrees.remove(worktree_path);
        Ok(())
    }

    async fn create_branch(&self, branch_name: &str, _base: &str) -> PluginResult<()> {
        if branch_name.is_empty() {
            return Err(PluginError::Validation(
                "branch name must be non-empty".to_string(),
            ));
        }
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        if state.branches.contains_key(branch_name) {
            return Err(PluginError::AlreadyExists(format!(
                "branch '{}' already exists",
                branch_name
            )));
        }
        state.branches.insert(branch_name.to_string(), ());
        Ok(())
    }

    async fn checkout_branch(&self, _branch_name: &str) -> PluginResult<()> {
        // No-op for an in-memory VCS; the "current branch" concept
        // doesn't exist without filesystem state.
        Ok(())
    }

    async fn merge_to_target(&self, source: &str, _target: &str) -> PluginResult<MergeResult> {
        // Reference implementation: succeed unless `source` contains
        // a sentinel conflict marker. This is enough to drive
        // integration tests that exercise both paths.
        if source.contains("conflict") {
            Ok(MergeResult {
                success: false,
                conflicts: vec![ConflictInfo {
                    path: "MEMORY_CONFLICT".to_string(),
                    ours: Some(format!("ours:{}", source)),
                    theirs: None,
                }],
                merged_commit: None,
            })
        } else {
            Ok(MergeResult {
                success: true,
                conflicts: vec![],
                merged_commit: Some(format!("mem-merge-{}", source)),
            })
        }
    }

    async fn detect_conflicts(
        &self,
        _source: &str,
        _target: &str,
    ) -> PluginResult<Vec<ConflictInfo>> {
        Ok(vec![])
    }

    async fn read_artifact(&self, feature_slug: &str, relative_path: &str) -> PluginResult<String> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        state
            .artifacts
            .get(&(feature_slug.to_string(), relative_path.to_string()))
            .cloned()
            .ok_or_else(|| {
                PluginError::NotFound(format!(
                    "artifact {}/{} not found",
                    feature_slug, relative_path
                ))
            })
    }

    async fn write_artifact(
        &self,
        feature_slug: &str,
        relative_path: &str,
        content: &str,
    ) -> PluginResult<()> {
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        state.artifacts.insert(
            (feature_slug.to_string(), relative_path.to_string()),
            content.to_string(),
        );
        Ok(())
    }

    async fn artifact_exists(&self, feature_slug: &str, relative_path: &str) -> PluginResult<bool> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state
            .artifacts
            .contains_key(&(feature_slug.to_string(), relative_path.to_string())))
    }

    async fn scan_feature_artifacts(&self, feature_slug: &str) -> PluginResult<FeatureArtifacts> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        let prefix = format!("{}/", feature_slug);
        let paths: Vec<String> = state
            .artifacts
            .keys()
            .filter(|(slug, _)| slug == feature_slug)
            .map(|(_, path)| format!("{}{}", prefix, path))
            .collect();
        Ok(FeatureArtifacts {
            meta_json: state
                .artifacts
                .get(&(feature_slug.to_string(), "meta.json".to_string()))
                .cloned(),
            audit_chain: state
                .artifacts
                .get(&(feature_slug.to_string(), "audit.chain".to_string()))
                .cloned(),
            evidence_paths: paths,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pheno_plugin_core::PluginRegistry;

    #[tokio::test]
    async fn test_memory_vcs_lifecycle() {
        let plugin = MemoryVcsPlugin::new();
        let path = plugin
            .create_worktree("feat-x", "WP-1")
            .await
            .expect("create worktree");
        assert!(path.starts_with("/mem-vcs/"));

        let trees = plugin.list_worktrees().await.expect("list");
        assert_eq!(trees.len(), 1);
        assert_eq!(trees[0].feature_slug, "feat-x");

        plugin
            .write_artifact("feat-x", "meta.json", r#"{"ok":true}"#)
            .await
            .expect("write");
        let body = plugin
            .read_artifact("feat-x", "meta.json")
            .await
            .expect("read");
        assert_eq!(body, r#"{"ok":true}"#);

        plugin
            .cleanup_worktree(&path)
            .await
            .expect("cleanup");
        let trees = plugin.list_worktrees().await.expect("list");
        assert!(trees.is_empty());
    }

    #[tokio::test]
    async fn test_memory_vcs_registered_in_registry() {
        let registry = PluginRegistry::new();
        registry
            .register_vcs(Box::new(MemoryVcsPlugin::new()))
            .expect("register");

        let plugin = registry.vcs("memory-vcs").expect("lookup");
        let path = plugin.create_worktree("demo", "WP-9").await.unwrap();
        assert!(path.starts_with("/mem-vcs/"));
    }

    #[tokio::test]
    async fn test_memory_vcs_artifact_not_found() {
        let plugin = MemoryVcsPlugin::new();
        let err = plugin
            .read_artifact("missing", "meta.json")
            .await
            .expect_err("should be NotFound");
        assert!(matches!(err, PluginError::NotFound(_)));
    }

    #[tokio::test]
    async fn test_memory_vcs_duplicate_worktree_rejected() {
        let plugin = MemoryVcsPlugin::new();
        plugin
            .create_worktree("dup", "WP-1")
            .await
            .expect("first");
        let err = plugin
            .create_worktree("dup", "WP-1")
            .await
            .expect_err("should fail");
        assert!(matches!(err, PluginError::AlreadyExists(_)));
    }

    #[tokio::test]
    async fn test_memory_vcs_merge_conflict_path() {
        let plugin = MemoryVcsPlugin::new();
        let r = plugin
            .merge_to_target("with-conflict-marker", "main")
            .await
            .expect("merge");
        assert!(!r.success);
        assert_eq!(r.conflicts.len(), 1);
    }

    #[tokio::test]
    async fn test_memory_vcs_merge_clean_path() {
        let plugin = MemoryVcsPlugin::new();
        let r = plugin
            .merge_to_target("feature/clean", "main")
            .await
            .expect("merge");
        assert!(r.success);
        assert!(r.merged_commit.is_some());
    }

    #[test]
    fn test_manifest_is_valid() {
        let m = MemoryVcsPlugin::manifest().expect("manifest");
        assert_eq!(m.name, "memory-vcs");
        assert!(m.has_capability(Capability::WorkingTree));
    }
}
