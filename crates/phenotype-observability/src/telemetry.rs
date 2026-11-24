//! Telemetry event types for observability
//!
//! This module defines the canonical event types emitted throughout the request lifecycle.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::headers::{RequestId, ResponseCost, TimeToFirstToken};

/// A telemetry event in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event_type", content = "data")]
pub enum TelemetryEvent {
    /// Request has started
    RequestStarted(RequestStartedEvent),
    /// Response has been received
    ResponseReceived(ResponseReceivedEvent),
    /// Fallback to another provider occurred
    ProviderFallback(ProviderFallbackEvent),
}

impl TelemetryEvent {
    /// Create a request started event
    pub fn request_started(request_id: RequestId, model: String, prompt_tokens: usize) -> Self {
        TelemetryEvent::RequestStarted(RequestStartedEvent {
            request_id,
            model,
            prompt_tokens,
            timestamp: Utc::now(),
        })
    }

    /// Create a response received event
    pub fn response_received(
        request_id: RequestId,
        completion_tokens: usize,
        cost: ResponseCost,
        ttft_ms: TimeToFirstToken,
    ) -> Self {
        TelemetryEvent::ResponseReceived(ResponseReceivedEvent {
            request_id,
            completion_tokens,
            cost,
            ttft_ms,
            timestamp: Utc::now(),
        })
    }

    /// Create a provider fallback event
    pub fn provider_fallback(
        request_id: RequestId,
        from_provider: String,
        to_provider: String,
        reason: String,
    ) -> Self {
        TelemetryEvent::ProviderFallback(ProviderFallbackEvent {
            request_id,
            from_provider,
            to_provider,
            reason,
            timestamp: Utc::now(),
        })
    }

    /// Get the timestamp of this event
    pub fn timestamp(&self) -> DateTime<Utc> {
        match self {
            TelemetryEvent::RequestStarted(e) => e.timestamp,
            TelemetryEvent::ResponseReceived(e) => e.timestamp,
            TelemetryEvent::ProviderFallback(e) => e.timestamp,
        }
    }

    /// Get the request ID associated with this event
    pub fn request_id(&self) -> &RequestId {
        match self {
            TelemetryEvent::RequestStarted(e) => &e.request_id,
            TelemetryEvent::ResponseReceived(e) => &e.request_id,
            TelemetryEvent::ProviderFallback(e) => &e.request_id,
        }
    }
}

/// Event emitted when a request is started
///
/// Traces the initialization of a request with model and token count.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestStartedEvent {
    /// Correlation ID for the request
    pub request_id: RequestId,
    /// Model name being used
    pub model: String,
    /// Estimated prompt tokens
    pub prompt_tokens: usize,
    /// Timestamp when the event was created
    pub timestamp: DateTime<Utc>,
}

impl RequestStartedEvent {
    /// Create a new request started event
    pub fn new(request_id: RequestId, model: String, prompt_tokens: usize) -> Self {
        Self {
            request_id,
            model,
            prompt_tokens,
            timestamp: Utc::now(),
        }
    }

    /// Create with a custom timestamp (primarily for testing)
    #[cfg(test)]
    pub fn with_timestamp(
        request_id: RequestId,
        model: String,
        prompt_tokens: usize,
        timestamp: DateTime<Utc>,
    ) -> Self {
        Self {
            request_id,
            model,
            prompt_tokens,
            timestamp,
        }
    }
}

/// Event emitted when a response is received
///
/// Captures the outcome of a request including cost and latency metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseReceivedEvent {
    /// Correlation ID matching the request
    pub request_id: RequestId,
    /// Completion tokens in the response
    pub completion_tokens: usize,
    /// Cost of the request/response
    pub cost: ResponseCost,
    /// Time-to-first-token latency
    pub ttft_ms: TimeToFirstToken,
    /// Timestamp when the event was created
    pub timestamp: DateTime<Utc>,
}

impl ResponseReceivedEvent {
    /// Create a new response received event
    pub fn new(
        request_id: RequestId,
        completion_tokens: usize,
        cost: ResponseCost,
        ttft_ms: TimeToFirstToken,
    ) -> Self {
        Self {
            request_id,
            completion_tokens,
            cost,
            ttft_ms,
            timestamp: Utc::now(),
        }
    }

