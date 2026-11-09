// SPDX-License-Identifier: MIT OR Apache-2.0

//! In-memory test doubles for [`SearchPort`] and [`SkillStoragePort`].
//!
//! These are the canonical doubles used in unit tests across the workspace.
//! They are always compiled (not behind `#[cfg(test)]`) so dependant crates
//! can use them in their own tests without re-implementing.

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

use async_trait::async_trait;
use serde_json::json;

use crate::{
    SearchDocument, SearchPortError, SearchResults, SkillEntry, SkillStoragePort,
    StoragePortError,
};
use crate::SearchPort;

// ── InMemorySearchStore ────────────────────────────────────────────────────

type IndexStore = HashMap<String, HashMap<String, SearchDocument>>;

/// In-memory [`SearchPort`] double.
///
/// Thread-safe. Suitable for unit tests and integration harnesses that
/// do not want a real Meilisearch instance.
#[derive(Clone, Default)]
pub struct InMemorySearchStore {
    inner: Arc<Mutex<IndexStore>>,
}

impl InMemorySearchStore {
    pub fn new() -> Self {
        Self::default()
    }
}

#[async_trait]
impl SearchPort for InMemorySearchStore {
    async fn ensure_index(
        &self,
        index: &str,
        _primary_key: &str,
    ) -> Result<(), SearchPortError> {
        let mut guard = self.inner.lock().await;
        guard.entry(index.to_string()).or_default();
        Ok(())
    }

    async fn index_documents(
        &self,
        index: &str,
        documents: Vec<SearchDocument>,
    ) -> Result<(), SearchPortError> {
        let mut guard = self.inner.lock().await;
        let store = guard.entry(index.to_string()).or_default();
        for doc in documents {
            store.insert(doc.id.clone(), doc);
        }
        Ok(())
    }

    async fn search(
        &self,
        index: &str,
        query: &str,
    ) -> Result<SearchResults, SearchPortError> {
        let guard = self.inner.lock().await;
        let hits: Vec<serde_json::Value> = guard
            .get(index)
            .map(|store| {
                store
                    .values()
                    // naive substring match — good enough for test doubles
                    .filter(|doc| {
                        doc.id.contains(query)
                            || doc.fields.to_string().contains(query)
                    })
                    .map(|doc| json!({"id": doc.id, "fields": doc.fields}))
                    .collect()
            })
            .unwrap_or_default();

        let count = hits.len() as u64;
        Ok(SearchResults {
            hits,
            estimated_total_hits: count,
            processing_time_ms: 0,
            query: query.to_string(),
        })
    }

    async fn delete_document(
        &self,
        index: &str,
        id: &str,
    ) -> Result<(), SearchPortError> {
        let mut guard = self.inner.lock().await;
        if let Some(store) = guard.get_mut(index) {
            store.remove(id);
        }
        Ok(())
    }
}

// ── InMemorySkillStore ─────────────────────────────────────────────────────

/// In-memory [`SkillStoragePort`] double.
///
/// Thread-safe. Suitable for unit tests that do not require a real SurrealDB
/// connection.
#[derive(Clone, Default)]
pub struct InMemorySkillStore {
    inner: Arc<Mutex<HashMap<String, SkillEntry>>>,
}

impl InMemorySkillStore {
    pub fn new() -> Self {
        Self::default()
    }
}

#[async_trait]
impl SkillStoragePort for InMemorySkillStore {
    async fn put(&self, entry: SkillEntry) -> Result<SkillEntry, StoragePortError> {
        let mut guard = self.inner.lock().await;
        guard.insert(entry.id.clone(), entry.clone());
        Ok(entry)
    }

    async fn get(&self, id: &str) -> Result<SkillEntry, StoragePortError> {
        let guard = self.inner.lock().await;
        guard
            .get(id)
            .cloned()
            .ok_or_else(|| StoragePortError::NotFound(id.to_string()))
    }

    async fn list(&self) -> Result<Vec<SkillEntry>, StoragePortError> {
        let guard = self.inner.lock().await;
        Ok(guard.values().cloned().collect())
    }

    async fn delete(&self, id: &str) -> Result<(), StoragePortError> {
        let mut guard = self.inner.lock().await;
        guard.remove(id);
        Ok(())
    }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{SearchDocument, SkillEntry};
    use serde_json::json;

    // ── SearchPort double tests ────────────────────────────────────────────

