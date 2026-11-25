//! Benchmarks for phenotype-daemon protocol and RPC operations.

use criterion::{criterion_group, criterion_main, Criterion};
use phenotype_daemon::protocol::{BufferPool, Request, Response};
use phenotype_daemon::rpc::{BytesPool, RpcHandler, SharedState};
use phenotype_skills::{Skill, SkillManifest};
use std::sync::Arc;

fn make_skill(id: &str) -> Skill {
    Skill::new(id, SkillManifest::new(id, "1.0.0"))
}

// ── BufferPool benchmarks ───────────────────────────────────────────────────

fn bench_buffer_pool(c: &mut Criterion) {
    let pool = BufferPool::new(64, 4096);
    c.bench_function("buffer_pool_acquire_release", |b| {
        b.iter(|| {
            let buf = pool.acquire(0).unwrap();
            pool.release(0, buf);
        });
    });
}

// ── BytesPool benchmarks ────────────────────────────────────────────────────

fn bench_bytes_pool(c: &mut Criterion) {
    c.bench_function("bytes_pool_acquire_release", |b| {
        b.iter_batched(
            || BytesPool::new(32),
            |mut pool| {
                let buf = pool.acquire();
                pool.release(buf);
            },
            criterion::BatchSize::SmallInput,
        );
    });
}

// ── Serialization benchmarks ────────────────────────────────────────────────

fn bench_serialization(c: &mut Criterion) {
    let request = Request::SkillRegister {
        skill: make_skill("bench-skill"),
    };
    let response = Response::SkillList {
        skills: (0..10).map(|i| make_skill(&format!("s{i}"))).collect(),
        total: 10,
    };

    let mut g = c.benchmark_group("serialization");

    g.bench_function("request_json_serialize", |b| {
        b.iter(|| serde_json::to_string(&request).unwrap());
    });
    g.bench_function("request_json_deserialize", |b| {
        let json = serde_json::to_string(&request).unwrap();
        b.iter(|| serde_json::from_str::<Request>(&json).unwrap());
    });
    g.bench_function("request_msgpack_serialize", |b| {
        b.iter(|| rmp_serde::to_vec_named(&request).unwrap());
    });
    g.bench_function("request_msgpack_deserialize", |b| {
        let bytes = rmp_serde::to_vec_named(&request).unwrap();
        b.iter(|| rmp_serde::from_slice::<Request>(&bytes).unwrap());
    });
    g.bench_function("response_json_serialize", |b| {
        b.iter(|| serde_json::to_string(&response).unwrap());
    });
    g.bench_function("response_json_deserialize", |b| {
        let json = serde_json::to_string(&response).unwrap();
        b.iter(|| serde_json::from_str::<Response>(&json).unwrap());
    });
    g.bench_function("response_msgpack_serialize", |b| {
        b.iter(|| rmp_serde::to_vec_named(&response).unwrap());
    });
    g.bench_function("response_msgpack_deserialize", |b| {
        let bytes = rmp_serde::to_vec_named(&response).unwrap();
        b.iter(|| rmp_serde::from_slice::<Response>(&bytes).unwrap());
    });
    g.finish();
}

// ── RpcHandler benchmarks ───────────────────────────────────────────────────

fn bench_rpc_handler(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let state = Arc::new(SharedState::new());

    // Register some skills so list/get have data
    rt.block_on(async {
        let handler = RpcHandler::new(state.clone());
        for i in 0..20 {
            handler
                .handle_request(Request::SkillRegister {
                    skill: make_skill(&format!("bench-s{i}")),
                })
                .await;
        }
    });

    let mut g = c.benchmark_group("rpc_handler");

    g.bench_function("handle_ping", |b| {
        let state = state.clone();
        b.iter(|| {
            let state = state.clone();
            rt.block_on(async move { RpcHandler::new(state).handle_request(Request::Ping).await });
        });
    });

    g.bench_function("handle_version", |b| {
        let state = state.clone();
        b.iter(|| {
            let state = state.clone();
            rt.block_on(async move {
                RpcHandler::new(state)
                    .handle_request(Request::Version)
                    .await
            });
        });
    });

    g.bench_function("handle_stats", |b| {
        let state = state.clone();
        b.iter(|| {
            let state = state.clone();
            rt.block_on(async move { RpcHandler::new(state).handle_request(Request::Stats).await });
        });
    });

    g.bench_function("handle_skill_list", |b| {
        let state = state.clone();
        b.iter(|| {
            let state = state.clone();
            rt.block_on(async move {
                RpcHandler::new(state)
                    .handle_request(Request::SkillList {
                        limit: None,
                        offset: None,
                    })
                    .await
            });
        });
    });

    g.bench_function("handle_skill_get", |b| {
        let state = state.clone();
        b.iter(|| {
            let state = state.clone();
            rt.block_on(async move {
                RpcHandler::new(state)
                    .handle_request(Request::SkillGet {
                        id: "bench-s5".into(),
                    })
                    .await
            });
        });
    });

    g.finish();
}

criterion_group!(
    benches,
    bench_buffer_pool,
    bench_bytes_pool,
    bench_serialization,
    bench_rpc_handler,
);
criterion_main!(benches);
