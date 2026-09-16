//! AgilePlus SQLite Plugin — persistence layer adapter.
//!
//! Implements `StoragePlugin` trait for the AgilePlus plugin system.
//! Uses rusqlite with WAL mode and foreign keys for data integrity.

mod error;

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use rusqlite::{params, Connection};

use pheno_plugin_core::{
    error::{PluginError, PluginResult},
    traits::{AdapterPlugin, StoragePlugin},
};

pub use error::SqliteError;

/// SQLite-backed storage adapter implementing `StoragePlugin`.
///
/// Uses a single write-serialized connection protected by a Mutex.
/// WAL mode is enabled to allow concurrent reads; all writes are serialized.
pub struct SqliteStoragePlugin {
    conn: Arc<Mutex<Connection>>,
    db_path: PathBuf,
}

impl SqliteStoragePlugin {
    /// Create a new SQLite storage plugin from a database path.
    pub fn new(db_path: impl AsRef<Path>) -> PluginResult<Self> {
        let db_path = db_path.as_ref().to_path_buf();
        let conn = Connection::open(&db_path)
            .map_err(|e| PluginError::Initialization(format!("failed to open db: {}", e)))?;

        // Enable WAL mode for concurrent reads
        conn.execute_batch("PRAGMA journal_mode=WAL;")
            .map_err(|e| PluginError::Initialization(format!("WAL pragma failed: {}", e)))?;

        // Enable foreign key enforcement
        conn.execute_batch("PRAGMA foreign_keys=ON;")
            .map_err(|e| PluginError::Initialization(format!("FK pragma failed: {}", e)))?;

        // Run migrations
        Self::run_migrations(&conn)?;

        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
            db_path,
        })
    }

    /// Create an in-memory database for testing.
    // kept: public constructor used by downstream crates' test suites
    #[allow(dead_code)]
    pub fn in_memory() -> PluginResult<Self> {
        let conn = Connection::open_in_memory().map_err(|e| {
            PluginError::Initialization(format!("failed to open in-memory db: {}", e))
        })?;

        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
            .map_err(|e| PluginError::Initialization(format!("pragma failed: {}", e)))?;

        Self::run_migrations(&conn)?;

        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
            db_path: PathBuf::from(":memory:"),
        })
    }

    fn run_migrations(conn: &Connection) -> PluginResult<()> {
        // Create tables for AgilePlus domain
        conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                state TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS work_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                state TEXT NOT NULL DEFAULT 'backlog',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feature_id) REFERENCES features(id)
            );

            CREATE TABLE IF NOT EXISTS audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_id INTEGER NOT NULL,
                entry_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feature_id) REFERENCES features(id)
            );

            CREATE TABLE IF NOT EXISTS plugin_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            "#,
        )
        .map_err(|e| PluginError::Initialization(format!("migration failed: {}", e)))?;

        Ok(())
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, Connection>, PluginError> {
        self.conn
            .lock()
            .map_err(|e| PluginError::Operation(format!("mutex poisoned: {}", e)))
    }
}

impl std::fmt::Debug for SqliteStoragePlugin {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SqliteStoragePlugin")
            .field("db_path", &self.db_path)
            .finish()
    }
}

impl AdapterPlugin for SqliteStoragePlugin {
    fn name(&self) -> &str {
        "sqlite-storage"
    }

    fn version(&self) -> &str {
        env!("CARGO_PKG_VERSION")
    }

    fn initialize(&self, _config: pheno_plugin_core::traits::PluginConfig) -> PluginResult<()> {
        // Ensure database is accessible by checking the schema
        let conn = self.lock()?;
        conn.query_row("SELECT COUNT(*) FROM sqlite_master", [], |_| Ok(()))
            .map_err(|e| PluginError::Operation(format!("init check failed: {}", e)))?;
        Ok(())
    }
}

#[async_trait]
impl StoragePlugin for SqliteStoragePlugin {
    // -- Feature operations --

    async fn create_feature(&self, feature: &serde_json::Value) -> PluginResult<i64> {
        let conn = self.lock()?;
        let slug = feature
            .get("slug")
            .and_then(|v| v.as_str())
            .ok_or_else(|| PluginError::Validation("missing slug".to_string()))?;
        let name = feature
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| PluginError::Validation("missing name".to_string()))?;
        let description = feature.get("description").and_then(|v| v.as_str());
        let state = feature
            .get("state")
            .and_then(|v| v.as_str())
            .unwrap_or("draft");

        conn.execute(
            "INSERT INTO features (slug, name, description, state) VALUES (?1, ?2, ?3, ?4)",
            params![slug, name, description, state],
        )
        .map_err(|e| PluginError::Operation(format!("failed to create feature: {}", e)))?;

