//! Integration tests for observability crate

use crate::headers::{
    EventId, FallbackStep, HeaderBuilder, RequestId, ResponseCost, TimeToFirstToken,
};
use crate::telemetry::{ResponseReceivedEvent, TelemetryEvent};

// Traces to: FR-OBSERVABILITY-INTEGRATION-HEADERS-001
#[test]
fn test_complete_header_flow() {
    let event_id = EventId::new();
    let request_id = RequestId::new();
    let cost = ResponseCost::from_usd(0.123).unwrap();
    let ttft = TimeToFirstToken::from_ms(456);
    let fallback = FallbackStep::new(1).unwrap();

    let headers = HeaderBuilder::new()
        .with_event_id(event_id.clone())
        .with_request_id(request_id.clone())
        .with_response_cost(cost)
        .with_ttft(ttft)
        .with_fallback_step(fallback)
        .build();

    assert_eq!(headers.event_id, event_id);
    assert_eq!(headers.request_id, request_id);
    assert_eq!(headers.response_cost, cost);
    assert_eq!(headers.ttft, ttft);
    assert_eq!(headers.fallback_step, fallback);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-HEADERS-002
#[test]
fn test_header_to_http_map() {
    let request_id = RequestId::new();
    let cost = ResponseCost::from_usd(0.05).unwrap();
    let ttft = TimeToFirstToken::from_ms(200);

    let map = HeaderBuilder::new()
        .with_request_id(request_id.clone())
        .with_response_cost(cost)
        .with_ttft(ttft)
        .build_map();

    assert!(map.contains_key("x-event-id"));
    assert!(map.contains_key("x-request-id"));
    assert!(map.contains_key("x-response-cost-microdollars"));
    assert!(map.contains_key("x-ttft-ms"));
    assert!(map.contains_key("x-fallback-step"));
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-TELEMETRY-001
#[test]
fn test_complete_request_lifecycle() {
    let request_id = RequestId::new();

    // Start request
    let start_event = TelemetryEvent::request_started(request_id.clone(), "gpt-4".to_string(), 150);

    // Receive response
    let cost = ResponseCost::from_usd(0.01).unwrap();
    let ttft = TimeToFirstToken::from_ms(100);
    let response_event = TelemetryEvent::response_received(request_id.clone(), 250, cost, ttft);

    // Verify both events share the same request ID
    assert_eq!(start_event.request_id(), response_event.request_id());
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-TELEMETRY-002
#[test]
fn test_failover_scenario() {
    let request_id = RequestId::new();

    // Request starts
    let _start = TelemetryEvent::request_started(request_id.clone(), "gpt-4".to_string(), 100);

    // First provider fails
    let fallback1 = TelemetryEvent::provider_fallback(
        request_id.clone(),
        "openai".to_string(),
        "anthropic".to_string(),
        "timeout".to_string(),
    );

    // Second provider also fails
    let fallback2 = TelemetryEvent::provider_fallback(
        request_id.clone(),
        "anthropic".to_string(),
        "together".to_string(),
        "rate_limited".to_string(),
    );

    // Third provider succeeds
    let cost = ResponseCost::from_usd(0.02).unwrap();
    let ttft = TimeToFirstToken::from_ms(150);
    let _response = TelemetryEvent::response_received(request_id.clone(), 200, cost, ttft);

    // Verify all events are correlated
    assert_eq!(fallback1.request_id(), &request_id);
    assert_eq!(fallback2.request_id(), &request_id);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-COST-001
#[test]
fn test_cost_accumulation_across_events() {
    let request_id1 = RequestId::new();
    let request_id2 = RequestId::new();

    let cost1 = ResponseCost::from_usd(0.001).unwrap();
    let cost2 = ResponseCost::from_usd(0.005).unwrap();

    let event1 = ResponseReceivedEvent::new(request_id1, 100, cost1, TimeToFirstToken::from_ms(50));
    let event2 =
        ResponseReceivedEvent::new(request_id2, 200, cost2, TimeToFirstToken::from_ms(100));

    let total = event1.cost.as_usd() + event2.cost.as_usd();
    assert!((total - 0.006).abs() < 0.000001);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-SERIALIZATION-001
#[test]
fn test_full_event_serialization() {
    let request_id = RequestId::new();
    let cost = ResponseCost::from_usd(0.02).unwrap();

    let events = vec![
        TelemetryEvent::request_started(request_id.clone(), "gpt-4".to_string(), 150),
        TelemetryEvent::response_received(
            request_id.clone(),
            250,
            cost,
            TimeToFirstToken::from_ms(120),
        ),
        TelemetryEvent::provider_fallback(
            request_id,
            "openai".to_string(),
            "anthropic".to_string(),
            "timeout".to_string(),
        ),
    ];

    // Serialize all events
    for event in &events {
        let json = serde_json::to_string(event).unwrap();
        assert!(!json.is_empty());

        // Verify deserialization
        let deserialized: TelemetryEvent = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.request_id(), event.request_id());
    }
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-HEADER-EXTRACTION-001
#[test]
fn test_header_extraction_from_map() {
    let request_id = RequestId::new();
    let cost = ResponseCost::from_usd(0.03).unwrap();
    let ttft = TimeToFirstToken::from_ms(180);

    let original = HeaderBuilder::new()
        .with_request_id(request_id.clone())
        .with_response_cost(cost)
        .with_ttft(ttft)
        .build();

    let map = original.to_map();
    let restored = crate::headers::ResponseHeaders::from_map(&map).unwrap();

    assert_eq!(original.request_id, restored.request_id);
    assert_eq!(original.response_cost, restored.response_cost);
    assert_eq!(original.ttft, restored.ttft);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-FALLBACK-TRACKING-001
#[test]
fn test_fallback_step_tracking() {
    let mut fallback_steps = vec![];

    // Simulate failover with step tracking
    for step in 0..3 {
        let fb_step = FallbackStep::new(step).unwrap();
        fallback_steps.push(fb_step);
    }

    // Verify progression
    assert!(fallback_steps[0].is_primary());
    assert!(!fallback_steps[1].is_primary());
    assert!(!fallback_steps[2].is_primary());

    assert_eq!(fallback_steps[0].as_u32(), 0);
    assert_eq!(fallback_steps[1].as_u32(), 1);
    assert_eq!(fallback_steps[2].as_u32(), 2);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-MULTI-REQUEST-001
#[test]
fn test_multiple_concurrent_requests() {
    let request_ids: Vec<RequestId> = (0..5).map(|_| RequestId::new()).collect();

    let mut events = vec![];

    for request_id in request_ids {
        events.push(TelemetryEvent::request_started(
            request_id.clone(),
            "gpt-4".to_string(),
            100,
        ));
    }

    // Verify all events have unique request IDs
    let unique_ids: std::collections::HashSet<_> =
        events.iter().map(|e| e.request_id().clone()).collect();
    assert_eq!(unique_ids.len(), 5);
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-ERROR-HANDLING-001
#[test]
fn test_invalid_header_value_handling() {
    use crate::headers::ResponseCost;

    // Test invalid cost
    let result = ResponseCost::from_usd(-1.0);
    assert!(result.is_err());

    // Test invalid header parsing
    let result = ResponseCost::from_header_value("not-a-number");
    assert!(result.is_err());
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-ZERO_COPY-001
#[test]
fn test_headers_zero_copy_potential() {
    let event_id = EventId::new();
    let request_id = RequestId::new();

    // Both should use string references without copying
    let event_id_str = event_id.as_str();
    let request_id_str = request_id.as_str();

    assert!(!event_id_str.is_empty());
    assert!(!request_id_str.is_empty());
}

// Traces to: FR-OBSERVABILITY-INTEGRATION-DISPLAY-001
#[test]
fn test_header_display_formatting() {
    let cost = ResponseCost::from_usd(0.05).unwrap();
    let ttft = TimeToFirstToken::from_ms(150);
    let fallback = FallbackStep::new(2).unwrap();

    let cost_str = format!("{}", cost);
    let ttft_str = format!("{}", ttft);
    let fallback_str = format!("{}", fallback);

    assert!(cost_str.contains("$0.05"));
    assert!(ttft_str.contains("150ms"));
    assert!(fallback_str.contains("step-2"));
}
