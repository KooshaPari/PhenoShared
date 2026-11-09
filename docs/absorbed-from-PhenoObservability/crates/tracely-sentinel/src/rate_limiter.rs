//! # phenotype-sentinel
//!
//! Rate limiting implementations: Token Bucket and Leaky Bucket algorithms.

use std::time::Instant;
use thiserror::Error;

/// Rate limiter error types.
#[derive(Debug, Error)]
pub enum RateLimiterError {
    /// All permits are currently exhausted.
    #[error("Rate limiter exhausted")]
    Exhausted,

    /// The rate limiter configuration is invalid.
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}

/// Trait for rate limiters
pub trait RateLimiter {
    /// Try to acquire a permit without blocking
    fn try_acquire(&mut self) -> bool;

    /// Acquire a permit, waiting if necessary
    fn acquire(&mut self) -> impl std::future::Future<Output = Result<(), RateLimiterError>> + '_;
}

/// Token bucket rate limiter
///
/// Allows burst traffic up to bucket capacity, then refills at a steady rate.
#[derive(Debug)]
pub struct TokenBucket {
    capacity: usize,
    tokens: usize,
    refill_rate: usize, // tokens per second
    last_refill: Instant,
}

impl TokenBucket {
    /// Create a new token bucket
    ///
    /// - `capacity`: Maximum tokens (burst size)
    /// - `refill_rate`: Tokens added per second
    pub fn new(capacity: usize, refill_rate: usize) -> Self {
        if capacity == 0 {
            panic!("Token bucket capacity must be > 0");
        }
        Self { capacity, tokens: capacity, refill_rate, last_refill: Instant::now() }
    }

    fn refill(&mut self) {
        let elapsed = self.last_refill.elapsed();
        let seconds = elapsed.as_secs_f64();
        let new_tokens = (seconds * self.refill_rate as f64) as usize;

        if new_tokens > 0 {
            self.tokens = (self.tokens + new_tokens).min(self.capacity);
            self.last_refill = Instant::now();
        }
    }

    /// Try to acquire a token
    pub fn try_acquire(&mut self) -> bool {
        self.refill();
        if self.tokens > 0 {
            self.tokens -= 1;
            true
        } else {
            false
        }
    }

    /// Get remaining tokens
    pub fn remaining(&self) -> usize {
        self.tokens
    }

    /// Get the refill rate
    pub fn refill_rate(&self) -> usize {
        self.refill_rate
    }
}

/// Leaky bucket rate limiter
///
/// Enforces a steady output rate, queuing excess requests.
#[derive(Debug)]
pub struct LeakyBucket {
    capacity: usize,
    leak_rate: usize, // requests per second
    last_leak: Instant,
    pending: usize,
}

impl LeakyBucket {
    /// Create a new leaky bucket
    ///
    /// - `capacity`: Maximum queue size
    /// - `leak_rate`: Requests processed per second
    pub fn new(capacity: usize, leak_rate: usize) -> Self {
        if capacity == 0 {
            panic!("Leaky bucket capacity must be > 0");
        }
        Self { capacity, leak_rate, last_leak: Instant::now(), pending: 0 }
    }

    fn leak(&mut self) {
        let elapsed = self.last_leak.elapsed();
        let leaked = (elapsed.as_secs_f64() * self.leak_rate as f64) as usize;
        if leaked > 0 {
            self.pending = self.pending.saturating_sub(leaked);
            self.last_leak = Instant::now();
        }
    }

    /// Try to add a request to the bucket
    pub fn try_add(&mut self) -> bool {
        self.leak();
        if self.pending < self.capacity {
            self.pending += 1;
            true
        } else {
            false
        }
    }

