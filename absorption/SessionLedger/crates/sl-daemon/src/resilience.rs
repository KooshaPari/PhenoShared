//! Cheap process-local circuit breaker and bounded retry policy.
//!
//! * [`ApiCircuitBreaker`] — Arc-shared closed/open/half-open gate for inbound
//!   `/api/*` handlers (same axum clone caveat as [`crate::http::ApiRateLimit`]).
//! * [`RetryPolicy`] — bounded exponential backoff for outbound CLI HTTP calls.
//!
//! Env knobs (see `.env.example` and `docs/ops/local-trust-boundary.md`):
//! `SL_API_CIRCUIT_BREAKER`, `SL_API_CIRCUIT_FAILURE_THRESHOLD`,
//! `SL_API_CIRCUIT_OPEN_MS`, `SL_HTTP_RETRY_MAX`, `SL_HTTP_RETRY_BASE_MS`.

use std::future::Future;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const DEFAULT_FAILURE_THRESHOLD: u32 = 5;
const DEFAULT_OPEN_DURATION: Duration = Duration::from_secs(30);
const DEFAULT_RETRY_MAX: u32 = 2;
const DEFAULT_RETRY_BASE: Duration = Duration::from_millis(50);

const SL_API_CIRCUIT_BREAKER: &str = "SL_API_CIRCUIT_BREAKER";
const SL_API_CIRCUIT_FAILURE_THRESHOLD: &str = "SL_API_CIRCUIT_FAILURE_THRESHOLD";
const SL_API_CIRCUIT_OPEN_MS: &str = "SL_API_CIRCUIT_OPEN_MS";
const SL_HTTP_RETRY_MAX: &str = "SL_HTTP_RETRY_MAX";
const SL_HTTP_RETRY_BASE_MS: &str = "SL_HTTP_RETRY_BASE_MS";

/// Circuit breaker states (classic Netflix-style).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BreakerState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug)]
struct BreakerInner {
    state: BreakerState,
    consecutive_failures: u32,
    opened_at: Option<Instant>,
    half_open_inflight: bool,
}

/// Process-wide circuit breaker for `/api/*` (shared across connections).
#[derive(Clone)]
pub struct ApiCircuitBreaker {
    inner: Option<Arc<Mutex<BreakerInner>>>,
    pub failure_threshold: u32,
    pub open_for: Duration,
}

impl ApiCircuitBreaker {
    /// Build from env.
    ///
    /// When `enforce_default` is true (non-loopback bind or `SL_API_KEY` set),
    /// an unset `SL_API_CIRCUIT_BREAKER` enables the default breaker. Loopback
    /// without a shared key leaves it off unless the env is set explicitly.
    /// `SL_API_CIRCUIT_BREAKER=0` / `off` disables it.
    pub fn from_env(enforce_default: bool) -> Result<Self, String> {
        Self::from_values(
            enforce_default,
            std::env::var(SL_API_CIRCUIT_BREAKER).ok(),
            std::env::var(SL_API_CIRCUIT_FAILURE_THRESHOLD).ok(),
            std::env::var(SL_API_CIRCUIT_OPEN_MS).ok(),
        )
    }

    pub(crate) fn from_values(
        enforce_default: bool,
        breaker: Option<String>,
        threshold: Option<String>,
        open_ms: Option<String>,
    ) -> Result<Self, String> {
        let enabled = match breaker.as_deref().map(str::trim) {
            None => enforce_default,
            Some("0") | Some("off") | Some("Off") | Some("OFF") => false,
            Some("1") | Some("on") | Some("On") | Some("ON") => true,
            Some(raw) => {
                return Err(format!("{SL_API_CIRCUIT_BREAKER} must be on/off/0/1, got {raw:?}"));
            }
        };
        if !enabled {
            return Ok(Self::disabled());
        }

        let failure_threshold = match threshold.as_deref() {
            None => DEFAULT_FAILURE_THRESHOLD,
            Some(raw) => parse_positive_u32(SL_API_CIRCUIT_FAILURE_THRESHOLD, raw)?,
        };
        let open_for = match open_ms.as_deref() {
            None => DEFAULT_OPEN_DURATION,
            Some(raw) => {
                let ms = parse_positive_u32(SL_API_CIRCUIT_OPEN_MS, raw)?;
                Duration::from_millis(u64::from(ms))
            }
        };
        Ok(Self::enabled(failure_threshold, open_for))
    }

    pub(crate) fn disabled() -> Self {
        Self {
            inner: None,
            failure_threshold: DEFAULT_FAILURE_THRESHOLD,
            open_for: DEFAULT_OPEN_DURATION,
        }
    }

    pub(crate) fn enabled(failure_threshold: u32, open_for: Duration) -> Self {
        Self {
            inner: Some(Arc::new(Mutex::new(BreakerInner {
                state: BreakerState::Closed,
                consecutive_failures: 0,
                opened_at: None,
                half_open_inflight: false,
            }))),
            failure_threshold,
            open_for,
        }
    }

    pub fn is_enabled(&self) -> bool {
        self.inner.is_some()
    }

