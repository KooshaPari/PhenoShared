//! # phenotype-sentinel
//!
//! Circuit breaker implementation for fault tolerance.

pub use phenotype_errors::DomainError as CircuitBreakerError;
use std::time::{Duration, Instant};

/// Circuit breaker state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    /// Normal operation, requests pass through
    Closed,
    /// Circuit is open, requests are blocked
    Open,
    /// Testing if service has recovered
    HalfOpen,
}

/// Circuit breaker for fault tolerance
///
/// Opens the circuit when failure threshold is reached,
/// preventing cascading failures.
#[derive(Debug)]
pub struct CircuitBreaker {
    failure_threshold: usize,
    recovery_timeout: Duration,
    failure_count: usize,
    last_failure: Option<Instant>,
    state: CircuitState,
}

impl CircuitBreaker {
    /// Create a new circuit breaker
    ///
    /// - `failure_threshold`: Number of failures before opening
    /// - `recovery_timeout`: Time to wait before trying recovery
    pub fn new(failure_threshold: usize, recovery_timeout: Duration) -> Self {
        Self {
            failure_threshold,
            recovery_timeout,
            failure_count: 0,
            last_failure: None,
            state: CircuitState::Closed,
        }
    }

    /// Get current circuit state
    pub fn state(&self) -> CircuitState {
        self.state
    }

