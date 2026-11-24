//! # Phenotype Infrastructure
//!
//! Infrastructure concerns for distributed systems:
//! - Generic connection pooling
//! - Circuit breakers
//! - Rate limiting
//! - Bulkhead patterns

use std::sync::Arc;
use thiserror::Error;

pub mod pool;
pub mod circuit;
pub mod rate_limit;
pub mod bulkhead;

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
    #[error(transparent)]
    Other(Arc<std::sync::Arc<std::string::String>>),
}

pub use pool::{ConnectionPool, PooledConnection, PoolConfig};
pub use circuit::{CircuitBreaker, CircuitConfig, CircuitState};
pub use rate_limit::{RateLimiter, RateLimitConfig, TokenBucket};
pub use bulkhead::{Bulkhead, BulkheadConfig};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fr_infra_001_error_display() {
        let err = InfrastructureError::PoolExhausted("test".to_string());
        assert!(err.to_string().contains("Pool exhausted"));
    }
}
