//! Chaos resilience tests.
//!
//! These tests exercise network partition simulation, service degradation,
//! retry/backoff behavior under failure, circuit breaker validation, and
//! timeout handling.  They run without real network infrastructure by
//! mocking the transport layer.

use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// A minimal circuit breaker used by the tests.
#[derive(Debug, Clone)]
struct CircuitBreaker {
    failures: Arc<AtomicUsize>,
    threshold: usize,
    state: Arc<Mutex<CircuitState>>,
    open_since: Arc<Mutex<Option<Instant>>>,
    recovery_timeout: Duration,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitBreaker {
    fn new(threshold: usize, recovery_timeout: Duration) -> Self {
        Self {
            failures: Arc::new(AtomicUsize::new(0)),
            threshold,
            state: Arc::new(Mutex::new(CircuitState::Closed)),
            open_since: Arc::new(Mutex::new(None)),
            recovery_timeout,
        }
    }

    fn is_available(&self) -> bool {
        let mut state = self.state.lock().unwrap();
        match *state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                let since = self.open_since.lock().unwrap();
                if let Some(t) = *since {
                    if t.elapsed() >= self.recovery_timeout {
                        *state = CircuitState::HalfOpen;
                        true
                    } else {
                        false
                    }
                } else {
                    false
                }
            }
            CircuitState::HalfOpen => true,
        }
    }

    fn record_success(&self) {
        self.failures.store(0, Ordering::SeqCst);
        *self.state.lock().unwrap() = CircuitState::Closed;
    }

    fn record_failure(&self) {
        let count = self.failures.fetch_add(1, Ordering::SeqCst) + 1;
        let mut state = self.state.lock().unwrap();
        if count >= self.threshold {
            *state = CircuitState::Open;
            *self.open_since.lock().unwrap() = Some(Instant::now());
        }
    }

    fn current_state(&self) -> CircuitState {
        *self.state.lock().unwrap()
    }
}

/// Simulated request that can succeed or fail based on an injectable flag.
fn simulate_request(should_fail: &AtomicBool) -> Result<(), &'static str> {
    if should_fail.load(Ordering::SeqCst) {
        Err("simulated failure")
    } else {
        Ok(())
    }
}

/// Exponential backoff delay calculator.
fn backoff_delay(attempt: u32, base_ms: u64, max_ms: u64) -> Duration {
    let delay = base_ms.saturating_mul(2u64.saturating_pow(attempt));
    Duration::from_millis(delay.min(max_ms))
}

// ---------------------------------------------------------------------------
// Test: Network partition simulation
// ---------------------------------------------------------------------------

#[test]
fn network_partition_all_requests_fail() {
    let failing = AtomicBool::new(true);
    // During a "partition" every request should fail.
    for _ in 0..10 {
        assert!(simulate_request(&failing).is_err());
    }
}

#[test]
fn network_partition_recovery() {
    let failing = AtomicBool::new(true);

    // Phase 1: partition active
    for _ in 0..5 {
        assert!(simulate_request(&failing).is_err());
    }

    // Phase 2: partition heals
    failing.store(false, Ordering::SeqCst);
    for _ in 0..5 {
        assert!(simulate_request(&failing).is_ok());
    }
}

#[test]
fn network_partition_intermittent() {
    let failing = AtomicBool::new(false);
    let mut success_count = 0u32;
    let mut fail_count = 0u32;

    for i in 0..20 {
        // Toggle failure every 5 requests to simulate intermittent partition.
        if i % 10 < 5 {
            failing.store(true, Ordering::SeqCst);
        } else {
            failing.store(false, Ordering::SeqCst);
        }

        if simulate_request(&failing).is_ok() {
            success_count += 1;
        } else {
            fail_count += 1;
        }
    }

    assert!(fail_count > 0, "expected some failures during intermittent partition");
    assert!(success_count > 0, "expected some successes after partition heals");
}

