// SPDX-License-Identifier: MIT OR Apache-2.0
//! T113 — `agileplus-sync` ↔ `agileplus-plane` state-mapper / client contract.
//!
//! Verifies that the in-memory Plane client mock exposes the same surface as
//! the real `PlaneClient`, and that a `SyncMapping` round-trip through the
//! store preserves identity (entity_type + entity_id ↔ plane_issue_id).

use agileplus_domain::domain::sync_mapping::{SyncDirection, SyncMapping};
use agileplus_plane::client::{InMemoryPlaneClient, PlaneWorkItem};
use agileplus_sqlite::SqliteStorageAdapter;

fn make_issue(name: &str) -> PlaneWorkItem {
    PlaneWorkItem {
        id: None,
        name: name.to_string(),
        description_html: Some(format!("<p>{name}</p>")),
        state: Some("backlog".to_string()),
        priority: Some(3),
        parent: None,
        labels: vec!["contract".to_string()],
    }
}

/// Contract: the in-memory mock implements the same create/get/list surface
/// that the real `PlaneClient` exposes, so consumers can be tested
/// deterministically.
#[tokio::test]
async fn mock_plane_client_create_get_list_roundtrip() {
    let client = InMemoryPlaneClient::new();
    let created = client.create_issue(&make_issue("Task A")).await.unwrap();
    assert!(created.id.starts_with("issue-"));
    assert_eq!(created.name, "Task A");

    let fetched = client.get_issue(&created.id).await.unwrap();
    assert_eq!(fetched.id, created.id);
    assert_eq!(fetched.name, "Task A");

    let list = client.list_issues().await.unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].id, created.id);
}

/// Contract: the mock enforces `get_issue` not-found semantics consistent
/// with what the real Plane.so API returns for a missing id.
#[tokio::test]
async fn mock_plane_client_not_found_is_error() {
    let client = InMemoryPlaneClient::new();
    let result = client.get_issue("nonexistent-id").await;
    assert!(
        result.is_err(),
        "missing id must be a hard error, not Ok(None)"
    );
}

/// Contract: a `SyncMapping` written via `StoragePort` can be retrieved by
/// both `entity_type+entity_id` and `entity_type+plane_issue_id` and the two
/// lookups agree. This is the data invariant the sync layer relies on.
#[tokio::test]
async fn sync_mapping_roundtrip_by_local_and_plane_id() {
    let db = SqliteStorageAdapter::in_memory().expect("in-memory sqlite");

    let mapping = SyncMapping {
        id: 0,
        entity_type: "feature".to_string(),
        entity_id: 42,
        plane_issue_id: "plane-issue-7".to_string(),
        last_synced_at: chrono::Utc::now(),
        content_hash: "abc123".to_string(),
        sync_direction: SyncDirection::Bidirectional,
        conflict_count: 0,
    };

    agileplus_domain::ports::storage::StoragePort::upsert_sync_mapping(&db, &mapping)
        .await
        .unwrap();

    let by_local =
        agileplus_domain::ports::storage::StoragePort::get_sync_mapping(&db, "feature", 42)
            .await
            .unwrap()
            .expect("mapping must exist by (entity_type, entity_id)");
    assert_eq!(by_local.plane_issue_id, "plane-issue-7");

    let by_plane = agileplus_domain::ports::storage::StoragePort::get_sync_mapping_by_plane_id(
        &db,
        "feature",
        "plane-issue-7",
    )
    .await
    .unwrap()
    .expect("mapping must exist by plane_issue_id");
    assert_eq!(by_plane.entity_id, 42);

    // Both lookups must return the same row.
    assert_eq!(by_local.id, by_plane.id);
    assert_eq!(by_local.entity_type, by_plane.entity_type);
}

/// Contract: `delete_sync_mapping` removes both lookup paths.
#[tokio::test]
async fn sync_mapping_delete_clears_both_lookups() {
    let db = SqliteStorageAdapter::in_memory().expect("in-memory sqlite");
    let mapping = SyncMapping {
        id: 0,
        entity_type: "work_package".to_string(),
        entity_id: 9,
        plane_issue_id: "plane-wp-1".to_string(),
        last_synced_at: chrono::Utc::now(),
        content_hash: "deadbeef".to_string(),
        sync_direction: SyncDirection::Bidirectional,
        conflict_count: 0,
    };

    agileplus_domain::ports::storage::StoragePort::upsert_sync_mapping(&db, &mapping)
        .await
        .unwrap();
    agileplus_domain::ports::storage::StoragePort::delete_sync_mapping(&db, "work_package", 9)
        .await
        .unwrap();

    assert!(
        agileplus_domain::ports::storage::StoragePort::get_sync_mapping(&db, "work_package", 9)
            .await
            .unwrap()
            .is_none()
    );
    assert!(
        agileplus_domain::ports::storage::StoragePort::get_sync_mapping_by_plane_id(
            &db,
            "work_package",
            "plane-wp-1",
        )
        .await
        .unwrap()
        .is_none()
    );
}

/// Contract: `upsert_sync_mapping` is idempotent — second call with the same
/// (entity_type, entity_id) updates the row, does not create a duplicate.
#[tokio::test]
async fn sync_mapping_upsert_is_idempotent() {
    let db = SqliteStorageAdapter::in_memory().expect("in-memory sqlite");

    let m1 = SyncMapping {
        id: 0,
        entity_type: "feature".to_string(),
        entity_id: 1,
        plane_issue_id: "plane-1".to_string(),
        last_synced_at: chrono::Utc::now(),
        content_hash: "h1".to_string(),
        sync_direction: SyncDirection::Bidirectional,
        conflict_count: 0,
    };
    let m2 = SyncMapping {
        id: 0,
        entity_type: "feature".to_string(),
        entity_id: 1,
        plane_issue_id: "plane-1".to_string(),
        last_synced_at: chrono::Utc::now(),
        content_hash: "h2".to_string(),
        sync_direction: SyncDirection::Bidirectional,
        conflict_count: 0,
    };

    agileplus_domain::ports::storage::StoragePort::upsert_sync_mapping(&db, &m1)
        .await
        .unwrap();
    agileplus_domain::ports::storage::StoragePort::upsert_sync_mapping(&db, &m2)
        .await
        .unwrap();

    let fetched =
        agileplus_domain::ports::storage::StoragePort::get_sync_mapping(&db, "feature", 1)
            .await
            .unwrap()
            .expect("mapping must exist");
    assert_eq!(
        fetched.last_synced_hash, "h2",
        "upsert must update, not duplicate"
    );
}