    #[tokio::test]
    async fn search_double_ensure_index_is_idempotent() {
        let store = InMemorySearchStore::new();
        store.ensure_index("skills", "id").await.unwrap();
        store.ensure_index("skills", "id").await.unwrap(); // idempotent
    }

    #[tokio::test]
    async fn search_double_index_and_retrieve_round_trip() {
        let store = InMemorySearchStore::new();
        store.ensure_index("skills", "id").await.unwrap();

        let doc = SearchDocument {
            id: "skill:greet".to_string(),
            fields: json!({ "name": "greet", "lang": "rust" }),
        };
        store
            .index_documents("skills", vec![doc.clone()])
            .await
            .unwrap();

        let results = store.search("skills", "greet").await.unwrap();
        assert_eq!(results.estimated_total_hits, 1);
        assert!(results.hits[0]["id"] == "skill:greet");
    }

    #[tokio::test]
    async fn search_double_delete_removes_document() {
        let store = InMemorySearchStore::new();
        store.ensure_index("idx", "id").await.unwrap();

        let doc = SearchDocument {
            id: "doc:1".to_string(),
            fields: json!({ "content": "hello" }),
        };
        store.index_documents("idx", vec![doc]).await.unwrap();
        store.delete_document("idx", "doc:1").await.unwrap();

        let results = store.search("idx", "hello").await.unwrap();
        assert_eq!(results.estimated_total_hits, 0);
    }

    #[tokio::test]
    async fn search_double_query_no_match_returns_empty() {
        let store = InMemorySearchStore::new();
        store.ensure_index("idx", "id").await.unwrap();
        let results = store.search("idx", "nonexistent").await.unwrap();
        assert!(results.hits.is_empty());
    }

    /// Object-safety smoke test: `Box<dyn SearchPort>` must compile.
    #[tokio::test]
    async fn search_double_is_object_safe() {
        let store: Box<dyn SearchPort> = Box::new(InMemorySearchStore::new());
        store.ensure_index("test", "id").await.unwrap();
    }

    // ── SkillStoragePort double tests ──────────────────────────────────────

    fn make_entry(id: &str) -> SkillEntry {
        SkillEntry {
            id: id.to_string(),
            name: id.to_string(),
            version: "1.0.0".to_string(),
            code: "fn main() {}".to_string(),
            runtime: "wasm".to_string(),
            metadata: json!({}),
        }
    }

    #[tokio::test]
    async fn skill_store_put_and_get_round_trip() {
        let store = InMemorySkillStore::new();
        let entry = make_entry("skill:greet");
        let stored = store.put(entry.clone()).await.unwrap();
        assert_eq!(stored, entry);

        let fetched = store.get("skill:greet").await.unwrap();
        assert_eq!(fetched, entry);
    }

    #[tokio::test]
    async fn skill_store_list_returns_all() {
        let store = InMemorySkillStore::new();
        store.put(make_entry("skill:a")).await.unwrap();
        store.put(make_entry("skill:b")).await.unwrap();
        let all = store.list().await.unwrap();
        assert_eq!(all.len(), 2);
    }

    #[tokio::test]
    async fn skill_store_delete_removes_entry() {
        let store = InMemorySkillStore::new();
        store.put(make_entry("skill:x")).await.unwrap();
        store.delete("skill:x").await.unwrap();
        let err = store.get("skill:x").await.unwrap_err();
        assert!(matches!(err, StoragePortError::NotFound(_)));
    }

    #[tokio::test]
    async fn skill_store_get_missing_returns_not_found() {
        let store = InMemorySkillStore::new();
        let err = store.get("missing").await.unwrap_err();
        assert!(matches!(err, StoragePortError::NotFound(_)));
    }

    #[tokio::test]
    async fn skill_store_put_replaces_existing() {
        let store = InMemorySkillStore::new();
        store.put(make_entry("skill:z")).await.unwrap();
        let updated = SkillEntry {
            version: "2.0.0".to_string(),
            ..make_entry("skill:z")
        };
        store.put(updated.clone()).await.unwrap();
        let fetched = store.get("skill:z").await.unwrap();
        assert_eq!(fetched.version, "2.0.0");
    }

    /// Object-safety smoke test: `Box<dyn SkillStoragePort>` must compile.
    #[tokio::test]
    async fn skill_store_is_object_safe() {
        let store: Box<dyn SkillStoragePort> = Box::new(InMemorySkillStore::new());
        let _ = store.list().await.unwrap();
    }
}
