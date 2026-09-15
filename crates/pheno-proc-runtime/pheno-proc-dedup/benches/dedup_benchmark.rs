//! Benchmarks for pheno-proc-dedup
//!
//! Measures DedupFilter, BloomFilter, and InMemoryLockAdapter throughput.

use criterion::{criterion_group, criterion_main, Criterion};
use pheno_proc_dedup::*;
use std::time::Duration;

fn bench_dedup_filter(c: &mut Criterion) {
    c.bench_function("dedup_filter_insert_1000", |b| {
        b.iter(|| {
            let mut filter = DedupFilter::new();
            for i in 0..1000 {
                filter.check_and_insert(format!("item-{i}"));
            }
        });
    });

    c.bench_function("dedup_filter_check_1000_hits", |b| {
        b.iter(|| {
            let mut filter = DedupFilter::new();
            for i in 0..1000 {
                filter.check_and_insert(format!("item-{i}"));
            }
            for i in 0..1000 {
                let _ = filter.check_and_insert(format!("item-{i}"));
            }
        });
    });
}

fn bench_bloom_filter(c: &mut Criterion) {
    c.bench_function("bloom_add_1000", |b| {
        b.iter(|| {
            let mut filter = BloomFilter::new(10_000, 7);
            for i in 0..1000 {
                filter.add(format!("item-{i}").as_bytes());
            }
        });
    });

    c.bench_function("bloom_check_1000_hits", |b| {
        b.iter(|| {
            let mut filter = BloomFilter::new(10_000, 7);
            for i in 0..1000 {
                filter.add(format!("item-{i}").as_bytes());
            }
            for i in 0..1000 {
                let _ = filter.check(format!("item-{i}").as_bytes());
            }
        });
    });

    c.bench_function("bloom_check_and_add_1000", |b| {
        b.iter(|| {
            let mut filter = BloomFilter::new(10_000, 7);
            for i in 0..1000 {
                let _ = filter.check_and_add(format!("item-{i}").as_bytes());
            }
        });
    });
}

fn bench_lock_adapter(c: &mut Criterion) {
    c.bench_function("lock_adapter_acquire_release_100", |b| {
        b.iter(|| {
            let adapter = InMemoryLockAdapter::with_ttl(Duration::from_secs(60));
            for i in 0..100 {
                let _ = adapter.acquire(&format!("cmd-{i}"), i, None);
            }
            for i in 0..100 {
                adapter.release(&format!("cmd-{i}"), i).unwrap();
            }
        });
    });

    c.bench_function("lock_adapter_prevent_duplicates_100", |b| {
        b.iter(|| {
            let adapter = InMemoryLockAdapter::new();
            for i in 0..100 {
                let _ = adapter.acquire(&format!("cmd-{i}"), 100, None);
            }
            // All 100 should fail (already locked)
            for i in 0..100 {
                let result = adapter.acquire(&format!("cmd-{i}"), 200, None);
                assert!(result.is_err());
            }
        });
    });

    c.bench_function("lock_adapter_cleanup_100_expired", |b| {
        b.iter(|| {
            let adapter = InMemoryLockAdapter::with_ttl(Duration::from_millis(1));
            for i in 0..100 {
                let _ = adapter.acquire(&format!("cmd-{i}"), i, None);
            }
            std::thread::sleep(Duration::from_millis(5));
            let _ = adapter.cleanup_expired();
        });
    });
}

criterion_group!(
    benches,
    bench_dedup_filter,
    bench_bloom_filter,
    bench_lock_adapter
);
criterion_main!(benches);
