//! Chat completions benchmark suite
//!
//! Measures the performance of chat completion requests.

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use omniroute_core::providers::MockProvider;
use omniroute_core::types::{ChatRequest, Message};
use std::time::Duration;

fn create_request(stream: bool) -> ChatRequest {
    ChatRequest {
        model: "mock-gpt-4".to_string(),
        messages: vec![
            Message::system("You are a helpful assistant."),
            Message::user("What is the capital of France?"),
        ],
        stream,
        temperature: Some(0.7),
        max_tokens: Some(100),
        ..Default::default()
    }
}

fn chat_completions_non_streaming(c: &mut Criterion) {
    let provider = MockProvider::new();
    let rt = tokio::runtime::Runtime::new().unwrap();

    let mut group = c.benchmark_group("chat_completions");
    group.measurement_time(Duration::from_secs(10));
    group.sample_size(100);

    group.throughput(Throughput::Elements(1));

    group.bench_function("non_streaming", |b| {
        let request = create_request(false);
        b.to_async(&rt).iter(|| async {
            let result = provider.chat_completions(black_box(request.clone())).await;
            black_box(result)
        });
    });

    group.finish();
}

fn chat_completions_with_large_context(c: &mut Criterion) {
    let provider = MockProvider::new();
    let rt = tokio::runtime::Runtime::new().unwrap();

    // Create a large context (simulating a long conversation)
    let mut messages = vec![Message::system("You are a helpful assistant.")];
    for i in 0..50 {
        messages.push(Message::user(format!("Message {} with some content", i)));
        messages.push(Message::assistant(format!("Response {} with detailed information", i)));
    }

    let request = ChatRequest {
        model: "mock-gpt-4".to_string(),
        messages,
        stream: false,
        ..Default::default()
    };

    let mut group = c.benchmark_group("chat_completions_large_context");
    group.measurement_time(Duration::from_secs(5));
    group.sample_size(50);

    group.bench_function("50_messages", |b| {
        b.to_async(&rt).iter(|| async {
            let result = provider.chat_completions(black_box(request.clone())).await;
            black_box(result)
        });
    });

    group.finish();
}

fn chat_completions_serialization(c: &mut Criterion) {
    let request = create_request(false);

    let mut group = c.benchmark_group("chat_completions_serialization");
    group.measurement_time(Duration::from_secs(5));

    group.bench_function("serialize_request", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&request)).unwrap();
            black_box(json)
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    chat_completions_non_streaming,
    chat_completions_with_large_context,
    chat_completions_serialization,
);
criterion_main!(benches);
