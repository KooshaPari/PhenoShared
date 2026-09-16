use criterion::{black_box, criterion_group, criterion_main, Criterion};
use datakit::{DataStream, Pipeline};

fn bench_pipeline_run(c: &mut Criterion) {
    let mut group = c.benchmark_group("pipeline_run");

    for size in [10, 100, 1000] {
        group.bench_with_input(format!("size_{size}"), &size, |b, &size| {
            let pipeline = Pipeline::new(Box::new(|x: i32| x * 2));
            let input: Vec<DataStream<i32>> = (0..size).map(DataStream::new).collect();
            b.iter(|| {
                let cloned: Vec<DataStream<i32>> = input.iter().cloned().collect();
                pipeline.run(black_box(cloned))
            });
        });
    }

    group.finish();
}

fn bench_datastream_new(c: &mut Criterion) {
    c.bench_function("datastream_new_i32", |b| {
        b.iter(|| DataStream::new(black_box(42)));
    });

    c.bench_function("datastream_new_string", |b| {
        b.iter(|| DataStream::new(black_box(String::from("hello world"))));
    });
}

criterion_group!(benches, bench_pipeline_run, bench_datastream_new);
criterion_main!(benches);
