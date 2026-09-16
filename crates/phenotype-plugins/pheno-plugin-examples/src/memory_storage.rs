//! Example: an in-memory storage plugin.
//!
//! `MemoryStoragePlugin` stores features, work packages, and audit
//! entries in plain `HashMap`s. It is the smallest possible
//! implementation of [`StoragePlugin`] and is intended as a
//! reference for adapter authors and a stable target for tests.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use async_trait::async_trait;
use pheno_plugin_core::capabilities::Capability;
use pheno_plugin_core::error::{PluginError, PluginResult};
use pheno_plugin_core::manifest::{PluginKind, PluginManifest};
use pheno_plugin_core::traits::{AdapterPlugin, PluginConfig, StoragePlugin};

/// An in-memory storage plugin.
#[derive(Clone, Default)]
pub struct MemoryStoragePlugin {
    inner: Arc<RwLock<MemoryStorageState>>,
}

#[derive(Default)]
struct MemoryStorageState {
    /// Auto-increment counter used for new IDs.
    next_id: i64,
    /// Features stored as the JSON value the caller passed in.
    features: HashMap<i64, serde_json::Value>,
    /// Slug → feature id index for `get_feature_by_slug`.
    slug_index: HashMap<String, i64>,
    /// Work packages, also keyed by id.
    work_packages: HashMap<i64, serde_json::Value>,
    /// Audit entries: `feature_id -> Vec<entry>`.
    audit: HashMap<i64, Vec<serde_json::Value>>,
}

impl MemoryStoragePlugin {
    /// Construct a fresh, empty in-memory storage.
    pub fn new() -> Self {
        Self::default()
    }

    /// Build the canonical manifest for this plugin.
    pub fn manifest() -> PluginResult<PluginManifest> {
        let m = PluginManifest::new("memory-storage", "0.1.0", PluginKind::Storage)?
            .with_description("In-memory storage plugin (for tests and SDK demos)".to_string())
            .with_capabilities(vec![
                Capability::Read,
                Capability::Storage,
                Capability::Audit,
            ]);
        m.validate()?;
        Ok(m)
    }
}

impl AdapterPlugin for MemoryStoragePlugin {
    fn name(&self) -> &str {
        "memory-storage"
    }

    fn version(&self) -> &str {
        env!("CARGO_PKG_VERSION")
    }

    fn initialize(&self, _config: PluginConfig) -> PluginResult<()> {
        Ok(())
    }
}

#[async_trait]
impl StoragePlugin for MemoryStoragePlugin {
    async fn create_feature(&self, feature: &serde_json::Value) -> PluginResult<i64> {
        let slug = feature
            .get("slug")
            .and_then(|v| v.as_str())
            .ok_or_else(|| PluginError::Validation("feature.slug is required".to_string()))?;
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        if state.slug_index.contains_key(slug) {
            return Err(PluginError::AlreadyExists(format!(
                "feature with slug '{}' already exists",
                slug
            )));
        }
        state.next_id += 1;
        let id = state.next_id;
        let mut stored = feature.clone();
        if let Some(obj) = stored.as_object_mut() {
            obj.insert("id".to_string(), serde_json::json!(id));
        }
        state.slug_index.insert(slug.to_string(), id);
        state.features.insert(id, stored);
        Ok(id)
    }

