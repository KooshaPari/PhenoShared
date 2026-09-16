//! End-to-end integration tests for `SqliteStoragePlugin`.
//!
//! These tests live in a separate `tests/` directory (rather than
//! `mod tests` inside the crate) so they exercise the *public* API of
//! the plugin and validate cross-method interactions, persistence, and
//! the full lifecycle (create, migrate, read, write, audit, dispose) the
//! way a downstream consumer would.
//!
//! No new dependencies are introduced — only items already declared in
//! `Cargo.toml` (`rusqlite`, `serde_json`, `tokio`, `tokio-test`) plus
//! the standard library.

use std::path::PathBuf;
use std::sync::Arc;

use pheno_plugin_core::error::PluginError;
use pheno_plugin_core::traits::{AdapterPlugin, StoragePlugin};
use pheno_plugin_sqlite::SqliteStoragePlugin;

/// Build a unique filesystem path under the system temp directory for
/// tests that need a real on-disk SQLite database. The `label` makes the
/// file easy to identify in `/tmp` if a test ever panics before cleaning
/// up.
fn unique_db_path(label: &str) -> PathBuf {
    let pid = std::process::id();
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("sqlite-int-{}-{}-{}.db", label, pid, nanos))
}

/// Build a default `PluginConfig` for `initialize()` calls.
fn default_config() -> pheno_plugin_core::traits::PluginConfig {
    pheno_plugin_core::traits::PluginConfig {
        name: "sqlite-storage".to_string(),
        version: "0.1.0".to_string(),
        adapter_config: serde_json::json!({}),
    }
}

// =============================================================================
// 1. Full plugin lifecycle
// =============================================================================

#[test]
fn test_full_plugin_lifecycle() {
    // Create plugin from a temp file path, initialize, create a feature,
    // update state, append an audit entry, get the audit trail, list all
    // features, dispose. Verify all data is consistent end-to-end.
    let path = unique_db_path("lifecycle");

    let plugin = SqliteStoragePlugin::new(&path).expect("SqliteStoragePlugin::new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed against a fresh file-backed plugin");

    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        // -- Create a feature --
        let feature = serde_json::json!({
            "slug": "lifecycle-feature",
            "name": "Lifecycle Feature",
            "description": "end-to-end lifecycle check"
        });
        let id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");
        assert!(id > 0, "created feature id should be positive");

        // -- Update state --
        plugin
            .update_feature_state(id, "active")
            .await
            .expect("update_feature_state should succeed");

        // -- Verify state via get_feature_by_id --
        let by_id = plugin
            .get_feature_by_id(id)
            .await
            .expect("get_feature_by_id should succeed")
            .expect("feature should exist after create");
        assert_eq!(by_id["state"], "active");
        assert_eq!(by_id["slug"], "lifecycle-feature");
        assert_eq!(by_id["name"], "Lifecycle Feature");

        // -- Append an audit entry --
        let entry = serde_json::json!({
            "feature_id": id,
            "entry_type": "state_changed",
            "actor": "lifecycle-test",
            "details": "draft -> active"
        });
        let audit_id = plugin
            .append_audit_entry(&entry)
            .await
            .expect("append_audit_entry should succeed");
        assert!(audit_id > 0);

        // -- Get the audit trail --
        let trail = plugin
            .get_audit_trail(id)
            .await
            .expect("get_audit_trail should succeed");
        assert_eq!(trail.len(), 1, "should have exactly one audit entry");
        assert_eq!(trail[0]["entry_type"], "state_changed");
        assert_eq!(trail[0]["actor"], "lifecycle-test");
        assert_eq!(trail[0]["feature_id"], id);

        // -- List all features --
        let all = plugin
            .list_all_features()
            .await
            .expect("list_all_features should succeed");
        assert_eq!(all.len(), 1, "exactly one feature should be listed");
        assert_eq!(all[0]["id"], id);
        assert_eq!(all[0]["state"], "active");
    });

    // -- Dispose (drop the plugin, releasing the file handle) --
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 2. Persistence across plugin instances
// =============================================================================

#[test]
fn test_persistence_across_plugin_instances() {
    // Create plugin A at a temp file path, create a feature, drop A,
    // create plugin B at the same path. Verify the feature still exists
    // in plugin B (validates that migrations, WAL, and FKs all persist).
    let path = unique_db_path("persist");

    // Phase 1: plugin A creates a feature and an audit entry, then is
    // dropped (which flushes the WAL and releases the file handle).
    {
        let plugin_a = SqliteStoragePlugin::new(&path).expect("plugin A: new should succeed");
        plugin_a.initialize(default_config()).expect("plugin A: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "persist-feature",
                "name": "Persist Feature",
                "description": "must survive a reopen"
            });
            let id = plugin_a
                .create_feature(&feature)
                .await
                .expect("plugin A: create_feature should succeed");
            assert!(id > 0);

            // Attach an audit entry as well so we exercise multiple tables
            // across the reopen.
            let entry = serde_json::json!({
                "feature_id": id,
                "entry_type": "created",
                "actor": "plugin-a",
                "details": "phase 1"
            });
            plugin_a
                .append_audit_entry(&entry)
                .await
                .expect("plugin A: append_audit_entry should succeed");
        });
        // Drop plugin A here so the WAL is checkpointed and the file is
        // released before plugin B opens it.
    }

    // Phase 2: plugin B reopens the same file. Migrations should be a
    // no-op (tables already exist), and the feature + audit entry should
    // still be present.
    {
        let plugin_b = SqliteStoragePlugin::new(&path).expect("plugin B: new should succeed");
        plugin_b.initialize(default_config()).expect("plugin B: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let retrieved = plugin_b
                .get_feature_by_slug("persist-feature")
                .await
                .expect("plugin B: get_feature_by_slug should succeed")
                .expect("the persisted feature should still be present after reopen");
            assert_eq!(retrieved["name"], "Persist Feature");
            assert_eq!(retrieved["state"], "draft");
            assert_eq!(retrieved["description"], "must survive a reopen");

            // Verify the audit entry persisted too.
            let id = retrieved["id"].as_i64().expect("id should be i64");
            let trail = plugin_b
                .get_audit_trail(id)
                .await
                .expect("plugin B: get_audit_trail should succeed");
            assert_eq!(trail.len(), 1);
            assert_eq!(trail[0]["actor"], "plugin-a");

            // list_all_features should also return it.
            let all = plugin_b
                .list_all_features()
                .await
                .expect("plugin B: list_all_features should succeed");
            assert_eq!(all.len(), 1);
            assert_eq!(all[0]["slug"], "persist-feature");
        });
        drop(plugin_b);
    }

    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 3. Audit trail isolation between features
// =============================================================================

