//! phenotype-rate-limit — token-bucket rate limiter.
//!
//! A thread-safe token-bucket implementation with configurable capacity and
//! refill rate. Designed for per-account or per-key quota enforcement in the
//! routing plane.

use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use thiserror::Error;

/// Errors from the rate-limit subsystem.
#[derive(Debug, Error)]
pub enum Error {
    /// The requested token count exceeds the bucket capacity.
    #[error("requested {requested} tokens exceeds bucket capacity {capacity}")]
    ExceedsCapacity { requested: u64, capacity: u64 },
    /// Rate limit exhausted; caller should wait `retry_after`.
    #[error("rate limit exhausted; retry after {retry_after:?}")]
    RateLimited { retry_after: Duration },
    /// Configuration error (e.g. zero capacity or zero refill rate).
    #[error("invalid rate-limit config: {0}")]
    InvalidConfig(String),
}

pub type Result<T> = std::result::Result<T, Error>;

/// Inner state of the token bucket (lock-protected).
#[derive(Debug)]
struct BucketState {
    tokens: f64,
    last_refill: Instant,
}

/// A thread-safe token-bucket rate limiter.
///
/// Tokens refill continuously at `refill_rate` tokens/second up to `capacity`.
#[derive(Debug, Clone)]
pub struct TokenBucket {
    /// Maximum token count.
    capacity: f64,
    /// Token refill rate in tokens per second.
    refill_rate: f64,
    state: Arc<Mutex<BucketState>>,
}

impl TokenBucket {
    /// Create a new bucket with the given capacity and refill rate (tokens/sec).
    pub fn new(capacity: u64, refill_rate: f64) -> std::result::Result<Self, Error> {
        if capacity == 0 {
            return Err(Error::InvalidConfig("capacity must be > 0".into()));
        }
        if refill_rate <= 0.0 {
            return Err(Error::InvalidConfig("refill_rate must be > 0".into()));
        }
        Ok(Self {
            capacity: capacity as f64,
            refill_rate,
            state: Arc::new(Mutex::new(BucketState {
                tokens: capacity as f64,
                last_refill: Instant::now(),
            })),
        })
    }

    /// Refill tokens based on elapsed time (called before every check/consume).
    fn refill(state: &mut BucketState, capacity: f64, refill_rate: f64) {
        let now = Instant::now();
        let elapsed = now.duration_since(state.last_refill).as_secs_f64();
        state.tokens = (state.tokens + elapsed * refill_rate).min(capacity);
        state.last_refill = now;
    }

    /// Try to consume `tokens` from the bucket.
    ///
    /// Returns `Ok(())` if tokens were available, or `Err(RateLimited { retry_after })`.
    pub fn try_consume(&self, tokens: u64) -> Result<()> {
        if tokens as f64 > self.capacity {
            return Err(Error::ExceedsCapacity {
                requested: tokens,
                capacity: self.capacity as u64,
            });
        }
        let mut state = self.state.lock().unwrap();
        Self::refill(&mut state, self.capacity, self.refill_rate);
        if state.tokens >= tokens as f64 {
            state.tokens -= tokens as f64;
            Ok(())
        } else {
            let deficit = tokens as f64 - state.tokens;
            let wait_secs = deficit / self.refill_rate;
            Err(Error::RateLimited {
                retry_after: Duration::from_secs_f64(wait_secs),
            })
        }
    }

    /// Peek at the current available tokens without consuming any.
    pub fn available(&self) -> f64 {
        let mut state = self.state.lock().unwrap();
        Self::refill(&mut state, self.capacity, self.refill_rate);
        state.tokens
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn consume_within_capacity_succeeds() {
        let bucket = TokenBucket::new(10, 1.0).unwrap();
        assert!(bucket.try_consume(5).is_ok());
        assert!(bucket.try_consume(5).is_ok());
    }

    #[test]
    fn consume_over_available_fails_with_retry_after() {
        let bucket = TokenBucket::new(5, 1.0).unwrap();
        bucket.try_consume(5).unwrap();
        let err = bucket.try_consume(1).unwrap_err();
        match err {
            Error::RateLimited { retry_after } => {
                // Should wait approximately 1 second for 1 token at 1/s rate.
                assert!(retry_after >= Duration::from_millis(900));
            }
            other => panic!("unexpected error: {other}"),
        }
    }

    #[test]
    fn exceeds_capacity_is_rejected() {
        let bucket = TokenBucket::new(5, 10.0).unwrap();
        let err = bucket.try_consume(10).unwrap_err();
        assert!(matches!(err, Error::ExceedsCapacity { .. }));
    }

    #[test]
    fn invalid_config_zero_capacity() {
        assert!(TokenBucket::new(0, 1.0).is_err());
    }

    #[test]
    fn invalid_config_zero_rate() {
        assert!(TokenBucket::new(10, 0.0).is_err());
    }

    #[test]
    fn available_starts_at_capacity() {
        let bucket = TokenBucket::new(100, 10.0).unwrap();
        assert!((bucket.available() - 100.0).abs() < 1.0);
    }

    #[test]
    fn refill_over_time() {
        let bucket = TokenBucket::new(10, 1000.0).unwrap(); // very fast refill
        bucket.try_consume(10).unwrap();
        // Sleep a tiny bit — at 1000 tokens/sec, 2ms ≈ 2 tokens.
        std::thread::sleep(Duration::from_millis(5));
        assert!(bucket.try_consume(1).is_ok(), "should have refilled by now");
    }

    #[test]
    fn bucket_is_clone_and_shared() {
        let b1 = TokenBucket::new(10, 1.0).unwrap();
        let b2 = b1.clone();
        b1.try_consume(5).unwrap();
        // Both handles share state.
        let err = b2.try_consume(10).unwrap_err();
        assert!(matches!(err, Error::RateLimited { .. }));
    }
}
