//! # httpora-core
//!
//! Ergonomic HTTP middleware building blocks — rate limiting, retries, circuit breakers,
//! and request/response helpers — for Tower-based HTTP services.
//!
//! ## Quick Start
//!
//! ```rust
//! use httpora_core::{RateLimiter, RetryLayer, CircuitBreaker};
//! use std::time::Duration;
//!
//! // Create a token bucket rate limiter
//! let limiter = RateLimiter::token_bucket(100, 10.0);
//!
//! // Configure retry with exponential backoff
//! let retry = RetryLayer::new(3, Duration::from_millis(100));
//!
//! // Create a circuit breaker
//! let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
//! ```

pub mod builder;
pub mod error;
pub mod middleware;

pub use builder::{RequestExtractor, ResponseBuilder};
pub use error::HttptoraError;
pub use middleware::circuit_breaker::CircuitBreaker;
pub use middleware::cors::{CorsConfig, CorsLayer};
pub use middleware::rate_limit::RateLimiter;
pub use middleware::retry::{BackoffConfig, HttpMethod, RetryConfig, RetryLayer};

// Re-export key config types
pub use middleware::circuit_breaker::CircuitBreakerConfig;
pub use middleware::rate_limit::RateLimitConfig;
