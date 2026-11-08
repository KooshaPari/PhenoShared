#![doc = "Dragonfly client for PhenoObservability - Redis-compatible, multi-threaded cache"]

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use phenotype_errors::RepositoryError;
use phenotype_observably_ports::cache::{CachePort, CacheResult};
use redis::{AsyncCommands, Client, aio::ConnectionManager};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Dragonfly client result type
pub type Result<T> = std::result::Result<T, RepositoryError>;

/// Session data stored in Dragonfly
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    pub user_id: Option<String>,
    pub created_at: DateTime<Utc>,
    pub last_accessed: DateTime<Utc>,
    pub data: HashMap<String, String>,
    pub ttl_seconds: u64,
}

/// Metric cache entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricCache {
    pub name: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
    pub timestamp: DateTime<Utc>,
}

/// Dragonfly client for caching and sessions
#[derive(Clone)]
pub struct DragonflyClient {
    conn: ConnectionManager,
}

impl DragonflyClient {
    /// Create new Dragonfly client
    pub async fn new(url: &str) -> Result<Self> {
        let client = Client::open(url).map_err(|e| RepositoryError::Connection(e.to_string()))?;
        let conn = ConnectionManager::new(client)
            .await
            .map_err(|e| RepositoryError::Connection(e.to_string()))?;
        Ok(Self { conn })
    }

    /// Set a session with TTL
    pub async fn set_session(&self, session: &Session) -> Result<()> {
        let key = format!("session:{}", session.id);
        let value = serde_json::to_string(session)
            .map_err(|e| RepositoryError::Serialization(e.to_string()))?;
        let mut conn = self.conn.clone();
        let _: () = conn
            .set_ex(&key, &value, session.ttl_seconds)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(())
    }

    /// Get session by ID
    pub async fn get_session(&self, id: &str) -> Result<Option<Session>> {
        let key = format!("session:{}", id);
        let mut conn = self.conn.clone();
        let value: Option<String> = conn
            .get(&key)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        match value {
            Some(v) => {
                let session: Session = serde_json::from_str(&v)
                    .map_err(|e| RepositoryError::Serialization(e.to_string()))?;
                Ok(Some(session))
            }
            None => Ok(None),
        }
    }

    /// Set with custom TTL
    pub async fn set_with_ttl(&self, key: &str, value: &[u8], ttl_seconds: u64) -> Result<()> {
        let mut conn = self.conn.clone();
        let _: () = conn
            .set_ex(key, value, ttl_seconds)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(())
    }

    /// Get value
    pub async fn get(&self, key: &str) -> Result<Option<Vec<u8>>> {
        let mut conn = self.conn.clone();
        let value: Option<String> = conn
            .get(key)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(value.map(|v| v.into_bytes()))
    }

    /// Increment counter (atomic)
    pub async fn incr(&self, key: &str, amount: i64) -> Result<i64> {
        let mut conn = self.conn.clone();
        let result: i64 = conn
            .incr(key, amount)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(result)
    }

    /// Health check
    pub async fn ping(&self) -> Result<bool> {
        let mut conn = self.conn.clone();
        let result: String = redis::cmd("PING")
            .query_async(&mut conn)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(result == "PONG")
    }

    /// Delete a key (raw, no prefix).
    pub async fn delete(&self, key: &str) -> Result<()> {
        let mut conn = self.conn.clone();
        let _: () = conn
            .del(key)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(())
    }

    /// Set expiry on a key.  Returns `true` if the key existed.
    pub async fn expire(&self, key: &str, ttl_seconds: u64) -> Result<bool> {
        let mut conn = self.conn.clone();
        let result: bool = conn
            .expire(key, ttl_seconds as i64)
            .await
            .map_err(|e| RepositoryError::Query(e.to_string()))?;
        Ok(result)
    }
}

// ---------------------------------------------------------------------------
// Hexagonal port implementation
// ---------------------------------------------------------------------------

#[async_trait]
impl CachePort for DragonflyClient {
    async fn get(&self, key: &str) -> CacheResult<Option<Vec<u8>>> {
        self.get(key).await
    }

    async fn set(&self, key: &str, value: &[u8], ttl_seconds: u64) -> CacheResult<()> {
        self.set_with_ttl(key, value, ttl_seconds).await
    }

    async fn delete(&self, key: &str) -> CacheResult<()> {
        self.delete(key).await
    }

    async fn expire(&self, key: &str, ttl_seconds: u64) -> CacheResult<bool> {
        self.expire(key, ttl_seconds).await
    }
}