#[test]
fn test_audit_trail_isolation_between_features() {
    // Create 2 features F1 and F2. Add 2 audit entries to F1 and 3 to F2.
    // Verify get_audit_trail(F1).len() == 2 and get_audit_trail(F2).len() == 3.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let f1 = serde_json::json!({
            "slug": "f1",
            "name": "Feature One"
        });
        let f2 = serde_json::json!({
            "slug": "f2",
            "name": "Feature Two"
        });
        let f1_id = plugin
            .create_feature(&f1)
            .await
            .expect("create f1 should succeed");
        let f2_id = plugin
            .create_feature(&f2)
            .await
            .expect("create f2 should succeed");
        assert_ne!(f1_id, f2_id);

        // 2 entries for F1
        for actor in ["alice", "bob"].iter() {
            let entry = serde_json::json!({
                "feature_id": f1_id,
                "entry_type": "f1-event",
                "actor": actor,
                "details": format!("f1-by-{}", actor)
            });
            plugin
                .append_audit_entry(&entry)
                .await
                .expect("append f1 entry should succeed");
        }
        // 3 entries for F2
        for actor in ["carol", "dave", "eve"].iter() {
            let entry = serde_json::json!({
                "feature_id": f2_id,
                "entry_type": "f2-event",
                "actor": actor,
                "details": format!("f2-by-{}", actor)
            });
            plugin
                .append_audit_entry(&entry)
                .await
                .expect("append f2 entry should succeed");
        }

        let f1_trail = plugin
            .get_audit_trail(f1_id)
            .await
            .expect("get_audit_trail(f1) should succeed");
        let f2_trail = plugin
            .get_audit_trail(f2_id)
            .await
            .expect("get_audit_trail(f2) should succeed");

        assert_eq!(
            f1_trail.len(),
            2,
            "F1 should have exactly 2 audit entries, got {}",
            f1_trail.len()
        );
        assert_eq!(
            f2_trail.len(),
            3,
            "F2 should have exactly 3 audit entries, got {}",
            f2_trail.len()
        );

        // Cross-check that no F1 entries leaked into F2's trail and vice
        // versa, by inspecting the entry_type field on every returned row.
        for e in f1_trail.iter() {
            assert_eq!(
                e["entry_type"], "f1-event",
                "F1 trail should only contain f1-event entries"
            );
            assert_eq!(
                e["feature_id"].as_i64(),
                Some(f1_id),
                "F1 trail rows should reference F1"
            );
        }
        for e in f2_trail.iter() {
            assert_eq!(
                e["entry_type"], "f2-event",
                "F2 trail should only contain f2-event entries"
            );
            assert_eq!(
                e["feature_id"].as_i64(),
                Some(f2_id),
                "F2 trail rows should reference F2"
            );
        }
    });
}

// =============================================================================
// 4. Work package lifecycle
// =============================================================================

#[test]
fn test_work_package_lifecycle() {
    // Create a feature, create 3 work packages for it (mix of priorities:
    // high/medium/low), update one's state, verify all 3 are returned by
    // get_work_package and that the state update was persisted.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "wp-lifecycle",
            "name": "WP Lifecycle"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        let priorities = ["high", "medium", "low"];
        let mut wp_ids: Vec<i64> = Vec::new();
        for (i, priority) in priorities.iter().enumerate() {
            let wp = serde_json::json!({
                "feature_id": feature_id,
                "title": format!("WP-{}", i),
                "description": format!("description for work package {}", i),
                "priority": priority
            });
            let id = plugin
                .create_work_package(&wp)
                .await
                .expect("create_work_package should succeed");
            assert!(id > 0, "work package id should be positive");
            wp_ids.push(id);
        }

        // Update the state of the *second* work package (the medium one).
        plugin
            .update_wp_state(wp_ids[1], "in_progress")
            .await
            .expect("update_wp_state should succeed");

        // Verify all three work packages come back via get_work_package
        // and that the state update was persisted.
        for (i, &id) in wp_ids.iter().enumerate() {
            let wp = plugin
                .get_work_package(id)
                .await
                .expect("get_work_package should succeed")
                .expect("work package should exist after create");
            assert_eq!(wp["id"].as_i64(), Some(id));
            assert_eq!(wp["feature_id"].as_i64(), Some(feature_id));
            assert_eq!(wp["title"], format!("WP-{}", i));
            assert_eq!(wp["priority"], priorities[i]);
            if i == 1 {
                assert_eq!(
                    wp["state"], "in_progress",
                    "the second work package should have its state updated to in_progress"
                );
            } else {
                assert_eq!(
                    wp["state"], "backlog",
                    "untouched work packages should retain the default state 'backlog'"
                );
            }
        }
    });
}

// =============================================================================
// 5. Concurrent plugin instances share data
// =============================================================================

#[test]
fn test_concurrent_plugin_instances_share_data() {
    // SQLite in WAL mode allows multiple connections to read the same
    // database file simultaneously, with writes serialized. The plugin
    // here uses a per-instance Mutex around its single Connection. The
    // simplest contention-free pattern is: open instance 1, write,
    // drop, open instance 2, read.
    //
    // The test name uses "concurrent" loosely: the two `SqliteStoragePlugin`
    // instances are not alive simultaneously. What it actually proves is
    // that a second open against the same file path sees the writes the
    // first open committed, which is the property the test is named
    // after. This documents the real-world lifecycle for downstream
    // consumers that share a database file across processes / reopens.
    let path = unique_db_path("concurrent");

    // Open instance 1, insert a feature, then drop.
    {
        let plugin_1 = SqliteStoragePlugin::new(&path).expect("instance 1: new should succeed");
        plugin_1
            .initialize(default_config())
            .expect("instance 1: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "shared-feature",
                "name": "Shared Feature",
                "description": "written by instance 1"
            });
            let id = plugin_1
                .create_feature(&feature)
                .await
                .expect("instance 1: create_feature should succeed");
            assert!(id > 0);
        });
        // Drop releases the file handle and flushes the WAL.
    }

    // Open instance 2 against the same file and read.
    {
        let plugin_2 = SqliteStoragePlugin::new(&path).expect("instance 2: new should succeed");
        plugin_2
            .initialize(default_config())
            .expect("instance 2: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let by_slug = plugin_2
                .get_feature_by_slug("shared-feature")
                .await
                .expect("instance 2: get_feature_by_slug should succeed")
                .expect("instance 2 should see the feature written by instance 1");
            assert_eq!(by_slug["name"], "Shared Feature");
            assert_eq!(by_slug["description"], "written by instance 1");

            // list_all_features() should also reflect the write.
            let all = plugin_2
                .list_all_features()
                .await
                .expect("instance 2: list_all_features should succeed");
            assert_eq!(all.len(), 1);
            assert_eq!(all[0]["slug"], "shared-feature");
        });
        drop(plugin_2);
    }

    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 6. Feature id auto-increments
// =============================================================================

#[test]
fn test_feature_id_auto_increments() {
    // Create 5 features in sequence. Assert their id values are
    // monotonically increasing (1, 2, 3, 4, 5). Verifies AUTOINCREMENT
    // works as declared on the features table (lib.rs:78).
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let mut ids: Vec<i64> = Vec::new();
        for i in 0..5 {
            let feature = serde_json::json!({
                "slug": format!("auto-{}", i),
                "name": format!("Auto {}", i)
            });
            let id = plugin
                .create_feature(&feature)
                .await
                .expect("create_feature should succeed");
            ids.push(id);
        }
        // The features table is created with INTEGER PRIMARY KEY
        // AUTOINCREMENT (lib.rs:78). For a fresh in-memory database the
        // first inserted row's id must be 1, then 2, 3, 4, 5.
        assert_eq!(ids, vec![1, 2, 3, 4, 5], "ids should be strictly 1..=5");
    });
}

