// SPDX-License-Identifier: MIT OR Apache-2.0
//! Criterion micro-benchmarks for `phenotype-contracts`.
//!
//! Benchmarks the hot serde round-trip on the public `Contract` / `Verdict`
//! types. Run with `cargo bench --workspace` or `cargo bench -p
//! phenotype-contracts`. Criterion is gated to `harness = false` in
//! `Cargo.toml` so it owns its own benchmark harness.
use criterion::{criterion_group, criterion_main, Criterion};
use phenotype_contracts::{Contract, Verdict};

fn contract_fixture() -> Contract {
    Contract {
        name: "bench_no_overflow".to_string(),
        predicate: "x + 1 > x".to_string(),
        target: "fn add_one(x: u64) -> u64".to_string(),
    }
}

fn verdict_fixture() -> Verdict {
    Verdict {
        ok: true,
        counterexample: None,
        proof: Some("kani:bench_no_overflow".to_string()),
        duration_ms: 10,
    }
}

fn bench_contract_serde(c: &mut Criterion) {
    let fixture = contract_fixture();
    c.bench_function("contract_serde_round_trip", |b| {
        b.iter(|| {
            let j = serde_json::to_string(&fixture).unwrap();
            let back: Contract = serde_json::from_str(&j).unwrap();
            back
        });
    });
}

fn bench_verdict_serde(c: &mut Criterion) {
    let fixture = verdict_fixture();
    c.bench_function("verdict_serde_round_trip", |b| {
        b.iter(|| {
            let j = serde_json::to_string(&fixture).unwrap();
            let back: Verdict = serde_json::from_str(&j).unwrap();
            back
        });
    });
}

criterion_group!(benches, bench_contract_serde, bench_verdict_serde);
criterion_main!(benches);
