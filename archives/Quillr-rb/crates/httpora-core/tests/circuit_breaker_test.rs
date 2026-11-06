use httpora_core::error::HttptoraError;
use httpora_core::middleware::circuit_breaker::{
    CircuitBreaker, CircuitBreakerConfig, CircuitState,
};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use std::time::Instant;

#[test]
fn circuit_starts_closed() {
    let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
    assert_eq!(cb.state().unwrap(), CircuitState::Closed);
    assert!(cb.before_request().is_ok());
}

#[test]
fn circuit_opens_on_failure_threshold() {
    let cb = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.3,
        min_requests: 3,
        window_size: 10,
        ..Default::default()
    });

    cb.on_success().unwrap();
    cb.on_success().unwrap();
    cb.on_success().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Closed);

    // 2 failures out of 5 = 40% >= 30% → trips
    cb.on_failure().unwrap();
    cb.on_failure().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Open);
    assert!(cb.before_request().is_err());
}

#[test]
fn open_circuit_rejects_requests() {
    let cb = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.0,
        reset_timeout: Duration::from_secs(60),
        min_requests: 1,
        ..Default::default()
    });
    cb.on_failure().unwrap(); // trips immediately
    match cb.before_request() {
        Err(HttptoraError::CircuitOpen) => {} // expected
        other => panic!("expected CircuitOpen, got {other:?}"),
    }
}

#[test]
fn half_open_probe_success_closes_circuit() {
    let cb = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.0,
        reset_timeout: Duration::from_millis(0),
        min_requests: 1,
        ..Default::default()
    });
    cb.on_failure().unwrap(); // trips

    // reset_timeout is 0ms, so before_request transitions to half-open
    assert!(cb.before_request().is_ok());
    assert_eq!(cb.state().unwrap(), CircuitState::HalfOpen);

    // Probe succeeds → circuit closes
    cb.on_success().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Closed);
}

#[test]
fn half_open_probe_failure_reopens() {
    let cb = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.0,
        reset_timeout: Duration::from_millis(0),
        min_requests: 1,
        ..Default::default()
    });
    cb.on_failure().unwrap(); // trips
    assert_eq!(cb.state().unwrap(), CircuitState::Open);

    assert!(cb.before_request().is_ok());
    assert_eq!(cb.state().unwrap(), CircuitState::HalfOpen);

    cb.on_failure().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Open);
}

#[test]
fn does_not_trip_below_min_requests() {
    let cb = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.1,
        min_requests: 10,
        window_size: 20,
        ..Default::default()
    });

    // 1 failure with only 2 requests total — below min_requests (10)
    cb.on_success().unwrap();
    cb.on_failure().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Closed);
}

#[test]
fn circuit_breaker_accepts_injected_clock() {
    let now = Arc::new(Mutex::new(Instant::now()));
    let clock_now = Arc::clone(&now);
    let cb = CircuitBreaker::with_config_and_clock(
        CircuitBreakerConfig {
            failure_threshold: 0.0,
            reset_timeout: Duration::from_secs(10),
            min_requests: 1,
            ..Default::default()
        },
        Arc::new(move || *clock_now.lock().unwrap()),
    );

    cb.on_failure().unwrap();
    assert_eq!(cb.state().unwrap(), CircuitState::Open);
    assert!(cb.before_request().is_err());

    *now.lock().unwrap() += Duration::from_secs(10);
    assert!(cb.before_request().is_ok());
    assert_eq!(cb.state().unwrap(), CircuitState::HalfOpen);
}
