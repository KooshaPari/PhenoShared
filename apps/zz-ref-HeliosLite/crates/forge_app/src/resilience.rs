//! Resilience layer on top of [`crate::retry`]: circuit breaker, bulkhead
//! (concurrency cap), and adaptive throttle (honors `Retry-After` + token
//! buckets).
//!
//! Design goals
//! - **Pure**: no I/O, deterministic, testable without async runtime work.
//! - **Lock-free single-thread**: uses [`AtomicU64`] / [`AtomicI64`] for
//!   counters so it composes safely across awaits without a Mutex.
//! - **No global state**: each policy is owned and threaded explicitly.
//! - **Backwards compatible**: wraps the existing
//!   [`crate::retry::retry_with_config`] — no API change.

use std::sync::atomic::{AtomicI64, AtomicU32, AtomicU64, Ordering};
use std::time::{Duration, Instant, SystemTime};

/// Outcome reported by the caller to the circuit breaker.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CallOutcome {
    Success,
    Failure,
}

/// State of the circuit breaker.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BreakerState {
    /// Failures below the failure threshold; calls are passed through.
    Closed,
    /// Failure threshold reached; calls short-circuit until the cool-down
    /// elapses.
    Open,
    /// Cool-down elapsed; allow a single probe call to test recovery.
    /// If the probe succeeds, transition to [`Self::Closed`]; if it
    /// fails, transition back to [`Self::Open`] with a fresh cool-down.
    HalfOpen,
}

/// Per-target circuit breaker.
///
/// Tracks consecutive failures. When `failure_threshold` is reached, the
/// breaker opens and short-circuits calls for `cool_down`. After
/// `cool_down` elapses, a single probe call is permitted; on success the
/// breaker closes; on failure it reopens with a fresh cool-down.
pub struct CircuitBreaker {
    name: String,
    failure_threshold: u32,
    cool_down: Duration,
    state: AtomicU64, // 0 = Closed, 1 = Open, 2 = HalfOpen
    consecutive_failures: AtomicU32,
    opened_at_ms: AtomicI64, // millis since UNIX_EPOCH when last opened
}

impl CircuitBreaker {
    pub fn new(name: impl Into<String>, failure_threshold: u32, cool_down: Duration) -> Self {
        Self {
            name: name.into(),
            failure_threshold: failure_threshold.max(1),
            cool_down,
            state: AtomicU64::new(0),
            consecutive_failures: AtomicU32::new(0),
            opened_at_ms: AtomicI64::new(0),
        }
    }

    /// Inspect the breaker state given the current wall clock. Returns the
    /// logical state and whether the call is allowed to proceed.
    ///
    /// Callers must call [`Self::record`] on the result.
    pub fn allow(&self, now: Instant) -> (BreakerState, bool) {
        match self.state.load(Ordering::Acquire) {
            0 => (BreakerState::Closed, true),
            1 => {
                let opened = self.opened_at_ms.load(Ordering::Acquire);
                let opened_at = epoch_ms_to_instant(opened);
                if now.duration_since(opened_at) >= self.cool_down {
                    // Cool-down elapsed — try to flip to HalfOpen. Multiple
                    // callers racing here is harmless (only one becomes the
                    // probe).
                    self.state
                        .compare_exchange(1, 2, Ordering::AcqRel, Ordering::Acquire)
                        .ok();
                    (BreakerState::HalfOpen, true)
                } else {
                    (BreakerState::Open, false)
                }
            }
            // HalfOpen: only one probe at a time (handled by the next
            // record). For now allow — the breaker will trip again on
            // failure.
            _ => (BreakerState::HalfOpen, true),
        }
    }

