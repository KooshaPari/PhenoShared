//! Token-bucket rate limiter.
//!
//! # Design
//! A `TokenBucket` starts full (`capacity` tokens). Each call to
//! [`TokenBucket::try_acquire`] consumes one token.  Tokens are
//! replenished at `refill_rate` per second on the next call after
//! sufficient time has elapsed.  This is **not** thread-safe by itself;
//! wrap in a `Mutex` / `RwLock` when sharing across tasks.
//!
//! A [`LeakyBucket`] enforces a strict output rate by queuing arrivals
//! up to `capacity`; excess arrivals are rejected immediately.

use std::time::Instant;

use crate::error::ResilienceError;

// ── Token Bucket ─────────────────────────────────────────────────────────────

/// Token-bucket rate limiter allowing burst traffic up to `capacity`,
/// then refilling at a steady `refill_rate` (tokens per second).
#[derive(Debug)]
pub struct TokenBucket {
    capacity: usize,
    tokens: usize,
    refill_rate: usize,
    last_refill: Instant,
}

impl TokenBucket {
    /// Create a token bucket.
    ///
    /// # Panics
    /// Panics if `capacity == 0`.
    pub fn new(capacity: usize, refill_rate: usize) -> Self {
        assert!(capacity > 0, "TokenBucket capacity must be > 0");
        Self {
            capacity,
            tokens: capacity,
            refill_rate,
            last_refill: Instant::now(),
        }
    }

    /// Refill tokens based on elapsed time (called lazily on acquire).
    fn refill(&mut self) {
        let elapsed_secs = self.last_refill.elapsed().as_secs_f64();
        let new_tokens = (elapsed_secs * self.refill_rate as f64) as usize;
        if new_tokens > 0 {
            self.tokens = (self.tokens + new_tokens).min(self.capacity);
            self.last_refill = Instant::now();
        }
    }

    /// Try to acquire one token.
    ///
    /// Returns `Ok(())` if a token was available, `Err(RateLimitExceeded)`
    /// otherwise.
    pub fn try_acquire(&mut self) -> Result<(), ResilienceError> {
        self.refill();
        if self.tokens > 0 {
            self.tokens -= 1;
            Ok(())
        } else {
            Err(ResilienceError::RateLimitExceeded)
        }
    }

    /// Remaining tokens without triggering a refill.
    pub fn remaining(&self) -> usize {
        self.tokens
    }

    /// Configured refill rate (tokens / second).
    pub fn refill_rate(&self) -> usize {
        self.refill_rate
    }

    /// Configured burst capacity.
    pub fn capacity(&self) -> usize {
        self.capacity
    }
}

// ── Leaky Bucket ─────────────────────────────────────────────────────────────

/// Leaky-bucket rate limiter enforcing a strict output rate.
///
/// Arrivals are queued up to `capacity`; arrivals beyond capacity are
/// rejected.  The queue drains at `leak_rate` entries per second.
#[derive(Debug)]
pub struct LeakyBucket {
    capacity: usize,
    leak_rate: usize,
    last_leak: Instant,
    pending: usize,
}

impl LeakyBucket {
    /// Create a leaky bucket.
    ///
    /// # Panics
    /// Panics if `capacity == 0`.
    pub fn new(capacity: usize, leak_rate: usize) -> Self {
        assert!(capacity > 0, "LeakyBucket capacity must be > 0");
        Self {
            capacity,
            leak_rate,
            last_leak: Instant::now(),
            pending: 0,
        }
    }

    fn leak(&mut self) {
        let leaked = (self.last_leak.elapsed().as_secs_f64() * self.leak_rate as f64) as usize;
        if leaked > 0 {
            self.pending = self.pending.saturating_sub(leaked);
            self.last_leak = Instant::now();
        }
    }

    /// Try to enqueue a request.
    ///
    /// Returns `Ok(())` if accepted, `Err(RateLimitExceeded)` if the bucket is
    /// full.
    pub fn try_add(&mut self) -> Result<(), ResilienceError> {
        self.leak();
        if self.pending < self.capacity {
            self.pending += 1;
            Ok(())
        } else {
            Err(ResilienceError::RateLimitExceeded)
        }
    }

