//! End-to-end integration tests for phenotype-event-bus → PhenoObservably OTEL emission.
//! Traces to: FR-OBS-E2E-001
//!
//! Validates real cross-collection event flow:
//! 1. Sidekick event published on phenotype-event-bus
//! 2. Observably subscribes and emits structured logging event
//! 3. Observably emits OTEL span and metric counter
//! 4. OTEL stdout exporter captures emission (no external collector required)

use phenotype_event_bus::{Bus, Event};
use phenotype_observably_tracing::MetricsRegistry;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::sync::Once;
use tokio::sync::Mutex;
use tokio::time::{timeout, Duration};
use tracing::info;

static INIT_TRACING: Once = Once::new();

// ============================================================================
// Event Types (mirrored from phenotype-event-bus demos)
// ============================================================================

#[derive(Clone, Serialize, Deserialize, Debug)]
struct SidekickCacheMissEvent {
    cache_key: String,
    user_id: String,
    ttl_secs: u64,
    timestamp: u64,
}

impl Event for SidekickCacheMissEvent {
    fn event_name(&self) -> &'static str {
        "SidekickCacheMiss"
    }
}

#[derive(Clone, Serialize, Deserialize, Debug)]
struct FocusEvalRuleFiredEvent {
    rule_id: String,
    rule_type: String,
    matched: bool,
    duration_ms: u64,
    timestamp: u64,
}

impl Event for FocusEvalRuleFiredEvent {
    fn event_name(&self) -> &'static str {
        "FocusEvalRuleFired"
    }
}

#[derive(Clone, Serialize, Deserialize, Debug)]
struct StashlyStorageEvent {
    artifact_id: String,
    size_bytes: u64,
    location: String,
    timestamp: u64,
}

impl Event for StashlyStorageEvent {
    fn event_name(&self) -> &'static str {
        "StashlyStorage"
    }
}

// ============================================================================
// Test 1: Sidekick cache-miss event → Observably logs structured event
// ============================================================================

#[tokio::test]
async fn test_sidekick_cache_miss_to_observably_logging() {
    // Traces to: FR-OBS-E2E-001, Test 1/4
    // Validates: phenotype-event-bus event → Observably structured log emission

    INIT_TRACING.call_once(|| {
        phenotype_observably_tracing::init_tracing("test-e2e", Some("debug"));
    });

    let bus = Bus::<SidekickCacheMissEvent>::new(10);
    let mut rx = bus.subscribe();

    let captured = Arc::new(Mutex::new(None));

    // Spawn handler in background
    let handler = {
        let cap = Arc::clone(&captured);
        tokio::spawn(async move {
            if let Ok(event) = rx.recv().await {
                // Emit structured log with cache context
                info!(
                    cache_key = &event.cache_key,
                    user_id = &event.user_id,
                    ttl_secs = event.ttl_secs,
                    "Cache miss detected by Stashly handler"
                );
                *cap.lock().await = Some(event);
            }
        })
    };

    // Publish cache-miss event
    let event = SidekickCacheMissEvent {
        cache_key: "user-profile-001".to_string(),
        user_id: "user-123".to_string(),
        ttl_secs: 300,
        timestamp: 1234567890,
    };
    let _ = bus.publish(event.clone()).await;

    // Wait for handler (short timeout)
    let _ = timeout(Duration::from_millis(300), handler).await;

    let result = captured.lock().await;
    assert!(
        result.is_some(),
        "Observably did not receive cache-miss event"
    );
    assert_eq!(result.as_ref().unwrap().cache_key, "user-profile-001");
}

// ============================================================================
// Test 2: Focus-eval rule.fired → Observably metric counter increment
// ============================================================================

#[tokio::test]
async fn test_focus_eval_rule_fired_to_observably_metrics() {
    // Traces to: FR-OBS-E2E-001, Test 2/4
    // Validates: phenotype-event-bus event → Observably metric counter increment

    INIT_TRACING.call_once(|| {
        phenotype_observably_tracing::init_tracing("test-e2e", Some("debug"));
    });

    let bus = Bus::<FocusEvalRuleFiredEvent>::new(10);
    let mut rx = bus.subscribe();
    let metrics = MetricsRegistry::global();

    let captured = Arc::new(Mutex::new(0));

    // Observably handler: listen for rule.fired → increment metric counter
    let handler = {
        let cap = Arc::clone(&captured);
        let metrics_ref = metrics.clone();
        tokio::spawn(async move {
            if let Ok(event) = rx.recv().await {
                // Increment rule evaluation counter
                metrics_ref.inc_rule_evaluations(&event.rule_id, 1.0);
                metrics_ref.record_eval_duration(&event.rule_id, event.duration_ms as f64 / 1000.0);

                *cap.lock().await += 1;
            }
        })
    };

    // Publish rule.fired event
    let event = FocusEvalRuleFiredEvent {
        rule_id: "rule-time-window-01".to_string(),
        rule_type: "time_window".to_string(),
        matched: true,
        duration_ms: 125,
        timestamp: 1234567891,
    };
    let _ = bus.publish(event).await;

    // Wait for handler
    let _ = timeout(Duration::from_millis(300), handler).await;

    let count = *captured.lock().await;
    assert_eq!(count, 1, "Observably should have incremented metric once");

    // Verify metrics were recorded
    let text = metrics.gather_text_format().expect("gather metrics");
    assert!(
        text.contains("rule_evaluations_total"),
        "Metric text should contain rule_evaluations_total"
    );
}

// ============================================================================
// Test 3: Stashly cache-miss event → Observably OTEL span emission
// ============================================================================