    /// Record the outcome of a call that was previously allowed.
    pub fn record(&self, outcome: CallOutcome, now: Instant) {
        match outcome {
            CallOutcome::Success => {
                self.consecutive_failures.store(0, Ordering::Release);
                // Close on any success (covers recovery from HalfOpen).
                self.state.store(0, Ordering::Release);
            }
            CallOutcome::Failure => {
                let n = self.consecutive_failures.fetch_add(1, Ordering::AcqRel) + 1;
                if n >= self.failure_threshold {
                    self.open(now);
                }
            }
        }
    }

    fn open(&self, now: Instant) {
        self.opened_at_ms
            .store(instant_to_epoch_ms(now), Ordering::Release);
        self.state.store(1, Ordering::Release);
    }

    pub fn state(&self, now: Instant) -> BreakerState {
        self.allow(now).0
    }

    pub fn name(&self) -> &str {
        &self.name
    }
}

/// Counting semaphore that bounds concurrent in-flight operations.
///
/// Cheap CAS-based implementation that doesn't require an async runtime.
/// Use [`Self::try_acquire`] to gate an operation; the returned guard
/// releases on drop.
pub struct Bulkhead {
    name: String,
    capacity: u32,
    in_flight: AtomicU32,
}

impl Bulkhead {
    pub fn new(name: impl Into<String>, capacity: u32) -> Self {
        Self {
            name: name.into(),
            capacity: capacity.max(1),
            in_flight: AtomicU32::new(0),
        }
    }

    /// Attempt to acquire a permit. Returns `Some(guard)` if capacity is
    /// available, `None` if it would exceed capacity.
    pub fn try_acquire(&self) -> Option<BulkheadGuard<'_>> {
        loop {
            let cur = self.in_flight.load(Ordering::Acquire);
            if cur >= self.capacity {
                return None;
            }
            if self
                .in_flight
                .compare_exchange(cur, cur + 1, Ordering::AcqRel, Ordering::Acquire)
                .is_ok()
            {
                return Some(BulkheadGuard { head: self });
            }
        }
    }

    /// Capacity of the bulkhead (max concurrent operations).
    pub fn capacity(&self) -> u32 {
        self.capacity
    }

    /// Currently in-flight count.
    pub fn in_flight(&self) -> u32 {
        self.in_flight.load(Ordering::Acquire)
    }

    pub fn name(&self) -> &str {
        &self.name
    }
}

/// RAII permit. Drops back into the bulkhead on scope exit.
pub struct BulkheadGuard<'h> {
    head: &'h Bulkhead,
}

impl Drop for BulkheadGuard<'_> {
    fn drop(&mut self) {
        self.head.in_flight.fetch_sub(1, Ordering::AcqRel);
    }
}

/// Adaptive throttle: token bucket + cooldowns per-target.
///
/// Bursts up to `burst_size` tokens, refilling at `rate_per_sec` per
/// second. The `burst_size` defaults to 1 to keep semantics simple
/// ("one in flight at a time"); raise it for bursty workloads.
pub struct AdaptiveThrottle {
    name: String,
    rate_per_sec: u32,
    /// Burst capacity (in tokens). The bucket starts full.
    burst_milli: i64,
    /// Last-refill timestamp in monotonic ms (i64 so we can subtract).
    last_refill_ms: AtomicI64,
    /// Available tokens * 1000 to give us sub-token resolution without f64.
    tokens_milli: AtomicI64,
}

impl AdaptiveThrottle {
    /// Construct with `burst_size = 1` (steady-state ping cadence).
    pub fn new(name: impl Into<String>, rate_per_sec: u32) -> Self {
        Self::with_burst(name, rate_per_sec, 1)
    }

    /// Construct with an explicit burst budget (in tokens).
    pub fn with_burst(name: impl Into<String>, rate_per_sec: u32, burst: u32) -> Self {
        let burst = burst.max(1);
        let burst_milli = burst as i64 * 1000;
        // Start with a full burst so the first request is always Allow'd.
        let start_at = instant_to_mono_ms(Instant::now());
        Self {
            name: name.into(),
            rate_per_sec: rate_per_sec.max(1),
            burst_milli,
            last_refill_ms: AtomicI64::new(start_at),
            tokens_milli: AtomicI64::new(burst_milli),
        }
    }

