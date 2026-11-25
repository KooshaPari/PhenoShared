use std::collections::HashMap;

use criterion::{black_box, criterion_group, criterion_main, Criterion};

use settly::application::builder::ConfigBuilder;
use settly::crypto;
use settly::domain::config::{Config, ConfigValue};
use settly::domain::validation::{
    CompositeValidator, RangeValidator, RequiredKeys, TypeValidator, Validator,
};
use settly::LayerPriority;

#[derive(serde::Serialize, serde::Deserialize, Clone)]
struct BenchPayload {
    name: String,
    port: u16,
    host: String,
    features: Vec<String>,
}

// ---------------------------------------------------------------------------
// Validation benchmarks
// ---------------------------------------------------------------------------

fn bench_validation(c: &mut Criterion) {
    let mut group = c.benchmark_group("validation");

    // Prepare a fully-populated config.
    let mut config = Config::new();
    config.set("name", "bench");
    config.set("port", 8080);
    config.set("host", "localhost");

    group.bench_function("required_keys", |b| {
        let validator = RequiredKeys::new(vec![
            "name".to_string(),
            "port".to_string(),
            "host".to_string(),
        ]);
        b.iter(|| validator.validate(black_box(&config)).unwrap());
    });

    group.bench_function("type_validator", |b| {
        let validator = TypeValidator::new("port", "number");
        b.iter(|| validator.validate(black_box(&config)).unwrap());
    });

    group.bench_function("range_validator", |b| {
        let validator = RangeValidator::new("port").with_min(1.0).with_max(65535.0);
        b.iter(|| validator.validate(black_box(&config)).unwrap());
    });

    group.bench_function("composite_3_validators", |b| {
        let composite = CompositeValidator::new()
            .push(RequiredKeys::new(vec![
                "name".to_string(),
                "port".to_string(),
                "host".to_string(),
            ]))
            .push(TypeValidator::new("port", "number"))
            .push(RangeValidator::new("port").with_min(1.0).with_max(65535.0));
        b.iter(|| composite.validate(black_box(&config)).unwrap());
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Builder benchmarks
// ---------------------------------------------------------------------------

fn make_values() -> HashMap<String, serde_json::Value> {
    let mut map = HashMap::new();
    map.insert("name".into(), serde_json::Value::String("bench".into()));
    map.insert("port".into(), serde_json::json!(8080));
    map.insert("host".into(), serde_json::Value::String("localhost".into()));
    map
}

fn bench_builder(c: &mut Criterion) {
    let mut group = c.benchmark_group("builder");

    group.bench_function("build_with_values", |b| {
        b.iter(|| {
            ConfigBuilder::new()
                .with_values("app", LayerPriority::Default, black_box(make_values()))
                .build()
                .unwrap()
        });
    });

    group.bench_function("build_with_validator", |b| {
        b.iter(|| {
            ConfigBuilder::new()
                .with_values("app", LayerPriority::Default, black_box(make_values()))
                .with_validator(RequiredKeys::new(vec!["name".to_string()]))
                .build()
                .unwrap()
        });
    });

    group.bench_function("build_two_layers", |b| {
        let mut overrides = HashMap::new();
        overrides.insert("port".into(), serde_json::json!(9090));
        b.iter(|| {
            ConfigBuilder::new()
                .with_values("default", LayerPriority::Default, black_box(make_values()))
                .with_values("override", LayerPriority::Cli, black_box(overrides.clone()))
                .build()
                .unwrap()
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Crypto benchmarks
// ---------------------------------------------------------------------------

fn bench_crypto(c: &mut Criterion) {
    let mut group = c.benchmark_group("crypto");
    let passphrase = b"correct horse battery staple";
    let payload = BenchPayload {
        name: "benchmark".into(),
        port: 8080,
        host: "localhost".into(),
        features: vec!["auth".into(), "metrics".into()],
    };

    group.bench_function("encrypt", |b| {
        b.iter(|| {
            crypto::encrypt(black_box(passphrase), black_box(&payload), b"bench-aad").unwrap()
        });
    });

    group.bench_function("decrypt", |b| {
        let env = crypto::encrypt(passphrase, &payload, b"bench-aad").unwrap();
        b.iter(|| {
            crypto::decrypt::<BenchPayload>(black_box(passphrase), black_box(&env)).unwrap()
        });
    });

    group.bench_function("encrypt_decrypt_roundtrip", |b| {
        b.iter(|| {
            let env =
                crypto::encrypt(black_box(passphrase), black_box(&payload), b"bench-aad").unwrap();
            crypto::decrypt::<BenchPayload>(black_box(passphrase), &env).unwrap()
        });
    });

    group.finish();
}

criterion_group!(benches, bench_validation, bench_builder, bench_crypto);
criterion_main!(benches);
