//! PostgreSQL Bridge - PostgreSQL with pgvector for Pheno
//!
//! Provides pgvector-compatible vector search with PostgreSQL.
//!
//! # Hexagonal port (D19)
//!
//! `PgBridge` implements the [`pheno_query::QueryPort`] trait so domain
//! code can depend on the trait only. Planning delegates to
//! [`pheno_query::PostgresQueryPlanner`].

use anyhow::Result;
use deadpool_postgres::{Config, ManagerConfig, Pool, RecyclingMethod, Runtime};
use pheno_data_core::{Dataset, DatasetFuture, Record};
use pheno_query::{QueryPort, QueryRequest, QueryStatement};
use serde::{Deserialize, Serialize};
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio_postgres::NoTls;
use tracing::instrument;
use url::Url;

type LoaderFuture = Pin<Box<dyn Future<Output = Result<Vec<Record>>> + Send>>;
type SchemaFuture = Pin<Box<dyn Future<Output = Result<serde_json::Value>> + Send>>;
type RecordsLoader = dyn Fn() -> LoaderFuture + Send + Sync;
type SchemaLoader = dyn Fn() -> SchemaFuture + Send + Sync;

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/// Typed error for PostgreSQL bridge operations.
#[derive(Error, Debug)]
pub enum PgBridgeError {
    #[error("connection pool error: {0}")]
    Pool(String),
    #[error("query execution error: {0}")]
    Query(String),
    #[error("configuration error: {0}")]
    Config(String),
}

/// Convenience alias for bridge methods returning a typed error.
pub type PgBridgeResult<T> = std::result::Result<T, PgBridgeError>;

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
async fn with_retry<F, Fut, T>(op: F) -> PgBridgeResult<T>
where
    F: Fn() -> Fut,
    Fut: Future<Output = PgBridgeResult<T>>,
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
                        "pg operation failed, retrying"
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

/// PgBridge - PostgreSQL with pgvector
pub struct PgBridge {
    pool: Pool,
    /// Embedded planner so `QueryPort::plan` is `&self`-callable.
    planner: pheno_query::PostgresQueryPlanner,
}

pub struct PgDataset {
    records_loader: Arc<RecordsLoader>,
    schema_loader: Arc<SchemaLoader>,
}

impl PgDataset {
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

impl Dataset for PgDataset {
    fn records(&self) -> DatasetFuture<Vec<Record>> {
        (self.records_loader)()
    }

    fn schema(&self) -> DatasetFuture<serde_json::Value> {
        (self.schema_loader)()
    }
}

impl QueryPort for PgBridge {
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement> {
        // Delegate to the embedded planner. The bridge owns no extra
        // planning state; this is a thin dispatch to keep the hexagonal
        // contract concrete (callers can hold `&dyn QueryPort` and call
        // `plan` on any backend).
        self.planner.plan(req)
    }
}

impl PgBridge {
    /// Create new PostgreSQL bridge with connection pool from a connection string.
    /// Supports standard PostgreSQL URI format:
    /// `postgres://user:pass@host:port/dbname?sslmode=require`
    #[instrument(skip(conn_string), fields(conn_string = %conn_string))]
    pub async fn new(conn_string: &str) -> PgBridgeResult<Self> {
        let parsed = Url::parse(conn_string)
            .map_err(|e| PgBridgeError::Config(format!("invalid connection string: {e}")))?;

        let mut cfg = Config::new();
        cfg.host = parsed.host_str().map(|h| h.to_string());
        cfg.port = parsed.port();
        cfg.user = if parsed.username().is_empty() {
            None
        } else {
            Some(parsed.username().to_string())
        };
        cfg.password = parsed.password().map(|p| p.to_string());
        cfg.dbname = if parsed.path().trim_start_matches('/').is_empty() {
            None
        } else {
            Some(parsed.path().trim_start_matches('/').to_string())
        };
        cfg.manager = Some(ManagerConfig {
            recycling_method: RecyclingMethod::Fast,
        });

        let pool = cfg
            .create_pool(Some(Runtime::Tokio1), NoTls)
            .map_err(|e| PgBridgeError::Config(format!("failed to create pool: {e}")))?;

        tracing::info!("pg-bridge pool created");
        Ok(Self {
            pool,
            planner: pheno_query::PostgresQueryPlanner,
        })
    }