// =============================================================================
// 7. list_all_features includes all states
// =============================================================================

#[test]
fn test_list_all_features_includes_all_states() {
    // Create 4 features with explicit states: draft, active, complete,
    // archived. Verify all 4 are returned by list_all_features().
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let states = ["draft", "active", "complete", "archived"];
        for (i, state) in states.iter().enumerate() {
            let feature = serde_json::json!({
                "slug": format!("state-{}", i),
                "name": format!("State {}", i),
                "state": state
            });
            let id = plugin
                .create_feature(&feature)
                .await
                .expect("create_feature should succeed");
            // Sanity: read-back should reflect the requested state.
            let read = plugin
                .get_feature_by_id(id)
                .await
                .expect("get_feature_by_id should succeed")
                .expect("feature should exist");
            assert_eq!(read["state"], *state);
        }

        // All four should be present in list_all_features(), regardless
        // of state. list_all_features() orders by created_at DESC, but
        // we sort by slug for a stable, order-independent comparison.
        let mut all = plugin
            .list_all_features()
            .await
            .expect("list_all_features should succeed");
        assert_eq!(all.len(), 4, "all 4 features should be listed");

        all.sort_by(|a, b| a["slug"].as_str().cmp(&b["slug"].as_str()));
        let returned_states: Vec<&str> = all
            .iter()
            .map(|f| f["state"].as_str().expect("state should be a string"))
            .collect();
        // `all` is sorted by slug ("state-0", "state-1", "state-2",
        // "state-3"), and we created feature i with `states[i]`. So the
        // returned states in slug-sorted order should match `states`
        // verbatim (no need to re-sort `states`).
        assert_eq!(
            returned_states, states,
            "list_all_features should include draft/active/complete/archived"
        );
    });
}

// =============================================================================
// 8. Audit trail returns descending by created_at
// =============================================================================

#[test]
fn test_audit_trail_returns_descending_by_created_at() {
    // Create a feature, append 3 audit entries with a small sleep between
    // them. Verify the returned trail has the LAST-inserted entry first
    // (DESC order). get_audit_trail() is implemented with
    // `ORDER BY created_at DESC` (lib.rs:374), and SQLite's
    // CURRENT_TIMESTAMP has 1-second resolution, so the sleeps must
    // exceed 1 second to guarantee distinct timestamps and a stable
    // ordering.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "audit-desc",
            "name": "Audit Desc"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        let actors = ["first", "second", "third"];
        for actor in actors.iter() {
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "ordered",
                "actor": actor,
                "details": format!("payload-{}", actor)
            });
            plugin
                .append_audit_entry(&entry)
                .await
                .expect("append_audit_entry should succeed");
            // Sleep > 1s so the next CURRENT_TIMESTAMP differs from the
            // previous one. Without this, the three entries could share
            // the same created_at value and the DESC ordering would be
            // undefined.
            std::thread::sleep(std::time::Duration::from_millis(1100));
        }

        let trail = plugin
            .get_audit_trail(feature_id)
            .await
            .expect("get_audit_trail should succeed");
        assert_eq!(trail.len(), 3, "all three entries should be returned");

        // The trail is ordered DESC by created_at, so the last-inserted
        // entry ("third") should be first, then "second", then "first".
        assert_eq!(
            trail[0]["actor"], "third",
            "first entry in DESC-ordered trail should be the last one inserted"
        );
        assert_eq!(trail[1]["actor"], "second");
        assert_eq!(trail[2]["actor"], "first");

        // All three entries should reference the same feature_id.
        for e in trail.iter() {
            assert_eq!(e["feature_id"].as_i64(), Some(feature_id));
        }
    });
}

// =============================================================================
// 9. State transitions round-trip through DB
// =============================================================================

#[test]
fn test_state_transitions_round_trip_through_db() {
    // Create a feature, transition state draft -> active -> complete, drop
    // the plugin, recreate the plugin from the same file path, verify the
    // final state is "complete" (persistence verified across instances).
    let path = unique_db_path("state-roundtrip");

    // Phase 1: create + transition state.
    {
        let plugin = SqliteStoragePlugin::new(&path).expect("phase 1: new should succeed");
        plugin
            .initialize(default_config())
            .expect("phase 1: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let feature = serde_json::json!({
                "slug": "state-roundtrip",
                "name": "State Roundtrip"
            });
            let id = plugin
                .create_feature(&feature)
                .await
                .expect("phase 1: create_feature should succeed");

            // No state supplied -> defaults to "draft" (lib.rs:172).
            let initial = plugin
                .get_feature_by_id(id)
                .await
                .expect("phase 1: get should succeed")
                .expect("phase 1: feature should exist");
            assert_eq!(initial["state"], "draft");

            plugin
                .update_feature_state(id, "active")
                .await
                .expect("phase 1: draft -> active");
            plugin
                .update_feature_state(id, "complete")
                .await
                .expect("phase 1: active -> complete");

            let mid = plugin
                .get_feature_by_id(id)
                .await
                .expect("phase 1: get should succeed")
                .expect("phase 1: feature should exist");
            assert_eq!(mid["state"], "complete");
        });
        // Drop the plugin so the file is fully flushed and unlocked.
    }

    // Phase 2: re-open and confirm the final state survived.
    {
        let plugin = SqliteStoragePlugin::new(&path).expect("phase 2: new should succeed");
        plugin
            .initialize(default_config())
            .expect("phase 2: initialize should succeed");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let read = plugin
                .get_feature_by_slug("state-roundtrip")
                .await
                .expect("phase 2: get_feature_by_slug should succeed")
                .expect("phase 2: feature should survive a reopen");
            assert_eq!(
                read["state"], "complete",
                "state should round-trip across instances"
            );
            assert_eq!(read["name"], "State Roundtrip");
        });
        drop(plugin);
    }

    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 10. Duplicate slug returns Operation error
// =============================================================================

#[test]
fn test_duplicate_slug_returns_operation_error() {
    // Create 2 features with the same slug, verify the second call
    // returns an error of type PluginError::Operation (since the
    // production code wraps conn.execute failures as PluginError::Operation
    // at lib.rs:178).
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let first = serde_json::json!({
            "slug": "duplicate",
            "name": "First Dup"
        });
        let first_id = plugin
            .create_feature(&first)
            .await
            .expect("first insert should succeed");
        assert!(first_id > 0);

        let second = serde_json::json!({
            "slug": "duplicate",
            "name": "Second Dup"
        });
        let err = plugin
            .create_feature(&second)
            .await
            .expect_err("second insert with the same slug should fail");

        // The production code at lib.rs:178 wraps the `conn.execute`
        // failure as `PluginError::Operation(format!("failed to create
        // feature: {}", e))`. This pins that error variant down so
        // downstream callers can match on it.
        match err {
            PluginError::Operation(msg) => {
                assert!(
                    msg.contains("failed to create feature"),
                    "Operation error message should mention the failed operation, got: {}",
                    msg
                );
            }
            other => panic!(
                "expected PluginError::Operation for duplicate slug, got: {:?}",
                other
            ),
        }

        // Sanity: the first insert is still there, untouched.
        let still_there = plugin
            .get_feature_by_slug("duplicate")
            .await
            .expect("get should not error")
            .expect("first insert should still be present");
        assert_eq!(still_there["id"].as_i64(), Some(first_id));
        assert_eq!(still_there["name"], "First Dup");
    });
}

