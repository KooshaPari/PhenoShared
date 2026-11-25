// SPDX-License-Identifier: MIT OR Apache-2.0

//! Qdrant SearchPort adapter for PhenoMCP.
//!
//! Qdrant is a high-performance vector search engine (Apache-2.0, self-hosted).
//!
//! # SearchPort mapping
//!
//! Qdrant is a *vector* store; `SearchPort` is a *keyword* port.  The adapter
//! bridges them as follows:
//!
//! | `SearchPort` method     | Qdrant REST call                                      |
//! |-------------------------|-------------------------------------------------------|
//! | `ensure_index`          | `PUT /collections/{index}` (vector_size=1, no-op if exists) |
//! | `index_documents`       | `PUT /collections/{index}/points` (zero-vector + payload) |
//! | `search`                | `POST /collections/{index}/points/scroll` (payload filter `$text` match) |
//! | `delete_document`       | `POST /collections/{index}/points/delete` (by id filter) |
//!
//! Because Qdrant does not have a native full-text search API in all versions,
//! the `search` implementation uses the **scroll + payload `match.text`** filter
//! (available since Qdrant 1.1).  The adapter builds the correct JSON request
//! body; the mapping logic is unit-tested without a live server.

use async_trait::async_trait;
use pheno_ports::{SearchDocument, SearchPort, SearchPortError, SearchResults};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::{debug, info};

// ── Qdrant-private error type ──────────────────────────────────────────────

/// Errors produced by the low-level Qdrant REST helpers.
#[derive(Error, Debug)]
pub enum QdrantError {
    #[error("HTTP error: {0}")]
    Http(String),

    #[error("not found: {0}")]
    NotFound(String),

    #[error("collection error: {0}")]
    Collection(String),

    #[error("parse error: {0}")]
    Parse(String),
}

// ── Wire types ─────────────────────────────────────────────────────────────

/// A vector point stored in Qdrant.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Point {
    pub id: String,
    pub vector: Vec<f32>,
    pub payload: HashMap<String, serde_json::Value>,
}

/// A single hit returned by vector search.
#[derive(Debug, Clone, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub score: f32,
    pub payload: HashMap<String, serde_json::Value>,
}

// ── Response shapes ────────────────────────────────────────────────────────

/// Qdrant scroll response envelope.
#[derive(Debug, Deserialize)]
struct ScrollResponse {
    result: ScrollResult,
}

#[derive(Debug, Deserialize)]
struct ScrollResult {
    points: Vec<ScrollPoint>,
}

/// A single point returned by the Qdrant scroll API.
#[derive(Debug, Deserialize)]
pub struct ScrollPoint {
    pub id: serde_json::Value,
    pub payload: Option<HashMap<String, serde_json::Value>>,
}

// ── Request body builders (public for unit testing) ────────────────────────

/// Build the JSON body for `PUT /collections/{index}`.
///
/// We use `vector_size = 1` because we store documents as keyword payloads;
/// vectors are not semantically used.  If the collection already exists Qdrant
/// returns 200 OK (idempotent).
pub fn build_create_collection_body() -> serde_json::Value {
    serde_json::json!({
        "vectors": {
            "size": 1,
            "distance": "Dot"
        },
        "on_disk_payload": false
    })
}

/// Build the JSON body for `PUT /collections/{index}/points`.
///
/// Each `SearchDocument` is stored as a Qdrant point with a zero-vector `[0.0]`
/// and the document's fields serialised into the payload.  The document `id`
/// is stored both as the point id and as `_pheno_id` inside the payload so
/// that it survives a scroll filter round-trip.
pub fn build_upsert_body(documents: &[SearchDocument]) -> serde_json::Value {
    let points: Vec<serde_json::Value> = documents
        .iter()
        .map(|doc| {
            let mut payload: HashMap<String, serde_json::Value> = HashMap::new();
            // Merge the document's flattened fields into the payload.
            if let serde_json::Value::Object(map) = &doc.fields {
                for (k, v) in map {
                    payload.insert(k.clone(), v.clone());
                }
            }
            // Always store the canonical id inside the payload for retrieval.
            payload.insert(
                "_pheno_id".to_string(),
                serde_json::Value::String(doc.id.clone()),
            );
            serde_json::json!({
                "id": doc.id,
                "vector": [0.0_f32],
                "payload": payload
            })
        })
        .collect();
    serde_json::json!({ "points": points })
}

