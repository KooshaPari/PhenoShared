use async_trait::async_trait;
use std::sync::Arc;

use forgecode_core::{
    Agent, AgentConfig, AgentExecutor, ForgecodeError, LLMRequest, LLMResponse, ProviderRegistry,
    TokenUsage,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
struct MockProvider {
    text: String,
    input_tokens: u32,
    output_tokens: u32,
}

impl MockProvider {
    fn new(text: impl Into<String>, input: u32, output: u32) -> Self {
        Self {
            text: text.into(),
            input_tokens: input,
            output_tokens: output,
        }
    }
}

#[async_trait]
impl forgecode_core::CustomProvider for MockProvider {
    async fn call(&self, _request: &LLMRequest) -> forgecode_core::Result<LLMResponse> {
        Ok(LLMResponse {
            text: self.text.clone(),
            usage: TokenUsage {
                input_tokens: self.input_tokens,
                output_tokens: self.output_tokens,
            },
        })
    }
}

struct FailingProvider;

#[async_trait]
impl forgecode_core::CustomProvider for FailingProvider {
    async fn call(&self, _request: &LLMRequest) -> forgecode_core::Result<LLMResponse> {
        Err(ForgecodeError::ProviderError("boom".into()))
    }
}

// ======================= AgentExecutor lifecycle =======================

#[tokio::test]
async fn register_multiple_agents_and_list() {
    let executor = AgentExecutor::new();
    for i in 0..5 {
        let cfg = AgentConfig::new(format!("agent-{i}"), format!("Agent {i}"), "1.0.0", "chat");
        executor.register(Agent::new(cfg)).unwrap();
    }
    let agents = executor.list_agents();
    assert_eq!(agents.len(), 5);
}

#[tokio::test]
async fn get_registered_agent() {
    let executor = AgentExecutor::new();
    let cfg = AgentConfig::new("a1", "Alpha", "0.1.0", "code");
    executor.register(Agent::new(cfg)).unwrap();
    let agent = executor.get("a1").unwrap();
    assert_eq!(agent.config().name, "Alpha");
}

#[tokio::test]
async fn get_unregistered_agent_returns_none() {
    let executor = AgentExecutor::new();
    assert!(executor.get("nope").is_none());
}

#[tokio::test]
async fn execute_agent_through_executor() {
    let executor = AgentExecutor::new();
    let registry = ProviderRegistry::new();
    let cfg = AgentConfig::new("e1", "Exec Agent", "2.0.0", "test");
    executor.register(Agent::new(cfg)).unwrap();
    let result = executor.execute("e1", "input", &registry).await.unwrap();
    assert!(result.contains("Exec Agent"));
    assert!(result.contains("2.0.0"));
}

#[tokio::test]
async fn execute_missing_agent_returns_error() {
    let executor = AgentExecutor::new();
    let registry = ProviderRegistry::new();
    let result = executor.execute("ghost", "hi", &registry).await;
    assert!(result.is_err());
    match result.unwrap_err() {
        ForgecodeError::AgentNotFound(id) => assert_eq!(id, "ghost"),
        other => panic!("expected AgentNotFound, got {other:?}"),
    }
}

// ======================= ProviderRegistry =======================

#[tokio::test]
async fn register_and_call_provider() {
    let registry = ProviderRegistry::new();
    registry
        .register("mock".into(), MockProvider::new("hello", 10, 20))
        .unwrap();

    let req = LLMRequest {
        model: "gpt-4o".into(),
        prompt: "test".into(),
        max_tokens: Some(100),
    };
    let resp = registry.call("mock", &req).await.unwrap();
    assert_eq!(resp.text, "hello");
    assert_eq!(resp.usage.input_tokens, 10);
    assert_eq!(resp.usage.output_tokens, 20);
}

#[tokio::test]
async fn multiple_providers_routing() {
    let registry = ProviderRegistry::new();
    registry
        .register("alpha".into(), MockProvider::new("from alpha", 5, 5))
        .unwrap();
    registry
        .register("beta".into(), MockProvider::new("from beta", 10, 10))
        .unwrap();

    let req = LLMRequest {
        model: "any".into(),
        prompt: "hi".into(),
        max_tokens: None,
    };
    let r1 = registry.call("alpha", &req).await.unwrap();
    let r2 = registry.call("beta", &req).await.unwrap();
    assert_eq!(r1.text, "from alpha");
    assert_eq!(r2.text, "from beta");

    let ids = registry.list_ids();
    assert_eq!(ids.len(), 2);
}

#[tokio::test]
async fn call_nonexistent_provider() {
    let registry = ProviderRegistry::new();
    let req = LLMRequest {
        model: "m".into(),
        prompt: "p".into(),
        max_tokens: None,
    };
    let result = registry.call("missing", &req).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn provider_error_propagates() {
    let registry = ProviderRegistry::new();
    registry.register("fail".into(), FailingProvider).unwrap();
    let req = LLMRequest {
        model: "m".into(),
        prompt: "p".into(),
        max_tokens: None,
    };
    let result = registry.call("fail", &req).await;
    assert!(matches!(
        result.unwrap_err(),
        ForgecodeError::ProviderError(_)
    ));
}

// ======================= Serialization roundtrip =======================

#[test]
fn llm_request_serialization_roundtrip() {
    let req = LLMRequest {
        model: "claude-3-5-sonnet".into(),
        prompt: "hello world".into(),
        max_tokens: Some(2048),
    };
    let json = serde_json::to_string(&req).unwrap();
    let back: LLMRequest = serde_json::from_str(&json).unwrap();
    assert_eq!(back, req);
}

#[test]
fn llm_response_serialization_roundtrip() {
    let resp = LLMResponse {
        text: "response text".into(),
        usage: TokenUsage {
            input_tokens: 42,
            output_tokens: 100,
        },
    };
    let json = serde_json::to_string(&resp).unwrap();
    let back: LLMResponse = serde_json::from_str(&json).unwrap();
    assert_eq!(back, resp);
}

#[test]
fn llm_request_no_max_tokens() {
    let req = LLMRequest {
        model: "m".into(),
        prompt: "p".into(),
        max_tokens: None,
    };
    let json = serde_json::to_string(&req).unwrap();
    let back: LLMRequest = serde_json::from_str(&json).unwrap();
    assert!(back.max_tokens.is_none());
}

// ======================= ForgecodeError display =======================

#[test]
fn error_display_provider_not_found() {
    let e = ForgecodeError::ProviderNotFound("xyz".into());
    assert_eq!(format!("{e}"), "provider not found: xyz");
}

#[test]
fn error_display_agent_not_found() {
    let e = ForgecodeError::AgentNotFound("abc".into());
    assert_eq!(format!("{e}"), "agent not found: abc");
}

#[test]
fn error_display_invalid_config() {
    let e = ForgecodeError::InvalidConfig("bad field".into());
    assert_eq!(format!("{e}"), "invalid config: bad field");
}

#[test]
fn error_display_provider_error() {
    let e = ForgecodeError::ProviderError("timeout".into());
    assert_eq!(format!("{e}"), "provider error: timeout");
}

// ======================= Error propagation =======================

#[tokio::test]
async fn error_propagation_through_executor() {
    let executor = AgentExecutor::new();
    let registry = ProviderRegistry::new();
    let result = executor.execute("nonexistent", "input", &registry).await;
    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(format!("{err}").contains("agent not found"));
}

// ======================= AgentConfig builder =======================

#[test]
fn agent_config_builder_pattern() {
    let cfg = AgentConfig::new("id1", "Name", "0.1.0", "chat")
        .with_metadata("env", serde_json::json!("production"))
        .with_metadata("region", serde_json::json!("us-east-1"));

    assert_eq!(cfg.id, "id1");
    assert_eq!(cfg.metadata.len(), 2);
    assert_eq!(cfg.metadata["env"], "production");
    assert_eq!(cfg.metadata["region"], "us-east-1");
}

#[test]
fn agent_config_serialization_roundtrip() {
    let cfg = AgentConfig::new("c1", "Cfg Agent", "1.0.0", "code")
        .with_metadata("k", serde_json::json!("v"));
    let json = serde_json::to_string(&cfg).unwrap();
    let back: AgentConfig = serde_json::from_str(&json).unwrap();
    assert_eq!(back, cfg);
}

// ======================= Concurrent registration =======================

#[tokio::test]
async fn concurrent_agent_registration() {
    let executor = Arc::new(AgentExecutor::new());
    let mut handles = vec![];

    for i in 0..20 {
        let exec = Arc::clone(&executor);
        handles.push(tokio::spawn(async move {
            let cfg = AgentConfig::new(
                format!("concurrent-{i}"),
                format!("Agent {i}"),
                "1.0.0",
                "chat",
            );
            exec.register(Agent::new(cfg)).unwrap();
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let agents = executor.list_agents();
    assert_eq!(agents.len(), 20);
}

#[tokio::test]
async fn concurrent_provider_registration() {
    let registry = Arc::new(ProviderRegistry::new());
    let mut handles = vec![];

    for i in 0..20 {
        let reg = Arc::clone(&registry);
        handles.push(tokio::spawn(async move {
            reg.register(
                format!("provider-{i}"),
                MockProvider::new(format!("resp {i}"), i as u32, i as u32),
            )
            .unwrap();
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let ids = registry.list_ids();
    assert_eq!(ids.len(), 20);
}

// ======================= Agent execute =======================

#[tokio::test]
async fn agent_execute_with_mock_provider() {
    let registry = ProviderRegistry::new();
    registry
        .register("prov".into(), MockProvider::new("mock response", 50, 30))
        .unwrap();

    let cfg = AgentConfig::new("agent-x", "X Agent", "3.0.0", "chat");
    let agent = Agent::new(cfg);
    let result = agent.execute("some input", &registry).await.unwrap();
    assert!(result.contains("X Agent"));
    assert!(result.contains("3.0.0"));
}