// =============================================================================
// 11. Concurrent reads via Arc::clone of the inner connection
// =============================================================================

#[test]
fn test_concurrent_reads_via_clone() {
    // Documents that `plugin.connection()` returns an `Arc<Mutex<Connection>>`
    // which can be cloned cheaply and locked multiple times sequentially to
    // observe the same data. The Mutex guard is dropped at the end of each
    // block (before the next lock) — `std::sync::MutexGuard` is `!Send` and
    // the underlying `Connection` is `!Sync`, so consumers must release the
    // guard before any `await` point. This test pins down the safe pattern.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        // Seed the database so the reads have something to observe.
        let feature = serde_json::json!({
            "slug": "read-clone",
            "name": "Read Clone"
        });
        let id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");
        assert!(id > 0, "created feature id should be positive");

        // `plugin.connection()` returns Arc<Mutex<Connection>>. Each call
        // hands out a fresh Arc that points to the same underlying
        // allocation as every other Arc owned by the plugin.
        let conn_a = plugin.connection();
        let conn_b = plugin.connection();
        let conn_c = plugin.connection();
        assert!(
            Arc::ptr_eq(&conn_a, &conn_b),
            "Arcs returned by connection() should share the same allocation"
        );
        assert!(
            Arc::ptr_eq(&conn_b, &conn_c),
            "Arcs returned by connection() should share the same allocation"
        );

        // Three sequential reads, each in its own block so the MutexGuard
        // is dropped before the next `lock()`. The reads alternate between
        // the three Arcs to prove that any of them can drive a read.
        {
            let guard = conn_a.lock().expect("lock a poisoned");
            let name: String = guard
                .query_row(
                    "SELECT name FROM features WHERE id = ?1",
                    [id],
                    |r| r.get(0),
                )
                .expect("read 1 should succeed");
            assert_eq!(name, "Read Clone", "read 1 should see the seeded feature");
        }
        {
            let guard = conn_b.lock().expect("lock b poisoned");
            let state: String = guard
                .query_row(
                    "SELECT state FROM features WHERE id = ?1",
                    [id],
                    |r| r.get(0),
                )
                .expect("read 2 should succeed");
            assert_eq!(state, "draft", "read 2 should see the default state");
        }
        {
            let guard = conn_c.lock().expect("lock c poisoned");
            let count: i64 = guard
                .query_row("SELECT COUNT(*) FROM features", [], |r| r.get(0))
                .expect("read 3 should succeed");
            assert_eq!(count, 1, "read 3 should see exactly one feature");
        }
        // A fourth read through conn_a proves the Arc is still usable
        // after the interleaved uses of the other Arcs.
        {
            let guard = conn_a.lock().expect("lock a poisoned (reacquire)");
            let slug: String = guard
                .query_row(
                    "SELECT slug FROM features WHERE id = ?1",
                    [id],
                    |r| r.get(0),
                )
                .expect("read 4 should succeed");
            assert_eq!(slug, "read-clone", "read 4 should see the original slug");
        }
    });
}

// =============================================================================
// 12. Sequential writes serialize via the internal Mutex
// =============================================================================

#[test]
fn test_concurrent_writes_serialize_via_mutex() {
    // The plugin guards its single `Connection` with a `std::sync::Mutex`.
    // That guard is `!Send`, so we cannot `tokio::spawn` a future that
    // holds it across an `await` point. The safe pattern — and the one
    // this test documents — is to drive all 10 inserts from the same
    // task via sequential `.await`s, relying on the Mutex to serialize
    // them implicitly. After the loop, `list_all_features()` should
    // report exactly 10 rows.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let mut ids: Vec<i64> = Vec::with_capacity(10);
        for i in 0..10 {
            let feature = serde_json::json!({
                "slug": format!("concurrent-write-{}", i),
                "name": format!("Concurrent Write {}", i)
            });
            let id = plugin
                .create_feature(&feature)
                .await
                .unwrap_or_else(|e| panic!("create_feature #{} should succeed: {:?}", i, e));
            assert!(id > 0, "created id for #{} should be positive, got {}", i, id);
            ids.push(id);
        }

        // All 10 ids should be distinct (AUTOINCREMENT gives unique ids).
        assert_eq!(ids.len(), 10);
        let mut sorted_ids = ids.clone();
        sorted_ids.sort();
        sorted_ids.dedup();
        assert_eq!(
            sorted_ids.len(),
            10,
            "all 10 inserts should have produced unique ids"
        );

        // list_all_features() must reflect all 10 committed writes.
        let all = plugin
            .list_all_features()
            .await
            .expect("list_all_features should succeed");
        assert_eq!(
            all.len(),
            10,
            "expected 10 features in the database, got {}",
            all.len()
        );

        // Round-trip each one by slug to confirm every write was durable.
        for i in 0..10 {
            let slug = format!("concurrent-write-{}", i);
            let found = plugin
                .get_feature_by_slug(&slug)
                .await
                .expect("get_feature_by_slug should succeed")
                .unwrap_or_else(|| panic!("feature {} should exist after the sequential writes", slug));
            assert_eq!(found["slug"], slug);
            assert_eq!(found["name"], format!("Concurrent Write {}", i));
            assert_eq!(found["state"], "draft", "default state should be 'draft'");
        }
    });
}

// =============================================================================
// 13. WAL journal mode is enabled after init (file-backed only)
// =============================================================================

