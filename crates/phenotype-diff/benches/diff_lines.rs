//! Criterion benchmarks for `phenotype-diff::diff` over synthesized inputs.
//!
//! Sweeps three line counts (1k, 10k, 100k) and two change densities
//! (1% modified, 10% modified) so the I/O hot path is exercised at
//! realistic scales.

use std::hint::black_box;

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use phenotype_diff::diff;

fn make_input(lines: usize, change_pct: usize) -> (String, String) {
    let old: Vec<String> = (0..lines)
        .map(|i| format!("line {i:06} payload\n"))
        .collect();
    let mut new = old.clone();
    let step = if change_pct == 0 {
        usize::MAX
    } else {
        100 / change_pct
    };
    for (i, line) in new.iter_mut().enumerate() {
        if i % step == 0 {
            *line = format!("line {i:06} MODIFIED payload\n");
        }
    }
    (old.join(""), new.join(""))
}

fn bench_diff_lines(c: &mut Criterion) {
    let mut group = c.benchmark_group("diff_lines");
    for &lines in &[1_000usize, 10_000, 100_000] {
        for &change_pct in &[1usize, 10] {
            let (old, new) = make_input(lines, change_pct);
            let label = format!("{lines}_lines_{change_pct}pct");
            group.bench_with_input(
                BenchmarkId::from_parameter(label),
                &(old, new),
                |b, (o, n)| {
                    b.iter(|| {
                        let patch = diff(black_box(o), black_box(n));
                        black_box(patch);
                    });
                },
            );
        }
    }
    group.finish();
}

criterion_group!(benches, bench_diff_lines);
criterion_main!(benches);
