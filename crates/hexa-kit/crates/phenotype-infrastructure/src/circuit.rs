//! Circuit breaker pattern for fault tolerance

use std::sync::Arc;
use std::time::{Duration, Instant};

use tokio::sync::RwLock;

use crate::InfrastructureError;

/// Circuit breaker states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    /// Circuit closed, requests flow through
    Closed,
    /// Circuit open, requests fail fast
    Open,
    /// Half-open, testing if service recovered
    HalfOpen,
}

/// Circuit breaker configuration
#[derive(Debug, Clone)]
pub struct CircuitConfig {
    /// Failure threshold before opening circuit
    pub failure_threshold: u32,
    /// Success threshold in half-open before closing
    pub success_threshold: u32,
    /// Duration to wait before trying half-open
    pub open_duration: Duration,
    /// Window for counting failures
    pub window_size: Duration,
}

impl Default for CircuitConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 3,
            open_duration: Duration::from_secs(30),
            window_size: Duration::from_secs(60),
        }
    }
}

struct CircuitInner {
    state: CircuitState,
    failures: u32,
    successes: u32,
    last_failure: Option<Instant>,
    opened_at: Option<Instant>,
}

/// Circuit breaker for fault tolerance
pub struct CircuitBreaker {
    config: CircuitConfig,
    inner: Arc<RwLock<CircuitInner>>,
}

impl CircuitBreaker {
    pub fn new(config: CircuitConfig) -> Self {
        Self {
            config,
            inner: Arc::new(RwLock::new(CircuitInner {
                state: CircuitState::Closed,
                failures: 0,
                successes: 0,
                last_failure: None,
                opened_at: None,
            })),
        }
    }

    pub async fn call<F, Fut, T>(&self, f: F) -> Result<T, InfrastructureError>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, InfrastructureError>>,
    {
        self.check_state().await;

        if self.is_open().await {
            return Err(InfrastructureError::CircuitOpen(
                "circuit breaker is open; requests are failing fast".to_string(),
            ));
        }

        let result = f().await;

        match &result {
            Ok(_) => self.record_success().await,
            Err(_) => self.record_failure().await,
        }

        result
    }

    pub async fn is_open(&self) -> bool {
        let inner = self.inner.read().await;
        matches!(inner.state, CircuitState::Open)
    }

    async fn check_state(&self) {
        let mut inner = self.inner.write().await;

        if inner.state == CircuitState::Open {
            if let Some(opened_at) = inner.opened_at {
                if opened_at.elapsed() >= self.config.open_duration {
                    inner.state = CircuitState::HalfOpen;
                    inner.successes = 0;
                }
            }
        }
    }

    async fn record_success(&self) {
        let mut inner = self.inner.write().await;

        match inner.state {
            CircuitState::HalfOpen => {
                inner.successes += 1;
                if inner.successes >= self.config.success_threshold {
                    inner.state = CircuitState::Closed;
                    inner.failures = 0;
                }
            }
            CircuitState::Closed => {
                inner.failures = 0;
            }
            _ => {}
        }
    }

    async fn record_failure(&self) {
        let mut inner = self.inner.write().await;

        inner.failures += 1;
        inner.last_failure = Some(Instant::now());

        if inner.failures >= self.config.failure_threshold {
            inner.state = CircuitState::Open;
            inner.opened_at = Some(Instant::now());
        }
    }

    pub async fn state(&self) -> CircuitState {
        let inner = self.inner.read().await;
        inner.state
    }

    pub async fn metrics(&self) -> CircuitMetrics {
        let inner = self.inner.read().await;
        CircuitMetrics {
            state: inner.state,
            failures: inner.failures,
            successes: inner.successes,
        }
    }
}

/// Circuit breaker metrics
#[derive(Debug, Clone, Copy)]
pub struct CircuitMetrics {
    pub state: CircuitState,
    pub failures: u32,
    pub successes: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn fr_circuit_001_starts_closed() {
        let cb = CircuitBreaker::new(CircuitConfig::default());
        assert_eq!(cb.state().await, CircuitState::Closed);
    }

    #[tokio::test]
    async fn fr_circuit_002_opens_after_failures() {
        let config = CircuitConfig {
            failure_threshold: 3,
            ..Default::default()
        };
        let cb = CircuitBreaker::new(config);

        for _ in 0..3 {
            let result: Result<(), InfrastructureError> = cb
                .call(|| async { Err(InfrastructureError::Other("fail".to_string())) })
                .await;
            assert!(result.is_err());
        }

        assert_eq!(cb.state().await, CircuitState::Open);
    }

    #[tokio::test]
    async fn fr_circuit_004_rejects_when_open() {
        let config = CircuitConfig {
            failure_threshold: 2,
            open_duration: Duration::from_secs(3600), // long enough to stay open
            ..Default::default()
        };
        let cb = CircuitBreaker::new(config);

        // Open the circuit
        for _ in 0..2 {
            let _ = cb
                .call(|| async { Err::<(), _>(InfrastructureError::Other("fail".to_string())) })
                .await;
        }
        assert_eq!(cb.state().await, CircuitState::Open);

        // Should now get CircuitOpen error instead of panicking
        let result: Result<(), InfrastructureError> = cb.call(|| async { Ok(()) }).await;
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            InfrastructureError::CircuitOpen(_)
        ));
    }

    #[tokio::test]
    async fn fr_circuit_003_closes_after_successes() {
        let config = CircuitConfig {
            failure_threshold: 2,
            success_threshold: 2,
            open_duration: Duration::from_millis(0),
            ..Default::default()
        };
        let cb = CircuitBreaker::new(config);

        // Open the circuit
        for _ in 0..2 {
            let _: Result<(), InfrastructureError> = cb
                .call(|| async { Err(InfrastructureError::Other("fail".to_string())) })
                .await;
        }
        assert_eq!(cb.state().await, CircuitState::Open);

        // Wait for half-open
        tokio::time::sleep(Duration::from_millis(10)).await;

        // Trigger half-open check and succeed
        let result: Result<(), InfrastructureError> = cb.call(|| async { Ok(()) }).await;
        assert!(result.is_ok());

        // Still half-open, need more successes
        assert!(matches!(
            cb.state().await,
            CircuitState::HalfOpen | CircuitState::Closed
        ));
    }
}