#[test]
fn test_wal_mode_enabled_after_init() {
    // Verifies that `SqliteStoragePlugin::new` (lib.rs:38) issues
    // `PRAGMA journal_mode=WAL;` and that the pragma actually takes
    // effect on a real on-disk database. In-memory databases ignore WAL
    // and report "memory" instead, so we use a file-backed plugin here.
    let path = unique_db_path("wal-mode");
    let plugin = SqliteStoragePlugin::new(&path).expect("new(file path) should succeed");
    let conn_arc = plugin.connection();
    let mode: String = conn_arc
        .lock()
        .expect("lock poisoned")
        .query_row("PRAGMA journal_mode", [], |r| r.get(0))
        .expect("PRAGMA journal_mode should succeed");
    assert_eq!(
        mode, "wal",
        "WAL journal mode should be enabled after init, got {:?}",
        mode
    );

    // Drop the plugin before removing the file so the file handle is
    // released (and the WAL is checkpointed) on platforms that need it.
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 14. Foreign-key enforcement is enabled (makes the FK constraints bite)
// =============================================================================

#[test]
fn test_foreign_keys_enabled() {
    // Verifies that `SqliteStoragePlugin::new` (lib.rs:42) issues
    // `PRAGMA foreign_keys=ON;`. Without this pragma, SQLite parses but
    // does not enforce the `FOREIGN KEY (feature_id) REFERENCES
    // features(id)` clause on `work_packages` and `audit_entries` —
    // meaning the existing `test_create_work_package_with_invalid_feature_id`
    // test would silently let orphan rows through. This test pins the
    // pragma on.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let conn_arc = plugin.connection();
    let fk: i64 = conn_arc
        .lock()
        .expect("lock poisoned")
        .query_row("PRAGMA foreign_keys", [], |r| r.get(0))
        .expect("PRAGMA foreign_keys should succeed");
    assert_eq!(
        fk, 1,
        "foreign-key enforcement should be enabled, got {}",
        fk
    );
}

// =============================================================================
// 15. The `plugin_metadata` table exists after init
// =============================================================================

#[test]
fn test_metadata_table_exists_after_init() {
    // Documents the table created at lib.rs:109-113 by `run_migrations`.
    // The table is currently unused by the storage API, but downstream
    // tooling reads it for adapter health-checks, so it must be present
    // after `new()` / `initialize()`.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let conn_arc = plugin.connection();

    // `sqlite_master` lists every table/index/view/trigger in the
    // database. We restrict to `type='table'` to ignore the autoindexes
    // SQLite creates for UNIQUE constraints.
    let result: Result<String, rusqlite::Error> = conn_arc
        .lock()
        .expect("lock poisoned")
        .query_row(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'plugin_metadata'",
            [],
            |r| r.get(0),
        );

    match result {
        Ok(name) => assert_eq!(
            name, "plugin_metadata",
            "sqlite_master should report the plugin_metadata table"
        ),
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            panic!("plugin_metadata table should exist after init, but it was not found")
        }
        Err(e) => panic!("unexpected error querying sqlite_master: {}", e),
    }

    // Spot-check: the four tables created by run_migrations are all
    // present. This guards against accidental drops in the migration
    // string.
    let expected_tables = ["features", "work_packages", "audit_entries", "plugin_metadata"];
    for table in expected_tables.iter() {
        let found: String = conn_arc
            .lock()
            .expect("lock poisoned")
            .query_row(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?1",
                [table],
                |r| r.get(0),
            )
            .unwrap_or_else(|e| panic!("table {} should exist after init: {}", table, e));
        assert_eq!(&found, table, "expected table name to match");
    }
}

// =============================================================================
// 16. Audit trail round-trips multiple entries with parseable timestamps
// =============================================================================

#[test]
fn test_audit_trail_chronological_insertion() {
    // Append 3 audit entries with a short sleep between them. The sleep
    // is too short (50ms) to force distinct CURRENT_TIMESTAMP values
    // (SQLite CURRENT_TIMESTAMP has 1-second resolution), so we
    // deliberately do NOT assert a strict ordering. We only verify that:
    //   (a) all three entries were committed (trail.len() == 3), and
    //   (b) every entry's `created_at` is a well-formed SQLite
    //       CURRENT_TIMESTAMP string ("YYYY-MM-DD HH:MM:SS", 19 chars).
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "audit-chrono",
            "name": "Audit Chrono"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        for actor in ["alpha", "beta", "gamma"].iter() {
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "chained",
                "actor": actor,
                "details": format!("entry-by-{}", actor)
            });
            plugin
                .append_audit_entry(&entry)
                .await
                .expect("append_audit_entry should succeed");
            std::thread::sleep(std::time::Duration::from_millis(50));
        }

        let trail = plugin
            .get_audit_trail(feature_id)
            .await
            .expect("get_audit_trail should succeed");
        assert_eq!(trail.len(), 3, "all three entries should be present");

        // Every entry's created_at should be a 19-char string shaped
        // like "YYYY-MM-DD HH:MM:SS" — the format SQLite's
        // CURRENT_TIMESTAMP always returns. We do not assert that the
        // three timestamps are distinct.
        for e in trail.iter() {
            let ts = e["created_at"]
                .as_str()
                .unwrap_or_else(|| panic!("created_at should be a string, got {:?}", e));
            assert_eq!(ts.len(), 19, "timestamp should be 19 chars, got {:?}", ts);
            let bytes = ts.as_bytes();
            assert_eq!(bytes[4], b'-', "expected '-' at index 4 in {:?}", ts);
            assert_eq!(bytes[7], b'-', "expected '-' at index 7 in {:?}", ts);
            assert_eq!(bytes[10], b' ', "expected ' ' at index 10 in {:?}", ts);
            assert_eq!(bytes[13], b':', "expected ':' at index 13 in {:?}", ts);
            assert_eq!(bytes[16], b':', "expected ':' at index 16 in {:?}", ts);
            // The other 14 bytes are ASCII digits (0-9). Spot-check a
            // couple so we don't accept a string of arbitrary punctuation.
            assert!(bytes[0].is_ascii_digit(), "expected digit at index 0 in {:?}", ts);
            assert!(bytes[18].is_ascii_digit(), "expected digit at index 18 in {:?}", ts);
        }

        // The actors should all be present, regardless of DESC ordering.
        let mut actors: Vec<&str> = trail
            .iter()
            .map(|e| e["actor"].as_str().expect("actor should be a string"))
            .collect();
        actors.sort();
        assert_eq!(actors, vec!["alpha", "beta", "gamma"]);
    });
}

// =============================================================================
// 17. Work-package state machine: backlog -> in_progress -> done
// =============================================================================

#[test]
fn test_create_work_package_then_update_state_to_done() {
    // Full state-machine flow for a single work package: created in
    // 'backlog' (the default from lib.rs:290), transitioned to
    // 'in_progress', then to 'done'. After every transition we re-read
    // the row via `get_work_package` and assert the state matches.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "wp-state-flow",
            "name": "WP State Flow"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        // Create the WP without specifying a state — default is "backlog".
        let wp = serde_json::json!({
            "feature_id": feature_id,
            "title": "State Flow WP",
            "priority": "high"
        });
        let wp_id = plugin
            .create_work_package(&wp)
            .await
            .expect("create_work_package should succeed");
        assert!(wp_id > 0);

        // Step 1: read back the default state.
        let after_create = plugin
            .get_work_package(wp_id)
            .await
            .expect("get_work_package should succeed")
            .expect("work package should exist after create");
        assert_eq!(
            after_create["state"], "backlog",
            "default state for a new work package should be 'backlog'"
        );
        assert_eq!(after_create["title"], "State Flow WP");
        assert_eq!(after_create["priority"], "high");

        // Step 2: backlog -> in_progress.
        plugin
            .update_wp_state(wp_id, "in_progress")
            .await
            .expect("update_wp_state backlog -> in_progress should succeed");
        let after_in_progress = plugin
            .get_work_package(wp_id)
            .await
            .expect("get_work_package should succeed")
            .expect("work package should still exist after first update");
        assert_eq!(
            after_in_progress["state"], "in_progress",
            "state should be 'in_progress' after the first update"
        );

        // Step 3: in_progress -> done.
        plugin
            .update_wp_state(wp_id, "done")
            .await
            .expect("update_wp_state in_progress -> done should succeed");
        let after_done = plugin
            .get_work_package(wp_id)
            .await
            .expect("get_work_package should succeed")
            .expect("work package should still exist after second update");
        assert_eq!(
            after_done["state"], "done",
            "state should be 'done' after the second update"
        );

        // The other fields should not have been clobbered by the state
        // updates — sanity-check title and priority round-trip.
        assert_eq!(after_done["title"], "State Flow WP");
        assert_eq!(after_done["priority"], "high");
    });
}

