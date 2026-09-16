//! Criterion benchmarks for `agent-elapsed` calculation.
//!
//! Generates random (start, end) timestamp pairs and times the
//! `chrono::DateTime<Utc>` arithmetic used to compute elapsed seconds.

use std::hint::black_box;

use chrono::{DateTime, Duration, Utc};
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};

/// 1000 deterministic-but-spread start/end pairs (no RNG to keep benches
/// reproducible across runs).
fn random_pairs() -> Vec<(DateTime<Utc>, DateTime<Utc>)> {
    let base = DateTime::parse_from_rfc3339("2024-01-01T00:00:00Z")
        .unwrap()
        .with_timezone(&Utc);
    (0..1000)
        .map(|i| {
            // Deterministic pseudo-random spread across +/-30 days.
            let offset_a = Duration::seconds(((i * 73) % (30 * 86_400)) as i64);
            let offset_b = Duration::seconds(((i * 211 + 17) % (60 * 86_400)) as i64);
            (base + offset_a, base + offset_b)
        })
        .collect()
}

fn bench_elapsed_subtraction(c: &mut Criterion) {
    let pairs = random_pairs();
    c.bench_function("elapsed_subtraction_1000", |b| {
        b.iter(|| {
            let mut total_secs: i64 = 0;
            for (a, b_dt) in black_box(&pairs) {
                let dt = *b_dt - *a;
                total_secs += dt.num_seconds();
            }
            black_box(total_secs);
        });
    });
}

fn bench_elapsed_subtraction_scaled(c: &mut Criterion) {
    let pairs = random_pairs();
    let mut group = c.benchmark_group("elapsed_subtraction_scaled");
    for &n in &[10usize, 100, 1000] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            let slice = &pairs[..n];
            b.iter(|| {
                let mut total: i64 = 0;
                for (a, e) in black_box(slice) {
                    total += (*e - *a).num_seconds();
                }
                black_box(total);
            });
        });
    }
    group.finish();
}

criterion_group!(
    benches,
    bench_elapsed_subtraction,
    bench_elapsed_subtraction_scaled
);
criterion_main!(benches);