    /// Initialize pgvector extension and tables
    #[instrument(skip(self))]
    pub async fn init_schema(&self) -> PgBridgeResult<()> {
        with_retry(|| async {
            let client = self
                .pool
                .get()
                .await
                .map_err(|e| PgBridgeError::Pool(e.to_string()))?;

            client
                .batch_execute(
                    "CREATE EXTENSION IF NOT EXISTS vector;
                 CREATE TABLE IF NOT EXISTS embeddings (
                     id SERIAL PRIMARY KEY,
                     name TEXT NOT NULL,
                     vector VECTOR(1536),
                     metadata JSONB
                 );
                 CREATE INDEX ON embeddings USING HNSW (vector vector_cosine_ops);",
                )
                .await
                .map_err(|e| PgBridgeError::Query(e.to_string()))?;

            tracing::info!("pgvector schema initialized");
            Ok(())
        })
        .await
    }

    /// Store embedding
    #[instrument(skip(self, vector, metadata), fields(name = %name, vector_len = vector.len()))]
    pub async fn store_embedding(
        &self,
        name: &str,
        vector: Vec<f32>,
        metadata: serde_json::Value,
    ) -> PgBridgeResult<i32> {
        with_retry(|| async {
            let client = self
                .pool
                .get()
                .await
                .map_err(|e| PgBridgeError::Pool(e.to_string()))?;

            let row = client
                .query_one(
                    "INSERT INTO embeddings (name, vector, metadata) VALUES ($1, $2, $3) RETURNING id",
                    &[&name, &vector, &metadata],
                )
                .await
                .map_err(|e| PgBridgeError::Query(e.to_string()))?;

            let id: i32 = row.get(0);
            tracing::debug!(id, "embedding stored");
            Ok(id)
        })
        .await
    }

    /// Search similar embeddings using pgvector
    #[instrument(skip(self, query), fields(query_len = query.len(), limit))]
    pub async fn search_similar(
        &self,
        query: &[f32],
        limit: usize,
    ) -> PgBridgeResult<Vec<EmbeddingResult>> {
        with_retry(|| async {
            let client = self
                .pool
                .get()
                .await
                .map_err(|e| PgBridgeError::Pool(e.to_string()))?;

            let rows = client
                .query(
                    "SELECT id, name, 1 - (vector <=> $1) AS similarity, metadata 
                 FROM embeddings 
                 ORDER BY vector <=> $1 
                 LIMIT $2",
                    &[&query, &(limit as i64)],
                )
                .await
                .map_err(|e| PgBridgeError::Query(e.to_string()))?;

            let results: Vec<EmbeddingResult> = rows
                .iter()
                .map(|row| EmbeddingResult {
                    id: row.get(0),
                    name: row.get(1),
                    similarity: row.get(2),
                    metadata: row.get(3),
                })
                .collect();

            tracing::debug!(count = results.len(), "search completed");
            Ok(results)
        })
        .await
    }
}

/// Embedding search result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingResult {
    pub id: i32,
    pub name: String,
    pub similarity: f64,
    pub metadata: serde_json::Value,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // Requires PostgreSQL with pgvector
    async fn test_store_and_search() -> Result<()> {
        let bridge = PgBridge::new("postgres://localhost/pheno").await?;
        bridge.init_schema().await?;

        let id = bridge
            .store_embedding(
                "test",
                vec![0.1; 1536],
                serde_json::json!({"source": "test"}),
            )
            .await?;

        assert!(id > 0);

        let results = bridge.search_similar(&vec![0.1; 1536], 5).await?;
        assert!(!results.is_empty());

        Ok(())
    }

    #[test]
    fn test_pg_bridge_error_display() {
        let err = PgBridgeError::Pool("connection refused".to_string());
        assert_eq!(err.to_string(), "connection pool error: connection refused");

        let err = PgBridgeError::Query("syntax error".to_string());
        assert_eq!(err.to_string(), "query execution error: syntax error");

        let err = PgBridgeError::Config("invalid URI".to_string());
        assert_eq!(err.to_string(), "configuration error: invalid URI");
    }

    #[test]
    fn test_pg_bridge_error_is_std_error() {
        use std::error::Error;
        let err = PgBridgeError::Pool("timeout".to_string());
        assert!(Error::source(&err).is_none());
        assert!(PgBridgeError::Query("fail".to_string()).source().is_none());
    }

    #[test]
    fn test_pg_bridge_result_alias() {
        // Verify PgBridgeResult<T> works with `?` in a fn returning PgBridgeResult
        fn ok_fn() -> PgBridgeResult<i32> {
            Ok(42)
        }
        fn err_fn() -> PgBridgeResult<i32> {
            Err(PgBridgeError::Config("nope".to_string()))
        }
        assert_eq!(ok_fn().unwrap(), 42);
        assert!(err_fn().is_err());
    }
}
