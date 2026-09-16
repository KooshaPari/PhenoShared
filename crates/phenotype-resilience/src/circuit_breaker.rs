//! Circuit-breaker pattern (closed → open → half-open state machine).
//!
//! # State machine
//! ```text
//! Closed ──[failures ≥ threshold]──► Open
//!   ▲                                  │
//!   │                        [timeout elapsed]
//!   │                                  ▼
//!   └──────[probe succeeds]──── HalfOpen
//!           [probe fails] ──────────────► Open
//! ```
//!
//! `CircuitBreaker` is **not** `Send` by default because it holds an
//! `Instant`.  Wrap in `Arc<Mutex<_>>` for shared async use.

use std::time::{Duration, Instant};

use crate::error::ResilienceError;

/// Observed state of the circuit breaker.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    /// Normal operation — requests pass through.
    Closed,
    /// Downstream is considered unhealthy — requests are rejected fast.
    Open,
    /// A single probe request is allowed to test recovery.
    HalfOpen,
}

/// Circuit breaker that trips after `failure_threshold` consecutive failures
/// and re-tries after `recovery_timeout`.
#[derive(Debug)]
pub struct CircuitBreaker {
    failure_threshold: usize,
    recovery_timeout: Duration,
    failure_count: usize,
    last_failure: Option<Instant>,
    state: CircuitState,
}

impl CircuitBreaker {
    /// Create a new circuit breaker.
    ///
    /// * `failure_threshold` — consecutive failures before opening.
    /// * `recovery_timeout` — how long to wait before probing in half-open.
    ///
    /// # Panics
    /// Panics if `failure_threshold == 0`.
    pub fn new(failure_threshold: usize, recovery_timeout: Duration) -> Self {
        assert!(failure_threshold > 0, "failure_threshold must be > 0");
        Self {
            failure_threshold,
            recovery_timeout,
            failure_count: 0,
            last_failure: None,
            state: CircuitState::Closed,
        }
    }

    /// Current state.
    pub fn state(&self) -> CircuitState {
        self.state
    }

    /// Number of failures accumulated since the last reset / success.
    pub fn failure_count(&self) -> usize {
        self.failure_count
    }

    /// Returns `true` if a request should be allowed through.
    ///
    /// An `Open` circuit transitions to `HalfOpen` (in-place) once the
    /// recovery timeout has elapsed, allowing a single probe.
    pub fn is_allowed(&mut self) -> bool {
        if self.state == CircuitState::Open {
            let timed_out = self
                .last_failure
                .map(|t| t.elapsed() >= self.recovery_timeout)
                .unwrap_or(false);
            if timed_out {
                self.state = CircuitState::HalfOpen;
            }
        }
        self.state != CircuitState::Open
    }

    /// Record a successful call.
    ///
    /// * `Closed` → resets failure counter.
    /// * `HalfOpen` → transitions back to `Closed`.
    pub fn record_success(&mut self) {
        self.failure_count = 0;
        if self.state == CircuitState::HalfOpen {
            self.state = CircuitState::Closed;
            self.last_failure = None;
        }
    }

