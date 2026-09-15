//! SurrealDB Bridge - SurrealDB embedded with Pheno extensions
//!
//! Provides embedded SurrealDB with MCP protocol adapter and skill storage.
//!
//! ## SurrealDB v3 compatibility
//! In v3, internal SQL types are fully opaque. All record and content
//! operations use `serde_json::Value`. Raw SQL via `db.query()` is the
//! primary API for anything beyond simple select/insert.

use anyhow::Result;
use pheno_data_core::{Dataset, DatasetFuture, Record};
use pheno_query::{QueryPort, QueryRequest, QueryStatement, SurrealQueryPlanner};
use serde::{Deserialize, Serialize};
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;
use surrealdb::Surreal;
use surrealdb::engine::local::Db;
use thiserror::Error;
use tracing::instrument;

#[cfg(windows)]
use surrealdb::engine::local::Mem;
#[cfg(not(windows))]
use surrealdb::engine::local::RocksDb;

pub type RecordId = String;
type LoaderFuture = Pin<Box<dyn Future<Output = Result<Vec<Record>>> + Send>>;
type SchemaFuture = Pin<Box<dyn Future<Output = Result<serde_json::Value>> + Send>>;
type RecordsLoader = dyn Fn() -> LoaderFuture + Send + Sync;
type SchemaLoader = dyn Fn() -> SchemaFuture + Send + Sync;

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/// Typed error for SurrealDB bridge operations.
#[derive(Error, Debug)]
pub enum SurrealBridgeError {
    #[error("connection error: {0}")]
    Connection(String),
    #[error("query error: {0}")]
    Query(String),
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("record ID extraction error: {0}")]
    RecordId(String),
}

/// Convenience alias for bridge methods returning a typed error.
pub type SurrealBridgeResult<T> = std::result::Result<T, SurrealBridgeError>;

// ---------------------------------------------------------------------------
// Retry helper
// ---------------------------------------------------------------------------

/// Maximum number of retry attempts for transient DB operations.
const MAX_RETRIES: u32 = 3;
/// Base delay in milliseconds (doubled each attempt: 50ms, 100ms, 200ms).
const BASE_DELAY_MS: u64 = 50;

/// Execute an async operation with exponential backoff retry.
///
/// Retries up to `MAX_RETRIES - 1` times on failure, with delay doubling each
/// attempt. Logs each retry via `tracing::warn!`.
async fn with_retry<F, Fut, T>(op: F) -> SurrealBridgeResult<T>
where
    F: Fn() -> Fut,
    Fut: Future<Output = SurrealBridgeResult<T>>,
{
    let mut last_err = None;
    for attempt in 0..MAX_RETRIES {
        match op().await {
            Ok(val) => return Ok(val),
            Err(e) => {
                if attempt + 1 < MAX_RETRIES {
                    let delay = Duration::from_millis(BASE_DELAY_MS * 2u64.pow(attempt));
                    tracing::warn!(
                        attempt,
                        delay_ms = delay.as_millis(),
                        error = %e,
                        "surreal operation failed, retrying"
                    );
                    tokio::time::sleep(delay).await;
                }
                last_err = Some(e);
            }
        }
    }
    Err(last_err.unwrap())
}

// ---------------------------------------------------------------------------
// Bridge types
// ---------------------------------------------------------------------------

/// PhenoSurreal - SurrealDB with extensions
pub struct PhenoSurreal {
    db: Surreal<Db>,
    /// Embedded planner so `QueryPort::plan` is `&self`-callable.
    planner: SurrealQueryPlanner,
}

pub struct SurrealDataset {
    records_loader: Arc<RecordsLoader>,
    schema_loader: Arc<SchemaLoader>,
}

impl SurrealDataset {
    pub fn new<RL, RF, SL, SF>(records_loader: RL, schema_loader: SL) -> Self
    where
        RL: Fn() -> RF + Send + Sync + 'static,
        RF: Future<Output = Result<Vec<Record>>> + Send + 'static,
        SL: Fn() -> SF + Send + Sync + 'static,
        SF: Future<Output = Result<serde_json::Value>> + Send + 'static,
    {
        Self {
            records_loader: Arc::new(move || Box::pin(records_loader())),
            schema_loader: Arc::new(move || Box::pin(schema_loader())),
        }
    }
}

impl Dataset for SurrealDataset {
    fn records(&self) -> DatasetFuture<Vec<Record>> {
        (self.records_loader)()
    }

    fn schema(&self) -> DatasetFuture<serde_json::Value> {
        (self.schema_loader)()
    }
}

impl QueryPort for PhenoSurreal {
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement> {
        // Hexagonal: bridge exposes the port so domain code can hold
        // `&dyn QueryPort` and dispatch to either backend uniformly.
        self.planner.plan(req)
    }
}

