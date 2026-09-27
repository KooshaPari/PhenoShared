# Bifrost-Routing Integration Guide

This document explains how to integrate `phenotype-observability` into bifrost-routing to standardize header handling and telemetry across the Phenotype ecosystem.

## Current State

Bifrost-routing currently implements observability locally:
- **metrics.rs**: Cost and latency tracking
- **models.rs**: Request/response structures with basic cost/latency fields

## Integration Strategy

### Phase 1: Direct Replacement (Low Risk)

Replace existing bifrost metrics with standardized observability types:

```rust
// Before (bifrost-routing/src/metrics.rs)
pub struct ProviderMetrics {
    provider_name: String,
    cost_tracker: CostTracker,      // Internal implementation
    latency_tracker: LatencyTracker, // Internal implementation
}

// After
use phenotype_observability::headers::{ResponseCost, TimeToFirstToken};

pub struct ProviderMetrics {
    provider_name: String,
    total_cost: ResponseCost,        // Use standardized type
    total_latency: TimeToFirstToken, // Use standardized type
}
```

### Phase 2: Response Headers Standardization

Inject response headers into `LLMResponse`:

```rust
// bifrost-routing/src/models.rs

use phenotype_observability::headers::{HeaderBuilder, ResponseHeaders};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMResponse {
    // Existing fields...
    pub request_id: String,
    pub content: String,
    pub model: String,
    pub cost_usd: f64,
    pub latency_ms: u64,

    // NEW: Standardized observability headers
    #[serde(skip)]
    pub observability_headers: ResponseHeaders,
}

impl LLMResponse {
    /// Create response headers from this response
    pub fn create_headers(&self) -> ResponseHeaders {
        HeaderBuilder::new()
            .with_event_id(EventId::new())
            .with_request_id(RequestId::from_string(self.request_id.clone()).unwrap())
            .with_response_cost(ResponseCost::from_usd(self.cost_usd).unwrap())
            .with_ttft(TimeToFirstToken::from_ms(self.latency_ms))
            .with_fallback_step(FallbackStep::new(0).unwrap()) // Track in router
            .build()
    }
}
```

### Phase 3: Telemetry Event Emission

Emit telemetry at key points:

```rust
// bifrost-routing/src/router.rs

use phenotype_observability::telemetry::TelemetryEvent;
use phenotype_observability::headers::RequestId;

pub async fn invoke(&self, request: &LLMRequest) -> BifrostResult<LLMResponse> {
    let request_id = RequestId::from_string(request.request_id.clone())?;

    // Emit: Request Started
    let start_event = TelemetryEvent::request_started(
        request_id.clone(),
        request.model.clone(),
        request.estimate_tokens(),
    );

    // (Optionally log: println!("{:?}", start_event))

    let mut current_provider_idx = 0;

    for attempt in 0..self.max_retries {
        let provider = self.strategy.select_provider(&self.providers, request).await?;

        match provider.invoke(request).await {
            Ok(mut response) => {
                // Emit: Response Received
                let response_event = TelemetryEvent::response_received(
                    request_id.clone(),
                    response.output_tokens,
                    ResponseCost::from_usd(response.cost_usd)?,
                    TimeToFirstToken::from_ms(response.latency_ms),
                );

                // Create headers for response
                response.observability_headers = HeaderBuilder::new()
                    .with_request_id(request_id)
                    .with_response_cost(ResponseCost::from_usd(response.cost_usd)?)
                    .with_ttft(TimeToFirstToken::from_ms(response.latency_ms))
                    .with_fallback_step(FallbackStep::new(current_provider_idx as u32)?)
                    .build();

                return Ok(response);
            }
            Err(e) => {
                // Emit: Provider Fallback
                if current_provider_idx + 1 < self.providers.len() {
                    let from_provider = provider.name().to_string();
                    let to_provider = self.providers[current_provider_idx + 1].name().to_string();

                    let fallback_event = TelemetryEvent::provider_fallback(
                        request_id.clone(),
                        from_provider,
                        to_provider,
                        format!("Error: {}", e), // Or classify: "timeout", "rate_limited"
                    );

                    current_provider_idx += 1;
                    continue;
                } else {
                    return Err(e);
                }
            }
        }
    }

    Err(BifrostError::RoutingError("All providers exhausted".to_string()))
}
```

## Header Format in HTTP Responses

When returning responses, bifrost can inject headers:

```rust
// Example: Axum or other web framework integration
use phenotype_observability::headers::ResponseHeaders;

async fn llm_chat(request: LLMRequest) -> (StatusCode, HeaderMap, Json<LLMResponse>) {
    let response = router.invoke(&request).await.unwrap();

    let mut headers = HeaderMap::new();

    // Convert observability headers to HTTP headers
    let obs_headers = response.observability_headers.to_map();
    for (key, value) in obs_headers {
        headers.insert(
            HeaderName::from_str(&key).unwrap(),
            HeaderValue::from_str(&value).unwrap(),
        );
    }

    (StatusCode::OK, headers, Json(response))
}
```

## Cost Tracking Precision