    /// Returns `Some(retry_after)` when the call should be rejected immediately.
    pub fn deny_if_open(&self) -> Option<Duration> {
        let Some(inner) = &self.inner else {
            return None;
        };
        let mut state = inner.lock().expect("api circuit breaker poisoned");
        match state.state {
            BreakerState::Closed => None,
            BreakerState::Open => {
                let opened_at = state.opened_at.unwrap_or_else(Instant::now);
                let elapsed = Instant::now().duration_since(opened_at);
                if elapsed >= self.open_for {
                    // Cooldown elapsed: admit a single half-open probe.
                    state.state = BreakerState::HalfOpen;
                    state.half_open_inflight = true;
                    None
                } else {
                    Some(self.open_for.saturating_sub(elapsed))
                }
            }
            BreakerState::HalfOpen => {
                if state.half_open_inflight {
                    Some(self.open_for)
                } else {
                    state.half_open_inflight = true;
                    None
                }
            }
        }
    }

    pub fn record_success(&self) {
        let Some(inner) = &self.inner else {
            return;
        };
        let mut state = inner.lock().expect("api circuit breaker poisoned");
        state.consecutive_failures = 0;
        state.half_open_inflight = false;
        state.opened_at = None;
        state.state = BreakerState::Closed;
    }

    pub fn record_failure(&self) {
        let Some(inner) = &self.inner else {
            return;
        };
        let mut state = inner.lock().expect("api circuit breaker poisoned");
        match state.state {
            BreakerState::HalfOpen => {
                state.state = BreakerState::Open;
                state.opened_at = Some(Instant::now());
                state.half_open_inflight = false;
                state.consecutive_failures = self.failure_threshold;
            }
            BreakerState::Closed => {
                state.consecutive_failures = state.consecutive_failures.saturating_add(1);
                if state.consecutive_failures >= self.failure_threshold {
                    state.state = BreakerState::Open;
                    state.opened_at = Some(Instant::now());
                }
            }
            BreakerState::Open => {}
        }
    }

    #[cfg(test)]
    pub fn state(&self) -> BreakerState {
        let Some(inner) = &self.inner else {
            return BreakerState::Closed;
        };
        inner.lock().expect("api circuit breaker poisoned").state
    }
}

/// Bounded exponential-backoff retry policy for outbound HTTP.
#[derive(Debug, Clone)]
pub struct RetryPolicy {
    pub max_retries: u32,
    pub base_delay: Duration,
}

impl RetryPolicy {
    pub fn from_env() -> Result<Self, String> {
        Self::from_values(
            std::env::var(SL_HTTP_RETRY_MAX).ok(),
            std::env::var(SL_HTTP_RETRY_BASE_MS).ok(),
        )
    }

    pub(crate) fn from_values(
        max_retries: Option<String>,
        base_ms: Option<String>,
    ) -> Result<Self, String> {
        let max_retries = match max_retries.as_deref().map(str::trim) {
            None => DEFAULT_RETRY_MAX,
            Some("0") | Some("off") | Some("Off") | Some("OFF") => 0,
            Some(raw) => parse_u32_allow_zero(SL_HTTP_RETRY_MAX, raw)?,
        };
        let base_delay = match base_ms.as_deref() {
            None => DEFAULT_RETRY_BASE,
            Some(raw) => {
                let ms = parse_positive_u32(SL_HTTP_RETRY_BASE_MS, raw)?;
                Duration::from_millis(u64::from(ms))
            }
        };
        Ok(Self { max_retries, base_delay })
    }

    pub fn default_policy() -> Self {
        Self { max_retries: DEFAULT_RETRY_MAX, base_delay: DEFAULT_RETRY_BASE }
    }

    /// Run `op` up to `1 + max_retries` times. Retries when `should_retry` is true.
    pub async fn run<T, E, Fut, F, P>(&self, mut op: F, should_retry: P) -> Result<T, E>
    where
        F: FnMut(u32) -> Fut,
        Fut: Future<Output = Result<T, E>>,
        P: Fn(&E) -> bool,
    {
        let mut attempt = 0u32;
        loop {
            match op(attempt).await {
                Ok(value) => return Ok(value),
                Err(err) if attempt < self.max_retries && should_retry(&err) => {
                    let delay = self.base_delay.saturating_mul(1u32 << attempt.min(4));
                    tokio::time::sleep(delay).await;
                    attempt += 1;
                }
                Err(err) => return Err(err),
            }
        }
    }
}

/// Whether a `reqwest` error is worth retrying (connect / timeout / transient).
pub fn reqwest_error_is_retryable(err: &reqwest::Error) -> bool {
    err.is_connect() || err.is_timeout() || err.is_request()
}

fn parse_positive_u32(name: &str, value: &str) -> Result<u32, String> {
    let parsed = value
        .parse::<u32>()
        .map_err(|_| format!("{name} must be a positive integer, got {value:?}"))?;
    if parsed == 0 {
        return Err(format!("{name} must be greater than zero"));
    }
    Ok(parsed)
}

