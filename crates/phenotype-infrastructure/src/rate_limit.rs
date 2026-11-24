//! Token bucket rate limiter

use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Rate limit configuration
#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub capacity: u32,
    pub refill_rate: u32, // tokens per second
    pub refill_interval: Duration,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            capacity: 100,
            refill_rate: 10,
            refill_interval: Duration::from_secs(1),
        }
    }
}

struct TokenBucketInner {
    tokens: f64,
    last_refill: Instant,
}

/// Token bucket rate limiter
pub struct TokenBucket {
    config: RateLimitConfig,
    inner: Arc<Mutex<TokenBucketInner>>,
}

impl TokenBucket {
    pub fn new(config: RateLimitConfig) -> Self {
        Self {
            config: config.clone(),
            inner: Arc::new(Mutex::new(TokenBucketInner {
                tokens: config.capacity as f64,
                last_refill: Instant::now(),
            })),
        }
    }

    /// Try to acquire tokens, returns true if successful
    pub async fn try_acquire(&self, tokens: u32) -> bool {
        let mut inner = self.inner.lock().await;

        self.refill(&mut inner);

        if inner.tokens >= tokens as f64 {
            inner.tokens -= tokens as f64;
            true
        } else {
            false
        }
    }

    /// Acquire tokens, waiting if necessary
    pub async fn acquire(&self, tokens: u32) {
        while !self.try_acquire(tokens).await {
            tokio::time::sleep(self.config.refill_interval / 10).await;
        }
    }

    /// Get current token count
    pub async fn available_tokens(&self) -> u32 {
        let mut inner = self.inner.lock().await;
        self.refill(&mut inner);
        inner.tokens as u32
    }

    fn refill(&self, inner: &mut TokenBucketInner) {
        let now = Instant::now();
        let elapsed = now.duration_since(inner.last_refill);
        let tokens_to_add =
            elapsed.as_secs_f64() * self.config.refill_rate as f64;

        inner.tokens = (inner.tokens + tokens_to_add).min(self.config.capacity as f64);
        inner.last_refill = now;
    }
}

/// Multi-bucket rate limiter for different keys
pub struct RateLimiter {
    config: RateLimitConfig,
    buckets: Arc<dashmap::DashMap<String, TokenBucket>>,
}

impl RateLimiter {
    pub fn new(config: RateLimitConfig) -> Self {
        Self {
            config,
            buckets: Arc::new(dashmap::DashMap::new()),
        }
    }

    pub async fn check_key(&self, key: &str, tokens: u32) -> bool {
        let bucket = self
            .buckets
            .entry(key.to_string())
            .or_insert_with(|| TokenBucket::new(self.config.clone()))
            .clone();

        bucket.try_acquire(tokens).await
    }

    pub async fn acquire_key(&self, key: &str, tokens: u32) {
        let bucket = self
            .buckets
            .entry(key.to_string())
            .or_insert_with(|| TokenBucket::new(self.config.clone()))
            .clone();

        bucket.acquire(tokens).await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn fr_rate_limit_001_acquire_tokens() {
        let bucket = TokenBucket::new(RateLimitConfig::default());

        // Should be able to acquire initial capacity
        for _ in 0..100 {
            assert!(bucket.try_acquire(1).await);
        }

        // Should be exhausted
        assert!(!bucket.try_acquire(1).await);
    }

    #[tokio::test]
    async fn fr_rate_limit_002_token_refill() {
        let config = RateLimitConfig {
            capacity: 5,
            refill_rate: 100, // 100 tokens per second
            refill_interval: Duration::from_millis(10),
        };
        let bucket = TokenBucket::new(config);

        // Exhaust tokens
        for _ in 0..5 {
            assert!(bucket.try_acquire(1).await);
        }
        assert!(!bucket.try_acquire(1).await);

        // Wait for refill
        tokio::time::sleep(Duration::from_millis(50)).await;

        // Should have refilled some tokens
        assert!(bucket.available_tokens().await > 0);
    }

    #[tokio::test]
    async fn fr_rate_limit_003_multi_key() {
        let limiter = RateLimiter::new(RateLimitConfig::default());

        // Each key gets its own bucket
        assert!(limiter.check_key("key1", 1).await);
        assert!(limiter.check_key("key2", 1).await);

        // Same key shares bucket
        assert!(limiter.check_key("key1", 1).await);
    }
}
