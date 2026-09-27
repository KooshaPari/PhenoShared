//! HTTP Header types for observability and tracing
//!
//! This module defines standardized header types used across the Phenotype ecosystem
//! for request tracing, cost tracking, latency measurement, and failover tracking.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::error::{ObservabilityError, Result};

/// Unique event identifier for distributed tracing
///
/// Used to correlate related events across multiple services.
/// Format: UUID v4
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct EventId(String);

impl EventId {
    /// Create a new random event ID
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }

    /// Create an event ID from a string
    pub fn from_string(id: String) -> Result<Self> {
        if id.is_empty() {
            return Err(ObservabilityError::InvalidHeaderFormat(
                "EventId cannot be empty".to_string(),
            ));
        }
        Ok(Self(id))
    }

    /// Get the event ID as a string
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Convert to header value format
    pub fn to_header_value(&self) -> String {
        self.0.clone()
    }

    /// Parse from header value
    pub fn from_header_value(value: &str) -> Result<Self> {
        Self::from_string(value.to_string())
    }
}

impl Default for EventId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for EventId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Request correlation ID for request aggregation
///
/// Allows aggregating all related requests and responses.
/// Format: UUID v4
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct RequestId(String);

impl RequestId {
    /// Create a new random request ID
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }

    /// Create a request ID from a string
    pub fn from_string(id: String) -> Result<Self> {
        if id.is_empty() {
            return Err(ObservabilityError::InvalidHeaderFormat(
                "RequestId cannot be empty".to_string(),
            ));
        }
        Ok(Self(id))
    }

    /// Get the request ID as a string
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Convert to header value format
    pub fn to_header_value(&self) -> String {
        self.0.clone()
    }

    /// Parse from header value
    pub fn from_header_value(value: &str) -> Result<Self> {
        Self::from_string(value.to_string())
    }
}

impl Default for RequestId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for RequestId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Response cost tracked in USD millionths
///
/// Allows precise cost tracking without floating-point arithmetic.
/// Format: integer representing millionths of USD (e.g., 1000000 = $1.00)
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct ResponseCost(u64);

impl ResponseCost {
    /// Create a cost from USD as f64
    pub fn from_usd(usd: f64) -> Result<Self> {
        if usd < 0.0 {
            return Err(ObservabilityError::InvalidCost(
                "Cost cannot be negative".to_string(),
            ));
        }
        let microdollars = (usd * 1_000_000.0) as u64;
        Ok(Self(microdollars))
    }

    /// Create a cost from millionths of USD
    pub fn from_microdollars(microdollars: u64) -> Self {
        Self(microdollars)
    }

    /// Get cost as USD (f64)
    pub fn as_usd(&self) -> f64 {
        self.0 as f64 / 1_000_000.0
    }

    /// Get cost as millionths of USD
    pub fn as_microdollars(&self) -> u64 {
        self.0
    }

    /// Convert to header value format
    pub fn to_header_value(&self) -> String {
        self.0.to_string()
    }

    /// Parse from header value
    pub fn from_header_value(value: &str) -> Result<Self> {
        value.parse::<u64>().map(Self).map_err(|_| {
            ObservabilityError::InvalidHeaderFormat(format!("Invalid cost header value: {}", value))
        })
    }
}

impl std::fmt::Display for ResponseCost {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "${:.6}", self.as_usd())
    }
}

/// Time-to-First-Token latency measurement in milliseconds
///
/// Tracks the latency from request start to first response token.
/// Format: non-negative integer in milliseconds
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct TimeToFirstToken(u64);

impl TimeToFirstToken {
    /// Create a TTFT measurement from milliseconds
    pub fn from_ms(ms: u64) -> Self {
        Self(ms)
    }

    /// Get TTFT in milliseconds
    pub fn as_ms(&self) -> u64 {
        self.0
    }

    /// Convert to header value format
    pub fn to_header_value(&self) -> String {
        self.0.to_string()
    }

    /// Parse from header value
    pub fn from_header_value(value: &str) -> Result<Self> {
        value.parse::<u64>().map(Self).map_err(|_| {
            ObservabilityError::InvalidHeaderFormat(format!("Invalid TTFT header value: {}", value))
        })
    }
}

impl std::fmt::Display for TimeToFirstToken {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}ms", self.0)
    }
}

/// Fallback step tracking for provider selection in failover chains
///
/// Identifies which provider in the failover chain was ultimately used.
/// Format: non-negative integer (0 = first provider, 1 = second, etc.)
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Default)]
pub struct FallbackStep(u32);

impl FallbackStep {
    /// Create a fallback step
    pub fn new(step: u32) -> Result<Self> {
        Ok(Self(step))
    }

    /// Get the step as u32
    pub fn as_u32(&self) -> u32 {
        self.0
    }

    /// Convert to header value format
    pub fn to_header_value(&self) -> String {
        self.0.to_string()
    }

    /// Parse from header value
    pub fn from_header_value(value: &str) -> Result<Self> {
        value.parse::<u32>().map(Self).map_err(|_| {
            ObservabilityError::InvalidHeaderFormat(format!(
                "Invalid fallback step header value: {}",
                value
            ))
        })
    }

