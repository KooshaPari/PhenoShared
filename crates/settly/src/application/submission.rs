//! Submission service with idempotency-token deduplication and DLQ fallback.
//!
//! # Design
//!
//! `SubmissionService` wraps any async executor `F: Fn() -> Future<Output = Result<V>>`.
//! On `submit(key, executor)`:
//!
//! 1. Check the idempotency store for `key`.  If found and not expired → return cached
//!    result (executor is **not** called).
//! 2. Otherwise invoke `executor` up to `max_retries` times.
//! 3. On success → store result, return it.
//! 4. On exhausted retries → push a `DeadLetterEntry`, return the last error.
//!
//! Both the store and the DLQ are injected via trait objects (hexagonal ports) so
//! the caller can swap in-memory impls for Redis / Postgres without any changes here.

use std::future::Future;
use std::sync::Arc;

use serde::Serialize;

use crate::domain::errors::ConfigError;
use crate::domain::idempotency::{
    DeadLetterEntry, DeadLetterQueue, IdempotencyKey, IdempotencyStore, SubmissionResult,
};

/// Submission service.
///
/// Cheap to clone — all state is behind `Arc`.
#[derive(Clone)]
pub struct SubmissionService {
    store: Arc<dyn IdempotencyStore>,
    dlq: Arc<dyn DeadLetterQueue>,
    max_retries: u32,
}

impl SubmissionService {
    /// Construct a new service with explicit port impls and retry limit.
    pub fn new(
        store: Arc<dyn IdempotencyStore>,
        dlq: Arc<dyn DeadLetterQueue>,
        max_retries: u32,
    ) -> Self {
        Self { store, dlq, max_retries }
    }

    /// Submit work identified by `key`.
    ///
    /// `executor` is only called if `key` is not already in the idempotency
    /// store (first submission or after TTL expiry).  On cache hit the cached
    /// `SubmissionResult` is returned unchanged without invoking `executor`.
    ///
    /// Returns `Err` only when retries are exhausted **and** a DLQ push also
    /// fails — otherwise the last executor error is returned after DLQ
    /// recording.
    pub async fn submit<F, Fut, V>(
        &self,
        key: IdempotencyKey,
        executor: F,
    ) -> Result<SubmissionResult, ConfigError>
    where
        F: Fn() -> Fut,
        Fut: Future<Output = Result<V, ConfigError>>,
        V: Serialize,
    {
        // --- 1. Cache hit ---
        if let Some(cached) = self.store.get(&key).await? {
            return Ok(cached);
        }

        // --- 2. Execute with retries ---
        let mut last_error = ConfigError::ParseError("no attempts made".to_string());
        for attempt in 0..=self.max_retries {
            match executor().await {
                Ok(value) => {
                    let payload = serde_json::to_value(&value)
                        .map_err(|e| ConfigError::SerializationError(e.to_string()))?;
                    let result = SubmissionResult::new(key.0.clone(), payload);
                    self.store.set(&key, result.clone()).await?;
                    return Ok(result);
                }
                Err(e) => {
                    last_error = e;
                    if attempt < self.max_retries {
                        tracing::warn!(
                            attempt = attempt + 1,
                            max = self.max_retries,
                            "submission attempt failed, retrying"
                        );
                    }
                }
            }
        }

        // --- 3. Exhausted → DLQ ---
        let entry =
            DeadLetterEntry::new(key.0.clone(), self.max_retries + 1, last_error.to_string());
        self.dlq.push(entry).await?;
        Err(last_error)
    }
}