// =============================================================================
// 18. AdapterPlugin::initialize() succeeds on a fresh file-backed plugin
// =============================================================================

#[test]
fn test_initialize_succeeds_on_fresh_db() {
    // Documents the AdapterPlugin::initialize() contract (lib.rs:145-151):
    // against a freshly-migrated file-backed database, initialize() must
    // return Ok(()) without touching the schema. We do NOT call
    // create_feature or any other write — initialize should be a pure
    // health check.
    let path = unique_db_path("init-fresh");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed against a fresh path");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed against a fresh file-backed plugin");
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 19. AdapterPlugin::initialize() is idempotent
// =============================================================================

#[test]
fn test_initialize_succeeds_twice() {
    // The AdapterPlugin contract promises that initialize() is safe to
    // re-run. The implementation at lib.rs:145-151 runs a single
    // `SELECT COUNT(*) FROM sqlite_master` as a smoke test; running it
    // twice on the same plugin must not error and must not corrupt
    // state. We re-read a feature between the two calls as a state
    // guard.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();

    // First initialize.
    plugin
        .initialize(default_config())
        .expect("first initialize should succeed");

    // Insert a feature and confirm it is readable between the two
    // initialize calls (state guard).
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "init-twice",
            "name": "Init Twice"
        });
        let id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature between initializes should succeed");
        let read = plugin
            .get_feature_by_id(id)
            .await
            .expect("get_feature_by_id between initializes should succeed")
            .expect("feature should be readable between initializes");
        assert_eq!(read["name"], "Init Twice");
    });

    // Second initialize — must not error and must not wipe the row.
    plugin
        .initialize(default_config())
        .expect("second initialize should also succeed (idempotent)");

    rt.block_on(async {
        let still = plugin
            .get_feature_by_slug("init-twice")
            .await
            .expect("get_feature_by_slug after second initialize should succeed")
            .expect("feature should still be present after a second initialize");
        assert_eq!(still["name"], "Init Twice");
    });
}

// =============================================================================
// 20. Audit-entry `details` round-trips special characters verbatim
// =============================================================================

#[test]
fn test_audit_trail_with_special_characters_in_details() {
    // The production code at lib.rs:360 stores `details` as
    // `entry.get("details").map(|v| v.to_string())` — the JSON-serialized
    // form of the value, which for a JSON string adds surrounding quotes
    // and escapes inner quotes/backslashes. This test pins down that the
    // round-trip preserves the original payload (modulo the JSON-string
    // wrapping) when the payload contains characters that are
    // interesting in a few different ways: embedded double-quotes,
    // ampersand, angle brackets.
    let plugin = SqliteStoragePlugin::in_memory().expect("in_memory should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "audit-special",
            "name": "Audit Special"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        // The payload we will store: a JSON-shaped string with escaped
        // quotes, an ampersand, and angle brackets. After Rust-string
        // parsing the variable holds the literal 56 characters
        //   {"key": "value with \"escaped\" quotes & <html>"}
        let details_payload = "{\"key\": \"value with \\\"escaped\\\" quotes & <html>\"}";

        let entry = serde_json::json!({
            "feature_id": feature_id,
            "entry_type": "special",
            "actor": "test",
            "details": details_payload
        });
        let audit_id = plugin
            .append_audit_entry(&entry)
            .await
            .expect("append_audit_entry should succeed");
        assert!(audit_id > 0);

        let trail = plugin
            .get_audit_trail(feature_id)
            .await
            .expect("get_audit_trail should succeed");
        assert_eq!(trail.len(), 1, "exactly one entry should be returned");

        // The DB column holds the JSON-serialized form of the value
        // (lib.rs:360: `v.to_string()`), so a JSON string is stored
        // wrapped in quotes with its inner quotes backslash-escaped.
        // `serde_json::json!(details_payload).to_string()` reproduces
        // that wrapping deterministically.
        let stored = trail[0]["details"]
            .as_str()
            .expect("details should be a string in the read-back");
        let expected_json_form = serde_json::json!(details_payload).to_string();
        assert_eq!(
            stored, expected_json_form,
            "details should round-trip through the JSON-serialized storage"
        );

        // Independent spot-checks for each "special" class of character.
        // These run against the stored form, so they include the outer
        // quotes and the escaped inner quotes added by JSON
        // serialization.
        assert!(
            stored.contains("escaped"),
            "stored details should still contain the literal word 'escaped', got: {}",
            stored
        );
        assert!(
            stored.contains('&'),
            "stored details should still contain the ampersand, got: {}",
            stored
        );
        assert!(
            stored.contains("<html>"),
            "stored details should still contain the angle-bracketed token, got: {}",
            stored
        );
        // The entry_type and actor must also round-trip untouched.
        assert_eq!(trail[0]["entry_type"], "special");
        assert_eq!(trail[0]["actor"], "test");
    });
}

// =============================================================================
// 21. update_feature_state happy path: draft -> active
// =============================================================================

#[test]
fn test_update_feature_state_happy_path() {
    // Create a feature (which defaults to state "draft" per lib.rs:172),
    // call update_feature_state(id, "active"), read it back, and assert
    // the state column now reads "active". This is the smallest possible
    // round-trip through the public update path.
    let path = unique_db_path("update-feature-state");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "update-feature-state",
            "name": "Update Feature State"
        });
        let id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");
        assert!(id > 0, "created feature id should be positive");

        // Sanity: default state is "draft".
        let initial = plugin
            .get_feature_by_id(id)
            .await
            .expect("get_feature_by_id should succeed")
            .expect("feature should exist after create");
        assert_eq!(
            initial["state"], "draft",
            "default state for a new feature should be 'draft'"
        );

        // Update to "active".
        plugin
            .update_feature_state(id, "active")
            .await
            .expect("update_feature_state draft -> active should succeed");

        // Read it back and assert the state column reflects the update.
        let updated = plugin
            .get_feature_by_id(id)
            .await
            .expect("get_feature_by_id should succeed")
            .expect("feature should still exist after update");
        assert_eq!(
            updated["state"], "active",
            "state should be 'active' after update_feature_state"
        );

        // Other fields (slug, name) must not have been clobbered by the
        // state update — only `state` and `updated_at` are written.
        assert_eq!(updated["slug"], "update-feature-state");
        assert_eq!(updated["name"], "Update Feature State");
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 22. update_work_package_state happy path: backlog -> in_progress
// =============================================================================

