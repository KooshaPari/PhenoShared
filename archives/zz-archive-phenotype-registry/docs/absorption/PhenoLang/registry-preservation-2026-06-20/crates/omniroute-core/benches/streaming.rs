//! Streaming benchmark suite
//!
//! Measures the performance of streaming responses.

use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use futures::StreamExt;
use omniroute_core::providers::MockProvider;
use omniroute_core::types::ChatRequest;
use std::time::Duration;

fn create_streaming_request() -> ChatRequest {
    ChatRequest {
        model: "mock-gpt-4".to_string(),
        messages: vec![Message::user("Count to 100")],
        stream: true,
        max_tokens: Some(100),
        ..Default::default()
    }
}

fn streaming_full_request(c: &mut Criterion) {
    let provider = MockProvider::new();
    let rt = tokio::runtime::Runtime::new().unwrap();

    let mut group = c.benchmark_group("streaming");
    group.measurement_time(Duration::from_secs(10));
    group.sample_size(20);

    group.throughput(Throughput::Elements(1));

    group.bench_function("full_stream", |b| {
        let request = create_streaming_request();
        b.to_async(&rt).iter(|| async {
            let stream = provider.chat_completions_stream(black_box(request.clone())).await.unwrap();
            let chunks: Vec<_> = stream.collect().await;
            black_box(chunks)
        });
    });

    group.finish();
}

fn streaming_chunk_processing(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let mock = MockProvider::new();
    let request = create_streaming_request();

    let mut group = c.benchmark_group("streaming_chunk_processing");
    group.measurement_time(Duration::from_secs(5));

    group.bench_function("collect_chunks", |b| {
        b.to_async(&rt).iter(|| async {
            let stream = mock.chat_completions_stream(request.clone()).await.unwrap();
            let count = stream.count().await;
            black_box(count)
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    streaming_full_request,
    streaming_chunk_processing,
);
criterion_main!(benches);
