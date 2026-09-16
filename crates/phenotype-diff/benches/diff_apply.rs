//! Criterion benchmarks for `phenotype-diff::apply` (patch application).
//!
//! Computes a diff once then times patch application across 1k/10k/100k
//! line sources to mirror common post-merge rebuild workflows.

use std::hint::black_box;

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use phenotype_diff::{apply, diff};

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

fn bench_diff_apply(c: &mut Criterion) {
    let mut group = c.benchmark_group("diff_apply");
    for &lines in &[1_000usize, 10_000, 100_000] {
        let (old, new) = make_input(lines, 1);
        let patch = diff(&old, &new);
        group.bench_with_input(
            BenchmarkId::from_parameter(lines),
            &(&old, &patch),
            |b, (o, p)| {
                b.iter(|| {
                    let out = apply(black_box(o), black_box(p)).unwrap();
                    black_box(out);
                });
            },
        );
    }
    group.finish();
}

criterion_group!(benches, bench_diff_apply);
criterion_main!(benches);
