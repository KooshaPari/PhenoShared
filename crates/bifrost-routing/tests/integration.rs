use std::sync::Arc;

use bifrost_routing::{
    BifrostError, CostAwareRouter, FailoverRouter, LatencyAwareRouter, Router, RoutingRequest,
    SemanticCacheRouter, TaskSpecificRouter,
};

// ---------------------------------------------------------------------------
// Helper: a router that always fails (for failover fallback testing)
// ---------------------------------------------------------------------------
struct AlwaysFailRouter;

#[async_trait::async_trait]
impl Router for AlwaysFailRouter {
    fn name(&self) -> &str {
        "always_fail"
    }

    async fn decide(
        &self,
        _req: &RoutingRequest,
    ) -> bifrost_routing::Result<bifrost_routing::RouterDecision> {
        Err(BifrostError::RoutingFailed("intentional".into()))
    }
}

// ======================= CostAwareRouter =======================

#[tokio::test]
async fn cost_aware_selects_cheapest() {
    let router = CostAwareRouter::new();
    let req = RoutingRequest::new("gpt-4o", "Hello");
    let d = router.decide(&req).await.unwrap();
    assert!(
        d.estimated_cost_usd < 0.006,
        "expected low cost, got {}",
        d.estimated_cost_usd
    );
}

#[tokio::test]
async fn cost_aware_name() {
    let router = CostAwareRouter::new();
    assert_eq!(router.name(), "cost_aware");
}

// ======================= LatencyAwareRouter =======================

#[tokio::test]
async fn latency_aware_selects_fastest() {
    let router = LatencyAwareRouter::new();
    let req = RoutingRequest::new("gpt-4o", "Hello");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "gemini-2.0-flash");
    assert!(
        d.estimated_latency_ms < 500,
        "expected low latency, got {}",
        d.estimated_latency_ms
    );
}

#[tokio::test]
async fn latency_aware_name() {
    let router = LatencyAwareRouter::new();
    assert_eq!(router.name(), "latency_aware");
}

// ======================= TaskSpecificRouter =======================

#[tokio::test]
async fn task_specific_code() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "write code").with_task("code");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "gpt-4o");
}

#[tokio::test]
async fn task_specific_analysis() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "analyse data").with_task("analysis");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "claude-3-5-sonnet");
}

#[tokio::test]
async fn task_specific_quick() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "ping").with_task("quick");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "gemini-2.0-flash");
}

#[tokio::test]
async fn task_specific_creative() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "write poem").with_task("creative");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "claude-3-5-sonnet");
}

#[tokio::test]
async fn task_specific_no_type_defaults() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "hello");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "gpt-4o-mini");
}

#[tokio::test]
async fn task_specific_unknown_type_defaults() {
    let router = TaskSpecificRouter::new();
    let req = RoutingRequest::new("any", "test").with_task("unknown_task");
    let d = router.decide(&req).await.unwrap();
    assert_eq!(d.provider, "gpt-4o-mini");
}

#[tokio::test]
async fn task_specific_name() {
    let router = TaskSpecificRouter::new();
    assert_eq!(router.name(), "task_specific");
}

// ======================= SemanticCacheRouter =======================

#[tokio::test]
async fn semantic_cache_miss_then_hit() {
    let router = Arc::new(SemanticCacheRouter::new());
    let req = RoutingRequest::new("gpt-4o", "What is Rust?");
    let d1 = router.decide(&req).await.unwrap();
    assert_eq!(d1.reasoning, "Cache miss");
    assert_eq!(d1.estimated_latency_ms, 800);

    let d2 = router.decide(&req).await.unwrap();
    assert_eq!(d2.reasoning, "Cache hit");
    assert_eq!(d2.estimated_latency_ms, 5);
}

#[tokio::test]
async fn semantic_cache_different_prompts_miss() {
    let router = SemanticCacheRouter::new();
    let d1 = router
        .decide(&RoutingRequest::new("m", "prompt A"))
        .await
        .unwrap();
    let d2 = router
        .decide(&RoutingRequest::new("m", "prompt B"))
        .await
        .unwrap();
    assert_eq!(d1.reasoning, "Cache miss");
    assert_eq!(d2.reasoning, "Cache miss");
}

#[tokio::test]
async fn semantic_cache_name() {
    let router = SemanticCacheRouter::new();
    assert_eq!(router.name(), "semantic_cache");
}

// ======================= FailoverRouter =======================

