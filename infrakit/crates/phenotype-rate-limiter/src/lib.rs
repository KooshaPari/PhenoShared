//! Rate limiting utilities

pub mod error;

pub use error::{RateLimitError, Result};

/// Token-bucket rate limiter.
///
/// Limits the number of requests that can be acquired within a time window.
/// After all tokens are consumed, `try_acquire` fails until `reset()` is
/// called or a time-based refill mechanism is implemented.
pub struct RateLimiter {
    capacity: u64,
    used: u64,
}

impl RateLimiter {
    /// Create a new rate limiter with the given capacity.
    pub fn new(capacity: u64) -> Self {
        Self { capacity, used: 0 }
    }

    /// Attempt to acquire a token. Returns `Ok` if a token is available,
    /// `Err(RateLimitError::RateLimited)` if the bucket is empty.
    pub fn try_acquire(&mut self) -> Result<()> {
        if self.used < self.capacity {
            self.used += 1;
            Ok(())
        } else {
            Err(RateLimitError::RateLimited)
        }
    }

    /// Reset the limiter, restoring all tokens to the bucket.
    ///
    /// Call this at the start of each time window (e.g., per second, per minute)
    /// to implement a simple fixed-window rate limiter.
    pub fn reset(&mut self) {
        self.used = 0;
    }

    /// Returns how many tokens remain.
    pub fn remaining(&self) -> u64 {
        self.capacity.saturating_sub(self.used)
    }

    /// Returns the total capacity.
    pub fn capacity(&self) -> u64 {
        self.capacity
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_acquire_within_capacity() {
        let mut limiter = RateLimiter::new(3);
        assert!(limiter.try_acquire().is_ok());
        assert!(limiter.try_acquire().is_ok());
        assert!(limiter.try_acquire().is_ok());
        assert_eq!(limiter.remaining(), 0);
    }

    #[test]
    fn test_acquire_exceeds_capacity() {
        let mut limiter = RateLimiter::new(2);
        assert!(limiter.try_acquire().is_ok());
        assert!(limiter.try_acquire().is_ok());
        assert!(limiter.try_acquire().is_err());
    }

    #[test]
    fn test_reset() {
        let mut limiter = RateLimiter::new(1);
        assert!(limiter.try_acquire().is_ok());
        assert!(limiter.try_acquire().is_err());
        limiter.reset();
        assert!(limiter.try_acquire().is_ok());
    }
}
