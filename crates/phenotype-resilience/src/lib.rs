//! # phenotype-resilience
//!
//! Shared resilience primitives for Phenotype-org services.
//!
//! Seeded from `tracely-sentinel` (PhenoObservability) per hexagonal/DRY
//! audit.  Each primitive is a zero-observability-coupling module that any
//! Phenotype crate can consume as a path or crates.io dependency.
//!
//! ## Primitives
//!
//! | Primitive | Type | Key method |
//! |-----------|------|-----------|
//! | Token-bucket rate limiter | [`rate_limiter::TokenBucket`] | `try_acquire() -> Result` |
//! | Leaky-bucket rate limiter | [`rate_limiter::LeakyBucket`] | `try_add() -> Result` |
//! | Circuit breaker | [`circuit_breaker::CircuitBreaker`] | `execute(f)` / `record_{success,failure}` |
//! | Bulkhead | [`bulkhead::Bulkhead`] | `try_acquire(partition).await` |
//!
//! ## Quick start
//!
//! ```rust
//! use phenotype_resilience::rate_limiter::TokenBucket;
//! use phenotype_resilience::circuit_breaker::{CircuitBreaker, CircuitState};
//! use phenotype_resilience::bulkhead::Bulkhead;
//! use std::time::Duration;
//!
//! // Rate limiter: 100 tokens, refill at 10/sec
//! let mut limiter = TokenBucket::new(100, 10);
//! assert!(limiter.try_acquire().is_ok());
//!
//! // Circuit breaker: trip after 5 failures, recover after 60s
//! let mut cb = CircuitBreaker::new(5, Duration::from_secs(60));
//! assert_eq!(cb.state(), CircuitState::Closed);
//!
//! // Bulkhead: 3 partitions, 10 slots each
//! let bh = Bulkhead::new(3, 10);
//! assert_eq!(bh.partition_capacity(), 10);
//! ```

pub mod bulkhead;
pub mod circuit_breaker;
pub mod error;
pub mod rate_limiter;

pub use bulkhead::{Bulkhead, BulkheadGuard};
pub use circuit_breaker::{CircuitBreaker, CircuitState};
pub use error::ResilienceError;
pub use rate_limiter::{LeakyBucket, TokenBucket};
