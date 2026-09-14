use std::hint::black_box;

use apisync::{Request, Response};
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_request_new(c: &mut Criterion) {
    c.bench_function("request_new", |b| {
        b.iter(|| Request::new(black_box("/users"), black_box("GET")));
    });
}

fn bench_request_with_headers(c: &mut Criterion) {
    c.bench_function("request_with_headers", |b| {
        b.iter(|| {
            Request::new(black_box("/users"), black_box("GET"))
                .with_header(black_box("Content-Type"), black_box("application/json"))
                // Use a non-secret placeholder so secret scanners do not flag this benchmark.
                .with_header(black_box("Authorization"), black_box("Bearer example-token"))
        });
    });
}

fn bench_request_with_body(c: &mut Criterion) {
    let body = vec![1u8; 1024];
    c.bench_function("request_with_body", |b| {
        b.iter(|| {
            Request::new(black_box("/users"), black_box("POST")).with_body(black_box(body.clone()))
        });
    });
}

fn bench_response_new(c: &mut Criterion) {
    c.bench_function("response_new", |b| {
        b.iter(|| Response::new(black_box(200)));
    });
}

fn bench_response_ok(c: &mut Criterion) {
    c.bench_function("response_ok", |b| {
        b.iter(Response::ok);
    });
}

fn bench_response_not_found(c: &mut Criterion) {
    c.bench_function("response_not_found", |b| {
        b.iter(Response::not_found);
    });
}

fn bench_response_server_error(c: &mut Criterion) {
    c.bench_function("response_server_error", |b| {
        b.iter(Response::server_error);
    });
}

fn bench_response_with_headers(c: &mut Criterion) {
    c.bench_function("response_with_headers", |b| {
        b.iter(|| {
            Response::ok()
                .with_header(black_box("Content-Type"), black_box("application/json"))
                .with_header(black_box("X-Request-Id"), black_box("12345"))
        });
    });
}

fn bench_response_with_large_body(c: &mut Criterion) {
    let body = vec![0u8; 4096];
    c.bench_function("response_with_large_body", |b| {
        b.iter(|| Response::ok().with_body(black_box(body.clone())));
    });
}

criterion_group!(
    benches,
    bench_request_new,
    bench_request_with_headers,
    bench_request_with_body,
    bench_response_new,
    bench_response_ok,
    bench_response_not_found,
    bench_response_server_error,
    bench_response_with_headers,
    bench_response_with_large_body
);
criterion_main!(benches);
