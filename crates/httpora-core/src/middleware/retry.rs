use std::time::Duration;

#[cfg(feature = "tower")]
use std::future::Future;

use crate::error::HttptoraError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum HttpMethod {
    Get,
    Head,
    Put,
    Delete,
    Options,
    Trace,
    Post,
    Patch,
    Other,
}

impl HttpMethod {
    pub fn is_idempotent(self) -> bool {
        matches!(
            self,
            Self::Get | Self::Head | Self::Put | Self::Delete | Self::Options | Self::Trace
        )
    }
}

/// Back-off configuration for retry logic.
#[derive(Debug, Clone)]
pub struct BackoffConfig {
    /// Starting delay before the first retry.
    pub base_delay: Duration,
    /// Upper bound on any single delay.
    pub max_delay: Duration,
    /// Exponential factor applied each attempt.
    pub multiplier: f64,
    /// Add uniform random jitter up to the computed delay to prevent thundering herd.
    pub jitter: bool,
}

impl Default for BackoffConfig {
    fn default() -> Self {
        Self {
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(30),
            multiplier: 2.0,
            jitter: true,
        }
    }
}

/// Configuration for the retry layer.
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Total attempts including the initial call (not just retries).
    pub max_attempts: usize,
    /// Back-off configuration.
    pub backoff: BackoffConfig,
    pub retry_non_idempotent: bool,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            backoff: BackoffConfig::default(),
            retry_non_idempotent: false,
        }
    }
}

/// Wraps an async callable with retry-and-backoff behaviour.
///
/// # Example
///
/// ```
/// use httpora_core::RetryLayer;
/// use std::time::Duration;
///
/// let retry = RetryLayer::new(3, Duration::from_millis(100));
/// ```
pub struct RetryLayer {
    config: RetryConfig,
}

impl RetryLayer {
    /// Return the configuration of this retry layer.
    pub fn config(&self) -> &RetryConfig {
        &self.config
    }

    /// Create a new retry layer with the given max attempts and base delay.
    pub fn new(max_attempts: usize, base_delay: Duration) -> Self {
        Self {
            config: RetryConfig {
                max_attempts,
                backoff: BackoffConfig {
                    base_delay,
                    ..Default::default()
                },
                retry_non_idempotent: false,
            },
        }
    }

    /// Create a retry layer with a fully custom configuration.
    pub fn with_config(config: RetryConfig) -> Self {
        Self { config }
    }

    pub fn should_retry_method(&self, method: HttpMethod) -> bool {
        method.is_idempotent() || self.config.retry_non_idempotent
    }

    /// Execute `f`, retrying on failure up to `max_attempts` times.
    ///
    /// Returns the result of `f` on success, or `HttptoraError::RetryExhausted`
    /// when all attempts are exhausted.
    ///
    /// Requires the `tower` feature (enabled by default).
    #[cfg(feature = "tower")]
    pub async fn execute<F, Fut, T, E>(&self, f: F) -> Result<T, HttptoraError>
    where
        F: Fn() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        E: std::fmt::Display,
    {
        let mut last_error: Option<E> = None;

        for attempt in 0..self.config.max_attempts {
            match f().await {
                Ok(value) => return Ok(value),
                Err(e) => {
                    last_error = Some(e);
                    if attempt < self.config.max_attempts - 1 {
                        let delay = self.compute_delay(attempt);
                        tokio::time::sleep(delay).await;
                    }
                }
            }
        }

        let reason = last_error
            .as_ref()
            .map(|e| e.to_string())
            .unwrap_or_else(|| "unknown error".to_owned());

        Err(HttptoraError::RetryExhausted {
            attempts: self.config.max_attempts,
            reason,
        })
    }

    #[cfg(feature = "tower")]
    pub async fn execute_for_method<F, Fut, T, E>(
        &self,
        method: HttpMethod,
        f: F,
    ) -> Result<T, HttptoraError>
    where
        F: Fn() -> Fut,
        Fut: Future<Output = Result<T, E>>,
        E: std::fmt::Display,
    {
        if self.should_retry_method(method) {
            return self.execute(f).await;
        }

        f().await.map_err(|e| HttptoraError::RetryExhausted {
            attempts: 1,
            reason: e.to_string(),
        })
    }

    fn compute_delay(&self, attempt: usize) -> Duration {
        let bc = &self.config.backoff;
        let delay_secs = bc.base_delay.as_secs_f64() * bc.multiplier.powi(attempt as i32);
        let delay_secs = delay_secs.min(bc.max_delay.as_secs_f64());
        let delay_secs = if bc.jitter {
            fastrand::f64() * delay_secs
        } else {
            delay_secs
        };
        Duration::from_secs_f64(delay_secs)
    }
}

#[cfg(all(test, feature = "tower"))]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[tokio::test]
    async fn retry_succeeds_on_first_attempt() {
        let retry = RetryLayer::new(3, Duration::from_millis(10));
        let result = retry.execute(|| async { Ok::<_, String>(42) }).await;
        assert_eq!(result.unwrap(), 42);
    }

    #[tokio::test]
    async fn retry_exhausted() {
        let retry = RetryLayer::new(2, Duration::from_millis(10));
        let counter = AtomicUsize::new(0);
        let result = retry
            .execute(|| async {
                counter.fetch_add(1, Ordering::SeqCst);
                Err::<(), String>("fail".into())
            })
            .await;
        assert!(result.is_err());
        assert_eq!(counter.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn retry_succeeds_after_retries() {
        let retry = RetryLayer::new(3, Duration::from_millis(10));
        let counter = AtomicUsize::new(0);
        let result = retry
            .execute(|| async {
                let prev = counter.fetch_add(1, Ordering::SeqCst);
                if prev < 1 {
                    Err::<(), String>("fail".into())
                } else {
                    Ok::<_, String>(())
                }
            })
            .await;
        assert!(result.is_ok());
        assert_eq!(counter.load(Ordering::SeqCst), 2);
    }
}
