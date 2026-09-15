use criterion::{black_box, criterion_group, criterion_main, Criterion};
use phenotype_config_loader::*;
use std::io::Write;
use tempfile::NamedTempFile;

#[derive(Debug, serde::Deserialize, serde::Serialize)]
struct BenchConfig {
    name: String,
    value: i64,
    nested: Nested,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
struct Nested {
    host: String,
    port: u16,
}

fn make_toml() -> String {
    format!(
        r#"name = "bench"
value = 42
[nested]
host = "localhost"
port = 8080"#
    )
}

fn make_json() -> String {
    r#"{"name":"bench","value":42,"nested":{"host":"localhost","port":8080}}"#.to_string()
}

fn make_yaml() -> String {
    "name: bench\nvalue: 42\nnested:\n  host: localhost\n  port: 8080".to_string()
}

fn bench_parse_config_throughput(c: &mut Criterion) {
    let toml_content = make_toml();
    let json_content = make_json();
    let yaml_content = make_yaml();

    let mut group = c.benchmark_group("parse_config_throughput");

    group.bench_function("toml_100_iters", |b| {
        b.iter(|| {
            for _ in 0..100 {
                black_box(
                    parse_config::<BenchConfig>(black_box(&toml_content), ConfigFormat::Toml)
                        .unwrap(),
                );
            }
        });
    });

    group.bench_function("json_100_iters", |b| {
        b.iter(|| {
            for _ in 0..100 {
                black_box(
                    parse_config::<BenchConfig>(black_box(&json_content), ConfigFormat::Json)
                        .unwrap(),
                );
            }
        });
    });

    group.bench_function("yaml_100_iters", |b| {
        b.iter(|| {
            for _ in 0..100 {
                black_box(
                    parse_config::<BenchConfig>(black_box(&yaml_content), ConfigFormat::Yaml)
                        .unwrap(),
                );
            }
        });
    });

    group.finish();
}

fn bench_load_from_file(c: &mut Criterion) {
    c.bench_function("load_from_file_json", |b| {
        b.iter_batched(
            || {
                let mut f = NamedTempFile::new().unwrap();
                write!(f, "{}", make_json()).unwrap();
                f
            },
            |f| {
                black_box(load_from_file::<BenchConfig, _>(black_box(f.path())).unwrap());
            },
            criterion::BatchSize::SmallInput,
        );
    });
}

fn bench_merge_configs(c: &mut Criterion) {
    c.bench_function("merge_configs_5_sources", |b| {
        b.iter(|| {
            let sources: Vec<(String, ConfigFormat)> = (0..5)
                .map(|i| {
                    let j = format!(
                        r#"{{"name":"src{}","value":{},"nested":{{"host":"h{}","port":{}}}}}"#,
                        i,
                        i,
                        i,
                        8000 + i
                    );
                    (j, ConfigFormat::Json)
                })
                .collect();
            black_box(merge_configs::<BenchConfig>(black_box(sources)).unwrap());
        });
    });
}

fn bench_config_format_from_path(c: &mut Criterion) {
    let paths = [
        "config.toml",
        "config.yaml",
        "config.yml",
        "config.json",
        "config.txt",
    ];
    c.bench_function("from_path_5_lookups", |b| {
        b.iter(|| {
            for p in &paths {
                black_box(ConfigFormat::from_path(black_box(*p)));
            }
        });
    });
}

criterion_group!(
    benches,
    bench_parse_config_throughput,
    bench_load_from_file,
    bench_merge_configs,
    bench_config_format_from_path,
);
criterion_main!(benches);
