use httpora_core::builder::HttpRequest;
use httpora_core::middleware::clock::Clock;
use httpora_core::middleware::rate_limit::RateLimitStrategy;
use httpora_core::middleware::retry::{BackoffConfig, HttpMethod};
use httpora_core::{
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CorsLayer, HttptoraError, RateLimitConfig,
    RateLimiter, RequestExtractor, ResponseBuilder, RetryConfig, RetryLayer,
};
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[test]
fn fr8_token_bucket_allows_burst_then_limits() {
    let limiter = RateLimiter::token_bucket(10, 10.0);
    for _ in 0..10 {
        assert!(limiter.check(1.0).is_ok());
    }
    assert!(matches!(
        limiter.check(1.0),
        Err(HttptoraError::RateLimited { .. })
    ));
}

#[test]
fn fr9_fixed_window_enforces_limit() {
    let limiter = RateLimiter::fixed_window(5, 1.0);
    for _ in 0..5 {
        assert!(limiter.check(1.0).is_ok());
    }
    assert!(matches!(
        limiter.check(1.0),
        Err(HttptoraError::RateLimited { .. })
    ));
}

#[test]
fn fr10_circuit_breaker_transitions_through_all_states() {
    let breaker = CircuitBreaker::with_config(CircuitBreakerConfig {
        failure_threshold: 0.0,
        reset_timeout: Duration::ZERO,
        min_requests: 1,
        ..Default::default()
    });
    breaker.on_failure().unwrap();
    assert_eq!(breaker.state().unwrap(), CircuitState::Open);
    assert!(breaker.before_request().is_ok());
    assert_eq!(breaker.state().unwrap(), CircuitState::HalfOpen);
    breaker.on_success().unwrap();
    assert_eq!(breaker.state().unwrap(), CircuitState::Closed);
}

#[tokio::test]
async fn fr11_retry_returns_a_later_success() {
    let attempts = AtomicUsize::new(0);
    let retry = RetryLayer::new(3, Duration::ZERO);
    let value = retry
        .execute(|| async {
            if attempts.fetch_add(1, Ordering::SeqCst) < 2 {
                Err("transient")
            } else {
                Ok(42)
            }
        })
        .await
        .expect("third attempt succeeds");
    assert_eq!(value, 42);
    assert_eq!(attempts.load(Ordering::SeqCst), 3);
}

#[tokio::test]
async fn fr12_post_is_not_retried_by_default() {
    let attempts = AtomicUsize::new(0);
    let retry = RetryLayer::new(3, Duration::ZERO);
    let result = retry
        .execute_for_method(HttpMethod::Post, || async {
            attempts.fetch_add(1, Ordering::SeqCst);
            Err::<(), _>("expected")
        })
        .await;
    assert!(matches!(
        result,
        Err(HttptoraError::RetryExhausted { attempts: 1, .. })
    ));
    assert_eq!(attempts.load(Ordering::SeqCst), 1);
}

fn request(method: &str, headers: HashMap<String, String>, body: Vec<u8>) -> HttpRequest {
    HttpRequest {
        method: method.to_owned(),
        path: "/resource".to_owned(),
        body,
        headers,
        query: HashMap::new(),
    }
}

#[test]
fn fr13_cors_preflight_has_required_headers() {
    let mut headers = HashMap::new();
    headers.insert("Origin".to_owned(), "https://example.com".to_owned());
    let response = CorsLayer::permissive().preflight(&request("OPTIONS", headers, Vec::new()));
    assert_eq!(response.status, 204);
    assert_eq!(
        response.headers.get("Access-Control-Allow-Origin"),
        Some(&"*".to_owned())
    );
}

#[test]
fn fr14_response_builder_constructs_json_and_rate_limit_responses() {
    let json = ResponseBuilder::json(200, &serde_json::json!({ "ok": true })).unwrap();
    assert_eq!(json.status, 200);
    assert_eq!(
        json.headers.get("Content-Type"),
        Some(&"application/json".to_owned())
    );
    let limited = ResponseBuilder::rate_limited(60).unwrap();
    assert_eq!(limited.status, 429);
    assert_eq!(limited.headers.get("Retry-After"), Some(&"60".to_owned()));
}

#[test]
fn fr15_request_extractor_handles_bearer_and_json() {
    let mut headers = HashMap::new();
    headers.insert("authorization".to_owned(), "Bearer token".to_owned());
    let req = request("POST", headers, br#"{"key":"value"}"#.to_vec());
    assert_eq!(
        RequestExtractor::bearer_token(&req).as_deref(),
        Some("token")
    );
    assert_eq!(
        RequestExtractor::json_body(&req).unwrap(),
        serde_json::json!({ "key": "value" })
    );
}

#[test]
fn fr16_and_nfr6_errors_are_displayable_standard_errors() {
    let error = HttptoraError::RateLimited {
        retry_after: Duration::from_secs(5),
    };
    assert!(error.to_string().contains("rate limited"));
    let boxed: Box<dyn std::error::Error> = Box::new(error);
    assert!(boxed.to_string().contains("5s"));
}

fn assert_send_sync<T: Send + Sync>() {}

#[test]
fn nfr2_stateful_middleware_is_send_and_sync() {
    assert_send_sync::<RateLimiter>();
    assert_send_sync::<CircuitBreaker>();
}

#[test]
fn nfr3_clocks_make_time_dependent_behavior_deterministic() {
    let now = Arc::new(Mutex::new(Instant::now()));
    let clock_now = Arc::clone(&now);
    let clock: Clock = Arc::new(move || *clock_now.lock().unwrap());
    let limiter = RateLimiter::token_bucket_with_clock(1, 1.0, Arc::clone(&clock));
    assert!(limiter.check(1.0).is_ok());
    assert!(limiter.check(1.0).is_err());
    *now.lock().unwrap() += Duration::from_secs(1);
    assert!(limiter.check(1.0).is_ok());
}

#[test]
fn nfr4_defaults_are_documented_production_values() {
    let rate = RateLimitConfig::default();
    assert_eq!(rate.capacity, 100);
    assert_eq!(rate.refill_rate, 10.0);
    assert_eq!(rate.strategy, RateLimitStrategy::TokenBucket);
    let retry = RetryConfig::default();
    assert_eq!(retry.max_attempts, 3);
    assert!(!retry.retry_non_idempotent);
    assert_eq!(retry.backoff.base_delay, Duration::from_millis(100));
    assert_eq!(retry.backoff.max_delay, Duration::from_secs(30));
    assert_eq!(retry.backoff.multiplier, 2.0);
    assert!(retry.backoff.jitter);
    let circuit = CircuitBreakerConfig::default();
    assert_eq!(circuit.failure_threshold, 0.5);
    assert_eq!(circuit.reset_timeout, Duration::from_secs(30));
    let _: BackoffConfig = retry.backoff;
}