    /// Check if this is the primary provider (step 0)
    pub fn is_primary(&self) -> bool {
        self.0 == 0
    }
}

impl std::fmt::Display for FallbackStep {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "step-{}", self.0)
    }
}

/// Builder for constructing response headers
///
/// Provides a fluent interface for building complete header sets.
#[derive(Debug, Clone, Default)]
pub struct HeaderBuilder {
    event_id: Option<EventId>,
    request_id: Option<RequestId>,
    response_cost: Option<ResponseCost>,
    ttft: Option<TimeToFirstToken>,
    fallback_step: Option<FallbackStep>,
}

impl HeaderBuilder {
    /// Create a new header builder
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the event ID
    pub fn with_event_id(mut self, event_id: EventId) -> Self {
        self.event_id = Some(event_id);
        self
    }

    /// Set the request ID
    pub fn with_request_id(mut self, request_id: RequestId) -> Self {
        self.request_id = Some(request_id);
        self
    }

    /// Set the response cost
    pub fn with_response_cost(mut self, cost: ResponseCost) -> Self {
        self.response_cost = Some(cost);
        self
    }

    /// Set the time-to-first-token
    pub fn with_ttft(mut self, ttft: TimeToFirstToken) -> Self {
        self.ttft = Some(ttft);
        self
    }

    /// Set the fallback step
    pub fn with_fallback_step(mut self, step: FallbackStep) -> Self {
        self.fallback_step = Some(step);
        self
    }

    /// Build the headers as a dictionary
    pub fn build(self) -> ResponseHeaders {
        ResponseHeaders {
            event_id: self.event_id.unwrap_or_default(),
            request_id: self.request_id.unwrap_or_default(),
            response_cost: self.response_cost.unwrap_or_default(),
            ttft: self.ttft.unwrap_or_default(),
            fallback_step: self.fallback_step.unwrap_or_default(),
        }
    }

    /// Build as a map for HTTP headers
    pub fn build_map(self) -> std::collections::HashMap<String, String> {
        let headers = self.build();
        let mut map = std::collections::HashMap::new();
        map.insert("x-event-id".to_string(), headers.event_id.to_header_value());
        map.insert(
            "x-request-id".to_string(),
            headers.request_id.to_header_value(),
        );
        map.insert(
            "x-response-cost-microdollars".to_string(),
            headers.response_cost.to_header_value(),
        );
        map.insert("x-ttft-ms".to_string(), headers.ttft.to_header_value());
        map.insert(
            "x-fallback-step".to_string(),
            headers.fallback_step.to_header_value(),
        );
        map
    }
}

/// Complete set of response headers
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseHeaders {
    pub event_id: EventId,
    pub request_id: RequestId,
    pub response_cost: ResponseCost,
    pub ttft: TimeToFirstToken,
    pub fallback_step: FallbackStep,
}

impl ResponseHeaders {
    /// Create from a map of header values
    pub fn from_map(map: &std::collections::HashMap<String, String>) -> Result<Self> {
        Ok(Self {
            event_id: map
                .get("x-event-id")
                .ok_or_else(|| ObservabilityError::MissingHeader("x-event-id".to_string()))
                .and_then(|v| EventId::from_header_value(v))?,
            request_id: map
                .get("x-request-id")
                .ok_or_else(|| ObservabilityError::MissingHeader("x-request-id".to_string()))
                .and_then(|v| RequestId::from_header_value(v))?,
            response_cost: map
                .get("x-response-cost-microdollars")
                .ok_or_else(|| {
                    ObservabilityError::MissingHeader("x-response-cost-microdollars".to_string())
                })
                .and_then(|v| ResponseCost::from_header_value(v))?,
            ttft: map
                .get("x-ttft-ms")
                .ok_or_else(|| ObservabilityError::MissingHeader("x-ttft-ms".to_string()))
                .and_then(|v| TimeToFirstToken::from_header_value(v))?,
            fallback_step: map
                .get("x-fallback-step")
                .ok_or_else(|| ObservabilityError::MissingHeader("x-fallback-step".to_string()))
                .and_then(|v| FallbackStep::from_header_value(v))?,
        })
    }

