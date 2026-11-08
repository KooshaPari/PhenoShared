//! Configuration validation for Sentinel
//!
//! Provides validation for circuit breaker, rate limiter, and bulkhead configurations.

use crate::validation::{validate_field, Result, ValidationError, ValidationResult};
use serde::{Deserialize, Serialize};

/// Circuit breaker configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CircuitBreakerConfig {
    /// Failure threshold before opening
    pub failure_threshold: u32,
    /// Timeout in seconds before attempting reset
    pub timeout_seconds: u64,
    /// Success threshold in half-open state
    pub success_threshold: u32,
}

/// Rate limiter configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimiterConfig {
    /// Requests per time window
    pub requests: u32,
    /// Time window in seconds
    pub window_seconds: u64,
    /// Burst capacity (optional)
    pub burst: Option<u32>,
}

/// Bulkhead configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BulkheadConfig {
    /// Total concurrent slots
    pub max_concurrent: u32,
    /// Slots reserved for critical operations
    pub reserved_slots: u32,
    /// Timeout for waiting on slot
    pub wait_timeout_ms: u64,
}

/// Complete Sentinel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentinelConfig {
    pub circuit_breaker: Option<CircuitBreakerConfig>,
    pub rate_limiter: Option<RateLimiterConfig>,
    pub bulkhead: Option<BulkheadConfig>,
}

/// Validates circuit breaker configuration
pub fn validate_circuit_breaker(config: &CircuitBreakerConfig) -> Result<ValidationResult> {
    let mut result = ValidationResult::valid();

    // Validate failure_threshold
    if let Some(err) = validate_field(
        "failure_threshold",
        config.failure_threshold as f64,
        Some(1.0),
        Some(1000.0),
    ) {
        result.add_error(err);
    }

    // Validate timeout_seconds
    if let Some(err) =
        validate_field("timeout_seconds", config.timeout_seconds as f64, Some(1.0), Some(3600.0))
    {
        result.add_error(err);
    }

    // Validate success_threshold
    if let Some(err) =
        validate_field("success_threshold", config.success_threshold as f64, Some(1.0), Some(100.0))
    {
        result.add_error(err);
    }

    Ok(result)
}

/// Validates rate limiter configuration
pub fn validate_rate_limiter(config: &RateLimiterConfig) -> Result<ValidationResult> {
    let mut result = ValidationResult::valid();

    // Validate requests
    if let Some(err) =
        validate_field("requests", config.requests as f64, Some(1.0), Some(1_000_000.0))
    {
        result.add_error(err);
    }

    // Validate window_seconds
    if let Some(err) =
        validate_field("window_seconds", config.window_seconds as f64, Some(1.0), Some(86_400.0))
    {
        result.add_error(err);
    }

    // Additional validation: burst should be >= requests if specified
    if let Some(burst) = config.burst {
        if burst < config.requests {
            result.add_error(ValidationError {
                field: "burst".to_string(),
                message: "burst capacity must be >= requests per window".to_string(),
                error_type: "constraint".to_string(),
            });
        }
    }

    Ok(result)
}

/// Validates bulkhead configuration
pub fn validate_bulkhead(config: &BulkheadConfig) -> Result<ValidationResult> {
    let mut result = ValidationResult::valid();

    // Validate max_concurrent
    if let Some(err) =
        validate_field("max_concurrent", config.max_concurrent as f64, Some(1.0), Some(10_000.0))
    {
        result.add_error(err);
    }

    // Validate wait_timeout_ms
    if let Some(err) =
        validate_field("wait_timeout_ms", config.wait_timeout_ms as f64, Some(1.0), Some(60_000.0))
    {
        result.add_error(err);
    }

    // Additional validation: reserved slots < max_concurrent
    if config.reserved_slots >= config.max_concurrent {
        result.add_error(ValidationError {
            field: "reserved_slots".to_string(),
            message: "reserved_slots must be less than max_concurrent".to_string(),
            error_type: "constraint".to_string(),
        });
    }

    Ok(result)
}

/// Validates complete Sentinel configuration
pub fn validate_sentinel_config(config: &SentinelConfig) -> Result<ValidationResult> {
    let mut combined = ValidationResult::valid();

    if let Some(ref cb) = config.circuit_breaker {
        let result = validate_circuit_breaker(cb)?;
        combined.merge(result);
    }

    if let Some(ref rl) = config.rate_limiter {
        let result = validate_rate_limiter(rl)?;
        combined.merge(result);
    }

    if let Some(ref bh) = config.bulkhead {
        let result = validate_bulkhead(bh)?;
        combined.merge(result);
    }

    Ok(combined)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_circuit_breaker() {
        let config = CircuitBreakerConfig {
            failure_threshold: 5,
            timeout_seconds: 30,
            success_threshold: 2,
        };

        let result = validate_circuit_breaker(&config).unwrap();
        assert!(result.is_valid);
    }

    #[test]
    fn test_invalid_circuit_breaker_threshold() {
        let config = CircuitBreakerConfig {
            failure_threshold: 0,
            timeout_seconds: 30,
            success_threshold: 2,
        };

        let result = validate_circuit_breaker(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_valid_rate_limiter() {
        let config = RateLimiterConfig { requests: 100, window_seconds: 60, burst: Some(150) };

        let result = validate_rate_limiter(&config).unwrap();
        assert!(result.is_valid);
    }

    #[test]
    fn test_invalid_burst() {
        let config = RateLimiterConfig {
            requests: 100,
            window_seconds: 60,
            burst: Some(50), // burst < requests
        };

        let result = validate_rate_limiter(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_valid_bulkhead() {
        let config =
            BulkheadConfig { max_concurrent: 10, reserved_slots: 2, wait_timeout_ms: 5000 };

        let result = validate_bulkhead(&config).unwrap();
        assert!(result.is_valid);
    }

    #[test]
    fn test_invalid_reserved_slots() {
        let config = BulkheadConfig {
            max_concurrent: 10,
            reserved_slots: 10, // reserved >= max
            wait_timeout_ms: 5000,
        };

        let result = validate_bulkhead(&config).unwrap();
        assert!(!result.is_valid);
    }

    #[test]
    fn test_complete_sentinel_config() {
        let config = SentinelConfig {
            circuit_breaker: Some(CircuitBreakerConfig {
                failure_threshold: 5,
                timeout_seconds: 30,
                success_threshold: 2,
            }),
            rate_limiter: Some(RateLimiterConfig {
                requests: 1000,
                window_seconds: 60,
                burst: Some(2000),
            }),
            bulkhead: Some(BulkheadConfig {
                max_concurrent: 100,
                reserved_slots: 10,
                wait_timeout_ms: 10000,
            }),
        };

        let result = validate_sentinel_config(&config).unwrap();
        assert!(result.is_valid);
    }
}
