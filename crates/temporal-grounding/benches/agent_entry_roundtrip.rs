//! Criterion benchmarks for `temporal-grounding`.
//!
//! Exercises the JSON serialization hot path (`AgentEntry`) over many
//! iterations, since `active-agents.json` is read on every CLI invocation.

use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion};
use temporal_grounding::AgentEntry;

fn build_entry(i: usize) -> AgentEntry {
    AgentEntry {
        id: format!("agent-{i}"),
        started_at: "2024-01-01T00:00:00Z".to_string(),
        label: Some("sweep".to_string()),
    }
}

fn bench_agent_entry_serialize(c: &mut Criterion) {
    let entry = build_entry(0);
    c.bench_function("agent_entry_serialize", |b| {
        b.iter(|| {
            let s = serde_json::to_string(black_box(&entry)).unwrap();
            black_box(s);
        });
    });
}

fn bench_agent_entry_roundtrip(c: &mut Criterion) {
    let entry = build_entry(0);
    let json = serde_json::to_string(&entry).unwrap();
    c.bench_function("agent_entry_roundtrip", |b| {
        b.iter(|| {
            let s = serde_json::to_string(black_box(&entry)).unwrap();
            let back: AgentEntry = serde_json::from_str(black_box(&s)).unwrap();
            black_box(back);
        });
    });
}

fn bench_agent_entry_roundtrip_x1000(c: &mut Criterion) {
    let entries: Vec<AgentEntry> = (0..1000).map(build_entry).collect();
    c.bench_function("agent_entry_roundtrip_x1000", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&entries)).unwrap();
            let back: Vec<AgentEntry> = serde_json::from_str(black_box(&json)).unwrap();
            black_box(back);
        });
    });
}

criterion_group!(
    benches,
    bench_agent_entry_serialize,
    bench_agent_entry_roundtrip,
    bench_agent_entry_roundtrip_x1000
);
criterion_main!(benches);