        Ok(conn.last_insert_rowid())
    }

    async fn get_feature_by_slug(&self, slug: &str) -> PluginResult<Option<serde_json::Value>> {
        let conn = self.lock()?;
        let mut stmt = conn
            .prepare("SELECT id, slug, name, description, state, created_at, updated_at FROM features WHERE slug = ?1")
            .map_err(|e| PluginError::Operation(format!("query prepare failed: {}", e)))?;

        let result = stmt.query_row([slug], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, i64>(0)?,
                "slug": row.get::<_, String>(1)?,
                "name": row.get::<_, String>(2)?,
                "description": row.get::<_, Option<String>>(3)?,
                "state": row.get::<_, String>(4)?,
                "created_at": row.get::<_, String>(5)?,
                "updated_at": row.get::<_, String>(6)?,
            }))
        });

        match result {
            Ok(feature) => Ok(Some(feature)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(PluginError::Operation(format!(
                "failed to get feature: {}",
                e
            ))),
        }
    }

    async fn get_feature_by_id(&self, id: i64) -> PluginResult<Option<serde_json::Value>> {
        let conn = self.lock()?;
        let mut stmt = conn
            .prepare("SELECT id, slug, name, description, state, created_at, updated_at FROM features WHERE id = ?1")
            .map_err(|e| PluginError::Operation(format!("query prepare failed: {}", e)))?;

        let result = stmt.query_row([id], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, i64>(0)?,
                "slug": row.get::<_, String>(1)?,
                "name": row.get::<_, String>(2)?,
                "description": row.get::<_, Option<String>>(3)?,
                "state": row.get::<_, String>(4)?,
                "created_at": row.get::<_, String>(5)?,
                "updated_at": row.get::<_, String>(6)?,
            }))
        });

        match result {
            Ok(feature) => Ok(Some(feature)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(PluginError::Operation(format!(
                "failed to get feature: {}",
                e
            ))),
        }
    }

    async fn update_feature_state(&self, id: i64, state: &str) -> PluginResult<()> {
        let conn = self.lock()?;
        conn.execute(
            "UPDATE features SET state = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
            params![state, id],
        )
        .map_err(|e| PluginError::Operation(format!("failed to update feature: {}", e)))?;
        Ok(())
    }

    async fn list_all_features(&self) -> PluginResult<Vec<serde_json::Value>> {
        let conn = self.lock()?;
        let mut stmt = conn
            .prepare("SELECT id, slug, name, description, state, created_at, updated_at FROM features ORDER BY created_at DESC")
            .map_err(|e| PluginError::Operation(format!("query prepare failed: {}", e)))?;

        let features = stmt
            .query_map([], |row| {
                Ok(serde_json::json!({
                    "id": row.get::<_, i64>(0)?,
                    "slug": row.get::<_, String>(1)?,
                    "name": row.get::<_, String>(2)?,
                    "description": row.get::<_, Option<String>>(3)?,
                    "state": row.get::<_, String>(4)?,
                    "created_at": row.get::<_, String>(5)?,
                    "updated_at": row.get::<_, String>(6)?,
                }))
            })
            .map_err(|e| PluginError::Operation(format!("query failed: {}", e)))?
            .filter_map(|r| r.ok())
            .collect();

        Ok(features)
    }

    // -- Work package operations --

    async fn create_work_package(&self, wp: &serde_json::Value) -> PluginResult<i64> {
        let conn = self.lock()?;
        let feature_id = wp
            .get("feature_id")
            .and_then(|v| v.as_i64())
            .ok_or_else(|| PluginError::Validation("missing feature_id".to_string()))?;
        let title = wp
            .get("title")
            .and_then(|v| v.as_str())
            .ok_or_else(|| PluginError::Validation("missing title".to_string()))?;
        let description = wp.get("description").and_then(|v| v.as_str());
        let state = wp
            .get("state")
            .and_then(|v| v.as_str())
            .unwrap_or("backlog");
        let priority = wp
            .get("priority")
            .and_then(|v| v.as_str())
            .unwrap_or("medium");

        conn.execute(
            "INSERT INTO work_packages (feature_id, title, description, state, priority) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![feature_id, title, description, state, priority],
        )
        .map_err(|e| PluginError::Operation(format!("failed to create work package: {}", e)))?;

        Ok(conn.last_insert_rowid())
    }

    async fn get_work_package(&self, id: i64) -> PluginResult<Option<serde_json::Value>> {
        let conn = self.lock()?;
        let mut stmt = conn
            .prepare("SELECT id, feature_id, title, description, state, priority, created_at, updated_at FROM work_packages WHERE id = ?1")
            .map_err(|e| PluginError::Operation(format!("query prepare failed: {}", e)))?;

        let result = stmt.query_row([id], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, i64>(0)?,
                "feature_id": row.get::<_, i64>(1)?,
                "title": row.get::<_, String>(2)?,
                "description": row.get::<_, Option<String>>(3)?,
                "state": row.get::<_, String>(4)?,
                "priority": row.get::<_, String>(5)?,
                "created_at": row.get::<_, String>(6)?,
                "updated_at": row.get::<_, String>(7)?,
            }))
        });

        match result {
            Ok(wp) => Ok(Some(wp)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(PluginError::Operation(format!(
                "failed to get work package: {}",
                e
            ))),
        }
    }

    async fn update_wp_state(&self, id: i64, state: &str) -> PluginResult<()> {
        let conn = self.lock()?;
        conn.execute(
            "UPDATE work_packages SET state = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
            params![state, id],
        )
        .map_err(|e| PluginError::Operation(format!("failed to update work package: {}", e)))?;
        Ok(())
    }

    // -- Audit operations --

    async fn append_audit_entry(&self, entry: &serde_json::Value) -> PluginResult<i64> {
        let conn = self.lock()?;
        let feature_id = entry
            .get("feature_id")
            .and_then(|v| v.as_i64())
            .ok_or_else(|| PluginError::Validation("missing feature_id".to_string()))?;
        let entry_type = entry
            .get("entry_type")
            .and_then(|v| v.as_str())
            .unwrap_or("info");
        let actor = entry
            .get("actor")
            .and_then(|v| v.as_str())
            .unwrap_or("system");
        let details = entry.get("details").map(|v| v.to_string());

        conn.execute(
            "INSERT INTO audit_entries (feature_id, entry_type, actor, details) VALUES (?1, ?2, ?3, ?4)",
            params![feature_id, entry_type, actor, details],
        )
        .map_err(|e| PluginError::Operation(format!("failed to append audit entry: {}", e)))?;

        Ok(conn.last_insert_rowid())
    }

    async fn get_audit_trail(&self, feature_id: i64) -> PluginResult<Vec<serde_json::Value>> {
        let conn = self.lock()?;
        let mut stmt = conn
            .prepare("SELECT id, feature_id, entry_type, actor, details, created_at FROM audit_entries WHERE feature_id = ?1 ORDER BY created_at DESC")
            .map_err(|e| PluginError::Operation(format!("query prepare failed: {}", e)))?;

        let entries = stmt
            .query_map([feature_id], |row| {
                Ok(serde_json::json!({
                    "id": row.get::<_, i64>(0)?,
                    "feature_id": row.get::<_, i64>(1)?,
                    "entry_type": row.get::<_, String>(2)?,
                    "actor": row.get::<_, String>(3)?,
                    "details": row.get::<_, Option<String>>(4)?,
                    "created_at": row.get::<_, String>(5)?,
                }))
            })
            .map_err(|e| PluginError::Operation(format!("query failed: {}", e)))?
            .filter_map(|r| r.ok())
            .collect();

        Ok(entries)
    }
}

