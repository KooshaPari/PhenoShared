use app_lib::ipc::IpcEnvelope;
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_ipc_layer(c: &mut Criterion) {
    let envelope = IpcEnvelope::sample_project_lookup();
    let json = serde_json::to_string(&envelope).expect("serialize benchmark fixture");

    c.bench_function("ipc_serialize_project_lookup", |b| {
        b.iter(|| serde_json::to_string(black_box(&envelope)).expect("serialize IPC envelope"))
    });

    c.bench_function("ipc_deserialize_project_lookup", |b| {
        b.iter(|| serde_json::from_str::<IpcEnvelope>(black_box(&json)).expect("deserialize IPC envelope"))
    });
}

criterion_group!(ipc_benches, bench_ipc_layer);
criterion_main!(ipc_benches);