/// Build the JSON body for `POST /collections/{index}/points/scroll`.
///
/// We use a `match.text` payload filter against all string fields (Qdrant ≥ 1.1).
/// Because Qdrant's text filter checks a specific field, we emit a `should` clause
/// that checks every text payload key as well as the generic `_pheno_id` field.
/// Callers can specify additional field names; by default the adapter checks
/// `name`, `content`, `text`, and `_pheno_id`.
pub fn build_scroll_body(query: &str) -> serde_json::Value {
    // Build a `should` filter that matches the query string against common text fields.
    let text_fields = ["name", "content", "text", "_pheno_id"];
    let should: Vec<serde_json::Value> = text_fields
        .iter()
        .map(|field| {
            serde_json::json!({
                "key": field,
                "match": { "text": query }
            })
        })
        .collect();

    serde_json::json!({
        "filter": {
            "should": should
        },
        "with_payload": true,
        "limit": 256
    })
}

/// Build the JSON body for `POST /collections/{index}/points/delete`.
pub fn build_delete_body(id: &str) -> serde_json::Value {
    serde_json::json!({
        "filter": {
            "must": [
                {
                    "key": "_pheno_id",
                    "match": { "value": id }
                }
            ]
        }
    })
}

// ── QdrantClient ───────────────────────────────────────────────────────────

/// Thin REST client for Qdrant.
///
/// Implements [`SearchPort`] so that MCPServer can consume this adapter
/// polymorphically as `Box<dyn SearchPort>`.
pub struct QdrantClient {
    http: Client,
    url: String,
    api_key: Option<String>,
}

impl QdrantClient {
    /// Create a new Qdrant client.
    ///
    /// # Arguments
    /// - `url` — base URL of the Qdrant instance (e.g. `http://localhost:6333`)
    /// - `api_key` — optional Qdrant API key (for cloud / auth-enabled instances)
    pub fn new(url: &str, api_key: Option<&str>) -> Self {
        Self {
            http: Client::new(),
            url: url.trim_end_matches('/').to_string(),
            api_key: api_key.map(|s| s.to_string()),
        }
    }

    fn auth(&self, req: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        if let Some(ref key) = self.api_key {
            req.header("api-key", key.as_str())
        } else {
            req
        }
    }

    // ── Low-level REST helpers ─────────────────────────────────────────────

    /// `PUT /collections/{name}` — create or silently no-op if already exists.
    pub async fn create_collection(&self, name: &str) -> Result<(), QdrantError> {
        let url = format!("{}/collections/{}", self.url, name);
        let req = self.auth(self.http.put(&url).json(&build_create_collection_body()));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;

        // 200 OK or 409 Conflict (already exists) are both acceptable.
        if response.status().is_success() || response.status().as_u16() == 409 {
            info!("Collection ready: {}", name);
            return Ok(());
        }
        Err(QdrantError::Collection(format!(
            "HTTP {}",
            response.status()
        )))
    }