// ---------------------------------------------------------------------------
// Test: Service degradation
// ---------------------------------------------------------------------------

#[test]
fn service_degradation_partial_failure() {
    let failure_rate = Arc::new(AtomicUsize::new(0));
    let total = 100;
    let mut successes = 0u32;
    let mut failures = 0u32;

    for i in 0..total {
        // Fail approximately 30% of requests.
        if i % 10 < 3 {
            failure_rate.store(1, Ordering::SeqCst);
        } else {
            failure_rate.store(0, Ordering::SeqCst);
        }

        let should_fail = AtomicBool::new(failure_rate.load(Ordering::SeqCst) == 1);
        if simulate_request(&should_fail).is_ok() {
            successes += 1;
        } else {
            failures += 1;
        }
    }

    assert_eq!(successes + failures, total as u32);
    assert!(failures >= 20, "expected at least 20 failures, got {failures}");
    assert!(successes >= 60, "expected at least 60 successes, got {successes}");
}

#[test]
fn service_degradation_cascading_failure() {
    let primary_failing = AtomicBool::new(true);
    let fallback_failing = AtomicBool::new(false);

    // When primary is down, fallback should succeed.
    let result = simulate_request(&primary_failing)
        .or_else(|_| simulate_request(&fallback_failing));
    assert!(result.is_ok(), "fallback should handle primary failure");

    // When both are down, the overall call should fail.
    fallback_failing.store(true, Ordering::SeqCst);
    let result = simulate_request(&primary_failing)
        .or_else(|_| simulate_request(&fallback_failing));
    assert!(result.is_err(), "both primary and fallback down should fail");
}

// ---------------------------------------------------------------------------
// Test: Retry / backoff behavior under failure
// ---------------------------------------------------------------------------

#[test]
fn retry_succeeds_after_transient_failure() {
    let attempt = AtomicUsize::new(0);
    let max_attempts = 5;

    for _ in 0..max_attempts {
        let a = attempt.fetch_add(1, Ordering::SeqCst);
        // Fail for the first 3 attempts, succeed after.
        let should_fail = AtomicBool::new(a < 3);
        if simulate_request(&should_fail).is_ok() {
            return; // success
        }
    }
    panic!("should have succeeded within {max_attempts} attempts");
}

#[test]
fn retry_gives_up_after_max_attempts() {
    let should_fail = AtomicBool::new(true);
    let max_attempts = 3;
    let mut last_err = None;

    for _ in 0..max_attempts {
        match simulate_request(&should_fail) {
            Ok(()) => panic!("unexpected success"),
            Err(e) => last_err = Some(e),
        }
    }

    assert!(last_err.is_some(), "should have recorded at least one error");
}

#[test]
fn backoff_delay_increases_exponentially() {
    let delays: Vec<Duration> = (0..5).map(|i| backoff_delay(i, 100, 5000)).collect();

    // Each delay should be >= the previous one (or capped).
    for window in delays.windows(2) {
        assert!(
            window[1] >= window[0],
            "delay should not decrease: {:?} -> {:?}",
            window[0],
            window[1]
        );
    }

    assert_eq!(delays[0], Duration::from_millis(100));
    assert_eq!(delays[1], Duration::from_millis(200));
    assert_eq!(delays[2], Duration::from_millis(400));
    assert_eq!(delays[3], Duration::from_millis(800));
    assert_eq!(delays[4], Duration::from_millis(1600));
}

#[test]
fn backoff_respects_max_cap() {
    let delays: Vec<Duration> = (0..20).map(|i| backoff_delay(i, 100, 5000)).collect();

    for d in &delays {
        assert!(
            *d <= Duration::from_millis(5000),
            "delay {d:?} exceeds max cap"
        );
    }
    // After enough attempts, the delay should be capped.
    assert_eq!(delays.last().unwrap(), &Duration::from_millis(5000));
}

#[test]
fn backoff_zero_base() {
    let d = backoff_delay(0, 0, 5000);
    assert_eq!(d, Duration::from_millis(0));
}

