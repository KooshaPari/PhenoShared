//! Benchmarks for pheno-proc-queue
//!
//! Measures enqueue/dequeue throughput and priority sorting.

use criterion::{criterion_group, criterion_main, Criterion};
use pheno_proc_queue::*;

fn bench_enqueue(c: &mut Criterion) {
    c.bench_function("queue_enqueue_100", |b| {
        b.iter(|| {
            let queue = InMemoryQueueAdapter::new();
            for i in 0..100 {
                let priority = match i % 4 {
                    0 => Priority::Critical,
                    1 => Priority::High,
                    2 => Priority::Normal,
                    _ => Priority::Low,
                };
                queue.enqueue(format!("cmd-{i}"), priority, None);
            }
        });
    });

    c.bench_function("queue_enqueue_1000", |b| {
        b.iter(|| {
            let queue = InMemoryQueueAdapter::new();
            for i in 0..1000 {
                queue.enqueue(format!("cmd-{i}"), Priority::Normal, None);
            }
        });
    });
}

fn bench_dequeue(c: &mut Criterion) {
    c.bench_function("queue_dequeue_100", |b| {
        b.iter(|| {
            let queue = InMemoryQueueAdapter::new();
            for i in 0..100 {
                queue.enqueue(format!("cmd-{i}"), Priority::Normal, None);
            }
            for _ in 0..100 {
                let _ = queue.dequeue();
            }
        });
    });
}

fn bench_priority_sort(c: &mut Criterion) {
    c.bench_function("queue_priority_sort_100_mixed", |b| {
        b.iter(|| {
            let queue = InMemoryQueueAdapter::new();
            // Enqueue in worst-case order (all low first, then critical last)
            for i in 0..25 {
                queue.enqueue(format!("low-{i}"), Priority::Low, None);
            }
            for i in 0..25 {
                queue.enqueue(format!("normal-{i}"), Priority::Normal, None);
            }
            for i in 0..25 {
                queue.enqueue(format!("high-{i}"), Priority::High, None);
            }
            for i in 0..25 {
                queue.enqueue(format!("critical-{i}"), Priority::Critical, None);
            }

            // Verify first is critical
            let first = queue.dequeue().unwrap();
            assert_eq!(first.priority, Priority::Critical);
        });
    });
}

fn bench_queue_stats(c: &mut Criterion) {
    c.bench_function("queue_stats_500", |b| {
        b.iter(|| {
            let queue = InMemoryQueueAdapter::new();
            for i in 0..500 {
                let item = queue.enqueue(format!("cmd-{i}"), Priority::Normal, None);
                if i % 3 == 0 {
                    queue
                        .update_status(&item.id, QueueStatus::Completed)
                        .unwrap();
                }
            }
            let _ = queue.stats();
        });
    });
}

criterion_group!(
    benches,
    bench_enqueue,
    bench_dequeue,
    bench_priority_sort,
    bench_queue_stats
);
criterion_main!(benches);