    /// `PUT /collections/{collection}/points` — upsert documents.
    pub async fn upsert_documents(
        &self,
        collection: &str,
        documents: &[SearchDocument],
    ) -> Result<(), QdrantError> {
        let url = format!("{}/collections/{}/points", self.url, collection);
        let body = build_upsert_body(documents);
        let req = self.auth(self.http.put(&url).json(&body));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(QdrantError::Http(format!("HTTP {}", response.status())));
        }
        debug!("Upserted {} documents to {}", documents.len(), collection);
        Ok(())
    }

    /// `POST /collections/{collection}/points/scroll` — keyword scroll filter.
    pub async fn scroll_by_text(
        &self,
        collection: &str,
        query: &str,
    ) -> Result<Vec<ScrollPoint>, QdrantError> {
        let url = format!("{}/collections/{}/points/scroll", self.url, collection);
        let body = build_scroll_body(query);
        let req = self.auth(self.http.post(&url).json(&body));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(QdrantError::Http(format!("HTTP {}", response.status())));
        }
        let envelope: ScrollResponse = response
            .json()
            .await
            .map_err(|e| QdrantError::Parse(e.to_string()))?;
        Ok(envelope.result.points)
    }

    /// `POST /collections/{collection}/points/delete` — delete by payload filter.
    pub async fn delete_by_id(
        &self,
        collection: &str,
        id: &str,
    ) -> Result<(), QdrantError> {
        let url = format!("{}/collections/{}/points/delete", self.url, collection);
        let body = build_delete_body(id);
        let req = self.auth(self.http.post(&url).json(&body));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(QdrantError::Http(format!("HTTP {}", response.status())));
        }
        Ok(())
    }

    /// `GET /health` — returns `true` if the server is up.
    pub async fn health(&self) -> Result<bool, QdrantError> {
        let url = format!("{}/health", self.url);
        let req = self.auth(self.http.get(&url));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;
        Ok(response.status().is_success())
    }

    // Keep the original vector search helper for callers that use it directly.
    /// `POST /collections/{collection}/points/search` — vector similarity search.
    pub async fn search_vectors(
        &self,
        collection: &str,
        query: &[f32],
        limit: usize,
    ) -> Result<Vec<SearchResult>, QdrantError> {
        let url = format!("{}/collections/{}/points/search", self.url, collection);
        let req = self.auth(self.http.post(&url).json(&serde_json::json!({
            "vector": query,
            "limit": limit,
            "with_payload": true
        })));
        let response = req
            .send()
            .await
            .map_err(|e| QdrantError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(QdrantError::Http(format!("HTTP {}", response.status())));
        }
        let results: Vec<SearchResult> = response
            .json()
            .await
            .map_err(|e| QdrantError::Parse(e.to_string()))?;
        Ok(results)
    }
}

// ── SearchPort implementation ──────────────────────────────────────────────

fn to_port_err(e: QdrantError) -> SearchPortError {
    match e {
        QdrantError::Http(s) | QdrantError::Parse(s) => SearchPortError::Transport(s),
        QdrantError::Collection(s) | QdrantError::NotFound(s) => SearchPortError::Index(s),
    }
}

#[async_trait]
impl SearchPort for QdrantClient {
    async fn ensure_index(
        &self,
        index: &str,
        _primary_key: &str,
    ) -> Result<(), SearchPortError> {
        self.create_collection(index).await.map_err(to_port_err)
    }

    async fn index_documents(
        &self,
        index: &str,
        documents: Vec<SearchDocument>,
    ) -> Result<(), SearchPortError> {
        self.upsert_documents(index, &documents)
            .await
            .map_err(to_port_err)
    }

    async fn search(
        &self,
        index: &str,
        query: &str,
    ) -> Result<SearchResults, SearchPortError> {
        let start = std::time::Instant::now();
        let points = self
            .scroll_by_text(index, query)
            .await
            .map_err(to_port_err)?;
        let processing_time_ms = start.elapsed().as_millis() as u64;

        let hits: Vec<serde_json::Value> = points
            .into_iter()
            .map(|p| {
                let payload = p.payload.unwrap_or_default();
                serde_json::json!({
                    "id": p.id,
                    "payload": payload
                })
            })
            .collect();
        let total = hits.len() as u64;
        Ok(SearchResults {
            hits,
            estimated_total_hits: total,
            processing_time_ms,
            query: query.to_string(),
        })
    }

    async fn delete_document(
        &self,
        index: &str,
        id: &str,
    ) -> Result<(), SearchPortError> {
        self.delete_by_id(index, id).await.map_err(to_port_err)
    }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use pheno_ports::SearchDocument;

    // ── Request-body mapping tests (no live server needed) ─────────────────

    #[test]
    fn test_build_create_collection_body_has_vector_config() {
        let body = build_create_collection_body();
        let vectors = &body["vectors"];
        assert_eq!(vectors["size"], 1);
        assert_eq!(vectors["distance"], "Dot");
    }

    #[test]
    fn test_build_upsert_body_encodes_id_and_fields() {
        let docs = vec![SearchDocument {
            id: "doc-1".to_string(),
            fields: serde_json::json!({ "name": "hello world" }),
        }];
        let body = build_upsert_body(&docs);
        let points = body["points"].as_array().unwrap();
        assert_eq!(points.len(), 1);
        let p = &points[0];
        assert_eq!(p["id"], "doc-1");
        // Vector must be a single-element array of 0.0
        assert_eq!(p["vector"], serde_json::json!([0.0_f32]));
        // Payload must contain the merged field and _pheno_id
        assert_eq!(p["payload"]["name"], "hello world");
        assert_eq!(p["payload"]["_pheno_id"], "doc-1");
    }

