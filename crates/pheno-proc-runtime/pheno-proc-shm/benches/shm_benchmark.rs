//! Benchmarks for pheno-proc-shm
//!
//! Measures SharedMemory read/write and ShmRegistry operations.

use criterion::{criterion_group, criterion_main, Criterion};
use pheno_proc_shm::*;

fn bench_shared_memory(c: &mut Criterion) {
    c.bench_function("shm_create_4k", |b| {
        b.iter(|| {
            let _ = SharedMemory::create("bench", 4096);
        });
    });

    c.bench_function("shm_write_read_1kb", |b| {
        b.iter(|| {
            let mut shm = SharedMemory::create("bench", 4096).unwrap();
            let data = vec![0u8; 1024];
            shm.write(0, &data).unwrap();
            let _ = shm.read(0, 1024).unwrap();
        });
    });

    c.bench_function("shm_write_read_sequential", |b| {
        b.iter(|| {
            let mut shm = SharedMemory::create("bench", 65536).unwrap();
            let data = vec![42u8; 256];
            for offset in (0..65536).step_by(256) {
                shm.write(offset, &data).unwrap();
            }
            for offset in (0..65536).step_by(256) {
                let _ = shm.read(offset, 256).unwrap();
            }
        });
    });
}

fn bench_shm_registry(c: &mut Criterion) {
    c.bench_function("registry_create_open", |b| {
        b.iter(|| {
            let registry = ShmRegistry::new();
            for i in 0..100 {
                let _ = registry.create(&format!("seg-{i}"), 256);
            }
            for i in 0..100 {
                let _ = registry.open(&format!("seg-{i}"));
            }
        });
    });

    c.bench_function("registry_lifecycle", |b| {
        b.iter(|| {
            let registry = ShmRegistry::new();
            for i in 0..50 {
                let name = format!("lifecycle-{i}");
                let shm = registry.create(&name, 512).unwrap();
                shm.lock().unwrap().write(0, b"data").unwrap();
                let _ = registry.open(&name).unwrap();
                registry.remove(&name).unwrap();
            }
        });
    });
}

criterion_group!(benches, bench_shared_memory, bench_shm_registry);
criterion_main!(benches);
