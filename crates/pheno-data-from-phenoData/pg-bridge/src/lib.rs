//! PostgreSQL Bridge - PostgreSQL with pgvector for Pheno
//!
//! Provides pgvector-compatible vector search with PostgreSQL.

use anyhow::Result;
use deadpool_postgres::{Config, ManagerConfig, Pool, RecyclingMethod, Runtime};
use serde::{Deserialize, Serialize};
use tokio_postgres::NoTls;
use url::Url;

/// PgBridge - PostgreSQL with pgvector
pub struct PgBridge {
    pool: Pool,
}

impl PgBridge {
    /// Create new PostgreSQL bridge with connection pool from a connection string.
    /// Supports standard PostgreSQL URI format:
    /// `postgres://user:pass@host:port/dbname?sslmode=require`
    pub async fn new(conn_string: &str) -> Result<Self> {
        let parsed = Url::parse(conn_string)
            .map_err(|e| anyhow::anyhow!("invalid connection string: {}", e))?;

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

        let pool = cfg.create_pool(Some(Runtime::Tokio1), NoTls)?;

        Ok(Self { pool })
    }

    /// Initialize pgvector extension and tables
    pub async fn init_schema(&self) -> Result<()> {
        let client = self.pool.get().await?;

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
            .await?;

        Ok(())
    }

    /// Store embedding
    pub async fn store_embedding(
        &self,
        name: &str,
        vector: Vec<f32>,
        metadata: serde_json::Value,
    ) -> Result<i32> {
        let client = self.pool.get().await?;

        let row = client
            .query_one(
                "INSERT INTO embeddings (name, vector, metadata) VALUES ($1, $2, $3) RETURNING id",
                &[&name, &vector, &metadata],
            )
            .await?;

        Ok(row.get(0))
    }

    /// Search similar embeddings using pgvector
    pub async fn search_similar(
        &self,
        query: &[f32],
        limit: usize,
    ) -> Result<Vec<EmbeddingResult>> {
        let client = self.pool.get().await?;

        let rows = client
            .query(
                "SELECT id, name, 1 - (vector <=> $1) AS similarity, metadata 
             FROM embeddings 
             ORDER BY vector <=> $1 
             LIMIT $2",
                &[&query, &(limit as i64)],
            )
            .await?;

        let results: Vec<EmbeddingResult> = rows
            .iter()
            .map(|row| EmbeddingResult {
                id: row.get(0),
                name: row.get(1),
                similarity: row.get(2),
                metadata: row.get(3),
            })
            .collect();

        Ok(results)
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
}
