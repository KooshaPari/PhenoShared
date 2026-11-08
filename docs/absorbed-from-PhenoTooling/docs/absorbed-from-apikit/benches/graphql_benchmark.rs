use std::sync::Arc;

use apisync::adapters::graphql::{build_schema, execute_mutation, execute_query};
use apisync::domain::ItemStore;
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use tokio::runtime::Runtime;

fn bench_schema_parsing(c: &mut Criterion) {
    c.bench_function("graphql_schema_parsing", |b| {
        let store = Arc::new(ItemStore::new());
        b.iter(|| build_schema(store.clone()));
    });
}

fn bench_query_execution(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let store = Arc::new(ItemStore::new());
    let schema = build_schema(store);
    c.bench_function("graphql_query_execution", |b| {
        b.iter(|| {
            rt.block_on(async {
                execute_query(black_box(&schema), black_box("{ items { id name description } }"))
                    .await;
            });
        });
    });
}

fn bench_mutation_handling(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();
    let store = Arc::new(ItemStore::new());
    let schema = build_schema(store);
    let mutation = r#"mutation { createItem(input: { name: "New Item", description: "New Desc" }) { id name description } }"#;
    c.bench_function("graphql_mutation_handling", |b| {
        b.iter(|| {
            rt.block_on(async {
                execute_mutation(black_box(&schema), black_box(mutation)).await;
            });
        });
    });
}

criterion_group!(benches, bench_schema_parsing, bench_query_execution, bench_mutation_handling);
criterion_main!(benches);