The observability crate provides exact cost tracking:

```rust
// Before: Floating-point imprecision
let cost = 0.01 + 0.02; // May not equal 0.03
let total = cost as u64; // Loss of precision

// After: Exact arithmetic
let cost1 = ResponseCost::from_usd(0.01)?;
let cost2 = ResponseCost::from_usd(0.02)?;
let total = cost1.as_microdollars() + cost2.as_microdollars(); // Exact: 30000
```

## Latency Tracking Precision

Use TimeToFirstToken for TTFT metrics:

```rust
// Before: Mixed units
let latency_ms = 150u64; // Unclear unit, prone to conversion errors
let latency_seconds = latency_ms as f64 / 1000.0; // Loss of precision

// After: Type-safe units
let ttft = TimeToFirstToken::from_ms(150);
println!("{}", ttft); // Displays as "150ms"
assert_eq!(ttft.as_ms(), 150); // Type-safe access
```

## Failover Tracking

Track which provider was used:

```rust
pub struct RoutingMetrics {
    requests_by_provider: HashMap<String, u64>,
    fallback_events: Vec<TelemetryEvent>,
}

// In router.invoke()
let mut fallback_step = 0;
for (attempt, provider) in providers.iter().enumerate() {
    match provider.invoke(request).await {
        Ok(response) => {
            metrics.requests_by_provider
                .entry(provider.name().to_string())
                .and_modify(|e| *e += 1)
                .or_insert(1);

            // Record which provider ultimately succeeded
            response.observability_headers.fallback_step = FallbackStep::new(fallback_step as u32)?;

            return Ok(response);
        }
        Err(_) => {
            fallback_step += 1;
        }
    }
}
```

## Event Collection

Bifrost can collect telemetry events for analysis:

```rust
pub struct TelemetryCollector {
    events: Vec<TelemetryEvent>,
}

impl TelemetryCollector {
    pub fn record(&mut self, event: TelemetryEvent) {
        self.events.push(event);
    }

    pub fn cost_by_provider(&self) -> HashMap<String, f64> {
        let mut costs = HashMap::new();
        for event in &self.events {
            if let TelemetryEvent::ResponseReceived(e) = event {
                // Aggregate costs...
            }
        }
        costs
    }

    pub fn export_json(&self) -> String {
        serde_json::to_string(&self.events).unwrap()
    }
}
```

## Testing Integration

Create integration tests:

```rust
#[tokio::test]
async fn test_bifrost_response_headers() {
    let router = create_test_router();
    let request = LLMRequest::new("gpt-4".to_string(), vec![...]);

    let response = router.invoke(&request).await.unwrap();

    // Verify headers are present
    assert!(!response.observability_headers.event_id.as_str().is_empty());
    assert_eq!(
        response.observability_headers.request_id,
        RequestId::from_string(request.request_id.clone()).unwrap()
    );

    // Verify cost precision
    let expected_cost = ResponseCost::from_usd(0.05).unwrap();
    assert_eq!(response.observability_headers.response_cost, expected_cost);

    // Verify TTFT tracking
    let ttft = response.observability_headers.ttft;
    assert!(ttft.as_ms() > 0);

    // Verify fallback step (should be 0 for successful primary)
    assert!(response.observability_headers.fallback_step.is_primary());
}
```

## Dependency Addition

Add to bifrost-routing's Cargo.toml:

```toml
[dependencies]
phenotype-observability = { path = "../phenotype-observability" }
```

Or with workspace dependencies:

```toml
[dependencies]
phenotype-observability.workspace = true
```

## Migration Checklist

- [ ] Add phenotype-observability to Cargo.toml
- [ ] Import header and telemetry types in models.rs
- [ ] Update LLMResponse to include ResponseHeaders
- [ ] Add event emission in Router::invoke()
- [ ] Implement fallover tracking in routing strategy
- [ ] Add integration tests for headers
- [ ] Test cost precision (no floating-point errors)
- [ ] Test latency precision (millisecond granularity)
- [ ] Document header format in API docs
- [ ] Update observability README

## Backward Compatibility

The integration is fully backward compatible:
- Existing `cost_usd` and `latency_ms` fields remain
- ResponseHeaders can be optional or derived from existing fields
- Telemetry events are emitted independently (no breaking changes)
- Headers can be opt-in (feature flag if needed)

## Performance Impact

Minimal performance impact:
- Header creation: O(1) allocations
- Event emission: Minimal overhead (no I/O unless collected)
- Cost tracking: Same precision as before, no additional computation

## Next Steps

1. Create a feature branch in bifrost-routing
2. Follow Phase 1 (direct replacement) first
3. Add comprehensive tests
4. Create PR with integration documentation
5. Coordinate with other Phenotype services for ecosystem-wide adoption

## Questions?

Refer to:
- `/Users/kooshapari/Repos/phenotype-infrakit/crates/phenotype-observability/README.md`
- `/Users/kooshapari/Repos/phenotype-infrakit/crates/phenotype-observability/IMPLEMENTATION_SUMMARY.md`