    async fn get_feature_by_slug(
        &self,
        slug: &str,
    ) -> PluginResult<Option<serde_json::Value>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state
            .slug_index
            .get(slug)
            .and_then(|id| state.features.get(id))
            .cloned())
    }

    async fn get_feature_by_id(&self, id: i64) -> PluginResult<Option<serde_json::Value>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state.features.get(&id).cloned())
    }

    async fn update_feature_state(&self, id: i64, state: &str) -> PluginResult<()> {
        let mut storage = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        let feature = storage
            .features
            .get_mut(&id)
            .ok_or_else(|| PluginError::NotFound(format!("feature {} not found", id)))?;
        if let Some(obj) = feature.as_object_mut() {
            obj.insert("state".to_string(), serde_json::json!(state));
        }
        Ok(())
    }

    async fn list_all_features(&self) -> PluginResult<Vec<serde_json::Value>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state.features.values().cloned().collect())
    }

    async fn create_work_package(&self, wp: &serde_json::Value) -> PluginResult<i64> {
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        state.next_id += 1;
        let id = state.next_id;
        let mut stored = wp.clone();
        if let Some(obj) = stored.as_object_mut() {
            obj.insert("id".to_string(), serde_json::json!(id));
        }
        state.work_packages.insert(id, stored);
        Ok(id)
    }

    async fn get_work_package(&self, id: i64) -> PluginResult<Option<serde_json::Value>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state.work_packages.get(&id).cloned())
    }

    async fn update_wp_state(&self, id: i64, state: &str) -> PluginResult<()> {
        let mut storage = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        let wp = storage
            .work_packages
            .get_mut(&id)
            .ok_or_else(|| PluginError::NotFound(format!("work package {} not found", id)))?;
        if let Some(obj) = wp.as_object_mut() {
            obj.insert("state".to_string(), serde_json::json!(state));
        }
        Ok(())
    }

    async fn append_audit_entry(&self, entry: &serde_json::Value) -> PluginResult<i64> {
        let feature_id = entry
            .get("feature_id")
            .and_then(|v| v.as_i64())
            .ok_or_else(|| {
                PluginError::Validation("audit entry must include feature_id".to_string())
            })?;
        let mut state = self
            .inner
            .write()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        let entries = state.audit.entry(feature_id).or_default();
        entries.push(entry.clone());
        Ok(entries.len() as i64)
    }

    async fn get_audit_trail(&self, feature_id: i64) -> PluginResult<Vec<serde_json::Value>> {
        let state = self
            .inner
            .read()
            .map_err(|_| PluginError::Operation("poisoned lock".to_string()))?;
        Ok(state.audit.get(&feature_id).cloned().unwrap_or_default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pheno_plugin_core::PluginRegistry;
    use serde_json::json;

    #[tokio::test]
    async fn test_create_and_lookup_feature() {
        let plugin = MemoryStoragePlugin::new();
        let id = plugin
            .create_feature(&json!({"slug": "demo", "title": "Demo"}))
            .await
            .expect("create");
        assert!(id > 0);

        let fetched = plugin
            .get_feature_by_slug("demo")
            .await
            .expect("lookup")
            .expect("present");
        assert_eq!(fetched["slug"], "demo");
        assert_eq!(fetched["id"], id);
    }

    #[tokio::test]
    async fn test_update_feature_state() {
        let plugin = MemoryStoragePlugin::new();
        let id = plugin
            .create_feature(&json!({"slug": "s"}))
            .await
            .expect("create");
        plugin
            .update_feature_state(id, "active")
            .await
            .expect("update");
        let f = plugin.get_feature_by_id(id).await.unwrap().unwrap();
        assert_eq!(f["state"], "active");
    }

    #[tokio::test]
    async fn test_duplicate_slug_rejected() {
        let plugin = MemoryStoragePlugin::new();
        plugin
            .create_feature(&json!({"slug": "dup"}))
            .await
            .expect("first");
        let err = plugin
            .create_feature(&json!({"slug": "dup"}))
            .await
            .expect_err("should fail");
        assert!(matches!(err, PluginError::AlreadyExists(_)));
    }

    #[tokio::test]
    async fn test_missing_slug_rejected() {
        let plugin = MemoryStoragePlugin::new();
        let err = plugin
            .create_feature(&json!({}))
            .await
            .expect_err("should fail validation");
        assert!(matches!(err, PluginError::Validation(_)));
    }

    #[tokio::test]
    async fn test_audit_trail_round_trip() {
        let plugin = MemoryStoragePlugin::new();
        let feature_id = 42;
        let _ = plugin
            .append_audit_entry(&json!({"feature_id": feature_id, "msg": "first"}))
            .await
            .expect("append");
        let _ = plugin
            .append_audit_entry(&json!({"feature_id": feature_id, "msg": "second"}))
            .await
            .expect("append");
        let trail = plugin
            .get_audit_trail(feature_id)
            .await
            .expect("trail");
        assert_eq!(trail.len(), 2);
        assert_eq!(trail[0]["msg"], "first");
        assert_eq!(trail[1]["msg"], "second");
    }

    #[tokio::test]
    async fn test_storage_registered_in_registry() {
        let registry = PluginRegistry::new();
        registry
            .register_storage(Box::new(MemoryStoragePlugin::new()))
            .expect("register");
        let plugin = registry.storage("memory-storage").expect("lookup");
        let id = plugin
            .create_feature(&json!({"slug": "r"}))
            .await
            .unwrap();
        assert!(id > 0);
    }

    #[tokio::test]
    async fn test_work_package_state_transitions() {
        let plugin = MemoryStoragePlugin::new();
        let id = plugin
            .create_work_package(&json!({"title": "WP-1"}))
            .await
            .expect("create");
        plugin
            .update_wp_state(id, "in_progress")
            .await
            .expect("update");
        let wp = plugin.get_work_package(id).await.unwrap().unwrap();
        assert_eq!(wp["state"], "in_progress");
    }

    #[test]
    fn test_manifest_is_valid() {
        let m = MemoryStoragePlugin::manifest().expect("manifest");
        assert_eq!(m.name, "memory-storage");
        assert!(m.has_capability(Capability::Storage));
        assert!(m.has_capability(Capability::Audit));
    }
}
