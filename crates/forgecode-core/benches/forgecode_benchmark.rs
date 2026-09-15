use criterion::{criterion_group, criterion_main, Criterion};

use forgecode_core::{
    Agent, AgentConfig, AgentExecutor, LLMRequest, LLMResponse, ProviderRegistry, TokenUsage,
};

use async_trait::async_trait;

struct BenchProvider;

#[async_trait]
impl forgecode_core::CustomProvider for BenchProvider {
    async fn call(&self, _req: &LLMRequest) -> forgecode_core::Result<LLMResponse> {
        Ok(LLMResponse {
            text: "bench response".into(),
            usage: TokenUsage {
                input_tokens: 10,
                output_tokens: 20,
            },
        })
    }
}

fn bench_agent_execute(c: &mut Criterion) {
    let executor = AgentExecutor::new();
    let cfg = AgentConfig::new("bench-agent", "BenchAgent", "1.0.0", "bench");
    executor.register(Agent::new(cfg)).unwrap();
    let registry = ProviderRegistry::new();

    c.bench_function("agent_execute", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(executor.execute("bench-agent", "input", &registry))
        });
    });
}

fn bench_provider_registry_register(c: &mut Criterion) {
    c.bench_function("provider_register", |b| {
        b.iter(|| {
            let registry = ProviderRegistry::new();
            for i in 0..100 {
                registry.register(format!("p-{i}"), BenchProvider).unwrap();
            }
        });
    });
}

fn bench_provider_registry_call(c: &mut Criterion) {
    let registry = ProviderRegistry::new();
    registry.register("bench".into(), BenchProvider).unwrap();
    let req = LLMRequest {
        model: "gpt-4o".into(),
        prompt: "benchmark prompt".into(),
        max_tokens: Some(100),
    };

    c.bench_function("provider_call", |b| {
        b.iter(|| {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(registry.call("bench", &req))
        });
    });
}

fn bench_llm_request_serialize(c: &mut Criterion) {
    let req = LLMRequest {
        model: "gpt-4o".into(),
        prompt: "benchmark prompt content".into(),
        max_tokens: Some(2048),
    };

    c.bench_function("llm_request_serialize", |b| {
        b.iter(|| serde_json::to_string(&req).unwrap());
    });

    let json = serde_json::to_string(&req).unwrap();
    c.bench_function("llm_request_deserialize", |b| {
        b.iter(|| {
            let _: LLMRequest = serde_json::from_str(&json).unwrap();
        });
    });
}

fn bench_agent_executor_lifecycle(c: &mut Criterion) {
    c.bench_function("executor_register_and_list", |b| {
        b.iter(|| {
            let executor = AgentExecutor::new();
            for i in 0..50 {
                let cfg = AgentConfig::new(format!("a-{i}"), format!("Agent {i}"), "1.0.0", "chat");
                executor.register(Agent::new(cfg)).unwrap();
            }
            let _ = executor.list_agents();
        });
    });
}

criterion_group!(
    benches,
    bench_agent_execute,
    bench_provider_registry_register,
    bench_provider_registry_call,
    bench_llm_request_serialize,
    bench_agent_executor_lifecycle,
);
criterion_main!(benches);