fn parse_u32_allow_zero(name: &str, value: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .map_err(|_| format!("{name} must be a non-negative integer, got {value:?}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn circuit_defaults_and_parses_env_values() {
        let loopback = ApiCircuitBreaker::from_values(false, None, None, None).unwrap();
        assert!(!loopback.is_enabled());

        let shared = ApiCircuitBreaker::from_values(true, None, None, None).unwrap();
        assert!(shared.is_enabled());
        assert_eq!(shared.failure_threshold, DEFAULT_FAILURE_THRESHOLD);
        assert_eq!(shared.open_for, DEFAULT_OPEN_DURATION);

        let off = ApiCircuitBreaker::from_values(true, Some("off".into()), None, None).unwrap();
        assert!(!off.is_enabled());

        let custom = ApiCircuitBreaker::from_values(
            false,
            Some("on".into()),
            Some("3".into()),
            Some("100".into()),
        )
        .unwrap();
        assert!(custom.is_enabled());
        assert_eq!(custom.failure_threshold, 3);
        assert_eq!(custom.open_for, Duration::from_millis(100));

        assert!(ApiCircuitBreaker::from_values(true, Some("maybe".into()), None, None).is_err());
        assert!(ApiCircuitBreaker::from_values(true, Some("on".into()), Some("0".into()), None)
            .is_err());
    }

    #[test]
    fn circuit_opens_after_threshold_and_rejects_until_cooldown() {
        let breaker = ApiCircuitBreaker::enabled(2, Duration::from_secs(60));
        assert!(breaker.deny_if_open().is_none());
        breaker.record_failure();
        assert_eq!(breaker.state(), BreakerState::Closed);
        assert!(breaker.deny_if_open().is_none());
        breaker.record_failure();
        assert_eq!(breaker.state(), BreakerState::Open);
        let retry_after = breaker.deny_if_open().expect("open");
        assert!(retry_after > Duration::from_secs(1));
    }

    #[test]
    fn circuit_half_open_success_closes() {
        let breaker = ApiCircuitBreaker::enabled(1, Duration::from_millis(1));
        breaker.record_failure();
        assert_eq!(breaker.state(), BreakerState::Open);
        std::thread::sleep(Duration::from_millis(5));
        assert!(breaker.deny_if_open().is_none());
        assert_eq!(breaker.state(), BreakerState::HalfOpen);
        // Second probe while half-open probe is in flight is denied.
        assert!(breaker.deny_if_open().is_some());
        breaker.record_success();
        assert_eq!(breaker.state(), BreakerState::Closed);
        assert!(breaker.deny_if_open().is_none());
    }

    #[test]
    fn circuit_half_open_failure_reopens() {
        let breaker = ApiCircuitBreaker::enabled(1, Duration::from_millis(1));
        breaker.record_failure();
        std::thread::sleep(Duration::from_millis(5));
        assert!(breaker.deny_if_open().is_none());
        breaker.record_failure();
        assert_eq!(breaker.state(), BreakerState::Open);
        assert!(breaker.deny_if_open().is_some());
    }

    #[test]
    fn retry_policy_parses_env_and_defaults() {
        let defaults = RetryPolicy::from_values(None, None).unwrap();
        assert_eq!(defaults.max_retries, DEFAULT_RETRY_MAX);
        assert_eq!(defaults.base_delay, DEFAULT_RETRY_BASE);

        let off = RetryPolicy::from_values(Some("off".into()), None).unwrap();
        assert_eq!(off.max_retries, 0);

        let custom = RetryPolicy::from_values(Some("3".into()), Some("25".into())).unwrap();
        assert_eq!(custom.max_retries, 3);
        assert_eq!(custom.base_delay, Duration::from_millis(25));

        assert!(RetryPolicy::from_values(Some("nope".into()), None).is_err());
        assert!(RetryPolicy::from_values(None, Some("0".into())).is_err());
    }

    #[tokio::test]
    async fn retry_policy_retries_then_succeeds() {
        let policy = RetryPolicy { max_retries: 2, base_delay: Duration::from_millis(1) };
        let attempts = Arc::new(Mutex::new(0u32));
        let attempts_clone = attempts.clone();
        let result = policy
            .run(
                |_| {
                    let attempts = attempts_clone.clone();
                    async move {
                        let mut n = attempts.lock().unwrap();
                        *n += 1;
                        if *n < 3 {
                            Err("transient")
                        } else {
                            Ok("ok")
                        }
                    }
                },
                |_| true,
            )
            .await;
        assert_eq!(result, Ok("ok"));
        assert_eq!(*attempts.lock().unwrap(), 3);
    }

    #[tokio::test]
    async fn retry_policy_stops_when_not_retryable() {
        let policy = RetryPolicy { max_retries: 5, base_delay: Duration::from_millis(1) };
        let attempts = Arc::new(Mutex::new(0u32));
        let attempts_clone = attempts.clone();
        let result: Result<(), &str> = policy
            .run(
                |_| {
                    let attempts = attempts_clone.clone();
                    async move {
                        *attempts.lock().unwrap() += 1;
                        Err("fatal")
                    }
                },
                |_| false,
            )
            .await;
        assert_eq!(result, Err("fatal"));
        assert_eq!(*attempts.lock().unwrap(), 1);
    }
}
