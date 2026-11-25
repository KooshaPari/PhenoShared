//! Shared error types for `phenotype-resilience`.

use thiserror::Error;

/// Errors returned by resilience primitives.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ResilienceError {
    /// Rate limit exceeded — caller should back off.
    #[error("rate limit exceeded")]
    RateLimitExceeded,

    /// Circuit breaker is open — downstream is considered unhealthy.
    #[error("circuit breaker is open")]
    CircuitOpen,

    /// Bulkhead capacity exhausted for the given partition.
    #[error("bulkhead partition {partition} exhausted (capacity {capacity})")]
    BulkheadExhausted {
        /// Partition index that was full.
        partition: usize,
        /// Per-partition capacity configured.
        capacity: usize,
    },

    /// Total bulkhead capacity across all partitions exhausted.
    #[error("bulkhead total capacity exhausted")]
    BulkheadTotalExhausted,
}