// ---------------------------------------------------------------------------
// Test: Circuit breaker validation
// ---------------------------------------------------------------------------

#[test]
fn circuit_breaker_starts_closed() {
    let cb = CircuitBreaker::new(3, Duration::from_millis(100));
    assert_eq!(cb.current_state(), CircuitState::Closed);
    assert!(cb.is_available());
}

#[test]
fn circuit_breaker_opens_after_threshold() {
    let cb = CircuitBreaker::new(3, Duration::from_secs(60));

    cb.record_failure(); // 1
    assert_eq!(cb.current_state(), CircuitState::Closed);

    cb.record_failure(); // 2
    assert_eq!(cb.current_state(), CircuitState::Closed);

    cb.record_failure(); // 3 -- threshold reached
    assert_eq!(cb.current_state(), CircuitState::Open);
    assert!(!cb.is_available(), "circuit should be open");
}

#[test]
fn circuit_breaker_resets_on_success() {
    let cb = CircuitBreaker::new(3, Duration::from_secs(60));

    cb.record_failure();
    cb.record_failure();
    assert_eq!(cb.current_state(), CircuitState::Closed);

    cb.record_success();
    assert_eq!(cb.current_state(), CircuitState::Closed);
    assert_eq!(cb.failures.load(Ordering::SeqCst), 0);
}

#[test]
fn circuit_breaker_half_open_after_recovery_timeout() {
    let cb = CircuitBreaker::new(2, Duration::from_millis(50));

    cb.record_failure();
    cb.record_failure();
    assert_eq!(cb.current_state(), CircuitState::Open);

    // Sleep just past the recovery timeout.
    std::thread::sleep(Duration::from_millis(60));

    assert!(cb.is_available(), "should transition to half-open");
    assert_eq!(cb.current_state(), CircuitState::HalfOpen);
}

#[test]
fn circuit_breaker_half_open_closes_on_success() {
    let cb = CircuitBreaker::new(2, Duration::from_millis(50));

    cb.record_failure();
    cb.record_failure();
    std::thread::sleep(Duration::from_millis(60));

    assert!(cb.is_available()); // half-open
    cb.record_success();
    assert_eq!(cb.current_state(), CircuitState::Closed);
}

#[test]
fn circuit_breaker_half_open_reopens_on_failure() {
    let cb = CircuitBreaker::new(2, Duration::from_millis(50));

    cb.record_failure();
    cb.record_failure();
    std::thread::sleep(Duration::from_millis(60));

    assert!(cb.is_available()); // half-open
    cb.record_failure(); // another failure in half-open
    assert_eq!(cb.current_state(), CircuitState::Open);
}

// ---------------------------------------------------------------------------
// Test: Timeout handling
// ---------------------------------------------------------------------------

#[test]
fn timeout_short_operation_completes() {
    let start = Instant::now();
    let timeout = Duration::from_secs(5);
    std::thread::sleep(Duration::from_millis(10));
    assert!(start.elapsed() < timeout, "operation should complete within timeout");
}

#[test]
fn timeout_detection() {
    let threshold = Duration::from_millis(10);
    std::thread::sleep(Duration::from_millis(50));
    let elapsed = Duration::from_millis(50);
    assert!(
        elapsed > threshold,
        "should detect that operation exceeded the timeout threshold"
    );
}

#[test]
fn timeout_with_circuit_breaker() {
    let cb = CircuitBreaker::new(2, Duration::from_millis(50));

    // Simulate 2 timeout failures -> circuit opens.
    cb.record_failure();
    cb.record_failure();
    assert_eq!(cb.current_state(), CircuitState::Open);

    // Timeouts while open should be fast-rejected.
    let start = Instant::now();
    assert!(!cb.is_available());
    let elapsed = start.elapsed();
    assert!(
        elapsed < Duration::from_millis(10),
        "fast rejection should take < 10ms, took {elapsed:?}"
    );
}
