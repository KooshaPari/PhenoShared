//! Tests for the idempotency + DLQ submission layer.
//!
//! Follows the existing `#[cfg(test)] mod tests` convention used throughout
//! this crate; each test module lives alongside the code it covers.

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;
    use std::time::Duration;

    use crate::adapters::idempotency::{InMemoryDlq, InMemoryIdempotencyStore};
    use crate::application::submission::SubmissionService;
    use crate::domain::errors::ConfigError;
    use crate::domain::idempotency::{DeadLetterQueue, IdempotencyKey};

    /// Helper: build a service with a 1-hour TTL and 2 retries.
    fn make_service() -> (SubmissionService, Arc<InMemoryDlq>) {
        let store = Arc::new(InMemoryIdempotencyStore::new(Duration::from_secs(3600)));
        let dlq = Arc::new(InMemoryDlq::new());
        let svc = SubmissionService::new(store, dlq.clone(), 2);
        (svc, dlq)
    }

    // -------------------------------------------------------------------------
    // T1: first submission executes the executor exactly once.
    // -------------------------------------------------------------------------
    #[tokio::test]
    async fn first_submit_executes_executor() {
        let (svc, _dlq) = make_service();
        let counter = Arc::new(AtomicU32::new(0));

        let key = IdempotencyKey::new("T1");
        let c = counter.clone();
        let result = svc
            .submit(key, || {
                let c = c.clone();
                async move {
                    c.fetch_add(1, Ordering::SeqCst);
                    Ok::<_, ConfigError>(serde_json::json!({"v": 1}))
                }
            })
            .await
            .unwrap();

        assert_eq!(counter.load(Ordering::SeqCst), 1, "executor must run once");
        assert!(!result.from_cache, "first result must not be marked from_cache");
        assert_eq!(result.payload, serde_json::json!({"v": 1}));
    }

    // -------------------------------------------------------------------------
    // T2: duplicate key returns cached result without re-executing.
    // -------------------------------------------------------------------------
    #[tokio::test]
    async fn duplicate_key_returns_cache_no_reexec() {
        let (svc, _dlq) = make_service();
        let counter = Arc::new(AtomicU32::new(0));

        let key = IdempotencyKey::new("T2");

        // First submit
        {
            let c = counter.clone();
            svc.submit(key.clone(), || {
                let c = c.clone();
                async move {
                    c.fetch_add(1, Ordering::SeqCst);
                    Ok::<_, ConfigError>(serde_json::json!({"v": 42}))
                }
            })
            .await
            .unwrap();
        }

        // Second submit — same key
        {
            let c = counter.clone();
            let result = svc
                .submit(key, || {
                    let c = c.clone();
                    async move {
                        c.fetch_add(1, Ordering::SeqCst);
                        Ok::<_, ConfigError>(serde_json::json!({"v": 99}))
                    }
                })
                .await
                .unwrap();

            assert_eq!(counter.load(Ordering::SeqCst), 1, "executor must NOT run on duplicate key");
            assert!(result.from_cache, "second result must be marked from_cache");
            // Payload is from the first run, not the second
            assert_eq!(result.payload, serde_json::json!({"v": 42}));
        }
    }

    // -------------------------------------------------------------------------
    // T3: distinct keys execute independently.
    // -------------------------------------------------------------------------
    #[tokio::test]
    async fn distinct_keys_execute_independently() {
        let (svc, _dlq) = make_service();
        let counter = Arc::new(AtomicU32::new(0));

        for i in 0u32..3 {
            let c = counter.clone();
            svc.submit(IdempotencyKey::new(format!("T3-{i}")), || {
                let c = c.clone();
                async move {
                    c.fetch_add(1, Ordering::SeqCst);
                    Ok::<_, ConfigError>(serde_json::json!({"i": i}))
                }
            })
            .await
            .unwrap();
        }

        assert_eq!(
            counter.load(Ordering::SeqCst),
            3,
            "each distinct key must invoke the executor once"
        );
    }

    // -------------------------------------------------------------------------
    // T4: exhausted retries land in DLQ.
    // -------------------------------------------------------------------------
    #[tokio::test]
    async fn exhausted_retries_land_in_dlq() {
        let store = Arc::new(InMemoryIdempotencyStore::new(Duration::from_secs(3600)));
        let dlq = Arc::new(InMemoryDlq::new());
        // max_retries = 1  →  2 total attempts
        let svc = SubmissionService::new(store, dlq.clone(), 1);

        let key = IdempotencyKey::new("T4");
        let result = svc
            .submit(key, || async {
                Err::<serde_json::Value, ConfigError>(ConfigError::ParseError("boom".to_string()))
            })
            .await;

        assert!(result.is_err(), "must propagate error");

        let entries = dlq.drain().await.unwrap();
        assert_eq!(entries.len(), 1, "one entry must be in the DLQ");
        assert_eq!(entries[0].key, "T4");
        assert_eq!(entries[0].attempts, 2, "2 total attempts (1 + 1 retry)");
        assert!(entries[0].last_error.contains("boom"), "DLQ entry must capture the error message");
    }

    // -------------------------------------------------------------------------
    // T5: TTL expiry — entry is evicted, next submit re-executes.
    // -------------------------------------------------------------------------
    #[tokio::test]
    async fn ttl_expiry_causes_reexec() {
        let store = Arc::new(InMemoryIdempotencyStore::new(Duration::from_millis(1)));
        let dlq = Arc::new(InMemoryDlq::new());
        let svc = SubmissionService::new(store, dlq, 0);
        let counter = Arc::new(AtomicU32::new(0));

        let key = IdempotencyKey::new("T5");
        // First submit
        {
            let c = counter.clone();
            svc.submit(key.clone(), || {
                let c = c.clone();
                async move {
                    c.fetch_add(1, Ordering::SeqCst);
                    Ok::<_, ConfigError>(serde_json::json!(1))
                }
            })
            .await
            .unwrap();
        }

        // Let the TTL expire
        tokio::time::sleep(Duration::from_millis(5)).await;

        // Second submit after TTL — should re-execute
        {
            let c = counter.clone();
            svc.submit(key, || {
                let c = c.clone();
                async move {
                    c.fetch_add(1, Ordering::SeqCst);
                    Ok::<_, ConfigError>(serde_json::json!(2))
                }
            })
            .await
            .unwrap();
        }

        assert_eq!(counter.load(Ordering::SeqCst), 2, "executor must re-run after TTL expiry");
    }
}
