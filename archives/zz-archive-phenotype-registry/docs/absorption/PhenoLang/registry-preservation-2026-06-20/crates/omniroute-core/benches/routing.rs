//! Routing benchmark suite for OmniRoute Core
//!
//! Measures the performance of the routing engine.

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use omniroute_core::router::Router;
use omniroute_core::types::{ChatRequest, Message};
use std::time::Duration;

fn create_router() -> Router {
    Router::with_mock().add_model_mapping("mock-", "mock")
}

fn create_request(model: &str) -> ChatRequest {
    ChatRequest {
        model: model.to_string(),
        messages: vec![Message::user("Hello, world!")],
        stream: false,
        ..Default::default()
    }
}

fn routing_benchmark(c: &mut Criterion) {
    let router = create_router();

    let models = vec![
        "mock-gpt-4",
        "mock-gpt-3.5-turbo",
        "mock-claude-3",
    ];

    let mut group = c.benchmark_group("routing");
    group.measurement_time(Duration::from_secs(5));
    group.sample_size(1000);

    for model in models {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::new("get_provider", model), model, |b, model| {
            b.iter(|| {
                let provider = router.get_provider_for_model(black_box(model));
                black_box(provider)
            });
        });
    }

    group.finish();
}

fn routing_with_fallback_benchmark(c: &mut Criterion) {
    let mut router = Router::with_mock();
    router = router.add_model_mapping("primary-", "mock");
    router = router.add_model_mapping("secondary-", "mock");
    router = router.add_model_mapping("fallback-", "mock");

    let models = vec![
        "primary-model",
        "secondary-model",
        "fallback-model",
        "unknown-model",
    ];

    let mut group = c.benchmark_group("routing_with_fallback");
    group.measurement_time(Duration::from_secs(3));

    for model in models {
        group.bench_function(BenchmarkId::new("get_provider", model), |b| {
            b.iter(|| {
                let provider = router.get_provider_for_model(black_box(model));
                black_box(provider)
            });
        });
    }

    group.finish();
}

fn model_lookup_benchmark(c: &mut Criterion) {
    let router = create_router();

    let mut group = c.benchmark_group("model_lookup");
    group.measurement_time(Duration::from_secs(5));

    // Benchmark supports_model check
    group.bench_function("supports_model_true", |b| {
        b.iter(|| {
            let result = router.supports_model(black_box("mock-gpt-4"));
            black_box(result)
        });
    });

    group.bench_function("supports_model_false", |b| {
        b.iter(|| {
            let result = router.supports_model(black_box("unknown-model"));
            black_box(result)
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    routing_benchmark,
    routing_with_fallback_benchmark,
    model_lookup_benchmark,
);
criterion_main!(benches);
