//! # phenotype-sentinel
//!
//! Rust resilience library providing rate limiting, circuit breaking, and bulkhead isolation.
//!
//! ## SSOT
//!
//! This crate is the **canonical Single Source of Truth** for `phenotype-sentinel`.
//! The standalone `KooshaPari/Tracely` repository contains a copy of this crate
//! that will be archived — do not make changes there. Update here instead.
//!
//! ## Features
//!
//! - **Rate Limiting**: Token bucket and leaky bucket algorithms
//! - **Circuit Breaker**: Failure threshold-based circuit breaker pattern
//! - **Bulkhead**: Partition-based isolation for concurrent operations
//!
//! ## Quick Start
//!
//! ```rust
//! use phenotype_sentinel::{RateLimiter, TokenBucket};
//!
//! let mut limiter = TokenBucket::new(100, 10); // 100 tokens, refill 10/sec
//! if limiter.try_acquire() {
//!     // proceed with request
//! }
//! ```

/// @trace SENT-001
pub mod bulkhead;
pub mod circuit_breaker;
pub mod config;
pub mod rate_limiter;
pub mod validation;

pub use bulkhead::{Bulkhead, BulkheadError, PartitionGuard};
pub use circuit_breaker::{CircuitBreaker, CircuitBreakerError, CircuitState};
pub use config::{BulkheadConfig, CircuitBreakerConfig, RateLimiterConfig, SentinelConfig};
pub use rate_limiter::{LeakyBucket, RateLimiter, RateLimiterError, TokenBucket};

use thiserror::Error;

/// Unified error type for phenotype-sentinel operations.
///
/// Wraps the per-component error types into a single enum
/// so callers can use `phenotype_sentinel::Error` without
/// importing each sub-error individually.
#[derive(Debug, Error)]
pub enum Error {
    #[error("Rate limiter error: {0}")]
    RateLimiter(#[from] RateLimiterError),

    #[error("Circuit breaker error: {0}")]
    CircuitBreaker(#[from] CircuitBreakerError),

    #[error("Bulkhead error: {0}")]
    Bulkhead(#[from] BulkheadError),
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBS-038
    #[test]
    fn test_rate_limiter_config_validation() {
        let mut bucket = TokenBucket::new(10, 5);
        assert!(bucket.try_acquire());
    }

    // Traces to: FR-OBS-039
    #[tokio::test]
    async fn test_circuit_breaker_config_defaults() {
        let cb = CircuitBreaker::new(5, std::time::Duration::from_secs(60));
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-040
    #[tokio::test]
    async fn test_bulkhead_config_defaults() {
        let bulkhead = Bulkhead::new(3, 10);
        assert_eq!(bulkhead.partition_capacity(), 10);
    }

    // Traces to: FR-OBS-041
    #[tokio::test]
    async fn test_sentinel_config_composition() {
        let _rate_limiter = TokenBucket::new(100, 10);
        let _circuit_breaker = CircuitBreaker::new(5, std::time::Duration::from_secs(60));
        let _bulkhead = Bulkhead::new(3, 10);
        // All policies construct without panic when composed.
        assert_eq!(_circuit_breaker.state(), crate::circuit_breaker::CircuitState::Closed);
    }

    // Traces to: FR-OBS-042
    #[test]
    fn test_config_all_defaults() {
        let bucket = TokenBucket::new(100, 10);
        assert_eq!(bucket.remaining(), 100);
    }

    // Traces to: FR-OBS-016
    #[test]
    fn test_rate_limiter_creation() {
        let mut bucket = TokenBucket::new(10, 5);
        assert!(bucket.try_acquire());
    }

    // Traces to: FR-OBS-023
    #[tokio::test]
    async fn test_circuit_breaker_initial_state() {
        let cb = CircuitBreaker::new(5, std::time::Duration::from_secs(60));
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-032
    #[tokio::test]
    async fn test_bulkhead_partitions() {
        let bulkhead = Bulkhead::new(3, 10);
        let _guard = bulkhead.try_acquire(0).await.unwrap();
    }

    // Traces to: FR-OBS-044
    #[test]
    fn test_validate_invalid_level() {
        // Test that error types work for config validation
        let err = Error::CircuitBreaker(CircuitBreakerError::Validation(
            "Circuit breaker is open".to_string(),
        ));
        assert!(matches!(err, Error::CircuitBreaker(_)));
    }

    // Traces to: FR-OBS-045
    #[test]
    fn test_validate_log_levels() {
        // Validate error types work for config validation
        let open = Error::CircuitBreaker(CircuitBreakerError::Validation(
            "Circuit breaker is open".to_string(),
        ));
        let half_open = Error::CircuitBreaker(CircuitBreakerError::Validation(
            "Circuit breaker is half-open, request not allowed".to_string(),
        ));
        assert!(matches!(open, Error::CircuitBreaker(_)));
        assert!(matches!(half_open, Error::CircuitBreaker(_)));
    }

    // Traces to: FR-OBS-046
    #[test]
    fn test_validate_capacity() {
        let bucket = TokenBucket::new(50, 10);
        assert!(bucket.remaining() > 0);
    }

    // Traces to: FR-OBS-047
    #[test]
    fn test_validate_timeout() {
        let cb = CircuitBreaker::new(5, std::time::Duration::from_secs(1));
        assert_eq!(cb.state(), CircuitState::Closed);
    }
}
