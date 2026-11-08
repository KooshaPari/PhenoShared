// SPDX-License-Identifier: MIT OR Apache-2.0
//! Criterion micro-benchmarks for `phenotype-port-interfaces`.
//!
//! Benchmarks the hot serde round-trip on the public `VerifyRequest` /
//! `VerifyResponse` types. Criterion is gated to `harness = false` in
//! `Cargo.toml` so it owns its own benchmark harness.
use criterion::{criterion_group, criterion_main, Criterion};
use phenotype_port_interfaces::{VerifyRequest, VerifyResponse};

fn verify_request_fixture() -> VerifyRequest {
    VerifyRequest {
        backend: phenotype_port_interfaces::Backend::Kani,
        contract_name: "bench_no_overflow".to_string(),
    }
}

fn verify_response_fixture() -> VerifyResponse {
    VerifyResponse {
        ok: true,
        proof: Some("kani:bench_no_overflow".to_string()),
        counterexample: None,
        duration_ms: 10,
    }
}

fn bench_verify_request_serde(c: &mut Criterion) {
    let fixture = verify_request_fixture();
    c.bench_function("verify_request_serde_round_trip", |b| {
        b.iter(|| {
            let j = serde_json::to_string(&fixture).unwrap();
            let back: VerifyRequest = serde_json::from_str(&j).unwrap();
            back
        });
    });
}

fn bench_verify_response_serde(c: &mut Criterion) {
    let fixture = verify_response_fixture();
    c.bench_function("verify_response_serde_round_trip", |b| {
        b.iter(|| {
            let j = serde_json::to_string(&fixture).unwrap();
            let back: VerifyResponse = serde_json::from_str(&j).unwrap();
            back
        });
    });
}

criterion_group!(benches, bench_verify_request_serde, bench_verify_response_serde);
criterion_main!(benches);
