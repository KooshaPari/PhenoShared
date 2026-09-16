use httpora_core::error::HttptoraError;
use httpora_core::middleware::rate_limit::RateLimiter;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[test]
fn token_bucket_initial_burst() {
    let limiter = RateLimiter::token_bucket(10, 10.0);
    for _ in 0..10 {
        assert!(limiter.check(1.0).is_ok(), "expected burst to pass");
    }
    // 11th should be rate-limited
    match limiter.check(1.0) {
        Err(HttptoraError::RateLimited { .. }) => {} // expected
        other => panic!("expected RateLimited, got {other:?}"),
    }
}

#[test]
fn fixed_window_honours_limit() {
    let limiter = RateLimiter::fixed_window(5, 10.0);
    for _ in 0..5 {
        assert!(limiter.check(1.0).is_ok());
    }
    assert!(limiter.check(1.0).is_err(), "6th request should be denied");
}

#[test]
fn token_bucket_returns_retry_after() {
    let limiter = RateLimiter::token_bucket(1, 1.0);
    assert!(limiter.check(1.0).is_ok());
    match limiter.check(1.0) {
        Err(HttptoraError::RateLimited { retry_after }) => {
            assert!(
                retry_after.as_secs_f64() > 0.0,
                "retry_after should be positive"
            );
        }
        other => panic!("expected RateLimited, got {other:?}"),
    }
}

#[test]
fn different_token_amounts() {
    let limiter = RateLimiter::token_bucket(10, 10.0);
    // Consume 5 tokens in one go — should work
    assert!(limiter.check(5.0).is_ok());
    // Remaining 5 should work
    assert!(limiter.check(5.0).is_ok());
    // Should be empty now
    assert!(limiter.check(1.0).is_err());
}

#[test]
fn token_bucket_accepts_injected_clock() {
    let now = Arc::new(Mutex::new(Instant::now()));
    let clock_now = Arc::clone(&now);
    let limiter =
        RateLimiter::token_bucket_with_clock(1, 1.0, Arc::new(move || *clock_now.lock().unwrap()));

    assert!(limiter.check(1.0).is_ok());
    assert!(limiter.check(1.0).is_err());
    *now.lock().unwrap() += Duration::from_secs(1);
    assert!(limiter.check(1.0).is_ok());
}