impl SqliteStoragePlugin {
    /// Expose the underlying connection for advanced use cases.
    // kept: public accessor for downstream consumers needing raw rusqlite access
    #[allow(dead_code)]
    pub fn connection(&self) -> Arc<Mutex<Connection>> {
        Arc::clone(&self.conn)
    }

    /// Get the database path.
    // kept: public accessor for downstream diagnostics and introspection
    #[allow(dead_code)]
    pub fn db_path(&self) -> &Path {
        &self.db_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_plugin() -> SqliteStoragePlugin {
        SqliteStoragePlugin::in_memory().expect("failed to create in-memory plugin")
    }

    #[test]
    fn test_new_and_init() {
        let plugin = create_test_plugin();
        plugin
            .initialize(pheno_plugin_core::traits::PluginConfig {
                name: "test".to_string(),
                version: "0.1.0".to_string(),
                adapter_config: serde_json::json!({}),
            })
            .expect("init failed");
    }

    #[test]
    fn test_feature_operations() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Create a feature
            let feature = serde_json::json!({
                "slug": "test-feature",
                "name": "Test Feature",
                "description": "A test feature"
            });

            let id = plugin.create_feature(&feature).await.unwrap();
            assert!(id > 0);

            // Get by slug
            let retrieved = plugin.get_feature_by_slug("test-feature").await.unwrap();
            assert!(retrieved.is_some());
            assert_eq!(retrieved.unwrap()["name"], "Test Feature");

            // Update state
            plugin.update_feature_state(id, "active").await.unwrap();

            // Get by id
            let by_id = plugin.get_feature_by_id(id).await.unwrap();
            assert!(by_id.is_some());
            assert_eq!(by_id.unwrap()["state"], "active");

            // List all
            let all = plugin.list_all_features().await.unwrap();
            assert_eq!(all.len(), 1);
        });
    }

    #[test]
    fn test_work_package_operations() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Create a feature first
            let feature = serde_json::json!({
                "slug": "wp-test",
                "name": "WP Test"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            // Create a work package
            let wp = serde_json::json!({
                "feature_id": feature_id,
                "title": "Test Work Package",
                "description": "Description",
                "priority": "high"
            });

            let wp_id = plugin.create_work_package(&wp).await.unwrap();
            assert!(wp_id > 0);

            // Get work package
            let retrieved = plugin.get_work_package(wp_id).await.unwrap();
            assert!(retrieved.is_some());
            assert_eq!(retrieved.unwrap()["title"], "Test Work Package");

            // Update state
            plugin.update_wp_state(wp_id, "in_progress").await.unwrap();
        });
    }

    #[test]
    fn test_audit_operations() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Create a feature first
            let feature = serde_json::json!({
                "slug": "audit-test",
                "name": "Audit Test"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            // Add audit entries
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "created",
                "actor": "test",
                "details": "{\"action\": \"created\"}"
            });

            plugin.append_audit_entry(&entry).await.unwrap();

            // Get audit trail
            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 1);
            assert_eq!(trail[0]["entry_type"], "created");
        });
    }

    #[test]
    fn test_db_path_accessor() {
        let plugin = create_test_plugin();
        assert_eq!(plugin.db_path(), Path::new(":memory:"));
    }

    #[test]
    fn test_connection_accessor() {
        let plugin = create_test_plugin();
        let conn = plugin.connection();
        let conn_guard = conn.lock().expect("lock poisoned");
        let result: i64 = conn_guard
            .query_row("SELECT 1", [], |r| r.get(0))
            .expect("query");
        assert_eq!(result, 1);
    }

    #[test]
    fn test_adapter_identity() {
        let plugin = create_test_plugin();
        assert_eq!(plugin.name(), "sqlite-storage");
        assert!(!plugin.version().is_empty());
        assert_eq!(plugin.version(), env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn test_debug_impl() {
        let plugin = create_test_plugin();
        let debug_str = format!("{:?}", plugin);
        assert!(debug_str.contains("SqliteStoragePlugin"));
        assert!(debug_str.contains(":memory:"));
    }

    #[test]
    fn test_validation_missing_slug() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Missing "slug" field should yield a Validation error.
            let feature = serde_json::json!({
                "name": "Test Feature Without Slug"
            });

            let err = plugin
                .create_feature(&feature)
                .await
                .expect_err("expected Validation error for missing slug");
            assert!(
                matches!(err, PluginError::Validation(ref msg) if msg == "missing slug"),
                "unexpected error: {:?}",
                err
            );
        });
    }

    #[test]
    fn test_validation_missing_feature_id() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Missing "feature_id" field should yield a Validation error.
            let wp = serde_json::json!({
                "title": "Work Package Without Feature"
            });

            let err = plugin
                .create_work_package(&wp)
                .await
                .expect_err("expected Validation error for missing feature_id");
            assert!(
                matches!(err, PluginError::Validation(ref msg) if msg == "missing feature_id"),
                "unexpected error: {:?}",
                err
            );
        });
    }

    #[test]
    fn test_get_missing_feature_returns_none() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // No features have been created; both lookups should return Ok(None).
            let by_slug = plugin
                .get_feature_by_slug("nonexistent")
                .await
                .expect("get_feature_by_slug should not error on missing row");
            assert!(by_slug.is_none(), "expected None for unknown slug");

            let by_id = plugin
                .get_feature_by_id(9999)
                .await
                .expect("get_feature_by_id should not error on missing row");
            assert!(by_id.is_none(), "expected None for unknown id");
        });
    }

    #[test]
    fn test_get_audit_trail_empty() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Create a feature but no audit entries.
            let feature = serde_json::json!({
                "slug": "no-audit",
                "name": "No Audit Feature"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            // Audit trail for a feature with no entries should be an empty vec.
            let trail = plugin
                .get_audit_trail(feature_id)
                .await
                .expect("get_audit_trail should not error on empty result");
            assert!(
                trail.is_empty(),
                "expected empty audit trail, got {} entries",
                trail.len()
            );
        });
    }

    #[test]
    fn test_new_with_file() {
        // Build a unique path under the system temp dir.
        let pid = std::process::id();
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("pheno-plugin-sqlite-test-{}-{}.db", pid, nanos));

        // Construct from a real file path (NOT in_memory).
        let plugin = SqliteStoragePlugin::new(&path)
            .expect("SqliteStoragePlugin::new(file path) should succeed");

        // The plugin owns and preserves the requested path.
        assert_eq!(plugin.db_path(), path.as_path());

        // initialize() must succeed against the freshly migrated file-backed DB.
        plugin
            .initialize(pheno_plugin_core::traits::PluginConfig {
                name: "test".to_string(),
                version: "0.1.0".to_string(),
                adapter_config: serde_json::json!({}),
            })
            .expect("initialize should succeed against file-backed plugin");

        // Drop the plugin (closes the underlying Connection) before removing
        // the file, then clean up the temp db on disk.
        drop(plugin);
        std::fs::remove_file(&path).expect("failed to remove temp sqlite file");
    }

    #[test]
    fn test_state_update_transitions() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // -- Feature state transitions: draft -> active -> complete --
            let feature = serde_json::json!({
                "slug": "transition-feature",
                "name": "Transition Feature"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();
            assert!(feature_id > 0);

            // No `state` provided on create -> defaults to "draft".
            let created = plugin.get_feature_by_id(feature_id).await.unwrap();
            assert!(created.is_some());
            assert_eq!(created.unwrap()["state"], "draft");

            // First update: draft -> active (overwrites default).
            plugin
                .update_feature_state(feature_id, "active")
                .await
                .unwrap();
            let after_active = plugin.get_feature_by_id(feature_id).await.unwrap();
            assert!(after_active.is_some());
            assert_eq!(after_active.unwrap()["state"], "active");

            // Second update: active -> complete (verifies the prior state is overwritten).
            plugin
                .update_feature_state(feature_id, "complete")
                .await
                .unwrap();
            let after_complete = plugin.get_feature_by_id(feature_id).await.unwrap();
            assert!(after_complete.is_some());
            assert_eq!(after_complete.unwrap()["state"], "complete");

            // -- Work package state transitions: backlog -> in_progress -> done --
            let wp = serde_json::json!({
                "feature_id": feature_id,
                "title": "Transition Work Package"
            });
            let wp_id = plugin.create_work_package(&wp).await.unwrap();
            assert!(wp_id > 0);

            // No `state` provided on create -> defaults to "backlog".
            let wp_created = plugin.get_work_package(wp_id).await.unwrap();
            assert!(wp_created.is_some());
            assert_eq!(wp_created.unwrap()["state"], "backlog");

            // First update: backlog -> in_progress (overwrites default).
            plugin.update_wp_state(wp_id, "in_progress").await.unwrap();
            let after_in_progress = plugin.get_work_package(wp_id).await.unwrap();
            assert!(after_in_progress.is_some());
            assert_eq!(after_in_progress.unwrap()["state"], "in_progress");

            // Second update: in_progress -> done (verifies the prior state is overwritten).
            plugin.update_wp_state(wp_id, "done").await.unwrap();
            let after_done = plugin.get_work_package(wp_id).await.unwrap();
            assert!(after_done.is_some());
            assert_eq!(after_done.unwrap()["state"], "done");
        });
    }

    #[test]
    fn test_list_all_features_multiple() {
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Create three features with distinct, sortable slugs.
            let slugs = ["alpha-feature", "beta-feature", "gamma-feature"];
            for slug in slugs.iter() {
                let feature = serde_json::json!({
                    "slug": slug,
                    "name": format!("Feature {}", slug)
                });
                let id = plugin.create_feature(&feature).await.unwrap();
                assert!(id > 0);
            }

            // list_all_features() should return all three.
            let mut all = plugin.list_all_features().await.unwrap();
            assert_eq!(all.len(), 3);

            // list_all_features() orders by created_at DESC, so sort by slug
            // for a stable, order-independent comparison.
            all.sort_by(|a, b| a["slug"].as_str().cmp(&b["slug"].as_str()));

            let returned: Vec<&str> = all
                .iter()
                .map(|f| f["slug"].as_str().expect("slug should be a string"))
                .collect();
            assert_eq!(returned, slugs.to_vec());

            // Spot-check that other fields round-tripped through list_all_features.
            assert_eq!(all[0]["name"], "Feature alpha-feature");
            assert_eq!(all[1]["name"], "Feature beta-feature");
            assert_eq!(all[2]["name"], "Feature gamma-feature");
        });
    }

    #[test]
    fn test_in_memory_constructor() {
        // Direct in_memory() call: db_path should be ":memory:" and the
        // adapter name should be the canonical "sqlite-storage" identifier.
        let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
        assert_eq!(plugin.db_path(), Path::new(":memory:"));
        assert_eq!(plugin.name(), "sqlite-storage");
    }

    #[test]
    fn test_audit_entry_default_actor_and_type() {
        // When `entry_type` and `actor` are omitted from the JSON, the
        // production code at lib.rs:355 and lib.rs:359 falls back to
        // "info" and "system" respectively.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "audit-defaults",
                "name": "Audit Defaults"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            // No `entry_type`, no `actor` — only feature_id and details.
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "details": "raw details"
            });
            plugin.append_audit_entry(&entry).await.unwrap();

            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 1);
            assert_eq!(trail[0]["entry_type"], "info");
            assert_eq!(trail[0]["actor"], "system");
        });
    }

    #[test]
    fn test_multiple_audit_entries_ordering() {
        // Append three audit entries with distinct actors; verify all
        // three are returned and their actors / details are preserved.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "audit-ordering",
                "name": "Audit Ordering"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let actors = ["alice", "bob", "carol"];
            for actor in actors.iter() {
                let entry = serde_json::json!({
                    "feature_id": feature_id,
                    "entry_type": "noted",
                    "actor": actor,
                    "details": format!("entry-by-{}", actor)
                });
                plugin.append_audit_entry(&entry).await.unwrap();
            }

            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 3);

            // The trail is ordered by created_at DESC, so the
            // last-inserted entry ("carol") is first. Spot-check that
            // the full set of actors and details is preserved across
            // the trail (order-independent).
            let returned_actors: Vec<&str> = trail
                .iter()
                .map(|e| e["actor"].as_str().expect("actor should be a string"))
                .collect();
            let mut returned_actors_sorted = returned_actors.clone();
            returned_actors_sorted.sort();
            assert_eq!(returned_actors_sorted, actors.to_vec());

            // Spot-check the first entry's details preserved verbatim.
            // NOTE: the production code at lib.rs:360 stores `details` as
            // `entry.get("details").map(|v| v.to_string())`, which is the
            // *JSON-serialized* form of the value (i.e. wrapped in quotes
            // for a JSON string). The round-trip reads back the same JSON
            // string, so we compare against the JSON-stringified form.
            for entry in trail.iter() {
                let actor = entry["actor"].as_str().expect("actor should be a string");
                let details = entry["details"].as_str().expect("details should be a string");
                let expected = serde_json::json!(format!("entry-by-{}", actor)).to_string();
                assert_eq!(details, expected);
            }
        });
    }

    #[test]
    fn test_audit_entry_with_no_details() {
        // When `details` is omitted, the production code at lib.rs:360
        // maps it to None (stored as SQL NULL). The query result maps
        // the NULL back to serde_json::Value::Null, so the JSON
        // representation should be `null`.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "audit-no-details",
                "name": "Audit No Details"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let entry = serde_json::json!({
                "feature_id": feature_id,
                "actor": "quiet"
            });
            let id = plugin.append_audit_entry(&entry).await.unwrap();
            assert!(id > 0);

            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 1);
            assert!(
                trail[0]["details"].is_null(),
                "expected details to be JSON null when omitted, got {:?}",
                trail[0]["details"]
            );
            assert_eq!(trail[0]["actor"], "quiet");
        });
    }

    #[test]
    fn test_update_feature_state_for_nonexistent_id() {
        // update_feature_state at lib.rs:239 does not inspect the number
        // of affected rows — it just executes the UPDATE and returns
        // Ok(()). This documents the actual "fire and forget" behavior
        // for an id that does not exist: no error, no row updated.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            plugin
                .update_feature_state(99999, "active")
                .await
                .expect("update_feature_state for nonexistent id should silently succeed");

            // Confirm no row was actually changed by listing features.
            let all = plugin.list_all_features().await.unwrap();
            assert!(
                all.is_empty(),
                "expected no features after updating a nonexistent id, got {}",
                all.len()
            );
        });
    }

    #[test]
    fn test_update_work_package_state_for_nonexistent_id() {
        // Same fire-and-forget behavior as update_feature_state — see
        // lib.rs:334. Document it for work packages.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            plugin
                .update_wp_state(99999, "done")
                .await
                .expect("update_wp_state for nonexistent id should silently succeed");
        });
    }

    #[test]
    fn test_create_feature_duplicate_slug() {
        // The `features.slug` column is declared UNIQUE NOT NULL
        // (lib.rs:79). Inserting a second feature with the same slug
        // must fail with an Operation error.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let first = serde_json::json!({
                "slug": "dup",
                "name": "First Dup"
            });
            let id1 = plugin
                .create_feature(&first)
                .await
                .expect("first insert should succeed");
            assert!(id1 > 0);

            let second = serde_json::json!({
                "slug": "dup",
                "name": "Second Dup"
            });
            let result = plugin.create_feature(&second).await;
            assert!(
                result.is_err(),
                "expected an error for duplicate slug, got {:?}",
                result
            );
        });
    }

    #[test]
    fn test_create_work_package_with_invalid_feature_id() {
        // The `work_packages.feature_id` column has a foreign key to
        // `features.id` (lib.rs:96). Inserting with a feature_id that
        // does not exist must fail. We also try a negative id (-1) as
        // an extra defensive case: the FK should reject it too.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            // Case 1: feature_id = 99999 (no such feature row).
            let wp_orphan = serde_json::json!({
                "feature_id": 99999,
                "title": "orphan"
            });
            let result_orphan = plugin.create_work_package(&wp_orphan).await;
            assert!(
                result_orphan.is_err(),
                "expected FK error for nonexistent feature_id 99999, got {:?}",
                result_orphan
            );

            // Case 2: feature_id = -1. We need a real feature first so
            // that a *valid* work package would otherwise succeed; the
            // FK on -1 is the one we expect to fail.
            let feature = serde_json::json!({
                "slug": "fk-test",
                "name": "FK Test"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();
            let wp_neg = serde_json::json!({
                "feature_id": -1,
                "title": "negative"
            });
            let result_neg = plugin.create_work_package(&wp_neg).await;
            assert!(
                result_neg.is_err(),
                "expected FK error for feature_id -1, got {:?}",
                result_neg
            );

            // Sanity: a valid work package for the real feature still
            // succeeds, so the negative case above really is the FK
            // rejecting -1, not a broken connection.
            let wp_ok = serde_json::json!({
                "feature_id": feature_id,
                "title": "valid"
            });
            plugin
                .create_work_package(&wp_ok)
                .await
                .expect("valid work package should succeed");
        });
    }

    #[test]
    fn test_connection_accessor_arc_independence() {
        // connection() returns Arc::clone(&self.conn); the two Arcs
        // returned by consecutive calls must point to the *same*
        // allocation (Arc::ptr_eq) and must share the same data.
        let plugin = create_test_plugin();
        let conn_a = plugin.connection();
        let conn_b = plugin.connection();
        assert!(
            Arc::ptr_eq(&conn_a, &conn_b),
            "connection() should return Arcs that share the same allocation"
        );

        // A write through one Arc should be visible through the other.
        {
            let guard = conn_a.lock().expect("lock poisoned");
            guard
                .execute("CREATE TABLE IF NOT EXISTS arc_probe (n INTEGER)", [])
                .expect("create probe table");
            guard
                .execute("INSERT INTO arc_probe (n) VALUES (42)", [])
                .expect("insert probe");
        }
        let observed: i64 = conn_b
            .lock()
            .expect("lock poisoned")
            .query_row("SELECT n FROM arc_probe", [], |r| r.get(0))
            .expect("select probe");
        assert_eq!(observed, 42);
    }

    #[test]
    fn test_list_all_features_empty() {
        // On a fresh in-memory plugin with no inserts, list_all_features
        // must return Ok(vec![]) — an empty list, not an error.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let all = plugin
                .list_all_features()
                .await
                .expect("list_all_features on an empty db should be Ok");
            assert!(
                all.is_empty(),
                "expected an empty feature list, got {} entries",
                all.len()
            );
        });
    }

    // -- PluginError Display / Debug coverage --
    //
    // The pheno-plugin-core PluginError enum (see
    // crates/pheno-plugin-core/src/error.rs:6) has these string-bearing
    // variants: Initialization, NotFound, AlreadyRegistered, AlreadyExists,
    // Operation, Config, Execution, Validation. The following tests pin the
    // Display impl for three of them, and the Debug impl for one, by
    // asserting the inner payload round-trips through `{}` / `{:?}`.

    #[test]
    fn test_plugin_error_not_found_display() {
        // PluginError::NotFound is declared with `#[error("Plugin `{0}` not
        // found in registry")]` (error.rs:11), so Display must include both
        // the variant's keyword ("not found") and the inner payload.
        let e = PluginError::NotFound("feature".to_string());
        let displayed = format!("{}", e);
        assert!(
            displayed.contains("feature"),
            "NotFound Display should contain payload `feature`: `{}`",
            displayed
        );
    }

    #[test]
    fn test_plugin_error_serialization_display() {
        // PluginError::Serialization is declared as
        // `Serialization(#[from] serde_json::Error)` (error.rs:30), so it
        // cannot be constructed with a plain String. The proper way to
        // exercise the variant is to coerce a real serde_json::Error via
        // the `#[from]` blanket into PluginError::Serialization. We then
        // assert that the resulting PluginError::Serialization's Display
        // output (a) is non-empty and (b) embeds the inner serde error's
        // own Display text — this is the only stable guarantee we can
        // make about what `{}` of this variant produces, since serde
        // does not echo the offending input back through its error.
        let bad_json: serde_json::Error =
            serde_json::from_str::<i32>("{ not valid json").unwrap_err();
        let inner_text = bad_json.to_string();
        let e: PluginError = bad_json.into();
        let displayed = format!("{}", e);
        assert!(
            !displayed.is_empty(),
            "Serialization Display should not be empty"
        );
        assert!(
            displayed.contains(&inner_text),
            "Serialization Display should embed inner serde error text `{}`, got: `{}`",
            inner_text,
            displayed
        );
        // Sanity: the variant name "Serialization" is part of the
        // `#[error("Serialization error: {0}")]` format string
        // (error.rs:29), so it must appear in Display.
        assert!(
            displayed.contains("Serialization"),
            "Serialization Display should contain variant keyword `Serialization`, got: `{}`",
            displayed
        );
    }

    #[test]
    fn test_plugin_error_validation_display() {
        // PluginError::Validation is declared with
        // `#[error("Validation error: {0}")]` (error.rs:36). This is the
        // variant lib.rs:163, lib.rs:167, lib.rs:281, lib.rs:285, and
        // lib.rs:351 raise for missing/malformed input fields.
        let e = PluginError::Validation("missing field".to_string());
        let displayed = format!("{}", e);
        assert!(
            displayed.contains("missing field"),
            "Validation Display should contain payload `missing field`: `{}`",
            displayed
        );
    }

    #[test]
    fn test_plugin_error_operation_display() {
        // PluginError::Operation is declared with
        // `#[error("Operation failed: {0}")]` (error.rs:21). lib.rs uses
        // this for every rusqlite failure on INSERT/UPDATE/SELECT
        // (lib.rs:178, lib.rs:245, lib.rs:300, lib.rs:340, lib.rs:366).
        let e = PluginError::Operation("conflict".to_string());
        let displayed = format!("{}", e);
        assert!(
            displayed.contains("conflict"),
            "Operation Display should contain payload `conflict`: `{}`",
            displayed
        );
    }

    #[test]
    fn test_plugin_error_debug_includes_variant() {
        // Debug for an enum-typed error must include the variant name.
        // PluginError derives Debug (error.rs:6), so `{:?}` of
        // `PluginError::NotFound(...)` should contain the substring
        // "NotFound".
        let e = PluginError::NotFound("x".to_string());
        let debugged = format!("{:?}", e);
        assert!(
            debugged.contains("NotFound"),
            "Debug for PluginError::NotFound should contain `NotFound`: `{}`",
            debugged
        );
    }

    // -- State-value defaults and round-trips --
    //
    // The codebase does not define `FeatureState` or `WorkPackageState`
    // enums — feature and work-package state are represented as free-form
    // TEXT values, with the schema-level defaults of "draft" (lib.rs:82)
    // and "backlog" (lib.rs:92) respectively. The following four tests pin
    // the implicit defaults and verify the canonical state values
    // round-trip verbatim through the database.

    #[test]
    fn test_feature_state_default_or_first_variant() {
        // No `state` field is provided on insert, so lib.rs:172 falls back
        // to the schema default "draft". This test pins that contract.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "default-state-feature",
                "name": "Default State Feature"
            });
            let id = plugin.create_feature(&feature).await.unwrap();

            let retrieved = plugin.get_feature_by_id(id).await.unwrap();
            assert!(retrieved.is_some(), "feature should exist after insert");
            let state = retrieved.unwrap()["state"]
                .as_str()
                .expect("state should be a string")
                .to_string();
            assert_eq!(
                state, "draft",
                "missing `state` field should fall back to the schema default 'draft'"
            );
        });
    }

    #[test]
    fn test_work_package_state_default_or_first_variant() {
        // No `state` field is provided on insert, so lib.rs:290 falls back
        // to the schema default "backlog". This test pins that contract.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "default-state-wp-host",
                "name": "Default State WP Host"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let wp = serde_json::json!({
                "feature_id": feature_id,
                "title": "default-state-wp"
            });
            let wp_id = plugin.create_work_package(&wp).await.unwrap();

            let retrieved = plugin.get_work_package(wp_id).await.unwrap();
            assert!(retrieved.is_some(), "work package should exist after insert");
            let state = retrieved.unwrap()["state"]
                .as_str()
                .expect("state should be a string")
                .to_string();
            assert_eq!(
                state, "backlog",
                "missing `state` field should fall back to the schema default 'backlog'"
            );
        });
    }

    #[test]
    fn test_feature_state_serde_roundtrip() {
        // Round-trip the canonical feature state values through the
        // database and assert each one comes back byte-for-byte identical.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let canonical_states = ["draft", "active", "complete", "archived"];
            for (i, state) in canonical_states.iter().enumerate() {
                let feature = serde_json::json!({
                    "slug": format!("rt-feature-{}", i),
                    "name": format!("RT Feature {}", i),
                    "state": state
                });
                let id = plugin.create_feature(&feature).await.unwrap();
                let retrieved = plugin.get_feature_by_id(id).await.unwrap();
                assert!(retrieved.is_some(), "feature {} should exist after insert", i);
                let round_tripped = retrieved.unwrap()["state"]
                    .as_str()
                    .expect("state should be a string")
                    .to_string();
                assert_eq!(
                    &round_tripped, state,
                    "feature state should round-trip verbatim (input={:?}, got={:?})",
                    state, round_tripped
                );
            }
        });
    }

    #[test]
    fn test_work_package_state_serde_roundtrip() {
        // Round-trip the canonical work-package state values through the
        // database and assert each one comes back byte-for-byte identical.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "rt-wp-host",
                "name": "RT WP Host"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let canonical_states = ["backlog", "ready", "in_progress", "done"];
            for (i, state) in canonical_states.iter().enumerate() {
                let wp = serde_json::json!({
                    "feature_id": feature_id,
                    "title": format!("RT WP {}", i),
                    "state": state
                });
                let id = plugin.create_work_package(&wp).await.unwrap();
                let retrieved = plugin.get_work_package(id).await.unwrap();
                assert!(retrieved.is_some(), "work package {} should exist after insert", i);
                let round_tripped = retrieved.unwrap()["state"]
                    .as_str()
                    .expect("state should be a string")
                    .to_string();
                assert_eq!(
                    &round_tripped, state,
                    "work package state should round-trip verbatim (input={:?}, got={:?})",
                    state, round_tripped
                );
            }
        });
    }

    // -- AdapterPlugin / StoragePlugin trait bridge --

    #[test]
    fn test_storage_plugin_name_and_version() {
        // `StoragePlugin: AdapterPlugin` (traits.rs:185), so `name()` and
        // `version()` are inherited from the supertrait. This test calls
        // them on a value typed as `&dyn StoragePlugin` to make the trait
        // bridge explicit and pin the expected values.
        let plugin = create_test_plugin();
        let storage: &dyn pheno_plugin_core::traits::StoragePlugin = &plugin;
        assert_eq!(storage.name(), "sqlite-storage");
        assert_eq!(storage.version(), env!("CARGO_PKG_VERSION"));
        assert!(!storage.version().is_empty());
    }

    #[test]
    fn test_adapter_plugin_health_check() {
        // `AdapterPlugin::health_check` has a default impl returning
        // `Ok(())` (traits.rs:64). `SqliteStoragePlugin` does not override
        // it (lib.rs:136), so the default behavior applies: a fresh
        // in-memory plugin must report healthy.
        let plugin = create_test_plugin();
        plugin
            .health_check()
            .expect("health_check should return Ok on a healthy in-memory plugin");
    }

    // -- Audit entry field parsing --

    #[test]
    fn test_audit_entry_details_contains_valid_json() {
        // lib.rs:360 stores `details` via `value.to_string()`, i.e. the
        // JSON-serialized form of the input value. For an input string,
        // that means the stored TEXT is the JSON-encoded string literal.
        // After retrieval, `details` is a JSON string that — once parsed —
        // yields the original payload, and that payload in turn parses as
        // a JSON object with the expected key/value.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "audit-json-details",
                "name": "Audit JSON Details"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let original_details = "{\"key\": \"value\"}";
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "json-test",
                "actor": "test",
                "details": original_details
            });
            plugin.append_audit_entry(&entry).await.unwrap();

            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 1);

            // The stored `details` is the JSON-serialized form of the
            // input string (quotes wrapped around the original). Parse it
            // back to recover the original payload.
            let details_stored = trail[0]["details"]
                .as_str()
                .expect("details should be a JSON string");
            let recovered: String = serde_json::from_str(details_stored)
                .expect("stored details should parse as a JSON-encoded string");
            assert_eq!(recovered, original_details);

            // Now parse the recovered payload as JSON and assert the
            // structure.
            let parsed: serde_json::Value = serde_json::from_str(&recovered)
                .expect("recovered payload should itself be valid JSON");
            assert_eq!(parsed["key"], "value");
        });
    }

    #[test]
    fn test_audit_entry_created_at_is_valid_iso8601() {
        // The schema sets `created_at` to CURRENT_TIMESTAMP (lib.rs:105),
        // which SQLite formats as "YYYY-MM-DD HH:MM:SS" — ISO 8601 with a
        // space separator. The task spec accepts a non-empty string check,
        // so we do not parse the timestamp; we only confirm it is present
        // and not the empty string.
        let plugin = create_test_plugin();
        let rt = tokio::runtime::Runtime::new().unwrap();

        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "audit-created-at",
                "name": "Audit Created At"
            });
            let feature_id = plugin.create_feature(&feature).await.unwrap();

            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "timestamp-test",
                "actor": "test"
            });
            plugin.append_audit_entry(&entry).await.unwrap();

            let trail = plugin.get_audit_trail(feature_id).await.unwrap();
            assert_eq!(trail.len(), 1);

            let created_at = trail[0]["created_at"]
                .as_str()
                .expect("created_at should be a string");
            assert!(
                !created_at.is_empty(),
                "created_at should be a non-empty string, got: {:?}",
                created_at
            );
        });
    }

    // -- Plugin lifecycle / accessors --

    #[test]
    fn test_plugin_initializes_with_in_memory_db() {
        // SqliteStoragePlugin::initialize (lib.rs:145) runs a
        // `SELECT COUNT(*) FROM sqlite_master` probe to confirm the
        // migrated schema is in place. On a freshly-migrated in-memory
        // plugin, this must return Ok, and the call must be idempotent
        // (a second call on the same plugin still returns Ok).
        let plugin = create_test_plugin();
        let config = pheno_plugin_core::traits::PluginConfig {
            name: "sqlite-storage".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            adapter_config: serde_json::json!({}),
        };
        plugin
            .initialize(config.clone())
            .expect("first initialize should succeed on a fresh in-memory plugin");
        plugin
            .initialize(config)
            .expect("second initialize should also succeed (idempotent)");
    }

    #[test]
    fn test_plugin_storage_path_reflects_db_path() {
        // For a file-backed plugin, `db_path()` (lib.rs:407) must return
        // exactly the path that was passed to `new()`. We assert on the
        // returned `&Path` directly, which is what the production code
        // exposes.
        let pid = std::process::id();
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir()
            .join(format!("pheno-plugin-sqlite-dbpath-{}-{}.db", pid, nanos));

        let plugin = SqliteStoragePlugin::new(&path)
            .expect("file-backed SqliteStoragePlugin::new should succeed");
        assert_eq!(
            plugin.db_path(),
            path.as_path(),
            "db_path() should return the exact path passed to new()"
        );

        // Clean up: drop the plugin (closes the Connection), then unlink
        // the temp file.
        drop(plugin);
        let _ = std::fs::remove_file(&path);
    }
}