#[tokio::test]
async fn failover_uses_primary_on_success() {
    let primary = Arc::new(CostAwareRouter::new());
    let fallback = Arc::new(LatencyAwareRouter::new());
    let router = FailoverRouter::new(primary, fallback);
    let d = router
        .decide(&RoutingRequest::new("gpt-4o", "hi"))
        .await
        .unwrap();
    assert_eq!(d.provider, "gpt-4o-mini");
}

#[tokio::test]
async fn failover_falls_back_on_error() {
    let primary = Arc::new(AlwaysFailRouter);
    let fallback = Arc::new(LatencyAwareRouter::new());
    let router = FailoverRouter::new(primary, fallback);
    let d = router
        .decide(&RoutingRequest::new("gpt-4o", "hi"))
        .await
        .unwrap();
    assert_eq!(d.provider, "gemini-2.0-flash");
}

#[tokio::test]
async fn failover_both_fail_returns_error() {
    let primary = Arc::new(AlwaysFailRouter);
    let fallback = Arc::new(AlwaysFailRouter);
    let router = FailoverRouter::new(primary, fallback);
    let result = router.decide(&RoutingRequest::new("gpt-4o", "hi")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn failover_name() {
    let primary = Arc::new(CostAwareRouter::new());
    let fallback = Arc::new(LatencyAwareRouter::new());
    let router = FailoverRouter::new(primary, fallback);
    assert_eq!(router.name(), "failover");
}

// ======================= Box<dyn Router> =======================

#[tokio::test]
async fn trait_object_dispatch() {
    let routers: Vec<Box<dyn Router>> = vec![
        Box::new(CostAwareRouter::new()),
        Box::new(LatencyAwareRouter::new()),
        Box::new(TaskSpecificRouter::new()),
        Box::new(SemanticCacheRouter::new()),
    ];
    let req = RoutingRequest::new("gpt-4o", "test prompt");
    for r in &routers {
        let d = r.decide(&req).await.unwrap();
        assert!(
            !d.provider.is_empty(),
            "router {} returned empty provider",
            r.name()
        );
    }
}

// ======================= Error formatting =======================

#[test]
fn bifrost_error_display_router_not_found() {
    let e = BifrostError::RouterNotFound("xyz".into());
    assert_eq!(format!("{e}"), "router not found: xyz");
}

#[test]
fn bifrost_error_display_no_providers() {
    let e = BifrostError::NoProvidersAvailable;
    assert_eq!(format!("{e}"), "no providers available");
}

#[test]
fn bifrost_error_display_routing_failed() {
    let e = BifrostError::RoutingFailed("timeout".into());
    assert_eq!(format!("{e}"), "routing failed: timeout");
}

// ======================= Serialization roundtrip =======================

#[test]
fn routing_request_serialization_roundtrip() {
    let req = RoutingRequest::new("gpt-4o", "hello").with_task("code");
    let json = serde_json::to_string(&req).unwrap();
    let back: RoutingRequest = serde_json::from_str(&json).unwrap();
    assert_eq!(back.model, "gpt-4o");
    assert_eq!(back.prompt, "hello");
    assert_eq!(back.task_type, Some("code".to_string()));
}

#[test]
fn router_decision_serialization_roundtrip() {
    let d = bifrost_routing::RouterDecision::new("claude-3-5-sonnet")
        .with_reasoning("best for code")
        .with_cost(0.003)
        .with_latency(500)
        .with_confidence(0.95);
    let json = serde_json::to_string(&d).unwrap();
    let back: bifrost_routing::RouterDecision = serde_json::from_str(&json).unwrap();
    assert_eq!(back.provider, "claude-3-5-sonnet");
    assert_eq!(back.estimated_cost_usd, 0.003);
    assert_eq!(back.estimated_latency_ms, 500);
    assert!((back.confidence - 0.95).abs() < f64::EPSILON);
}

// ======================= Edge cases =======================

#[tokio::test]
async fn empty_prompt() {
    let router = CostAwareRouter::new();
    let req = RoutingRequest::new("gpt-4o", "");
    let d = router.decide(&req).await.unwrap();
    assert!(!d.provider.is_empty());
}

#[tokio::test]
async fn unknown_model_cost_aware() {
    let router = CostAwareRouter::new();
    let req = RoutingRequest::new("nonexistent-model", "test");
    let d = router.decide(&req).await.unwrap();
    // Unknown model gets default cost 0.001 (not < 0.001), so gpt-4o-mini
    assert_eq!(d.provider, "gpt-4o-mini");
}