    /// Create with a custom timestamp (primarily for testing)
    #[cfg(test)]
    pub fn with_timestamp(
        request_id: RequestId,
        completion_tokens: usize,
        cost: ResponseCost,
        ttft_ms: TimeToFirstToken,
        timestamp: DateTime<Utc>,
    ) -> Self {
        Self {
            request_id,
            completion_tokens,
            cost,
            ttft_ms,
            timestamp,
        }
    }
}

/// Event emitted when a provider is substituted in a failover
///
/// Tracks failover decisions and their reasons.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderFallbackEvent {
    /// Correlation ID of the request triggering the fallback
    pub request_id: RequestId,
    /// Provider that was tried and failed
    pub from_provider: String,
    /// Provider selected as replacement
    pub to_provider: String,
    /// Reason for the fallback (e.g., "timeout", "rate_limited", "unavailable")
    pub reason: String,
    /// Timestamp when the event was created
    pub timestamp: DateTime<Utc>,
}

impl ProviderFallbackEvent {
    /// Create a new provider fallback event
    pub fn new(
        request_id: RequestId,
        from_provider: String,
        to_provider: String,
        reason: String,
    ) -> Self {
        Self {
            request_id,
            from_provider,
            to_provider,
            reason,
            timestamp: Utc::now(),
        }
    }

