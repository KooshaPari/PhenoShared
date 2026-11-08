//! Retry utilities for Phenotype

use std::time::Duration;

/// Retry configuration
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_attempts: u32,
    pub base_delay: Duration,
    pub max_delay: Duration,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(30),
        }
    }
}

/// Retry an operation
pub async fn retry<F, Fut, T, E>(config: &RetryConfig, f: F) -> Result<T, E>
where
    F: Fn() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
{
    let mut last_err = None;
    for attempt in 0..config.max_attempts {
        match f().await {
            Ok(val) => return Ok(val),
            Err(e) => {
                last_err = Some(e);
                if attempt < config.max_attempts - 1 {
                    tokio::time::sleep(config.base_delay).await;
                }
            }
        }
    }
    Err(last_err.unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    #[test]
    fn default_retry_config() {
        let cfg = RetryConfig::default();
        assert_eq!(cfg.max_attempts, 3);
        assert_eq!(cfg.base_delay, Duration::from_millis(100));
        assert_eq!(cfg.max_delay, Duration::from_secs(30));
    }

    #[tokio::test]
    async fn retry_succeeds_on_first_attempt() {
        let cfg = RetryConfig {
            max_attempts: 3,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(1),
        };
        let calls = Arc::new(AtomicU32::new(0));
        let calls2 = calls.clone();
        let result: Result<i32, &'static str> = retry(&cfg, || {
            let c = calls2.clone();
            async move {
                c.fetch_add(1, Ordering::SeqCst);
                Ok(42)
            }
        })
        .await;
        assert_eq!(result, Ok(42));
        assert_eq!(calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn retry_succeeds_on_last_attempt() {
        let cfg = RetryConfig {
            max_attempts: 3,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(1),
        };
        let calls = Arc::new(AtomicU32::new(0));
        let calls2 = calls.clone();
        let result: Result<&'static str, &'static str> = retry(&cfg, || {
            let c = calls2.clone();
            async move {
                let n = c.fetch_add(1, Ordering::SeqCst) + 1;
                if n < 3 { Err("not yet") } else { Ok("done") }
            }
        })
        .await;
        assert_eq!(result, Ok("done"));
        assert_eq!(calls.load(Ordering::SeqCst), 3);
    }

    #[tokio::test]
    async fn retry_returns_last_error_after_exhausting() {
        let cfg = RetryConfig {
            max_attempts: 3,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(1),
        };
        let calls = Arc::new(AtomicU32::new(0));
        let calls2 = calls.clone();
        let result: Result<i32, i32> = retry(&cfg, || {
            let c = calls2.clone();
            async move {
                let n: u32 = c.fetch_add(1, Ordering::SeqCst) + 1;
                Err(n as i32 * 10)
            }
        })
        .await;
        assert_eq!(result, Err(30));
        assert_eq!(calls.load(Ordering::SeqCst), 3);
    }

    #[tokio::test]
    async fn retry_with_single_attempt_does_not_sleep() {
        let cfg = RetryConfig {
            max_attempts: 1,
            base_delay: Duration::from_secs(60), // would be obvious if used
            max_delay: Duration::from_secs(60),
        };
        let calls = Arc::new(AtomicU32::new(0));
        let calls2 = calls.clone();
        let result: Result<(), &'static str> = retry(&cfg, || {
            let c = calls2.clone();
            async move {
                c.fetch_add(1, Ordering::SeqCst);
                Err("nope")
            }
        })
        .await;
        assert_eq!(result, Err("nope"));
        assert_eq!(calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn retry_propagates_different_error_types() {
        let cfg = RetryConfig {
            max_attempts: 2,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(1),
        };
        // String error type
        let r: Result<(), String> = retry(&cfg, || async { Err(String::from("boom")) }).await;
        assert_eq!(r, Err(String::from("boom")));
        // Custom error type
        #[derive(Debug, PartialEq)]
        struct MyErr(u32);
        let r2: Result<(), MyErr> = retry(&cfg, || async { Err(MyErr(7)) }).await;
        assert_eq!(r2, Err(MyErr(7)));
    }

    #[tokio::test]
    async fn retry_with_zero_max_attempts_panics() {
        // Documented edge case: with 0 attempts the loop body never runs,
        // so last_err stays None and the trailing unwrap() panics.
        let cfg = RetryConfig {
            max_attempts: 0,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(1),
        };
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap();
            rt.block_on(async {
                let _: Result<i32, &'static str> = retry(&cfg, || async { Ok(1) }).await;
            });
        }));
        assert!(result.is_err(), "retry with 0 max_attempts should panic");
    }
}