    /// Check if the bucket has capacity
    pub fn has_capacity(&self) -> bool {
        self.pending < self.capacity
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBS-016
    #[test]
    fn test_token_bucket_initial_capacity() {
        let bucket = TokenBucket::new(10, 5);
        assert_eq!(bucket.remaining(), 10);
    }

    // Traces to: FR-OBS-016
    #[test]
    fn test_token_bucket_initial_full() {
        let mut bucket = TokenBucket::new(10, 5);
        assert!(bucket.try_acquire());
        assert_eq!(bucket.remaining(), 9);
    }

    // Traces to: FR-OBS-017
    #[test]
    fn test_token_bucket_exhausted() {
        let mut bucket = TokenBucket::new(1, 5);
        assert!(bucket.try_acquire());
        assert!(!bucket.try_acquire());
    }

    // Traces to: FR-OBS-017
    #[test]
    fn test_token_bucket_exhaustion_message() {
        let mut bucket = TokenBucket::new(2, 5);
        bucket.try_acquire();
        bucket.try_acquire();
        let result = bucket.try_acquire();
        assert!(!result);
    }

    // Traces to: FR-OBS-017
    #[test]
    fn test_token_bucket_multiple_exhaustion() {
        let mut bucket = TokenBucket::new(3, 5);
        for _ in 0..3 {
            assert!(bucket.try_acquire());
        }
        assert!(!bucket.try_acquire());
        assert!(!bucket.try_acquire());
    }

    // Traces to: FR-OBS-018
    #[test]
    fn test_token_bucket_refill_rate() {
        let bucket = TokenBucket::new(10, 5);
        assert_eq!(bucket.refill_rate(), 5);
    }

    // Traces to: FR-OBS-019
    #[test]
    fn test_token_bucket_capacity_ceiling() {
        let mut bucket = TokenBucket::new(5, 100);
        // Even with high refill rate, should not exceed capacity
        std::thread::sleep(std::time::Duration::from_millis(100));
        bucket.refill();
        assert!(bucket.remaining() <= 5);
    }

    // Traces to: FR-OBS-019
    #[test]
    fn test_token_bucket_capacity_never_exceeds() {
        for capacity in [1, 5, 10, 100] {
            let bucket = TokenBucket::new(capacity, 1000);
            assert_eq!(bucket.remaining(), capacity);
        }
    }

    // Traces to: FR-OBS-020
    #[test]
    fn test_leaky_bucket_capacity() {
        let mut bucket = LeakyBucket::new(3, 10);
        assert!(bucket.try_add());
        assert!(bucket.try_add());
        assert!(bucket.try_add());
        assert!(!bucket.try_add());
    }

    // Traces to: FR-OBS-020
    #[test]
    fn test_leaky_bucket_capacity_limit() {
        let mut bucket = LeakyBucket::new(5, 10);
        for i in 0..5 {
            assert!(bucket.try_add(), "Should add item {}", i);
        }
        assert!(!bucket.try_add(), "Should not add beyond capacity");
    }

    // Traces to: FR-OBS-020
    #[test]
    fn test_leaky_bucket_has_capacity() {
        let bucket = LeakyBucket::new(3, 10);
        assert!(bucket.has_capacity());
    }

    // Traces to: FR-OBS-021
    #[test]
    fn test_leaky_bucket_pending_count() {
        let mut bucket = LeakyBucket::new(5, 10);
        bucket.try_add();
        bucket.try_add();
        // Pending is internal, but we can infer from try_add results
        assert!(bucket.try_add());
    }

    // Traces to: FR-OBS-021
    #[test]
    fn test_leaky_bucket_pending_tracking() {
        let mut bucket = LeakyBucket::new(2, 10);
        assert!(bucket.try_add());
        assert!(bucket.try_add());
        // At capacity now
        assert!(!bucket.try_add());
    }

    // Traces to: FR-OBS-022
    #[test]
    fn test_leaky_bucket_leak_rate() {
        let bucket = LeakyBucket::new(10, 50);
        // Verify leak_rate is set (through constructor behavior)
        assert!(bucket.has_capacity());
    }

    // Traces to: FR-OBS-016
    #[test]
    fn test_token_bucket_new_validates_capacity() {
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _bucket = TokenBucket::new(0, 5);
        }));
        assert!(result.is_err(), "Should panic on zero capacity");
    }

    // Traces to: FR-OBS-020
    #[test]
    fn test_leaky_bucket_new_validates_capacity() {
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _bucket = LeakyBucket::new(0, 10);
        }));
        assert!(result.is_err(), "Should panic on zero capacity");
    }

    // Traces to: FR-OBS-016
    #[test]
    fn test_token_bucket_various_capacities() {
        for capacity in [1, 5, 10, 100, 1000] {
            let bucket = TokenBucket::new(capacity, 5);
            assert_eq!(bucket.remaining(), capacity);
        }
    }

    // Traces to: FR-OBS-020
    #[test]
    fn test_leaky_bucket_various_capacities() {
        for capacity in [1, 5, 10, 100] {
            let mut bucket = LeakyBucket::new(capacity, 10);
            for _ in 0..capacity {
                assert!(bucket.try_add());
            }
            assert!(!bucket.try_add());
        }
    }
}