impl PhenoSurreal {
    /// Create new embedded SurrealDB
    #[instrument(skip(path))]
    pub async fn new(path: impl Into<String>) -> SurrealBridgeResult<Self> {
        let path_str: String = path.into();
        tracing::debug!(path = %path_str, "opening surreal db");
        let db = open_local_db(path_str).await?;
        db.use_ns("pheno")
            .use_db("main")
            .await
            .map_err(|e| SurrealBridgeError::Connection(e.to_string()))?;
        tracing::info!("surreal db opened");
        Ok(Self {
            db,
            planner: SurrealQueryPlanner,
        })
    }

    /// Store a skill with versioning via raw SQL
    #[instrument(skip(self, skill), fields(skill_name = %skill.name, skill_version = %skill.version))]
    pub async fn store_skill(&self, skill: Skill) -> SurrealBridgeResult<RecordId> {
        with_retry(|| async {
            let data = serde_json::to_value(&skill)
                .map_err(|e| SurrealBridgeError::Serialization(e.to_string()))?;
            let response: Option<serde_json::Value> = self
                .db
                .query("CREATE skill CONTENT $data RETURN id")
                .bind(("data", data))
                .await
                .map_err(|e| SurrealBridgeError::Query(e.to_string()))?
                .take(0)
                .map_err(|e| SurrealBridgeError::Query(e.to_string()))?;

            match response {
                Some(v) => {
                    let id = extract_record_id(&v)?;
                    tracing::debug!(record_id = %id, "skill stored");
                    Ok(id)
                }
                None => Err(SurrealBridgeError::Query(
                    "failed to create skill: no record returned".to_string(),
                )),
            }
        })
        .await
    }

    /// Query all skills
    #[instrument(skip(self))]
    pub async fn query_skills(&self) -> SurrealBridgeResult<Vec<Skill>> {
        let records: Vec<serde_json::Value> = self
            .db
            .select("skill")
            .await
            .map_err(|e| SurrealBridgeError::Query(e.to_string()))?;
        let skills: Vec<Skill> = records
            .into_iter()
            .filter_map(|r| serde_json::from_value(r).ok())
            .collect();
        tracing::debug!(count = skills.len(), "skills queried");
        Ok(skills)
    }

    /// Store a vector embedding via raw SQL
    #[instrument(skip(self, embedding), fields(embedding_len = embedding.vector.len()))]
    pub async fn store_embedding(&self, embedding: Embedding) -> SurrealBridgeResult<RecordId> {
        with_retry(|| async {
            let data = serde_json::to_value(&embedding)
                .map_err(|e| SurrealBridgeError::Serialization(e.to_string()))?;
            let response: Option<serde_json::Value> = self
                .db
                .query("CREATE embedding CONTENT $data RETURN id")
                .bind(("data", data))
                .await
                .map_err(|e| SurrealBridgeError::Query(e.to_string()))?
                .take(0)
                .map_err(|e| SurrealBridgeError::Query(e.to_string()))?;

            match response {
                Some(v) => {
                    let id = extract_record_id(&v)?;
                    tracing::debug!(record_id = %id, "embedding stored");
                    Ok(id)
                }
                None => Err(SurrealBridgeError::Query(
                    "failed to create embedding: no record returned".to_string(),
                )),
            }
        })
        .await
    }

    /// Search similar embeddings using cosine distance
    #[instrument(skip(self, query), fields(query_len = query.len(), limit))]
    pub async fn search_similar(
        &self,
        query: &[f32],
        limit: usize,
    ) -> SurrealBridgeResult<Vec<ScoredEmbedding>> {
        let results: Vec<serde_json::Value> = self
            .db
            .query(
                "SELECT *, vector::distance::cosine(embedding, $query) AS score \
                 FROM embedding ORDER BY score ASC LIMIT $limit",
            )
            .bind(("query", serde_json::json!(query)))
            .bind(("limit", limit))
            .await
            .map_err(|e| SurrealBridgeError::Query(e.to_string()))?
            .take(0)
            .map_err(|e| SurrealBridgeError::Query(e.to_string()))?;

        let scored: Vec<ScoredEmbedding> = results
            .into_iter()
            .filter_map(|r| serde_json::from_value(r).ok())
            .collect();
        tracing::debug!(count = scored.len(), "similarity search completed");
        Ok(scored)
    }
}

async fn open_local_db(path: String) -> SurrealBridgeResult<Surreal<Db>> {
    #[cfg(not(windows))]
    {
        Surreal::new::<RocksDb>(path)
            .await
            .map_err(|e| SurrealBridgeError::Connection(e.to_string()))
    }
    #[cfg(windows)]
    {
        let _ = path;
        Surreal::new::<Mem>(())
            .await
            .map_err(|e| SurrealBridgeError::Connection(e.to_string()))
    }
}