    #[test]
    fn test_build_upsert_body_multiple_documents() {
        let docs = vec![
            SearchDocument {
                id: "a".to_string(),
                fields: serde_json::json!({ "content": "foo" }),
            },
            SearchDocument {
                id: "b".to_string(),
                fields: serde_json::json!({ "content": "bar" }),
            },
        ];
        let body = build_upsert_body(&docs);
        let points = body["points"].as_array().unwrap();
        assert_eq!(points.len(), 2);
        assert_eq!(points[0]["payload"]["_pheno_id"], "a");
        assert_eq!(points[1]["payload"]["_pheno_id"], "b");
    }

    #[test]
    fn test_build_scroll_body_has_should_filter() {
        let body = build_scroll_body("rust");
        let filter = &body["filter"];
        let should = filter["should"].as_array().unwrap();
        // Must contain at least one clause per field
        assert!(!should.is_empty());
        // Every clause has a "match.text" key
        for clause in should {
            assert!(clause["match"]["text"] == "rust");
        }
        assert_eq!(body["with_payload"], true);
    }

    #[test]
    fn test_build_scroll_body_checks_pheno_id_field() {
        let body = build_scroll_body("x");
        let should = body["filter"]["should"].as_array().unwrap();
        let has_pheno_id = should
            .iter()
            .any(|c| c["key"] == "_pheno_id");
        assert!(has_pheno_id, "_pheno_id field must be included in scroll filter");
    }

    #[test]
    fn test_build_delete_body_uses_pheno_id_filter() {
        let body = build_delete_body("doc-42");
        let must = &body["filter"]["must"];
        let clause = &must[0];
        assert_eq!(clause["key"], "_pheno_id");
        assert_eq!(clause["match"]["value"], "doc-42");
    }

    #[test]
    fn test_build_upsert_body_non_object_fields_ignored_gracefully() {
        // fields is a primitive (not an object) — should not panic
        let docs = vec![SearchDocument {
            id: "edge".to_string(),
            fields: serde_json::json!("just a string"),
        }];
        let body = build_upsert_body(&docs);
        let points = body["points"].as_array().unwrap();
        // _pheno_id still present
        assert_eq!(points[0]["payload"]["_pheno_id"], "edge");
    }

    // ── Object-safety smoke test ───────────────────────────────────────────

    #[tokio::test]
    async fn test_qdrant_client_is_search_port() {
        // Verify QdrantClient can be boxed as dyn SearchPort (object-safety).
        let _: Box<dyn pheno_ports::SearchPort> =
            Box::new(QdrantClient::new("http://localhost:6333", None));
    }

    // ── Live-server tests (require a running Qdrant instance) ─────────────

    #[tokio::test]
    #[ignore = "requires live Qdrant on localhost:6333"]
    async fn test_live_health_check() {
        let client = QdrantClient::new("http://localhost:6333", None);
        assert!(client.health().await.unwrap());
    }

    #[tokio::test]
    #[ignore = "requires live Qdrant on localhost:6333"]
    async fn test_live_ensure_index_is_idempotent() {
        use pheno_ports::SearchPort;
        let client = QdrantClient::new("http://localhost:6333", None);
        client.ensure_index("pheno_test", "id").await.unwrap();
        client.ensure_index("pheno_test", "id").await.unwrap(); // must not error
    }

    #[tokio::test]
    #[ignore = "requires live Qdrant on localhost:6333"]
    async fn test_live_index_search_delete_roundtrip() {
        use pheno_ports::SearchPort;
        let client = QdrantClient::new("http://localhost:6333", None);
        client.ensure_index("pheno_test", "id").await.unwrap();

        let doc = SearchDocument {
            id: "live-1".to_string(),
            fields: serde_json::json!({ "content": "phenotype voxel kernel" }),
        };
        client
            .index_documents("pheno_test", vec![doc])
            .await
            .unwrap();

        // Wait briefly for Qdrant to index
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;

        let results = client.search("pheno_test", "voxel").await.unwrap();
        assert!(!results.hits.is_empty());

        client.delete_document("pheno_test", "live-1").await.unwrap();

        let results_after = client.search("pheno_test", "voxel").await.unwrap();
        assert!(results_after.hits.is_empty());
    }
}