    /// Create with a custom timestamp (primarily for testing)
    #[cfg(test)]
    pub fn with_timestamp(
        request_id: RequestId,
        from_provider: String,
        to_provider: String,
        reason: String,
        timestamp: DateTime<Utc>,
    ) -> Self {
        Self {
            request_id,
            from_provider,
            to_provider,
            reason,
            timestamp,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBSERVABILITY-TELEMETRY-REQUEST-STARTED-001
    #[test]
    fn test_request_started_event_creation() {
        let request_id = RequestId::new();
        let event = RequestStartedEvent::new(request_id.clone(), "gpt-4".to_string(), 150);

        assert_eq!(event.request_id, request_id);
        assert_eq!(event.model, "gpt-4");
        assert_eq!(event.prompt_tokens, 150);
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-REQUEST-STARTED-002
    #[test]
    fn test_request_started_telemetry_event() {
        let request_id = RequestId::new();
        let event =
            TelemetryEvent::request_started(request_id.clone(), "claude-opus".to_string(), 200);

        if let TelemetryEvent::RequestStarted(e) = event {
            assert_eq!(e.request_id, request_id);
            assert_eq!(e.model, "claude-opus");
            assert_eq!(e.prompt_tokens, 200);
        } else {
            panic!("Expected RequestStarted event");
        }
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-RESPONSE-RECEIVED-001
    #[test]
    fn test_response_received_event_creation() {
        let request_id = RequestId::new();
        let cost = ResponseCost::from_usd(0.05).unwrap();
        let ttft = TimeToFirstToken::from_ms(150);

        let event = ResponseReceivedEvent::new(request_id.clone(), 250, cost, ttft);

        assert_eq!(event.request_id, request_id);
        assert_eq!(event.completion_tokens, 250);
        assert_eq!(event.cost, cost);
        assert_eq!(event.ttft_ms, ttft);
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-RESPONSE-RECEIVED-002
    #[test]
    fn test_response_received_telemetry_event() {
        let request_id = RequestId::new();
        let cost = ResponseCost::from_usd(0.02).unwrap();
        let ttft = TimeToFirstToken::from_ms(100);

        let event = TelemetryEvent::response_received(request_id.clone(), 300, cost, ttft);

        if let TelemetryEvent::ResponseReceived(e) = event {
            assert_eq!(e.request_id, request_id);
            assert_eq!(e.completion_tokens, 300);
            assert_eq!(e.cost, cost);
            assert_eq!(e.ttft_ms, ttft);
        } else {
            panic!("Expected ResponseReceived event");
        }
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-PROVIDER-FALLBACK-001
    #[test]
    fn test_provider_fallback_event_creation() {
        let request_id = RequestId::new();
        let event = ProviderFallbackEvent::new(
            request_id.clone(),
            "openai".to_string(),
            "anthropic".to_string(),
            "timeout".to_string(),
        );

        assert_eq!(event.request_id, request_id);
        assert_eq!(event.from_provider, "openai");
        assert_eq!(event.to_provider, "anthropic");
        assert_eq!(event.reason, "timeout");
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-PROVIDER-FALLBACK-002
    #[test]
    fn test_provider_fallback_telemetry_event() {
        let request_id = RequestId::new();
        let event = TelemetryEvent::provider_fallback(
            request_id.clone(),
            "openai".to_string(),
            "together".to_string(),
            "rate_limited".to_string(),
        );

        if let TelemetryEvent::ProviderFallback(e) = event {
            assert_eq!(e.request_id, request_id);
            assert_eq!(e.from_provider, "openai");
            assert_eq!(e.to_provider, "together");
            assert_eq!(e.reason, "rate_limited");
        } else {
            panic!("Expected ProviderFallback event");
        }
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-EVENT-TIMESTAMP-001
    #[test]
    fn test_telemetry_event_timestamp() {
        let request_id = RequestId::new();
        let event = TelemetryEvent::request_started(request_id, "gpt-4".to_string(), 100);

        let timestamp = event.timestamp();
        let now = Utc::now();

        // Timestamp should be very recent (within a second)
        let diff = (now - timestamp).num_seconds();
        assert!(diff.abs() <= 1, "Timestamp diff: {} seconds", diff);
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-EVENT-REQUEST-ID-001
    #[test]
    fn test_telemetry_event_request_id_extraction() {
        let request_id = RequestId::new();
        let event = TelemetryEvent::response_received(
            request_id.clone(),
            100,
            ResponseCost::from_usd(0.01).unwrap(),
            TimeToFirstToken::from_ms(50),
        );

        assert_eq!(event.request_id(), &request_id);
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-SERIALIZATION-001
    #[test]
    fn test_telemetry_event_serialization() {
        let request_id = RequestId::new();
        let event = TelemetryEvent::request_started(request_id, "gpt-4".to_string(), 150);

        let json = serde_json::to_string(&event).unwrap();
        assert!(json.contains("RequestStarted"));
        assert!(json.contains("gpt-4"));
        assert!(json.contains("150"));
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-SERIALIZATION-002
    #[test]
    fn test_telemetry_event_deserialization() {
        let request_id = RequestId::new();
        let original = TelemetryEvent::response_received(
            request_id.clone(),
            250,
            ResponseCost::from_usd(0.05).unwrap(),
            TimeToFirstToken::from_ms(120),
        );

        let json = serde_json::to_string(&original).unwrap();
        let deserialized: TelemetryEvent = serde_json::from_str(&json).unwrap();

        assert_eq!(deserialized.request_id(), original.request_id());
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-FALLBACK-REASONS-001
    #[test]
    fn test_fallback_event_with_various_reasons() {
        let reasons = vec!["timeout", "rate_limited", "unavailable", "invalid_response"];

        for reason in reasons {
            let request_id = RequestId::new();
            let event = ProviderFallbackEvent::new(
                request_id,
                "provider1".to_string(),
                "provider2".to_string(),
                reason.to_string(),
            );

            assert_eq!(event.reason, reason);
        }
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-COST-TRACKING-001
    #[test]
    fn test_response_received_cost_accumulation() {
        let request_id = RequestId::new();
        let cost1 = ResponseCost::from_usd(0.01).unwrap();
        let ttft = TimeToFirstToken::from_ms(100);

        let _event1 = ResponseReceivedEvent::new(request_id.clone(), 100, cost1, ttft);
        let cost2 = ResponseCost::from_usd(0.02).unwrap();
        let event2 = ResponseReceivedEvent::new(request_id, 200, cost2, ttft);

        let total_cost = cost1.as_usd() + event2.cost.as_usd();
        assert!((total_cost - 0.03).abs() < 0.000001);
    }

    // Traces to: FR-OBSERVABILITY-TELEMETRY-EVENT-ENUM-001
    #[test]
    fn test_telemetry_event_pattern_matching() {
        let request_id = RequestId::new();
        let events = vec![
            TelemetryEvent::request_started(request_id.clone(), "gpt-4".to_string(), 150),
            TelemetryEvent::response_received(
                request_id.clone(),
                250,
                ResponseCost::from_usd(0.05).unwrap(),
                TimeToFirstToken::from_ms(120),
            ),
            TelemetryEvent::provider_fallback(
                request_id,
                "openai".to_string(),
                "anthropic".to_string(),
                "timeout".to_string(),
            ),
        ];

        let mut started_count = 0;
        let mut received_count = 0;
        let mut fallback_count = 0;

        for event in events {
            match event {
                TelemetryEvent::RequestStarted(_) => started_count += 1,
                TelemetryEvent::ResponseReceived(_) => received_count += 1,
                TelemetryEvent::ProviderFallback(_) => fallback_count += 1,
            }
        }

        assert_eq!(started_count, 1);
        assert_eq!(received_count, 1);
        assert_eq!(fallback_count, 1);
    }
}