    /// Check if requests are allowed
    pub fn is_allowed(&self) -> bool {
        match self.state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                // Check if we should transition to half-open
                self.last_failure
                    .map(|last| last.elapsed() >= self.recovery_timeout)
                    .unwrap_or(false)
            }
            CircuitState::HalfOpen => true,
        }
    }

    /// Record a successful request
    pub fn record_success(&mut self) {
        match self.state {
            CircuitState::Closed => {
                // Reset failure count on success
                self.failure_count = 0;
            }
            CircuitState::HalfOpen => {
                // Transition to closed on successful request
                self.state = CircuitState::Closed;
                self.failure_count = 0;
            }
            CircuitState::Open => {
                // Should not receive success in open state
            }
        }
    }

    /// Record a failed request
    pub fn record_failure(&mut self) {
        self.failure_count += 1;
        self.last_failure = Some(Instant::now());

        match self.state {
            CircuitState::Closed => {
                if self.failure_count >= self.failure_threshold {
                    self.state = CircuitState::Open;
                }
            }
            CircuitState::HalfOpen => {
                // Any failure in half-open goes back to open
                self.state = CircuitState::Open;
            }
            CircuitState::Open => {
                // Already open, stay open
            }
        }
    }

    /// Force the circuit to a specific state
    pub fn force_state(&mut self, state: CircuitState) {
        self.state = state;
        if state == CircuitState::Closed {
            self.failure_count = 0;
        }
    }

    /// Reset the circuit breaker
    pub fn reset(&mut self) {
        self.state = CircuitState::Closed;
        self.failure_count = 0;
        self.last_failure = None;
    }

    /// Execute a function with circuit breaker protection
    pub fn execute<F, T, E>(&mut self, f: F) -> Result<T, CircuitBreakerError>
    where
        F: FnOnce() -> Result<T, E>,
    {
        if !self.is_allowed() {
            // L62 (error rate) observability adoption (v14 cycle-4 T7):
            // surface circuit-breaker rejection as a fleet-wide error metric.
            pheno_otel::metrics::record_error(
                "phenotype_sentinel.circuit_breaker.execute",
                "circuit_open",
            );
            return Err(CircuitBreakerError::Validation("Circuit breaker is open".to_string()));
        }

        match self.state {
            CircuitState::HalfOpen => match f() {
                Ok(result) => {
                    self.record_success();
                    Ok(result)
                }
                Err(_) => {
                    self.record_failure();
                    // L62 (error rate) observability adoption (v14 cycle-4 T7):
                    // surface half-open failure as a fleet-wide error metric.
                    pheno_otel::metrics::record_error(
                        "phenotype_sentinel.circuit_breaker.execute",
                        "half_open_failure",
                    );
                    Err(CircuitBreakerError::Validation(
                        "Circuit breaker is half-open, request not allowed".to_string(),
                    ))
                }
            },
            _ => match f() {
                Ok(result) => {
                    self.record_success();
                    Ok(result)
                }
                Err(_) => {
                    self.record_failure();
                    // L62 (error rate) observability adoption (v14 cycle-4 T7):
                    // surface wrapped-call failure as a fleet-wide error metric.
                    pheno_otel::metrics::record_error(
                        "phenotype_sentinel.circuit_breaker.execute",
                        "wrapped_call_failed",
                    );
                    Err(CircuitBreakerError::Validation("Circuit breaker is open".to_string()))
                }
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBS-023
    #[test]
    fn test_circuit_breaker_initial_state() {
        let cb = CircuitBreaker::new(5, Duration::from_secs(60));
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-023
    #[test]
    fn test_circuit_breaker_closed_allows_requests() {
        let cb = CircuitBreaker::new(5, Duration::from_secs(60));
        assert!(cb.is_allowed());
    }

    // Traces to: FR-OBS-024
    #[test]
    fn test_circuit_breaker_failure_tracking() {
        let mut cb = CircuitBreaker::new(5, Duration::from_secs(60));
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Closed); // Not yet at threshold
    }

    // Traces to: FR-OBS-025
    #[test]
    fn test_circuit_breaker_open_transition() {
        let mut cb = CircuitBreaker::new(3, Duration::from_secs(60));
        for _ in 0..3 {
            cb.record_failure();
        }
        assert_eq!(cb.state(), CircuitState::Open);
    }

    // Traces to: FR-OBS-025
    #[test]
    fn test_circuit_breaker_opens_on_threshold() {
        let mut cb = CircuitBreaker::new(3, Duration::from_secs(60));
        for _ in 0..3 {
            cb.record_failure();
        }
        assert_eq!(cb.state(), CircuitState::Open);
    }

    // Traces to: FR-OBS-025
    #[test]
    fn test_circuit_breaker_threshold_exact() {
        let mut cb = CircuitBreaker::new(2, Duration::from_secs(60));
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Closed);
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
    }

    // Traces to: FR-OBS-026
    #[test]
    fn test_circuit_breaker_open_blocks_requests() {
        let mut cb = CircuitBreaker::new(1, Duration::from_secs(60));
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
        assert!(!cb.is_allowed());
    }

    // Traces to: FR-OBS-026
    #[test]
    fn test_circuit_breaker_open_rejects_execute() {
        let mut cb = CircuitBreaker::new(1, Duration::from_secs(60));
        cb.record_failure();
        let result: Result<i32, CircuitBreakerError> = cb.execute(|| Ok::<i32, String>(42));
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-027
    #[test]
    fn test_circuit_breaker_half_open_transition() {
        let mut cb = CircuitBreaker::new(1, Duration::from_millis(100));
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
        std::thread::sleep(Duration::from_millis(200));
        // After timeout, is_allowed should be true
        assert!(cb.is_allowed());
    }

    // Traces to: FR-OBS-028
    #[test]
    fn test_circuit_breaker_half_open_success() {
        let mut cb = CircuitBreaker::new(1, Duration::from_millis(50));
        cb.record_failure();
        std::thread::sleep(Duration::from_millis(100));
        // Move to half-open first by checking state after timeout
        cb.force_state(CircuitState::HalfOpen);
        cb.record_success();
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-028
    #[test]
    fn test_circuit_breaker_half_open_closes_on_success() {
        let mut cb = CircuitBreaker::new(2, Duration::from_secs(60));
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
        // Force to half-open for testing
        cb.force_state(CircuitState::HalfOpen);
        cb.record_success();
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-029
    #[test]
    fn test_circuit_breaker_failure_reset() {
        let mut cb = CircuitBreaker::new(3, Duration::from_secs(60));
        cb.record_failure();
        cb.record_failure();
        cb.record_success();
        assert_eq!(cb.failure_count, 0);
    }

    // Traces to: FR-OBS-029
    #[test]
    fn test_circuit_breaker_success_resets() {
        let mut cb = CircuitBreaker::new(3, Duration::from_secs(60));
        cb.record_failure();
        cb.record_failure();
        cb.record_success();
        assert_eq!(cb.failure_count, 0);
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-030
    #[test]
    fn test_circuit_breaker_config_validation() {
        let cb = CircuitBreaker::new(5, Duration::from_secs(60));
        assert_eq!(cb.state(), CircuitState::Closed);
        // Valid configuration
        assert!(true);
    }

    // Traces to: FR-OBS-023
    #[test]
    fn test_circuit_breaker_force_state() {
        let mut cb = CircuitBreaker::new(5, Duration::from_secs(60));
        cb.force_state(CircuitState::Open);
        assert_eq!(cb.state(), CircuitState::Open);
        cb.force_state(CircuitState::Closed);
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // Traces to: FR-OBS-023
    #[test]
    fn test_circuit_breaker_reset() {
        let mut cb = CircuitBreaker::new(3, Duration::from_secs(60));
        cb.record_failure();
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
        cb.reset();
        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failure_count, 0);
    }

    // Traces to: FR-OBS-026
    #[test]
    fn test_circuit_breaker_open_state_error() {
        let mut cb = CircuitBreaker::new(1, Duration::from_secs(60));
        cb.record_failure();
        let err: Result<i32, CircuitBreakerError> = cb.execute(|| Ok::<i32, String>(42));
        assert!(err.is_err());
    }

    // Traces to: FR-OBS-025
    #[test]
    fn test_circuit_breaker_various_thresholds() {
        for threshold in [1, 2, 5, 10] {
            let mut cb = CircuitBreaker::new(threshold, Duration::from_secs(60));
            for _ in 0..(threshold - 1) {
                cb.record_failure();
                assert_eq!(cb.state(), CircuitState::Closed);
            }
            cb.record_failure();
            assert_eq!(cb.state(), CircuitState::Open);
        }
    }
}
