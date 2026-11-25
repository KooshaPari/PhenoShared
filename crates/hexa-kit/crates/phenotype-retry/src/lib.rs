//! phenotype-retry — exponential-backoff retry primitives.
//!
//! Provides synchronous retry with jittered exponential backoff and
//! configurable per-attempt predicates.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use thiserror::Error;

/// Errors produced by the retry machinery.
#[derive(Debug, Error)]
pub enum Error {
    /// All attempts exhausted; carries the last underlying error message.
    #[error("all {attempts} retry attempts exhausted: {last_error}")]
    Exhausted { attempts: u32, last_error: String },
    /// Policy configuration is invalid (e.g. zero attempts).
    #[error("invalid retry policy: {0}")]
    InvalidPolicy(String),
}

pub type Result<T> = std::result::Result<T, Error>;

/// Backoff strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BackoffStrategy {
    /// Fixed delay between each attempt.
    Fixed,
    /// Exponential backoff: `base * 2^attempt`.
    Exponential,
    /// Exponential backoff with full jitter (uniform in [0, base * 2^attempt]).
    ExponentialJitter,
}

impl Default for BackoffStrategy {
    fn default() -> Self {
        Self::ExponentialJitter
    }
}

/// Configuration for a retry policy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryPolicy {
    /// Maximum number of attempts (including the first try).
    pub max_attempts: u32,
    /// Base delay for backoff computation.
    pub base_delay: Duration,
    /// Maximum delay cap; backoff is clamped to this.
    pub max_delay: Duration,
    /// Backoff strategy.
    pub strategy: BackoffStrategy,
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(30),
            strategy: BackoffStrategy::ExponentialJitter,
        }
    }
}

impl RetryPolicy {
    /// Build a policy with the given maximum attempts and default backoff.
    pub fn with_attempts(max_attempts: u32) -> std::result::Result<Self, Error> {
        if max_attempts == 0 {
            return Err(Error::InvalidPolicy("max_attempts must be >= 1".into()));
        }
        Ok(Self {
            max_attempts,
            ..Default::default()
        })
    }

    /// Compute the delay before the `attempt`-th retry (0-indexed; first retry = 1).
    pub fn delay_for(&self, attempt: u32) -> Duration {
        let base_ms = self.base_delay.as_millis() as u64;
        let raw_ms: u64 = match self.strategy {
            BackoffStrategy::Fixed => base_ms,
            BackoffStrategy::Exponential => base_ms.saturating_mul(1u64 << attempt.min(62)),
            BackoffStrategy::ExponentialJitter => {
                let ceiling = base_ms.saturating_mul(1u64 << attempt.min(62));
                rand::thread_rng().gen_range(0..=ceiling)
            }
        };
        Duration::from_millis(raw_ms.min(self.max_delay.as_millis() as u64))
    }

    /// Retry a synchronous fallible closure according to this policy.
    ///
    /// `f` receives the current attempt index (0-based) and returns `Ok` or
    /// `Err(msg)` where `msg` is recorded on final exhaustion.
    pub fn retry_sync<F, T>(&self, mut f: F) -> Result<T>
    where
        F: FnMut(u32) -> std::result::Result<T, String>,
    {
        let mut last_error = String::new();
        for attempt in 0..self.max_attempts {
            match f(attempt) {
                Ok(v) => return Ok(v),
                Err(e) => {
                    last_error = e;
                    if attempt + 1 < self.max_attempts {
                        std::thread::sleep(self.delay_for(attempt));
                    }
                }
            }
        }
        Err(Error::Exhausted {
            attempts: self.max_attempts,
            last_error,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    #[test]
    fn succeeds_on_first_attempt() {
        let policy = RetryPolicy::with_attempts(3).unwrap();
        let result = policy.retry_sync(|_| Ok::<_, String>(42));
        assert_eq!(result.unwrap(), 42);
    }

    #[test]
    fn retries_and_succeeds() {
        let policy = RetryPolicy {
            max_attempts: 3,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(10),
            strategy: BackoffStrategy::Fixed,
        };
        let counter = Arc::new(AtomicU32::new(0));
        let c = counter.clone();
        let result = policy.retry_sync(|_| {
            let n = c.fetch_add(1, Ordering::SeqCst);
            if n < 2 {
                Err("not yet".to_string())
            } else {
                Ok(n)
            }
        });
        assert_eq!(result.unwrap(), 2);
        assert_eq!(counter.load(Ordering::SeqCst), 3);
    }

    #[test]
    fn exhausts_and_returns_error() {
        let policy = RetryPolicy {
            max_attempts: 2,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(5),
            strategy: BackoffStrategy::Fixed,
        };
        let err = policy
            .retry_sync(|_| Err::<(), _>("fail".to_string()))
            .unwrap_err();
        match err {
            Error::Exhausted { attempts, .. } => assert_eq!(attempts, 2),
            _ => panic!("unexpected error variant"),
        }
    }

    #[test]
    fn invalid_policy_zero_attempts() {
        assert!(RetryPolicy::with_attempts(0).is_err());
    }

    #[test]
    fn delay_for_exponential_capped_by_max_delay() {
        let policy = RetryPolicy {
            max_attempts: 5,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_millis(500),
            strategy: BackoffStrategy::Exponential,
        };
        // At high attempt indices the uncapped value would exceed max_delay.
        let d = policy.delay_for(10);
        assert!(d <= Duration::from_millis(500));
    }

    #[test]
    fn delay_for_jitter_within_bounds() {
        let policy = RetryPolicy {
            max_attempts: 5,
            base_delay: Duration::from_millis(50),
            max_delay: Duration::from_millis(1000),
            strategy: BackoffStrategy::ExponentialJitter,
        };
        for attempt in 0..5 {
            let d = policy.delay_for(attempt);
            assert!(d <= Duration::from_millis(1000));
        }
    }
}