    /// Convert to a map for HTTP headers
    pub fn to_map(&self) -> std::collections::HashMap<String, String> {
        let mut map = std::collections::HashMap::new();
        map.insert("x-event-id".to_string(), self.event_id.to_header_value());
        map.insert(
            "x-request-id".to_string(),
            self.request_id.to_header_value(),
        );
        map.insert(
            "x-response-cost-microdollars".to_string(),
            self.response_cost.to_header_value(),
        );
        map.insert("x-ttft-ms".to_string(), self.ttft.to_header_value());
        map.insert(
            "x-fallback-step".to_string(),
            self.fallback_step.to_header_value(),
        );
        map
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBSERVABILITY-HEADERS-EVENT-ID-001
    #[test]
    fn test_event_id_creation() {
        let event_id = EventId::new();
        assert!(!event_id.as_str().is_empty());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-EVENT-ID-002
    #[test]
    fn test_event_id_from_string() {
        let id_str = "test-event-id".to_string();
        let event_id = EventId::from_string(id_str.clone()).unwrap();
        assert_eq!(event_id.as_str(), "test-event-id");
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-EVENT-ID-003
    #[test]
    fn test_event_id_empty_string_fails() {
        let result = EventId::from_string(String::new());
        assert!(result.is_err());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-REQUEST-ID-001
    #[test]
    fn test_request_id_creation() {
        let request_id = RequestId::new();
        assert!(!request_id.as_str().is_empty());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-REQUEST-ID-002
    #[test]
    fn test_request_id_from_string() {
        let id_str = "test-request-id".to_string();
        let request_id = RequestId::from_string(id_str).unwrap();
        assert_eq!(request_id.as_str(), "test-request-id");
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-COST-001
    #[test]
    fn test_response_cost_from_usd() {
        let cost = ResponseCost::from_usd(0.01).unwrap();
        assert_eq!(cost.as_microdollars(), 10000);
        assert!((cost.as_usd() - 0.01).abs() < 0.000001);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-COST-002
    #[test]
    fn test_response_cost_from_microdollars() {
        let cost = ResponseCost::from_microdollars(5000000);
        assert_eq!(cost.as_usd(), 5.0);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-COST-003
    #[test]
    fn test_response_cost_negative_fails() {
        let result = ResponseCost::from_usd(-0.01);
        assert!(result.is_err());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-COST-004
    #[test]
    fn test_response_cost_header_roundtrip() {
        let cost = ResponseCost::from_usd(0.05).unwrap();
        let header_value = cost.to_header_value();
        let parsed = ResponseCost::from_header_value(&header_value).unwrap();
        assert_eq!(cost, parsed);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-TTFT-001
    #[test]
    fn test_ttft_creation() {
        let ttft = TimeToFirstToken::from_ms(150);
        assert_eq!(ttft.as_ms(), 150);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-TTFT-002
    #[test]
    fn test_ttft_header_roundtrip() {
        let ttft = TimeToFirstToken::from_ms(250);
        let header_value = ttft.to_header_value();
        let parsed = TimeToFirstToken::from_header_value(&header_value).unwrap();
        assert_eq!(ttft, parsed);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-FALLBACK-001
    #[test]
    fn test_fallback_step_creation() {
        let step = FallbackStep::new(2).unwrap();
        assert_eq!(step.as_u32(), 2);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-FALLBACK-002
    #[test]
    fn test_fallback_step_is_primary() {
        let primary = FallbackStep::new(0).unwrap();
        let secondary = FallbackStep::new(1).unwrap();
        assert!(primary.is_primary());
        assert!(!secondary.is_primary());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-FALLBACK-003
    #[test]
    fn test_fallback_step_header_roundtrip() {
        let step = FallbackStep::new(3).unwrap();
        let header_value = step.to_header_value();
        let parsed = FallbackStep::from_header_value(&header_value).unwrap();
        assert_eq!(step, parsed);
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-BUILDER-001
    #[test]
    fn test_header_builder_basic() {
        let headers = HeaderBuilder::new()
            .with_event_id(EventId::new())
            .with_request_id(RequestId::new())
            .with_response_cost(ResponseCost::from_usd(0.01).unwrap())
            .with_ttft(TimeToFirstToken::from_ms(100))
            .with_fallback_step(FallbackStep::new(0).unwrap())
            .build();

        assert!(!headers.event_id.as_str().is_empty());
        assert!(!headers.request_id.as_str().is_empty());
        assert_eq!(headers.response_cost.as_microdollars(), 10000);
        assert_eq!(headers.ttft.as_ms(), 100);
        assert!(headers.fallback_step.is_primary());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-BUILDER-002
    #[test]
    fn test_header_builder_defaults() {
        let headers = HeaderBuilder::new().build();
        assert_eq!(headers.response_cost.as_microdollars(), 0);
        assert_eq!(headers.ttft.as_ms(), 0);
        assert!(headers.fallback_step.is_primary());
    }

    // Traces to: FR-OBSERVABILITY-HEADERS-BUILDER-003
    #[test]
    fn test_header_builder_map_roundtrip() {
        let original = HeaderBuilder::new()
            .with_event_id(EventId::new())
            .with_request_id(RequestId::new())
            .with_response_cost(ResponseCost::from_usd(0.02).unwrap())
            .with_ttft(TimeToFirstToken::from_ms(200))
            .with_fallback_step(FallbackStep::new(1).unwrap())
            .build();

        let map = original.to_map();
        let restored = ResponseHeaders::from_map(&map).unwrap();

        assert_eq!(original.event_id, restored.event_id);
        assert_eq!(original.request_id, restored.request_id);
        assert_eq!(original.response_cost, restored.response_cost);
        assert_eq!(original.ttft, restored.ttft);
        assert_eq!(original.fallback_step, restored.fallback_step);
    }
}
