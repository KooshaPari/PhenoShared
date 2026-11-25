//! # Phenotype Infrastructure
//!
//! Infrastructure concerns for distributed systems:
//! - Generic connection pooling
//! - Circuit breakers
//! - Rate limiting
//! - Bulkhead patterns

use thiserror::Error;

pub mod bulkhead;
pub mod circuit;
pub mod pool;
pub mod rate_limit;

/// Infrastructure errors
#[derive(Error, Debug, Clone)]
pub enum InfrastructureError {
    #[error("Pool exhausted: {0}")]
    PoolExhausted(String),
    #[error("Circuit breaker open: {0}")]
    CircuitOpen(String),
    #[error("Rate limit exceeded: {0}")]
    RateLimitExceeded(String),
    #[error("Bulkhead full: {0}")]
    BulkheadFull(String),
    #[error("Timeout: {0}")]
    Timeout(String),
    #[error("Other: {0}")]
    Other(String),
}

pub use bulkhead::{Bulkhead, BulkheadConfig};
pub use circuit::{CircuitBreaker, CircuitConfig, CircuitState};
pub use pool::{ConnectionPool, PoolConfig, PooledConnection};
pub use rate_limit::{RateLimitConfig, RateLimiter, TokenBucket};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fr_infra_001_error_display() {
        let err = InfrastructureError::PoolExhausted("test".to_string());
        assert!(err.to_string().contains("Pool exhausted"));
    }
}
