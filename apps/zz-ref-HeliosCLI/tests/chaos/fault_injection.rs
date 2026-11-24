//! Fault injection tests.
//!
//! Exercises random error injection, latency injection, resource exhaustion
//! scenarios, and graceful degradation verification.  All tests use
//! deterministic seeding so results are reproducible.

use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Simple pseudo-random number generator (xorshift64) for deterministic tests.
#[derive(Debug)]
struct XorShift64 {
    state: u64,
}

impl XorShift64 {
    fn new(seed: u64) -> Self {
        Self { state: seed.max(1) }
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.state = x;
        x
    }

    /// Returns a value in `[0, bound)`.
    fn next_bounded(&mut self, bound: u64) -> u64 {
        self.next_u64() % bound
    }
}

/// Simulates a fallible operation with injectable error rate and latency.
fn inject_fault(
    rng: &mut XorShift64,
    error_rate_ppm: u64,
    min_latency_ms: u64,
    max_latency_ms: u64,
) -> Result<Duration, &'static str> {
    // Random latency in range.
    let latency_range = max_latency_ms.saturating_sub(min_latency_ms);
    let latency_ms = if latency_range > 0 {
        min_latency_ms + rng.next_bounded(latency_range + 1)
    } else {
        min_latency_ms
    };

    std::thread::sleep(Duration::from_millis(latency_ms));

    // Random error injection (parts per million for fine-grained control).
    if error_rate_ppm > 0 && rng.next_bounded(1_000_000) < error_rate_ppm {
        return Err("injected fault");
    }

    Ok(Duration::from_millis(latency_ms))
}

/// Tracks resource consumption for exhaustion tests.
struct ResourceTracker {
    used: AtomicU64,
    limit: u64,
}

impl ResourceTracker {
    fn new(limit: u64) -> Self {
        Self {
            used: AtomicU64::new(0),
            limit,
        }
    }

    /// Try to allocate `amount` units.  Returns `true` if successful.
    fn try_allocate(&self, amount: u64) -> bool {
        loop {
            let cur = self.used.load(Ordering::SeqCst);
            if cur + amount > self.limit {
                return false;
            }
            if self
                .used
                .compare_exchange(cur, cur + amount, Ordering::SeqCst, Ordering::SeqCst)
                .is_ok()
            {
                return true;
            }
        }
    }

    fn release(&self, amount: u64) {
        self.used.fetch_sub(amount, Ordering::SeqCst);
    }

    fn available(&self) -> u64 {
        self.limit.saturating_sub(self.used.load(Ordering::SeqCst))
    }
}

// ---------------------------------------------------------------------------
// Test: Random error injection
// ---------------------------------------------------------------------------

#[test]
fn random_error_injection_low_rate() {
    let mut rng = XorShift64::new(42);
    let error_rate_ppm = 1_000; // 0.1%
    let iterations = 10_000;
    let mut errors = 0u64;

    for _ in 0..iterations {
        if inject_fault(&mut rng, error_rate_ppm, 0, 0).is_err() {
            errors += 1;
        }
    }

    let error_pct = (errors as f64 / iterations as f64) * 100.0;
    // Allow some tolerance: expected 0.1%, allow 0% - 0.5%.
    assert!(
        error_pct <= 0.5,
        "error rate {error_pct:.2}% exceeds 0.5% threshold"
    );
    assert!(errors > 0, "expected at least some errors at 0.1% rate");
}

#[test]
fn random_error_injection_high_rate() {
    let mut rng = XorShift64::new(123);
    let error_rate_ppm = 500_000; // 50%
    let iterations = 10_000;
    let mut errors = 0u64;

    for _ in 0..iterations {
        if inject_fault(&mut rng, error_rate_ppm, 0, 0).is_err() {
            errors += 1;
        }
    }

    let error_pct = (errors as f64 / iterations as f64) * 100.0;
    // Should be roughly 50%, allow 45%-55%.
    assert!(
        (45.0..=55.0).contains(&error_pct),
        "error rate {error_pct:.2}% not near 50%"
    );
}

#[test]
fn random_error_injection_zero_rate() {
    let mut rng = XorShift64::new(999);
    for _ in 0..1_000 {
        assert!(
            inject_fault(&mut rng, 0, 0, 0).is_ok(),
            "zero error rate should never fail"
        );
    }
}

// ---------------------------------------------------------------------------
// Test: Latency injection
// ---------------------------------------------------------------------------

#[test]
fn latency_injection_respects_bounds() {
    let mut rng = XorShift64::new(7);
    let min_ms = 5;
    let max_ms = 50;
    let iterations = 100;
    let mut total = Duration::ZERO;

    for _ in 0..iterations {
        let start = Instant::now();
        let latency = inject_fault(&mut rng, 0, min_ms, max_ms).unwrap();
        let elapsed = start.elapsed();
        total += elapsed;

        assert!(
            latency >= Duration::from_millis(min_ms),
            "latency {latency:?} below min {min_ms}ms"
        );
        assert!(
            latency <= Duration::from_millis(max_ms),
            "latency {latency:?} above max {max_ms}ms"
        );
    }

    let avg = total / iterations;
    let expected_avg_ms = (min_ms + max_ms) / 2;
    let tolerance = Duration::from_millis(max_ms / 3);
    assert!(
        avg >= Duration::from_millis(expected_avg_ms) - tolerance,
        "average {avg:?} surprisingly low"
    );
    assert!(
        avg <= Duration::from_millis(expected_avg_ms) + tolerance,
        "average {avg:?} surprisingly high"
    );
}