    /// Record a failed call.
    ///
    /// * `Closed` → increments counter; trips to `Open` at threshold.
    /// * `HalfOpen` → immediately re-opens.
    /// * `Open` → stays open, updates timestamp.
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
                self.state = CircuitState::Open;
            }
            CircuitState::Open => {}
        }
    }

    /// Execute a synchronous closure under circuit-breaker protection.
    ///
    /// Returns `Err(CircuitOpen)` immediately when the breaker is open.
    /// Any `Err` result from `f` is recorded as a failure.
    pub fn execute<F, T, E>(&mut self, f: F) -> Result<T, ResilienceError>
    where
        F: FnOnce() -> Result<T, E>,
    {
        if !self.is_allowed() {
            return Err(ResilienceError::CircuitOpen);
        }
        match f() {
            Ok(v) => {
                self.record_success();
                Ok(v)
            }
            Err(_) => {
                self.record_failure();
                Err(ResilienceError::CircuitOpen)
            }
        }
    }

    /// Hard-reset the breaker to `Closed` with zero failure count.
    pub fn reset(&mut self) {
        self.state = CircuitState::Closed;
        self.failure_count = 0;
        self.last_failure = None;
    }

    /// Force the breaker into an arbitrary state (useful for testing /
    /// operations dashboards).
    pub fn force_state(&mut self, state: CircuitState) {
        self.state = state;
        if state == CircuitState::Closed {
            self.failure_count = 0;
            self.last_failure = None;
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_cb(threshold: usize) -> CircuitBreaker {
        CircuitBreaker::new(threshold, Duration::from_secs(60))
    }

    // ── Initial state ────────────────────────────────────────────────────────

    #[test]
    fn starts_closed() {
        assert_eq!(make_cb(5).state(), CircuitState::Closed);
    }

    #[test]
    fn closed_allows_requests() {
        let mut cb = make_cb(5);
        assert!(cb.is_allowed());
    }

    #[test]
    fn zero_failures_on_creation() {
        assert_eq!(make_cb(3).failure_count(), 0);
    }

    // ── Trip to Open ─────────────────────────────────────────────────────────

    #[test]
    fn trips_open_at_threshold() {
        let mut cb = make_cb(3);
        cb.record_failure();
        cb.record_failure();
        assert_eq!(
            cb.state(),
            CircuitState::Closed,
            "should stay closed before threshold"
        );
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
    }

    #[test]
    fn open_blocks_requests() {
        let mut cb = make_cb(1);
        cb.record_failure();
        assert!(!cb.is_allowed());
    }

    #[test]
    fn open_execute_returns_circuit_open_err() {
        let mut cb = make_cb(1);
        cb.record_failure();
        let r: Result<i32, ResilienceError> = cb.execute(|| Ok::<i32, &str>(42));
        assert_eq!(r.unwrap_err(), ResilienceError::CircuitOpen);
    }

    #[test]
    fn exact_threshold_boundary() {
        let mut cb = make_cb(2);
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Closed);
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
    }

    #[test]
    fn trips_at_various_thresholds() {
        for t in [1usize, 2, 5, 10] {
            let mut cb = make_cb(t);
            for _ in 0..(t - 1) {
                cb.record_failure();
                assert_eq!(cb.state(), CircuitState::Closed);
            }
            cb.record_failure();
            assert_eq!(cb.state(), CircuitState::Open);
        }
    }

    // ── Half-open / recovery ─────────────────────────────────────────────────

    #[test]
    fn half_open_after_timeout() {
        let mut cb = CircuitBreaker::new(1, Duration::from_millis(50));
        cb.record_failure();
        std::thread::sleep(Duration::from_millis(100));
        assert!(cb.is_allowed(), "should allow probe after timeout");
        assert_eq!(cb.state(), CircuitState::HalfOpen);
    }

    #[test]
    fn half_open_success_closes_breaker() {
        let mut cb = make_cb(1);
        cb.force_state(CircuitState::HalfOpen);
        cb.record_success();
        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failure_count(), 0);
    }

    #[test]
    fn half_open_failure_reopens() {
        let mut cb = make_cb(1);
        cb.force_state(CircuitState::HalfOpen);
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
    }

    // ── Success resets failure counter ───────────────────────────────────────

    #[test]
    fn success_resets_failure_count_when_closed() {
        let mut cb = make_cb(5);
        cb.record_failure();
        cb.record_failure();
        cb.record_success();
        assert_eq!(cb.failure_count(), 0);
        assert_eq!(cb.state(), CircuitState::Closed);
    }

    // ── Execute helper ───────────────────────────────────────────────────────

    #[test]
    fn execute_records_success() {
        let mut cb = make_cb(3);
        let r = cb.execute(|| Ok::<i32, &str>(7));
        assert_eq!(r.unwrap(), 7);
        assert_eq!(cb.failure_count(), 0);
    }

    #[test]
    fn execute_records_failure_and_trips() {
        let mut cb = make_cb(1);
        let r: Result<i32, ResilienceError> = cb.execute(|| Err("boom"));
        assert!(r.is_err());
        assert_eq!(cb.state(), CircuitState::Open);
    }

    // ── Reset / force_state ──────────────────────────────────────────────────

    #[test]
    fn reset_closes_open_breaker() {
        let mut cb = make_cb(1);
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Open);
        cb.reset();
        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failure_count(), 0);
    }

    #[test]
    fn force_state_open_then_closed() {
        let mut cb = make_cb(5);
        cb.force_state(CircuitState::Open);
        assert_eq!(cb.state(), CircuitState::Open);
        cb.force_state(CircuitState::Closed);
        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failure_count(), 0);
    }
}