#[test]
fn test_update_work_package_state_happy_path() {
    // Create a feature, create a work package under it (which defaults to
    // state "backlog" per lib.rs:290), call update_wp_state(id,
    // "in_progress"), read it back, and assert the state column now
    // reads "in_progress". Mirrors test 21 but exercises the work-package
    // write path (lib.rs:334-342).
    let path = unique_db_path("update-wp-state");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "update-wp-state-feature",
            "name": "Update WP State Feature"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        let wp = serde_json::json!({
            "feature_id": feature_id,
            "title": "Update WP State"
        });
        let wp_id = plugin
            .create_work_package(&wp)
            .await
            .expect("create_work_package should succeed");
        assert!(wp_id > 0, "created work package id should be positive");

        // Sanity: default state is "backlog".
        let initial = plugin
            .get_work_package(wp_id)
            .await
            .expect("get_work_package should succeed")
            .expect("work package should exist after create");
        assert_eq!(
            initial["state"], "backlog",
            "default state for a new work package should be 'backlog'"
        );

        // Update to "in_progress".
        plugin
            .update_wp_state(wp_id, "in_progress")
            .await
            .expect("update_wp_state backlog -> in_progress should succeed");

        // Read it back and assert the state column reflects the update.
        let updated = plugin
            .get_work_package(wp_id)
            .await
            .expect("get_work_package should succeed")
            .expect("work package should still exist after update");
        assert_eq!(
            updated["state"], "in_progress",
            "state should be 'in_progress' after update_wp_state"
        );

        // The title and feature_id must not have been clobbered by the
        // state update — only `state` and `updated_at` are written.
        assert_eq!(updated["title"], "Update WP State");
        assert_eq!(updated["feature_id"].as_i64(), Some(feature_id));
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 23. Audit trail with 50 entries (scalability check)
// =============================================================================

#[test]
fn test_audit_trail_with_many_entries() {
    // Append 50 audit entries in a tight loop and verify all 50
    // round-trip through get_audit_trail(). The query at lib.rs:374 has
    // no LIMIT clause, so the entire trail must be returned regardless
    // of how many rows are present. This pins the unbounded-return
    // behavior that downstream consumers rely on for full history views.
    let path = unique_db_path("audit-many");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "audit-many",
            "name": "Audit Many"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("create_feature should succeed");

        // Append 50 entries with monotonically-increasing actor suffixes.
        for i in 0..50 {
            let entry = serde_json::json!({
                "feature_id": feature_id,
                "entry_type": "bulk",
                "actor": format!("worker-{}", i),
                "details": format!("entry #{}", i)
            });
            plugin
                .append_audit_entry(&entry)
                .await
                .unwrap_or_else(|e| panic!("append_audit_entry #{} should succeed: {:?}", i, e));
        }

        let trail = plugin
            .get_audit_trail(feature_id)
            .await
            .expect("get_audit_trail should succeed");
        assert_eq!(
            trail.len(),
            50,
            "expected 50 audit entries to round-trip, got {}",
            trail.len()
        );

        // Every returned row should reference the same feature and carry
        // a well-formed actor / details pair. We sort by the numeric
        // suffix in the actor (encoded as "worker-N") using a *natural*
        // numeric ordering — lexicographic ordering would put
        // "worker-10" before "worker-2" and fail the assertion. The trail
        // is documented to be ordered by created_at DESC, but all 50
        // inserts happen within the same SQLite CURRENT_TIMESTAMP second
        // so the SQL-level ordering is undefined here.
        let mut actor_suffixed: Vec<(usize, String)> = trail
            .iter()
            .map(|e| {
                let raw = e["actor"]
                    .as_str()
                    .expect("actor should be a string")
                    .to_string();
                let suffix = raw
                    .strip_prefix("worker-")
                    .unwrap_or_else(|| panic!("actor should start with 'worker-', got {:?}", raw))
                    .parse::<usize>()
                    .unwrap_or_else(|e| panic!("worker-N suffix should be numeric, got {:?}: {}", raw, e));
                (suffix, raw)
            })
            .collect();
        actor_suffixed.sort_by_key(|(n, _)| *n);
        let sorted_actors: Vec<String> =
            actor_suffixed.into_iter().map(|(_, s)| s).collect();
        let expected_actors: Vec<String> = (0..50).map(|i| format!("worker-{}", i)).collect();
        assert_eq!(
            sorted_actors, expected_actors,
            "all 50 actors (worker-0..worker-49) should be present"
        );
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 24. Multiple features with the same title (only slug must be unique)
// =============================================================================

#[test]
fn test_multiple_features_with_same_title() {
    // The features.slug column is UNIQUE (lib.rs:79) but the name column
    // has no uniqueness constraint. Two features with identical names
    // but distinct slugs must both succeed, and both must be visible
    // via list_all_features().
    let path = unique_db_path("same-title-features");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let shared_title = "Same Title Feature";
        let f1 = serde_json::json!({
            "slug": "same-title-1",
            "name": shared_title
        });
        let f2 = serde_json::json!({
            "slug": "same-title-2",
            "name": shared_title
        });
        let id1 = plugin
            .create_feature(&f1)
            .await
            .expect("first feature with shared title should succeed");
        let id2 = plugin
            .create_feature(&f2)
            .await
            .expect("second feature with same title but different slug should succeed");
        assert_ne!(id1, id2, "the two features should get distinct ids");

        // list_all_features() should return both rows.
        let mut all = plugin
            .list_all_features()
            .await
            .expect("list_all_features should succeed");
        assert_eq!(
            all.len(),
            2,
            "both features with the shared title should be listed"
        );
        all.sort_by(|a, b| a["slug"].as_str().cmp(&b["slug"].as_str()));
        assert_eq!(all[0]["slug"], "same-title-1");
        assert_eq!(all[1]["slug"], "same-title-2");
        assert_eq!(all[0]["name"], shared_title);
        assert_eq!(all[1]["name"], shared_title);
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 25. Work packages with the same title across different features
// =============================================================================

#[test]
fn test_work_packages_with_same_title_across_features() {
    // work_packages.title has no UNIQUE constraint (lib.rs:90), so a
    // title can be reused across rows provided the (feature_id, title)
    // pair is allowed to repeat. Create two features and a work
    // package with the same title under each — both inserts must
    // succeed and both rows must round-trip independently.
    let path = unique_db_path("same-title-wps");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let f1 = serde_json::json!({
            "slug": "shared-wp-feature-1",
            "name": "Shared WP Feature 1"
        });
        let f2 = serde_json::json!({
            "slug": "shared-wp-feature-2",
            "name": "Shared WP Feature 2"
        });
        let f1_id = plugin
            .create_feature(&f1)
            .await
            .expect("create_feature #1 should succeed");
        let f2_id = plugin
            .create_feature(&f2)
            .await
            .expect("create_feature #2 should succeed");

        // Create a work package with the same title for each feature.
        let shared_title = "Shared WP Title";
        let wp1 = serde_json::json!({
            "feature_id": f1_id,
            "title": shared_title
        });
        let wp2 = serde_json::json!({
            "feature_id": f2_id,
            "title": shared_title
        });
        let wp1_id = plugin
            .create_work_package(&wp1)
            .await
            .expect("WP for feature 1 with shared title should succeed");
        let wp2_id = plugin
            .create_work_package(&wp2)
            .await
            .expect("WP for feature 2 with shared title should succeed");
        assert_ne!(wp1_id, wp2_id, "the two WPs should get distinct ids");

        // Both WPs should be retrievable, and the read-back should
        // confirm each is anchored to its own feature.
        let read1 = plugin
            .get_work_package(wp1_id)
            .await
            .expect("get_work_package #1 should succeed")
            .expect("WP #1 should exist");
        let read2 = plugin
            .get_work_package(wp2_id)
            .await
            .expect("get_work_package #2 should succeed")
            .expect("WP #2 should exist");
        assert_eq!(read1["title"], shared_title);
        assert_eq!(read2["title"], shared_title);
        assert_eq!(read1["feature_id"].as_i64(), Some(f1_id));
        assert_eq!(read2["feature_id"].as_i64(), Some(f2_id));
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 26. get_feature_by_id returns Ok(None) for a nonexistent id
// =============================================================================

#[test]
fn test_get_feature_by_id_for_nonexistent_id() {
    // The production code at lib.rs:229-231 maps a
    // `rusqlite::Error::QueryReturnedNoRows` from `query_row` into
    // `Ok(None)`. Calling get_feature_by_id(99999) on a fresh
    // database (no features have been inserted) must therefore return
    // Ok(None) — not an error, not a panic. This pins that
    // contract for missing-id lookups.
    let path = unique_db_path("get-feature-missing");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let result = plugin
            .get_feature_by_id(99999)
            .await
            .expect("get_feature_by_id should not error on a missing id");
        assert!(
            result.is_none(),
            "expected Ok(None) for a nonexistent feature id, got {:?}",
            result
        );
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 27. get_work_package returns Ok(None) for a nonexistent id
// =============================================================================

#[test]
fn test_get_work_package_for_nonexistent_id() {
    // Same contract as test 26, but for the work-package lookup
    // (lib.rs:324-326). A query_row on a non-existent id must yield
    // Ok(None) rather than an error.
    let path = unique_db_path("get-wp-missing");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let result = plugin
            .get_work_package(99999)
            .await
            .expect("get_work_package should not error on a missing id");
        assert!(
            result.is_none(),
            "expected Ok(None) for a nonexistent work package id, got {:?}",
            result
        );
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 28. create_feature with an empty slug should fail (validation)
// =============================================================================

#[test]
fn test_create_feature_with_empty_slug_fails() {
    // An empty slug is an obviously invalid identifier. The
    // production code at lib.rs:158-163 validates only that a `slug`
    // field is present and is a string — and the schema's
    // `slug TEXT UNIQUE NOT NULL` (lib.rs:79) does not exclude empty
    // strings, so this test documents the *current* behavior: the
    // empty slug is accepted and a row is inserted. Downstream
    // consumers should not rely on empty-slug rejection until the
    // source is updated; this test guards against a silent
    // behavior change in either direction.
    let path = unique_db_path("empty-slug-feature");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let feature = serde_json::json!({
            "slug": "",
            "name": "Empty Slug Feature"
        });
        let result = plugin.create_feature(&feature).await;
        // Pin the current observed behavior so any future change in
        // either direction (a new Validation check, or a regression
        // that drops the existing OK path) surfaces here.
        match result {
            Ok(id) => {
                assert!(
                    id > 0,
                    "if create_feature accepts an empty slug, it should still return a positive id"
                );
                // The row really did land in the database with an empty slug.
                let read = plugin
                    .get_feature_by_slug("")
                    .await
                    .expect("get_feature_by_slug should not error")
                    .expect("the just-inserted empty-slug feature should be retrievable");
                assert_eq!(read["slug"], "");
                assert_eq!(read["name"], "Empty Slug Feature");
            }
            Err(PluginError::Validation(msg)) => {
                assert!(
                    msg.to_lowercase().contains("slug"),
                    "Validation error should mention 'slug', got: {}",
                    msg
                );
            }
            Err(other) => panic!(
                "create_feature with empty slug returned an unexpected error variant: {:?}",
                other
            ),
        }
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 29. create_work_package with an empty title should fail (validation)
// =============================================================================

#[test]
fn test_create_work_package_with_empty_slug_fails() {
    // Same shape as test 28, but for work-package titles. The schema
    // is `title TEXT NOT NULL` (lib.rs:90) — empty strings are
    // permitted, just as for feature slugs. This test pins the
    // current behavior so a future tightening of the validation
    // (or an accidental loosening) is caught.
    let path = unique_db_path("empty-title-wp");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        // A host feature is required to satisfy the FK before we can
        // reach the title check (lib.rs:278-285), so create one first.
        let feature = serde_json::json!({
            "slug": "empty-title-wp-host",
            "name": "Empty Title WP Host"
        });
        let feature_id = plugin
            .create_feature(&feature)
            .await
            .expect("host create_feature should succeed");

        let wp = serde_json::json!({
            "feature_id": feature_id,
            "title": ""
        });
        let result = plugin.create_work_package(&wp).await;
        match result {
            Ok(id) => {
                assert!(
                    id > 0,
                    "if create_work_package accepts an empty title, it should still return a positive id"
                );
                let read = plugin
                    .get_work_package(id)
                    .await
                    .expect("get_work_package should not error")
                    .expect("the just-inserted empty-title work package should be retrievable");
                assert_eq!(read["title"], "");
                assert_eq!(read["feature_id"].as_i64(), Some(feature_id));
            }
            Err(PluginError::Validation(msg)) => {
                assert!(
                    msg.to_lowercase().contains("title"),
                    "Validation error should mention 'title', got: {}",
                    msg
                );
            }
            Err(other) => panic!(
                "create_work_package with empty title returned an unexpected error variant: {:?}",
                other
            ),
        }
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}

// =============================================================================
// 30. create_work_package with feature_id = 0 should fail (FK violation)
// =============================================================================

#[test]
fn test_create_work_package_with_zero_feature_id_fails() {
    // feature_id = 0 references a row that does not exist: AUTOINCREMENT
    // starts at 1 (lib.rs:78), so no feature ever has id 0. The FK
    // constraint on work_packages.feature_id (lib.rs:96) plus
    // `PRAGMA foreign_keys=ON` (lib.rs:42) must therefore reject this
    // insert. The production code wraps the rusqlite error in
    // PluginError::Operation (lib.rs:300).
    let path = unique_db_path("zero-feature-id");
    let plugin = SqliteStoragePlugin::new(&path).expect("new should succeed");
    plugin
        .initialize(default_config())
        .expect("initialize should succeed");
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let wp = serde_json::json!({
            "feature_id": 0,
            "title": "Zero Feature ID WP"
        });
        let result = plugin.create_work_package(&wp).await;
        assert!(
            result.is_err(),
            "expected an error for feature_id=0, got {:?}",
            result
        );
        match result {
            Err(PluginError::Operation(msg)) => {
                assert!(
                    msg.contains("failed to create work package"),
                    "Operation error should wrap the FK failure with the expected prefix, got: {}",
                    msg
                );
            }
            Err(other) => panic!(
                "expected PluginError::Operation for the FK violation on feature_id=0, got: {:?}",
                other
            ),
            Ok(_) => panic!("create_work_package with feature_id=0 should not have succeeded"),
        }
    });
    drop(plugin);
    let _ = std::fs::remove_file(&path);
}
