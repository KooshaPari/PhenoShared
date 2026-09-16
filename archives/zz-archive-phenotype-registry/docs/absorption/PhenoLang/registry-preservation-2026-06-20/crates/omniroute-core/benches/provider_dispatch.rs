//! Provider dispatch benchmark suite
//!
//! Measures the performance of provider selection and dispatch.

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use omniroute_core::router::Router;
use omniroute_core::types::ProviderConfig;
use std::sync::Arc;
use std::time::Duration;

fn create_multi_provider_router() -> Router {
    let mut router = Router::new();

    // Register multiple providers
    let providers: Vec<(&str, &str)> = vec![
        ("provider-a", "model-a-"),
        ("provider-b", "model-b-"),
        ("provider-c", "model-c-"),
    ];

    for (name, _) in &providers {
        let config = ProviderConfig::new(name);
        // In real scenario, we'd create actual providers
        // For benchmark, we use mock
        router = router.add_model_mapping(providers.iter().find(|p| p.0 == *name).unwrap().1, name);
    }

    router.with_mock()
}

fn provider_selection_benchmark(c: &mut Criterion) {
    let router = create_multi_provider_router();

    let models = vec![
        "model-a-gpt-4",
        "model-b-claude",
        "model-c-gemini",
        "unknown-model",
    ];

    let mut group = c.benchmark_group("provider_selection");
    group.measurement_time(Duration::from_secs(5));

    for model in models {
        group.bench_with_input(
            BenchmarkId::new("get_provider", model),
            model,
            |b, model| {
                b.iter(|| {
                    let provider = router.get_provider_for_model(black_box(model));
                    black_box(provider)
                });
            },
        );
    }

    group.finish();
}

fn concurrent_provider_access(c: &mut Criterion) {
    let router = Arc::new(create_multi_provider_router());

    let mut group = c.benchmark_group("concurrent_provider_access");
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("10_concurrent_requests", |b| {
        b.to_async(&tokio::runtime::Runtime::new().unwrap())
            .iter(|| async {
                let mut handles = Vec::new();
                for _ in 0..10 {
                    let router = router.clone();
                    handles.push(tokio::spawn(async move {
                        router.get_provider_for_model("mock-gpt-4")
                    }));
                }
                let results: Vec<_> = futures::future::join_all(handles).await;
                black_box(results)
            });
    });

    group.finish();
}

criterion_group!(
    benches,
    provider_selection_benchmark,
    concurrent_provider_access,
);
criterion_main!(benches);
