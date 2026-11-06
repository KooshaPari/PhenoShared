use std::sync::Mutex;
use std::time::{Duration, Instant};

use crate::error::HttptoraError;

use super::clock::{system_clock, Clock};

/// Rate limiter strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RateLimitStrategy {
    TokenBucket,
    FixedWindow,
}

/// Configuration for a rate limiter.
#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    /// Maximum number of tokens (token bucket) or requests (fixed window).
    pub capacity: u64,
    /// Tokens added per second (token bucket) or window size in seconds (fixed window).
    pub refill_rate: f64,
    /// Which rate-limiting strategy to use.
    pub strategy: RateLimitStrategy,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            capacity: 100,
            refill_rate: 10.0,
            strategy: RateLimitStrategy::TokenBucket,
        }
    }
}

// ---------------------------------------------------------------------------
// Token bucket internals
// ---------------------------------------------------------------------------

struct TokenBucket {
    capacity: f64,
    refill_rate: f64,
    tokens: f64,
    last_refill: Instant,
    clock: Clock,
}

impl TokenBucket {
    fn new(capacity: u64, refill_rate: f64, clock: Clock) -> Self {
        let cap = capacity as f64;
        let last_refill = clock();
        Self {
            capacity: cap,
            refill_rate,
            tokens: cap,
            last_refill,
            clock,
        }
    }

    /// Attempt to consume `tokens`. Returns `Ok(())` on success, or
    /// `Err(wait_duration)` if the caller must wait.
    fn consume(&mut self, tokens: f64) -> Result<(), Duration> {
        let now = (self.clock)();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        self.tokens = (self.capacity).min(self.tokens + elapsed * self.refill_rate);
        self.last_refill = now;

        if self.tokens >= tokens {
            self.tokens -= tokens;
            Ok(())
        } else {
            let deficit = tokens - self.tokens;
            let wait = Duration::from_secs_f64(deficit / self.refill_rate);
            Err(wait)
        }
    }
}

// ---------------------------------------------------------------------------
// Fixed-window internals
// ---------------------------------------------------------------------------

struct FixedWindow {
    limit: u64,
    window: Duration,
    count: u64,
    window_start: Instant,
    clock: Clock,
}

impl FixedWindow {
    fn new(limit: u64, window_seconds: f64, clock: Clock) -> Self {
        let window_start = clock();
        Self {
            limit,
            window: Duration::from_secs_f64(window_seconds),
            count: 0,
            window_start,
            clock,
        }
    }

    fn consume(&mut self) -> Result<(), Duration> {
        let now = (self.clock)();
        if now.duration_since(self.window_start) >= self.window {
            self.count = 0;
            self.window_start = now;
        }

        if self.count < self.limit {
            self.count += 1;
            Ok(())
        } else {
            let elapsed = now.duration_since(self.window_start);
            let remaining = self.window.checked_sub(elapsed).unwrap_or_default();
            Err(remaining)
        }
    }
}

// ---------------------------------------------------------------------------
// Public RateLimiter
// ---------------------------------------------------------------------------

/// A composable rate limiter supporting token-bucket and fixed-window strategies.
///
/// # Example
///
/// ```
/// use httpora_core::middleware::rate_limit::RateLimiter;
///
/// let limiter = RateLimiter::token_bucket(100, 10.0);
/// assert!(limiter.check(1.0).is_ok()); // first request passes
/// ```
pub struct RateLimiter {
    config: RateLimitConfig,
    inner: Mutex<Inner>,
}

enum Inner {
    TokenBucket(TokenBucket),
    FixedWindow(FixedWindow),
}

impl RateLimiter {
    /// Return the configuration of this rate limiter.
    pub fn config(&self) -> &RateLimitConfig {
        &self.config
    }

    /// Create a token-bucket rate limiter (burst-friendly).
    pub fn token_bucket(capacity: u64, refill_per_sec: f64) -> Self {
        Self::token_bucket_with_clock(capacity, refill_per_sec, system_clock())
    }

    pub fn token_bucket_with_clock(capacity: u64, refill_per_sec: f64, clock: Clock) -> Self {
        Self {
            config: RateLimitConfig {
                capacity,
                refill_rate: refill_per_sec,
                strategy: RateLimitStrategy::TokenBucket,
            },
            inner: Mutex::new(Inner::TokenBucket(TokenBucket::new(
                capacity,
                refill_per_sec,
                clock,
            ))),
        }
    }

    /// Create a fixed-window rate limiter.
    pub fn fixed_window(limit: u64, window_seconds: f64) -> Self {
        Self::fixed_window_with_clock(limit, window_seconds, system_clock())
    }

    pub fn fixed_window_with_clock(limit: u64, window_seconds: f64, clock: Clock) -> Self {
        Self {
            config: RateLimitConfig {
                capacity: limit,
                refill_rate: window_seconds,
                strategy: RateLimitStrategy::FixedWindow,
            },
            inner: Mutex::new(Inner::FixedWindow(FixedWindow::new(
                limit,
                window_seconds,
                clock,
            ))),
        }
    }

    /// Check whether a request should be allowed through.
    ///
    /// Returns `Ok(())` if the request passes, or
    /// `Err(HttptoraError::RateLimited { retry_after })` if it should be rejected.
    pub fn check(&self, tokens: f64) -> Result<(), HttptoraError> {
        let mut inner = self.inner.lock().map_err(|e| HttptoraError::Poisoned {
            detail: format!("rate limiter mutex: {e}"),
        })?;
        let result = match &mut *inner {
            Inner::TokenBucket(tb) => tb.consume(tokens),
            Inner::FixedWindow(fw) => fw.consume(),
        };
        match result {
            Ok(()) => Ok(()),
            Err(wait) => Err(HttptoraError::RateLimited { retry_after: wait }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn token_bucket_allows_initial_burst() {
        let limiter = RateLimiter::token_bucket(10, 10.0);
        for _ in 0..10 {
            assert!(limiter.check(1.0).is_ok());
        }
        // 11th should be rate-limited (we consumed all tokens)
        assert!(limiter.check(1.0).is_err());
    }

    #[test]
    fn fixed_window_allows_up_to_limit() {
        let limiter = RateLimiter::fixed_window(5, 1.0);
        for _ in 0..5 {
            assert!(limiter.check(1.0).is_ok());
        }
        assert!(limiter.check(1.0).is_err());
    }

    #[test]
    fn token_bucket_retry_after_duration() {
        let limiter = RateLimiter::token_bucket(1, 1.0);
        assert!(limiter.check(1.0).is_ok());
        match limiter.check(1.0) {
            Err(HttptoraError::RateLimited { retry_after }) => {
                assert!(retry_after > Duration::ZERO);
            }
            other => panic!("expected RateLimited, got {other:?}"),
        }
    }
}