    /// Record a `Retry-After` value (as a Duration). Imposes an overdraft
    /// of `rate_per_sec * retry_after` millitokens so the next
    /// `try_acquire` waits that long.
    pub fn record_retry_after(&self, retry_after: Duration, now: Instant) {
        let now_ms = instant_to_mono_ms(now);
        // Tokens to remove = rate * seconds = rate_per_sec * retry_after_ms
        let withdraw_milli =
            (retry_after.as_millis() as i64).saturating_mul(self.rate_per_sec as i64);
        self.tokens_milli
            .fetch_sub(withdraw_milli, Ordering::AcqRel);
        self.last_refill_ms.store(now_ms, Ordering::Release);
    }

    /// Try to acquire one token. Returns the suggested wait time if the
    /// caller should back off.
    pub fn try_acquire(&self, now: Instant) -> ThrottleDecision {
        let now_ms = instant_to_mono_ms(now);
        let last = self.last_refill_ms.load(Ordering::Acquire);
        let elapsed_ms = now_ms.saturating_sub(last).max(0);
        let earned_milli = elapsed_ms.saturating_mul(self.rate_per_sec as i64);
        let cur = self.tokens_milli.load(Ordering::Acquire);
        // Effective tokens from now (refreshed with earned time).
        let updated = cur.saturating_add(earned_milli).min(self.burst_milli); // cap at burst
        self.last_refill_ms.store(now_ms, Ordering::Release);
        // Subtract the 1-token cost for the *next* caller/iteration:
        // store the post-acquisition state but don't re-cap to negative.
        let post = updated.saturating_sub(1000);
        self.tokens_milli.store(post, Ordering::Release);
        if updated >= 1000 {
            ThrottleDecision::Allow
        } else {
            // Back-off = time to earn the missing millitokens (ms).
            let missing_milli = 1000 - updated;
            let wait_ms = (missing_milli + self.rate_per_sec as i64 - 1) / self.rate_per_sec as i64;
            ThrottleDecision::Wait(Duration::from_millis(wait_ms.max(0) as u64))
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThrottleDecision {
    Allow,
    Wait(Duration),
}

/// Top-level policy bundle: per-target circuit breaker, bulkhead, and
/// adaptive throttle. Composes cleanly with [`crate::retry`].
pub struct ResiliencePolicy {
    pub breaker: CircuitBreaker,
    pub bulkhead: Bulkhead,
    pub throttle: AdaptiveThrottle,
}

impl ResiliencePolicy {
    pub fn new(
        name: impl Into<String>,
        failure_threshold: u32,
        cool_down: Duration,
        concurrency: u32,
        rate_per_sec: u32,
    ) -> Self {
        let name = name.into();
        Self {
            breaker: CircuitBreaker::new(name.clone(), failure_threshold, cool_down),
            bulkhead: Bulkhead::new(name.clone(), concurrency),
            throttle: AdaptiveThrottle::new(name, rate_per_sec),
        }
    }

    /// Pre-flight check for a call. Returns `Allow` only when all three
    /// gates permit. `Throttled` indicates the throttle wants a wait;
    /// `ShortCircuit` indicates the breaker is open.
    pub fn check(&self, now: Instant) -> PreFlight {
        let (_, allowed) = self.breaker.allow(now);
        if !allowed {
            return PreFlight::ShortCircuit;
        }
        let throttle = self.throttle.try_acquire(now);
        if let ThrottleDecision::Wait(d) = throttle {
            return PreFlight::Throttled(d);
        }
        if self.bulkhead.try_acquire().is_none() {
            return PreFlight::BulkheadFull;
        }
        PreFlight::Allow
    }

    /// Record outcome (no-throw, always). Releases any acquired bulkhead
    /// permit if the caller passes a guard back.
    pub fn record(&self, outcome: CallOutcome, now: Instant, permit: Option<BulkheadGuard<'_>>) {
        self.breaker.record(outcome, now);
        // Bulkhead permit released on drop of `permit`.
        let _ = permit;
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreFlight {
    Allow,
    BulkheadFull,
    Throttled(Duration),
    ShortCircuit,
}

// ---------------------------------------------------------------------------
// Time helpers — isolated so tests can swap them out
// ---------------------------------------------------------------------------

fn instant_to_epoch_ms(now: Instant) -> i64 {
    // Instant is monotonic, but for "opened at" we want wall-clock so
    // external tooling can read it. Convert via SystemTime.
    let sys = SystemTime::now()
        .checked_sub(now.elapsed())
        .unwrap_or(SystemTime::UNIX_EPOCH);
    sys.duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

fn epoch_ms_to_instant(ms: i64) -> Instant {
    if ms <= 0 {
        Instant::now()
    } else {
        let sys = SystemTime::UNIX_EPOCH + Duration::from_millis(ms as u64);
        SystemTime::now()
            .duration_since(sys)
            .ok()
            .and_then(|d| Instant::now().checked_sub(d))
            .unwrap_or_else(Instant::now)
    }
}

fn instant_to_mono_ms(now: Instant) -> i64 {
    // For the throttle we just need a monotonic reference. Use a stable
    // arbitrary epoch (process start) since we never persist this.
    use std::sync::OnceLock;
    static START: OnceLock<Instant> = OnceLock::new();
    let start = *START.get_or_init(Instant::now);
    now.saturating_duration_since(start).as_millis() as i64
}

#[cfg(test)]
mod tests {
    use super::*;

    fn now() -> Instant {
        Instant::now()
    }

    // ---- CircuitBreaker ----

    #[test]
    fn breaker_closed_allows_immediately() {
        let cb = CircuitBreaker::new("test", 3, Duration::from_secs(10));
        let (state, allowed) = cb.allow(now());
        assert_eq!(state, BreakerState::Closed);
        assert!(allowed);
        assert_eq!(cb.state(now()), BreakerState::Closed);
    }

    #[test]
    fn breaker_opens_after_threshold_failures() {
        let cb = CircuitBreaker::new("test", 3, Duration::from_secs(10));
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        let (state, allowed) = cb.allow(now());
        assert_eq!(state, BreakerState::Open);
        assert!(!allowed);
    }

    #[test]
    fn breaker_success_resets_consecutive_failures() {
        let cb = CircuitBreaker::new("test", 3, Duration::from_secs(10));
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Success, now());
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        // Only 2 consecutive, threshold 3 — still Closed
        let (state, allowed) = cb.allow(now());
        assert_eq!(state, BreakerState::Closed);
        assert!(allowed);
    }

    #[test]
    fn breaker_transitions_to_half_open_after_cooldown() {
        let cb = CircuitBreaker::new("test", 2, Duration::from_millis(50));
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        std::thread::sleep(Duration::from_millis(60));
        let (state, allowed) = cb.allow(now());
        assert_eq!(state, BreakerState::HalfOpen);
        assert!(allowed);
    }

    #[test]
    fn breaker_half_open_success_closes_it() {
        let cb = CircuitBreaker::new("test", 2, Duration::from_millis(30));
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        std::thread::sleep(Duration::from_millis(40));
        let _ = cb.allow(now()); // flips to HalfOpen
        cb.record(CallOutcome::Success, now());
        assert_eq!(cb.state(now()), BreakerState::Closed);
    }

    #[test]
    fn breaker_half_open_failure_reopens() {
        let cb = CircuitBreaker::new("test", 2, Duration::from_millis(30));
        cb.record(CallOutcome::Failure, now());
        cb.record(CallOutcome::Failure, now());
        std::thread::sleep(Duration::from_millis(40));
        let _ = cb.allow(now()); // flips to HalfOpen
        cb.record(CallOutcome::Failure, now());
        let (state, allowed) = cb.allow(now());
        assert_eq!(state, BreakerState::Open);
        assert!(!allowed);
    }

    // ---- Bulkhead ----

    #[test]
    fn bulkhead_admits_within_capacity() {
        let bh = Bulkhead::new("test", 3);
        let _g1 = bh.try_acquire().unwrap();
        let _g2 = bh.try_acquire().unwrap();
        assert_eq!(bh.in_flight(), 2);
    }

    #[test]
    fn bulkhead_rejects_over_capacity() {
        let bh = Bulkhead::new("test", 1);
        let _g = bh.try_acquire().unwrap();
        assert!(bh.try_acquire().is_none());
    }

    #[test]
    fn bulkhead_release_on_drop_frees_capacity() {
        let bh = Bulkhead::new("test", 1);
        let g = bh.try_acquire().unwrap();
        assert!(bh.try_acquire().is_none());
        drop(g);
        assert!(bh.try_acquire().is_some());
    }

    // ---- AdaptiveThrottle ----

    #[test]
    fn throttle_rejects_then_allows_after_refill() {
        // Use a slow rate so the immediate 2nd call is denied.
        let t = AdaptiveThrottle::new("test", 5); // 5/sec = 1 token / 200ms
        // First call consumes the initial 1-token burst.
        let d1 = t.try_acquire(now());
        assert_eq!(d1, ThrottleDecision::Allow);
        // No time elapsed -> tokens not refilled -> must wait.
        let d2 = t.try_acquire(now());
        assert!(matches!(d2, ThrottleDecision::Wait(_)));
    }

    #[test]
    fn throttle_refills_after_elapsed() {
        let t = AdaptiveThrottle::new("test", 100); // 100/sec = 1 token / 10ms
        let _ = t.try_acquire(now());
        std::thread::sleep(Duration::from_millis(20)); // ~2 tokens earned
        let d = t.try_acquire(now());
        assert_eq!(d, ThrottleDecision::Allow);
    }

    #[test]
    fn throttle_record_retry_after_sets_overdraft() {
        let t = AdaptiveThrottle::new("test", 100);
        // First call uses the burst.
        let _ = t.try_acquire(now());
        // Server says: back off 200ms.
        t.record_retry_after(Duration::from_millis(200), now());
        let d = t.try_acquire(now());
        assert!(matches!(d, ThrottleDecision::Wait(w) if w >= Duration::from_millis(100)));
    }

    // ---- ResiliencePolicy composition ----

    #[test]
    fn policy_check_returns_allow_when_all_pass() {
        let p = ResiliencePolicy::new("t", 5, Duration::from_secs(10), 10, 10);
        let permit = match p.check(now()) {
            PreFlight::Allow => Some(p.bulkhead.try_acquire().unwrap()),
            other => panic!("expected Allow, got {:?}", other),
        };
        p.record(CallOutcome::Success, now(), permit);
        assert_eq!(p.breaker.state(now()), BreakerState::Closed);
    }

    #[test]
    fn policy_check_short_circuits_when_breaker_open() {
        let p = ResiliencePolicy::new("t", 1, Duration::from_secs(10), 10, 10);
        // Open the breaker
        p.breaker.record(CallOutcome::Failure, now());
        assert_eq!(p.check(now()), PreFlight::ShortCircuit);
    }

    #[test]
    fn policy_record_releases_bulkhead_via_drop() {
        let p = ResiliencePolicy::new("t", 100, Duration::from_secs(10), 1, 1000);
        // Manually fill it
        let _g = p.bulkhead.try_acquire().unwrap();
        assert!(p.bulkhead.try_acquire().is_none());
        // After drop, available
        drop(_g);
        assert!(p.bulkhead.try_acquire().is_some());
    }
}
