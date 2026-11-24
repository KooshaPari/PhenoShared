//! Per-account token-bucket rate limiter for the routing plane.
//!
//! Delegates to `phenotype-rate-limit::TokenBucket`.  Each account key gets
//! its own bucket; the defaults (100 tokens, 10 tokens/sec) match OmniRoute's
//! standard per-account quota and can be overridden at construction time.

pub use phenotype_rate_limit::{Error, Result, TokenBucket};

/// Default token-bucket capacity for a routing-plane account.
pub const DEFAULT_CAPACITY: u64 = 100;
/// Default refill rate (tokens per second) for a routing-plane account.
pub const DEFAULT_REFILL_RATE: f64 = 10.0;

/// A rate limiter for a single routing-plane account.
#[derive(Debug, Clone)]
pub struct RateLimiter {
    bucket: TokenBucket,
}

impl RateLimiter {
    /// Create with default capacity and refill rate.
    pub fn new() -> Self {
        Self {
            // Capacity and rate are hardcoded defaults; infallible.
            bucket: TokenBucket::new(DEFAULT_CAPACITY, DEFAULT_REFILL_RATE)
                .expect("default config is always valid"),
        }
    }

    /// Create with explicit capacity (tokens) and refill rate (tokens/sec).
    pub fn with_quota(capacity: u64, refill_rate: f64) -> Result<Self> {
        Ok(Self {
            bucket: TokenBucket::new(capacity, refill_rate)?,
        })
    }

    /// Attempt to consume `tokens` for this request.  Returns `Ok(())` if
    /// allowed or `Err(RateLimited { retry_after })` if the bucket is empty.
    pub fn try_consume(&self, tokens: u64) -> Result<()> {
        self.bucket.try_consume(tokens)
    }

    /// Available tokens at this instant (informational; not authoritative).
    pub fn available(&self) -> f64 {
        self.bucket.available()
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_constructs_and_allows_requests() {
        let rl = RateLimiter::new();
        assert!(rl.try_consume(1).is_ok());
    }

    #[test]
    fn with_quota_small_capacity_exhausts() {
        let rl = RateLimiter::with_quota(2, 1.0).unwrap();
        rl.try_consume(2).unwrap();
        assert!(rl.try_consume(1).is_err());
    }

    #[test]
    fn available_reports_current_tokens() {
        let rl = RateLimiter::new();
        let before = rl.available();
        rl.try_consume(10).unwrap();
        let after = rl.available();
        assert!(before > after, "tokens should decrease after consume");
    }
}
