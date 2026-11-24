//! Idempotency domain types and port.
//!
//! Provides a swappable key→result store and DLQ hook for submission deduplication.

use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use super::errors::ConfigError;

/// Opaque idempotency key provided by the caller on submission.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct IdempotencyKey(pub String);

impl IdempotencyKey {
    pub fn new(key: impl Into<String>) -> Self {
        Self(key.into())
    }
}

impl std::fmt::Display for IdempotencyKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// The outcome of a single submission, stored in the idempotency store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubmissionResult {
    /// Idempotency key that produced this result.
    pub key: String,
    /// Opaque payload returned by the executor (JSON-encoded).
    pub payload: serde_json::Value,
    /// Whether this result was produced from cache (not re-executed).
    pub from_cache: bool,
}

impl SubmissionResult {
    pub fn new(key: impl Into<String>, payload: serde_json::Value) -> Self {
        Self { key: key.into(), payload, from_cache: false }
    }

    pub fn cached(mut self) -> Self {
        self.from_cache = true;
        self
    }
}

/// A record placed on the dead-letter queue when retries are exhausted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeadLetterEntry {
    pub key: String,
    pub attempts: u32,
    pub last_error: String,
}

impl DeadLetterEntry {
    pub fn new(key: impl Into<String>, attempts: u32, last_error: impl Into<String>) -> Self {
        Self { key: key.into(), attempts, last_error: last_error.into() }
    }
}

/// Entry stored per idempotency key (result + expiry).
#[derive(Debug, Clone)]
pub struct CacheEntry {
    pub result: SubmissionResult,
    pub inserted_at: Instant,
    pub ttl: Duration,
}

impl CacheEntry {
    pub fn new(result: SubmissionResult, ttl: Duration) -> Self {
        Self { result, inserted_at: Instant::now(), ttl }
    }

    pub fn is_expired(&self) -> bool {
        self.inserted_at.elapsed() > self.ttl
    }
}

/// Port: swappable idempotency store (in-memory, Redis, Postgres, …).
#[async_trait]
pub trait IdempotencyStore: Send + Sync {
    /// Return a cached result if the key is present and not expired.
    async fn get(&self, key: &IdempotencyKey) -> Result<Option<SubmissionResult>, ConfigError>;

    /// Persist a result under the given key with the configured TTL.
    async fn set(&self, key: &IdempotencyKey, result: SubmissionResult) -> Result<(), ConfigError>;
}

/// Port: dead-letter sink (in-memory Vec, log line, DB table, …).
#[async_trait]
pub trait DeadLetterQueue: Send + Sync {
    /// Record an exhausted submission on the DLQ.
    async fn push(&self, entry: DeadLetterEntry) -> Result<(), ConfigError>;

    /// Drain all current DLQ entries (useful for inspection / tests).
    async fn drain(&self) -> Result<Vec<DeadLetterEntry>, ConfigError>;
}
