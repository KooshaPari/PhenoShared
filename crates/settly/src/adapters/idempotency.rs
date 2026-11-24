//! In-memory implementations of the idempotency store and DLQ ports.
//!
//! These are the default adapters; swap them out at wiring time for Redis /
//! Postgres variants without touching any application or domain code.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use async_trait::async_trait;

use crate::domain::errors::ConfigError;
use crate::domain::idempotency::{
    CacheEntry, DeadLetterEntry, DeadLetterQueue, IdempotencyKey, IdempotencyStore,
    SubmissionResult,
};

/// In-memory idempotency store backed by a `HashMap` behind a `Mutex`.
///
/// TTL eviction is lazy (checked on `get`).
pub struct InMemoryIdempotencyStore {
    inner: Arc<Mutex<HashMap<String, CacheEntry>>>,
    ttl: Duration,
}

impl InMemoryIdempotencyStore {
    /// Create with an explicit TTL.
    pub fn new(ttl: Duration) -> Self {
        Self { inner: Arc::new(Mutex::new(HashMap::new())), ttl }
    }

    /// Default TTL: 24 hours.
    pub fn default_ttl() -> Self {
        Self::new(Duration::from_secs(86_400))
    }
}

#[async_trait]
impl IdempotencyStore for InMemoryIdempotencyStore {
    async fn get(&self, key: &IdempotencyKey) -> Result<Option<SubmissionResult>, ConfigError> {
        let mut store = self.inner.lock().map_err(|e| {
            ConfigError::ParseError(format!("idempotency store lock poisoned: {e}"))
        })?;

        if let Some(entry) = store.get(&key.0) {
            if entry.is_expired() {
                store.remove(&key.0);
                return Ok(None);
            }
            return Ok(Some(entry.result.clone().cached()));
        }

        Ok(None)
    }

    async fn set(&self, key: &IdempotencyKey, result: SubmissionResult) -> Result<(), ConfigError> {
        let mut store = self.inner.lock().map_err(|e| {
            ConfigError::ParseError(format!("idempotency store lock poisoned: {e}"))
        })?;
        store.insert(key.0.clone(), CacheEntry::new(result, self.ttl));
        Ok(())
    }
}

/// In-memory dead-letter queue backed by a `Vec` behind a `Mutex`.
pub struct InMemoryDlq {
    inner: Arc<Mutex<Vec<DeadLetterEntry>>>,
}

impl InMemoryDlq {
    pub fn new() -> Self {
        Self { inner: Arc::new(Mutex::new(Vec::new())) }
    }
}

impl Default for InMemoryDlq {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl DeadLetterQueue for InMemoryDlq {
    async fn push(&self, entry: DeadLetterEntry) -> Result<(), ConfigError> {
        let mut queue = self
            .inner
            .lock()
            .map_err(|e| ConfigError::ParseError(format!("DLQ lock poisoned: {e}")))?;
        queue.push(entry);
        Ok(())
    }

    async fn drain(&self) -> Result<Vec<DeadLetterEntry>, ConfigError> {
        let mut queue = self
            .inner
            .lock()
            .map_err(|e| ConfigError::ParseError(format!("DLQ lock poisoned: {e}")))?;
        Ok(std::mem::take(&mut *queue))
    }
}