/// Extract a `RecordId` string from a `{"id": ...}` JSON value.
/// Handles both `{"id": "table:id"}` string form and `{"id": {"tb": "table", "id": "..."}}` object form.
fn extract_record_id(v: &serde_json::Value) -> SurrealBridgeResult<RecordId> {
    let id_val = v
        .get("id")
        .ok_or_else(|| SurrealBridgeError::RecordId("no 'id' field in response".to_string()))?;

    match id_val {
        serde_json::Value::String(s) => Ok(s.clone()),
        serde_json::Value::Object(o) => {
            let tb = o.get("tb").and_then(|v| v.as_str()).ok_or_else(|| {
                SurrealBridgeError::RecordId("id object missing 'tb'".to_string())
            })?;
            let id = o
                .get("id")
                .and_then(|v| v.as_str().map(str::to_string))
                .or_else(|| o.get("id").and_then(|v| v.as_i64().map(|i| i.to_string())))
                .ok_or_else(|| {
                    SurrealBridgeError::RecordId("id object missing 'id'".to_string())
                })?;
            Ok(format!("{}:{}", tb, id))
        }
        _ => Err(SurrealBridgeError::RecordId(format!(
            "id field has unexpected type: {}",
            id_val
        ))),
    }
}

/// Skill record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    #[serde(rename = "id", skip_serializing_if = "Option::is_none")]
    pub id: Option<RecordId>,
    pub name: String,
    pub version: String,
    pub code: String,
    pub runtime: String,
    pub metadata: serde_json::Value,
}

impl Skill {
    pub fn new(name: String, version: String, code: String, runtime: String) -> Self {
        Self {
            id: None,
            name,
            version,
            code,
            runtime,
            metadata: serde_json::json!({}),
        }
    }
}

/// Embedding record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    #[serde(rename = "id", skip_serializing_if = "Option::is_none")]
    pub id: Option<RecordId>,
    pub vector: Vec<f32>,
    pub metadata: serde_json::Value,
}

/// Scored embedding result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredEmbedding {
    pub id: RecordId,
    pub embedding: Vec<f32>,
    pub metadata: serde_json::Value,
    pub score: f32,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_skill() -> anyhow::Result<()> {
        let dir = tempdir()?;
        let path = dir.path().join("test.db").to_string_lossy().into_owned();
        let db = PhenoSurreal::new(path).await?;

        let skill = Skill::new(
            "test-skill".to_string(),
            "1.0.0".to_string(),
            "fn main() {}".to_string(),
            "wasm".to_string(),
        );

        let id = db.store_skill(skill).await?;
        assert!(id.starts_with("skill:"));
        Ok(())
    }

    #[test]
    fn test_surreal_bridge_error_display() {
        let err = SurrealBridgeError::Connection("refused".to_string());
        assert_eq!(err.to_string(), "connection error: refused");

        let err = SurrealBridgeError::Query("bad syntax".to_string());
        assert_eq!(err.to_string(), "query error: bad syntax");

        let err = SurrealBridgeError::Serialization("invalid utf-8".to_string());
        assert_eq!(err.to_string(), "serialization error: invalid utf-8");

        let err = SurrealBridgeError::RecordId("missing field".to_string());
        assert_eq!(err.to_string(), "record ID extraction error: missing field");
    }

    #[test]
    fn test_surreal_bridge_error_is_std_error() {
        use std::error::Error;
        let err = SurrealBridgeError::Connection("timeout".to_string());
        assert!(Error::source(&err).is_none());
    }

    #[test]
    fn test_extract_record_id_string_form() {
        let v = serde_json::json!({"id": "skill:abc123"});
        let id = extract_record_id(&v).unwrap();
        assert_eq!(id, "skill:abc123");
    }

    #[test]
    fn test_extract_record_id_object_form() {
        let v = serde_json::json!({"id": {"tb": "skill", "id": "abc123"}});
        let id = extract_record_id(&v).unwrap();
        assert_eq!(id, "skill:abc123");
    }

    #[test]
    fn test_extract_record_id_missing_id() {
        let v = serde_json::json!({"not_id": 42});
        let err = extract_record_id(&v).unwrap_err();
        assert!(matches!(err, SurrealBridgeError::RecordId(_)));
    }

    #[test]
    fn test_surreal_bridge_result_alias() {
        fn ok_fn() -> SurrealBridgeResult<i32> {
            Ok(99)
        }
        fn err_fn() -> SurrealBridgeResult<i32> {
            Err(SurrealBridgeError::Query("fail".to_string()))
        }
        assert_eq!(ok_fn().unwrap(), 99);
        assert!(err_fn().is_err());
    }
}
