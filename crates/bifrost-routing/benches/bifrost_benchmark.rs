use criterion::{criterion_group, criterion_main, Criterion};

use bifrost_routing::{
    CostAwareRouter, FailoverRouter, LatencyAwareRouter, Router, RoutingRequest,
    SemanticCacheRouter, TaskSpecificRouter,
};

fn bench_cost_aware(c: &mut Criterion) {
    let router = CostAwareRouter::new();
    let req = RoutingRequest::new("gpt-4o", "benchmark prompt");
    c.bench_function("cost_aware_decide", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_latency_aware(c: &mut Criterion) {
    let router = LatencyAwareRouter::new();
    let req = RoutingRequest::new("gpt-4o", "benchmark prompt");
    c.bench_function("latency_aware_decide", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_task_specific(c: &mut Criterion) {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("gpt-4o", "benchmark prompt").with_task("code");
    c.bench_function("task_specific_decide", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_failover(c: &mut Criterion) {
    use std::sync::Arc;
    let primary = Arc::new(CostAwareRouter::new());
    let fallback = Arc::new(LatencyAwareRouter::new());
    let router = FailoverRouter::new(primary, fallback);
    let req = RoutingRequest::new("gpt-4o", "benchmark prompt");
    c.bench_function("failover_decide", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_semantic_cache_miss(c: &mut Criterion) {
    let router = SemanticCacheRouter::new();
    c.bench_function("semantic_cache_miss", |b| {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let mut i: u64 = 0;
        b.iter(|| {
            i += 1;
            let req = RoutingRequest::new("gpt-4o", format!("unique prompt {i}"));
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_semantic_cache_hit(c: &mut Criterion) {
    let router = SemanticCacheRouter::new();
    let req = RoutingRequest::new("gpt-4o", "cached prompt for benchmark");
    // Prime the cache
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(router.decide(&req)).unwrap();

    c.bench_function("semantic_cache_hit", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(router.decide(&req))
        });
    });
}

fn bench_serialization(c: &mut Criterion) {
    let req = RoutingRequest::new("gpt-4o", "test prompt").with_task("code");
    c.bench_function("routing_request_serialize", |b| {
        b.iter(|| serde_json::to_string(&req).unwrap());
    });

    let json = serde_json::to_string(&req).unwrap();
    c.bench_function("routing_request_deserialize", |b| {
        b.iter(|| {
            let _: RoutingRequest = serde_json::from_str(&json).unwrap();
        });
    });

    let decision = bifrost_routing::RouterDecision::new("gpt-4o")
        .with_reasoning("test")
        .with_cost(0.003)
        .with_latency(500)
        .with_confidence(0.95);
    c.bench_function("router_decision_serialize", |b| {
        b.iter(|| serde_json::to_string(&decision).unwrap());
    });
}

criterion_group!(
    benches,
    bench_cost_aware,
    bench_latency_aware,
    bench_task_specific,
    bench_failover,
    bench_semantic_cache_miss,
    bench_semantic_cache_hit,
    bench_serialization,
);
criterion_main!(benches);