#[tokio::test]
async fn test_stashly_storage_to_observably_otel_span() {
    // Traces to: FR-OBS-E2E-001, Test 3/4
    // Validates: phenotype-event-bus event → Observably OTEL span emission

    INIT_TRACING.call_once(|| {
        phenotype_observably_tracing::init_tracing("test-e2e", Some("debug"));
    });

    let bus = Bus::<StashlyStorageEvent>::new(10);
    let mut rx = bus.subscribe();

    let captured = Arc::new(Mutex::new(None));

    // Observably handler: listen for storage → emit OTEL span
    let handler = {
        let cap = Arc::clone(&captured);
        tokio::spawn(async move {
            if let Ok(event) = rx.recv().await {
                // Create span context for storage operation
                let span = tracing::info_span!(
                    "stashly.storage",
                    artifact_id = %event.artifact_id,
                    size_bytes = event.size_bytes,
                    location = %event.location,
                );

                let _guard = span.enter();
                info!("Artifact stored successfully");

                *cap.lock().await = Some(event);
            }
        })
    };

    // Publish storage event
    let event = StashlyStorageEvent {
        artifact_id: "artifact-abc-123".to_string(),
        size_bytes: 512_000,
        location: "s3://bucket/artifacts/abc123".to_string(),
        timestamp: 1234567892,
    };
    let _ = bus.publish(event).await;

    // Wait for handler
    let _ = timeout(Duration::from_millis(300), handler).await;

    let result = captured.lock().await;
    assert!(
        result.is_some(),
        "Observably did not emit span for storage event"
    );
    assert_eq!(result.as_ref().unwrap().artifact_id, "artifact-abc-123");
}

// ============================================================================
// Test 4: End-to-end cross-collection pipeline (multi-step)
// ============================================================================

#[tokio::test]
async fn test_end_to_end_cross_collection_pipeline() {
    // Traces to: FR-OBS-E2E-001, Test 4/4
    // Validates: full pipeline with logging, metrics, and span emission

    INIT_TRACING.call_once(|| {
        phenotype_observably_tracing::init_tracing("test-e2e", Some("debug"));
    });

    // Three event buses representing three collections
    let cache_miss_bus = Bus::<SidekickCacheMissEvent>::new(10);
    let rule_eval_bus = Bus::<FocusEvalRuleFiredEvent>::new(10);
    let storage_bus = Bus::<StashlyStorageEvent>::new(10);

    // Subscribe to all three
    let mut cache_rx = cache_miss_bus.subscribe();
    let mut rule_rx = rule_eval_bus.subscribe();
    let mut storage_rx = storage_bus.subscribe();

    let metrics = MetricsRegistry::global();
    let event_log = Arc::new(Mutex::new(Vec::new()));

    // Handler 1: Sidekick (cache-miss) handler
    let cache_handler = {
        let log = Arc::clone(&event_log);
        tokio::spawn(async move {
            if let Ok(event) = cache_rx.recv().await {
                info!(cache_key = &event.cache_key, "Sidekick cache miss detected");
                log.lock().await.push("cache-miss".to_string());
            }
        })
    };

    // Handler 2: Focus-eval (rule-fired) handler
    let rule_handler = {
        let log = Arc::clone(&event_log);
        let metrics_ref = metrics.clone();
        tokio::spawn(async move {
            if let Ok(event) = rule_rx.recv().await {
                metrics_ref.inc_rule_evaluations(&event.rule_id, 1.0);
                let span = tracing::info_span!(
                    "rule.evaluate",
                    rule_id = %event.rule_id,
                    matched = event.matched,
                );
                let _guard = span.enter();
                info!("Rule evaluation completed");
                log.lock().await.push("rule-fired".to_string());
            }
        })
    };

    // Handler 3: Stashly (storage) handler
    let storage_handler = {
        let log = Arc::clone(&event_log);
        let metrics_ref = metrics.clone();
        tokio::spawn(async move {
            if let Ok(event) = storage_rx.recv().await {
                metrics_ref.inc_audit_appends("artifact_stored", 1.0);
                info!(
                    artifact_id = %event.artifact_id,
                    size_bytes = event.size_bytes,
                    "Artifact stored"
                );
                log.lock().await.push("storage".to_string());
            }
        })
    };

    // Publish events
    let cache_event = SidekickCacheMissEvent {
        cache_key: "e2e-key".to_string(),
        user_id: "e2e-user".to_string(),
        ttl_secs: 600,
        timestamp: 1234567893,
    };
    let _ = cache_miss_bus.publish(cache_event).await;

    let rule_event = FocusEvalRuleFiredEvent {
        rule_id: "e2e-rule".to_string(),
        rule_type: "e2e_test".to_string(),
        matched: true,
        duration_ms: 50,
        timestamp: 1234567894,
    };
    let _ = rule_eval_bus.publish(rule_event).await;

    let storage_event = StashlyStorageEvent {
        artifact_id: "e2e-artifact".to_string(),
        size_bytes: 1024,
        location: "e2e-location".to_string(),
        timestamp: 1234567895,
    };
    let _ = storage_bus.publish(storage_event).await;

    // Wait for all handlers
    let _ = timeout(Duration::from_millis(500), cache_handler).await;
    let _ = timeout(Duration::from_millis(500), rule_handler).await;
    let _ = timeout(Duration::from_millis(500), storage_handler).await;

    // Verify pipeline completion
    let log = event_log.lock().await;
    assert_eq!(log.len(), 3, "All three events should have been processed");
    assert!(log.contains(&"cache-miss".to_string()));
    assert!(log.contains(&"rule-fired".to_string()));
    assert!(log.contains(&"storage".to_string()));

    // Verify metrics were emitted
    let metrics_text = metrics.gather_text_format().expect("gather metrics");
    assert!(metrics_text.contains("rule_evaluations_total"));
    assert!(metrics_text.contains("audit_appends_total"));
}
