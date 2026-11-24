use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use httpora_core::middleware::circuit_breaker::{
    CircuitBreaker, CircuitBreakerConfig, CircuitState,
};
use httpora_core::middleware::rate_limit::RateLimiter;
use httpora_core::middleware::retry::{BackoffConfig, HttpMethod, RetryConfig, RetryLayer};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

// ---------------------------------------------------------------------------
// Rate Limiter Benchmarks
// ---------------------------------------------------------------------------

fn bench_rate_limiter_token_bucket(c: &mut Criterion) {
    let mut group = c.benchmark_group("rate_limiter_token_bucket");

    // Benchmark: successful check (token available)
    group.bench_function("check_allowed", |b| {
        // High capacity so we never exhaust tokens during benchmark
        let limiter = RateLimiter::token_bucket(1_000_000, 1_000_000.0);
        b.iter(|| {
            black_box(limiter.check(1.0)).ok();
        });
    });

    // Benchmark: rate-limited check (no tokens available)
    group.bench_function("check_rejected", |b| {
        let limiter = RateLimiter::token_bucket(1, 0.001);
        // Exhaust the single token
        limiter.check(1.0).ok();
        b.iter(|| {
            black_box(limiter.check(1.0)).ok();
        });
    });

    // Benchmark: fixed-window allowed
    group.bench_function("fixed_window_allowed", |b| {
        let limiter = RateLimiter::fixed_window(1_000_000, 1_000.0);
        b.iter(|| {
            black_box(limiter.check(1.0)).ok();
        });
    });

    // Benchmark: fixed-window rejected
    group.bench_function("fixed_window_rejected", |b| {
        let limiter = RateLimiter::fixed_window(1, 1_000.0);
        limiter.check(1.0).ok();
        b.iter(|| {
            black_box(limiter.check(1.0)).ok();
        });
    });

    group.finish();
}