#[test]
fn latency_injection_zero_latency() {
    let mut rng = XorShift64::new(1);
    let start = Instant::now();
    let latency = inject_fault(&mut rng, 0, 0, 0).unwrap();
    let elapsed = start.elapsed();

    assert_eq!(latency, Duration::ZERO);
    assert!(elapsed < Duration::from_millis(5), "zero latency took {elapsed:?}");
}

// ---------------------------------------------------------------------------
// Test: Resource exhaustion scenarios
// ---------------------------------------------------------------------------

#[test]
fn resource_exhaustion_detected() {
    let tracker = ResourceTracker::new(100);

    // Fill up to capacity.
    assert!(tracker.try_allocate(80));
    assert!(tracker.try_allocate(20));
    assert_eq!(tracker.available(), 0);

    // Next allocation should fail.
    assert!(!tracker.try_allocate(1));
}

#[test]
fn resource_exhaustion_with_release() {
    let tracker = ResourceTracker::new(100);

    assert!(tracker.try_allocate(100));
    assert!(!tracker.try_allocate(1));

    tracker.release(50);
    assert_eq!(tracker.available(), 50);
    assert!(tracker.try_allocate(50));
    assert!(!tracker.try_allocate(1));
}

#[test]
fn resource_exhaustion_concurrent_pressure() {
    let tracker = Arc::new(ResourceTracker::new(1000));
    let allocated = Arc::new(AtomicUsize::new(0));

    let handles: Vec<_> = (0..10)
        .map(|_| {
            let tracker = Arc::clone(&tracker);
            let allocated = Arc::clone(&allocated);
            std::thread::spawn(move || {
                for _ in 0..200 {
                    if tracker.try_allocate(1) {
                        allocated.fetch_add(1, Ordering::SeqCst);
                        std::thread::sleep(Duration::from_micros(10));
                        tracker.release(1);
                    }
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    assert_eq!(tracker.available(), 1000);
    assert!(
        allocated.load(Ordering::SeqCst) > 0,
        "should have allocated at least some resources"
    );
}

#[test]
fn resource_exhaustion_zero_limit() {
    let tracker = ResourceTracker::new(0);
    assert!(!tracker.try_allocate(1));
    assert_eq!(tracker.available(), 0);
}

// ---------------------------------------------------------------------------
// Test: Graceful degradation verification
// ---------------------------------------------------------------------------

#[test]
fn graceful_degradation_returns_cached_result() {
    let cache = Arc::new(Mutex::new(Some("cached_value")));
    let upstream_failing = AtomicBool::new(true);

    let result = if upstream_failing.load(Ordering::SeqCst) {
        cache.lock().unwrap().clone()
    } else {
        Some("fresh_value")
    };

    assert_eq!(result.as_deref(), Some("cached_value"));
}

#[test]
fn graceful_degradation_uses_default_on_total_failure() {
    let cache: Option<&str> = None;
    let upstream_failing = AtomicBool::new(true);

    let result = if upstream_failing.load(Ordering::SeqCst) {
        cache.unwrap_or("default_value")
    } else {
        "fresh_value"
    };

    assert_eq!(result, "default_value");
}

#[test]
fn graceful_degradation_recovers_when_upstream_restores() {
    let upstream_failing = AtomicBool::new(true);
    let mut results = Vec::new();

    // Phase 1: upstream down
    for _ in 0..5 {
        let r = if upstream_failing.load(Ordering::SeqCst) {
            "degraded"
        } else {
            "healthy"
        };
        results.push(r);
    }

    // Phase 2: upstream restored
    upstream_failing.store(false, Ordering::SeqCst);
    for _ in 0..5 {
        let r = if upstream_failing.load(Ordering::SeqCst) {
            "degraded"
        } else {
            "healthy"
        };
        results.push(r);
    }

    assert_eq!(
        results.iter().filter(|&&r| r == "degraded").count(),
        5,
        "first 5 should be degraded"
    );
    assert_eq!(
        results.iter().filter(|&&r| r == "healthy").count(),
        5,
        "last 5 should be healthy"
    );
}

#[test]
fn graceful_degradation_error_budget() {
    let mut rng = XorShift64::new(42);
    let error_budget_ppm = 10_000; // 1% error budget
    let iterations = 10_000;
    let mut errors = 0u64;

    for _ in 0..iterations {
        if inject_fault(&mut rng, error_budget_ppm, 0, 0).is_err() {
            errors += 1;
        }
    }

    let error_pct = (errors as f64 / iterations as f64) * 100.0;
    assert!(
        error_pct <= 2.0,
        "error rate {error_pct:.2}% exceeds 2% degradation threshold"
    );
}

#[test]
fn graceful_degradation_timeout_with_fallback() {
    let slow_threshold = Duration::from_millis(100);
    let operation_duration = Duration::from_millis(200);

    let start = Instant::now();
    std::thread::sleep(operation_duration);
    let elapsed = start.elapsed();

    let result = if elapsed > slow_threshold {
        "fallback_response"
    } else {
        "primary_response"
    };

    assert_eq!(result, "fallback_response");
}