    /// Whether the bucket has any remaining capacity.
    pub fn has_capacity(&self) -> bool {
        self.pending < self.capacity
    }

    /// Number of queued (pending) entries.
    pub fn pending(&self) -> usize {
        self.pending
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── TokenBucket ──────────────────────────────────────────────────────────

    #[test]
    fn token_bucket_starts_full() {
        let bucket = TokenBucket::new(10, 5);
        assert_eq!(bucket.remaining(), 10);
    }

    #[test]
    fn token_bucket_consumes_token_on_acquire() {
        let mut bucket = TokenBucket::new(10, 5);
        assert!(bucket.try_acquire().is_ok());
        assert_eq!(bucket.remaining(), 9);
    }

    #[test]
    fn token_bucket_exhaustion_returns_err() {
        let mut bucket = TokenBucket::new(1, 5);
        assert!(bucket.try_acquire().is_ok());
        let err = bucket.try_acquire().unwrap_err();
        assert_eq!(err, ResilienceError::RateLimitExceeded);
    }

    #[test]
    fn token_bucket_sequential_exhaustion() {
        let mut bucket = TokenBucket::new(3, 5);
        for _ in 0..3 {
            assert!(bucket.try_acquire().is_ok());
        }
        assert!(bucket.try_acquire().is_err());
        assert!(bucket.try_acquire().is_err());
    }

    #[test]
    fn token_bucket_capacity_never_exceeded_after_time() {
        let mut bucket = TokenBucket::new(5, 100);
        std::thread::sleep(std::time::Duration::from_millis(100));
        // Force refill path
        let _ = bucket.try_acquire();
        assert!(bucket.remaining() <= 5);
    }

    #[test]
    fn token_bucket_various_capacities_start_full() {
        for cap in [1usize, 5, 10, 100, 1000] {
            assert_eq!(TokenBucket::new(cap, 5).remaining(), cap);
        }
    }

    #[test]
    fn token_bucket_refill_rate_accessor() {
        let bucket = TokenBucket::new(10, 7);
        assert_eq!(bucket.refill_rate(), 7);
    }

    #[test]
    fn token_bucket_capacity_accessor() {
        let bucket = TokenBucket::new(42, 1);
        assert_eq!(bucket.capacity(), 42);
    }

    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn token_bucket_zero_capacity_panics() {
        let _ = TokenBucket::new(0, 5);
    }

    // ── LeakyBucket ──────────────────────────────────────────────────────────

    #[test]
    fn leaky_bucket_accepts_up_to_capacity() {
        let mut bucket = LeakyBucket::new(3, 10);
        assert!(bucket.try_add().is_ok());
        assert!(bucket.try_add().is_ok());
        assert!(bucket.try_add().is_ok());
        assert!(bucket.try_add().is_err());
    }

    #[test]
    fn leaky_bucket_has_capacity_initially() {
        let bucket = LeakyBucket::new(5, 10);
        assert!(bucket.has_capacity());
    }

    #[test]
    fn leaky_bucket_pending_tracked() {
        let mut bucket = LeakyBucket::new(5, 10);
        bucket.try_add().unwrap();
        bucket.try_add().unwrap();
        assert_eq!(bucket.pending(), 2);
    }

    #[test]
    fn leaky_bucket_rejects_over_capacity() {
        let mut bucket = LeakyBucket::new(2, 10);
        bucket.try_add().unwrap();
        bucket.try_add().unwrap();
        let err = bucket.try_add().unwrap_err();
        assert_eq!(err, ResilienceError::RateLimitExceeded);
    }

    #[test]
    fn leaky_bucket_various_capacities() {
        for cap in [1usize, 5, 10, 100] {
            let mut b = LeakyBucket::new(cap, 10);
            for _ in 0..cap {
                assert!(b.try_add().is_ok());
            }
            assert!(b.try_add().is_err());
        }
    }

    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn leaky_bucket_zero_capacity_panics() {
        let _ = LeakyBucket::new(0, 10);
    }
}
