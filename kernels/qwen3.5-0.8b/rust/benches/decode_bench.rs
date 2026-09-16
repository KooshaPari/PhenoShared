// benches/decode_bench.rs — Criterion throughput benchmark for the QwenEngine.
//
// Measures tokens/sec of the decode loop and per-kernel latency for the
// fine-grained API.
//
// Run with: `cargo bench --bench decode_bench`

use std::time::Duration;

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use pheno_qwen_kernels::ffi;
use pheno_qwen_kernels::{arch, Engine, EngineError, QwenEngine, Weights};

fn skip_if_no_metal() -> bool {
    let mut h: bool = false;
    unsafe {
        let _ = ffi::pheno_engine_has_metal(std::ptr::null_mut(), &mut h);
    }
    false // We can't probe without an engine; rely on the constructor's NoDevice path.
}

fn make_engine() -> Option<QwenEngine> {
    // Synthetic weight blob large enough for the orchestrator.
    let n = arch::VOCAB_SIZE * arch::HIDDEN_SIZE * 2
        + arch::NUM_HIDDEN_LAYERS * arch::HIDDEN_SIZE * 2
        + arch::HIDDEN_SIZE * 2;
    let buf: Vec<u8> = vec![0u8; n];
    let weights = Weights {
        ptr: buf.as_ptr(),
        bytes: n,
    };
    let _hold = buf;

    match QwenEngine::new(
        std::env::var("PHENO_METAL_LIB").ok().as_deref(),
        weights,
        /*max_seq_len=*/512,
        /*batch_size=*/1,
    ) {
        Ok(e) => Some(e),
        Err(EngineError::NoDevice) => {
            eprintln!("[bench] no Metal device — skipping");
            None
        }
        Err(e) => {
            eprintln!("[bench] engine init failed: {e} — skipping");
            None
        }
    }
}

fn bench_decode_throughput(c: &mut Criterion) {
    if skip_if_no_metal() {
        return;
    }
    let mut eng = match make_engine() {
        Some(e) => e,
        None => return,
    };

    let mut group = c.benchmark_group("decode_throughput");
    group.measurement_time(Duration::from_secs(5));
    group.throughput(Throughput::Elements(1));

    // Warmup: 1 step to JIT pipelines.
    let _ = eng.decode_step(0, 0);

    for n in [10u32, 50, 100, 500].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(n), n, |b, &n| {
            b.iter(|| {
                for i in 0..n {
                    let _ = eng.decode_step(i as i32, i);
                }
            });
        });
    }
    group.finish();
}

fn bench_engine_construct(c: &mut Criterion) {
    let mut group = c.benchmark_group("engine_construct");
    group.measurement_time(Duration::from_secs(3));
    group.bench_function("create_destroy", |b| {
        b.iter(|| {
            let n = arch::VOCAB_SIZE * arch::HIDDEN_SIZE * 2;
            let buf = vec![0u8; n];
            let weights = Weights {
                ptr: buf.as_ptr(),
                bytes: n,
            };
            let _hold = buf;
            let eng = QwenEngine::new(
                std::env::var("PHENO_METAL_LIB").ok().as_deref(),
                weights,
                128,
                1,
            );
            let _ = eng; // dropped here
        });
    });
    group.finish();
}

fn bench_kv_cache_progression(c: &mut Criterion) {
    if skip_if_no_metal() {
        return;
    }
    let mut eng = match make_engine() {
        Some(e) => e,
        None => return,
    };

    let mut group = c.benchmark_group("kv_cache_progression");
    group.measurement_time(Duration::from_secs(3));

    for seq_len in [16u32, 64, 256, 1024].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(seq_len), seq_len, |b, &s| {
            b.iter(|| {
                for i in 0..s {
                    let _ = eng.decode_step(i as i32, i);
                }
            });
        });
    }
    group.finish();
}

fn bench_engine_probes(c: &mut Criterion) {
    let mut group = c.benchmark_group("engine_probes");
    let eng = match Engine::new() {
        Ok(e) => e,
        Err(_) => return,
    };
    group.bench_function("device_name", |b| b.iter(|| eng.device_name()));
    group.bench_function("has_metal", |b| b.iter(|| eng.has_metal()));
    group.finish();
}

criterion_group!(
    benches,
    bench_decode_throughput,
    bench_kv_cache_progression,
    bench_engine_probes,
    bench_engine_construct,
);
criterion_main!(benches);
