use criterion::{black_box, criterion_group, criterion_main, Criterion};
use httpora_core::{RateLimiter, RetryLayer, CircuitBreaker};
use std::time::Duration;

fn benchmark_rate_limiter(c: &mut Criterion) {
    c.bench_function("token_bucket_creation", |b| {
        b.iter(|| {
            let _ = RateLimiter::token_bucket(black_box(100), black_box(10.0));
        });
    });
}

fn benchmark_retry_layer(c: &mut Criterion) {
    c.bench_function("retry_layer_creation", |b| {
        b.iter(|| {
            let _ = RetryLayer::new(black_box(3), black_box(Duration::from_millis(100)));
        });
    });
}

fn benchmark_circuit_breaker(c: &mut Criterion) {
    c.bench_function("circuit_breaker_creation", |b| {
        b.iter(|| {
            let _ = CircuitBreaker::new(black_box(0.5), black_box(Duration::from_secs(30)));
        });
    });
}

criterion_group!(
    benches,
    benchmark_rate_limiter,
    benchmark_retry_layer,
    benchmark_circuit_breaker
);
criterion_main!(benches);