fn bench_rate_limiter_concurrent(c: &mut Criterion) {
    let mut group = c.benchmark_group("rate_limiter_concurrent");

    for num_threads in [2, 4, 8] {
        group.bench_with_input(
            BenchmarkId::new("token_bucket", num_threads),
            &num_threads,
            |b, &num_threads| {
                let limiter = Arc::new(RateLimiter::token_bucket(100_000, 100_000.0));
                b.iter(|| {
                    let handles: Vec<_> = (0..num_threads)
                        .map(|_| {
                            let lim = limiter.clone();
                            std::thread::spawn(move || {
                                for _ in 0..100 {
                                    black_box(lim.check(1.0)).ok();
                                }
                            })
                        })
                        .collect();
                    for h in handles {
                        h.join().unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Retry Benchmarks
// ---------------------------------------------------------------------------

fn bench_retry(c: &mut Criterion) {
    let mut group = c.benchmark_group("retry");

    // Benchmark: execute succeeds on first attempt (no actual retries)
    group.bench_function("execute_success_first_attempt", |b| {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let retry = RetryLayer::new(3, Duration::from_millis(10));
        b.iter(|| {
            rt.block_on(async {
                black_box(retry.execute(|| async { Ok::<_, String>(42) }).await).ok();
            });
        });
    });

    // Benchmark: execute fails and exhausts all retries (with small delays)
    group.bench_function("execute_exhausted", |b| {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let retry = RetryLayer::new(3, Duration::from_millis(1));
        b.iter(|| {
            rt.block_on(async {
                let _ = black_box(
                    retry
                        .execute(|| async { Err::<i32, String>("fail".into()) })
                        .await,
                );
            });
        });
    });

    // Benchmark: execute_for_method (idempotent GET with retry)
    group.bench_function("execute_for_method_idempotent", |b| {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let retry = RetryLayer::new(3, Duration::from_millis(10));
        let counter = AtomicUsize::new(0);
        b.iter(|| {
            counter.store(0, Ordering::SeqCst);
            rt.block_on(async {
                let _ = black_box(
                    retry
                        .execute_for_method(HttpMethod::Get, || async {
                            let prev = counter.fetch_add(1, Ordering::SeqCst);
                            if prev < 1 {
                                Err::<(), String>("fail".into())
                            } else {
                                Ok(())
                            }
                        })
                        .await,
                );
            });
        });
    });

    // Benchmark: compute_delay (private, but we benchmark the overall execute path)
    group.bench_function("execute_with_jitter_disabled", |b| {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let config = RetryConfig {
            max_attempts: 5,
            backoff: BackoffConfig {
                base_delay: Duration::from_micros(1),
                max_delay: Duration::from_micros(10),
                multiplier: 2.0,
                jitter: false,
            },
            retry_non_idempotent: false,
        };
        let retry = RetryLayer::with_config(config);
        b.iter(|| {
            rt.block_on(async {
                black_box(retry.execute(|| async { Ok::<_, String>(42) }).await).ok();
            });
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Circuit Breaker Benchmarks
// ---------------------------------------------------------------------------

fn bench_circuit_breaker(c: &mut Criterion) {
    let mut group = c.benchmark_group("circuit_breaker");

    // Benchmark: before_request in closed state (normal operation)
    group.bench_function("before_request_closed", |b| {
        let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
        b.iter(|| {
            black_box(cb.before_request()).ok();
        });
    });

    // Benchmark: on_success in closed state
    group.bench_function("on_success_closed", |b| {
        let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
        b.iter(|| {
            black_box(cb.on_success()).ok();
        });
    });

    // Benchmark: on_failure in closed state (below threshold)
    group.bench_function("on_failure_closed", |b| {
        let cb = CircuitBreaker::new(0.9, Duration::from_secs(30));
        b.iter(|| {
            black_box(cb.on_failure()).ok();
        });
    });

    // Benchmark: before_request in open state (fast reject)
    group.bench_function("before_request_open", |b| {
        let cb = CircuitBreaker::new(0.5, Duration::from_secs(30));
        // Trip the circuit
        for _ in 0..20 {
            cb.on_failure().ok();
        }
        assert_eq!(cb.state().unwrap(), CircuitState::Open);
        b.iter(|| {
            black_box(cb.before_request()).ok();
        });
    });

    // Benchmark: before_request in half-open state
    group.bench_function("before_request_half_open", |b| {
        let config = CircuitBreakerConfig {
            failure_threshold: 0.0,
            reset_timeout: Duration::from_millis(0),
            min_requests: 1,
            window_size: 10,
            half_open_max_requests: 100,
        };
        let cb = CircuitBreaker::with_config(config);
        cb.on_failure().ok(); // trips immediately
                              // Transition to half-open (reset_timeout is 0)
        cb.before_request().ok();
        assert_eq!(cb.state().unwrap(), CircuitState::HalfOpen);
        b.iter(|| {
            black_box(cb.before_request()).ok();
        });
    });

    // Benchmark: full lifecycle (closed → open → half-open → closed)
    group.bench_function("full_lifecycle", |b| {
        let config = CircuitBreakerConfig {
            failure_threshold: 0.5,
            reset_timeout: Duration::from_millis(0),
            min_requests: 2,
            window_size: 10,
            half_open_max_requests: 1,
        };
        b.iter(|| {
            let cb = CircuitBreaker::with_config(config.clone());

            // Normal operation: some successes
            for _ in 0..5 {
                cb.before_request().ok();
                cb.on_success().ok();
            }

            // Generate failures to trip the breaker
            for _ in 0..5 {
                cb.before_request().ok();
                cb.on_failure().ok();
            }
            // Now the circuit should be open
            assert_eq!(cb.state().unwrap(), CircuitState::Open);

            // Transition to half-open (reset_timeout is 0)
            cb.before_request().ok();
            assert_eq!(cb.state().unwrap(), CircuitState::HalfOpen);

            // Probe succeeds → back to closed
            cb.on_success().ok();
            assert_eq!(cb.state().unwrap(), CircuitState::Closed);
        });
    });

    group.finish();
}

fn bench_circuit_breaker_concurrent(c: &mut Criterion) {
    let mut group = c.benchmark_group("circuit_breaker_concurrent");

    for num_threads in [2, 4, 8] {
        group.bench_with_input(
            BenchmarkId::new("before_request", num_threads),
            &num_threads,
            |b, &num_threads| {
                let cb = Arc::new(CircuitBreaker::new(0.5, Duration::from_secs(30)));
                b.iter(|| {
                    let handles: Vec<_> = (0..num_threads)
                        .map(|_| {
                            let cb = cb.clone();
                            std::thread::spawn(move || {
                                for _ in 0..100 {
                                    if cb.before_request().is_ok() {
                                        cb.on_success().ok();
                                    }
                                }
                            })
                        })
                        .collect();
                    for h in handles {
                        h.join().unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Criterion groups
// ---------------------------------------------------------------------------

criterion_group!(
    benches,
    bench_rate_limiter_token_bucket,
    bench_rate_limiter_concurrent,
    bench_retry,
    bench_circuit_breaker,
    bench_circuit_breaker_concurrent,
);

criterion_main!(benches);
