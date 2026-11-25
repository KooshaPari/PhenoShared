# Phenotype Observability

Standardized header types and telemetry structures for the Phenotype ecosystem.

This crate provides canonical implementations for cross-cutting observability concerns across distributed LLM services.

## Features

- **Standardized Headers**: Request/response headers for tracing, cost tracking, and latency measurement
- **Telemetry Events**: Complete event types for request lifecycle tracking
- **Zero Unsafe Code**: 100% safe Rust implementation
- **Comprehensive Tests**: 42+ unit and integration tests with full FR traceability
- **Serialization Support**: Full serde integration for JSON serialization/deserialization

## Header Types

### EventId
Unique request identifier for distributed tracing across services.
- Format: UUID v4
- Use case: Correlate related events across multiple services
- Header: `x-event-id`

```rust
let event_id = EventId::new();
assert!(!event_id.as_str().is_empty());
```

### RequestId
Correlation ID for request aggregation within a single request scope.
- Format: UUID v4
- Use case: Group related operations for a single user request
- Header: `x-request-id`

```rust
let request_id = RequestId::new();
```

### ResponseCost
Cost tracking in USD millionths (avoids floating-point precision issues).
- Format: u64 representing millionths of USD
- Example: 1,000,000 = $1.00
- Header: `x-response-cost-microdollars`

```rust
let cost = ResponseCost::from_usd(0.01)?;
assert_eq!(cost.as_microdollars(), 10000);
assert_eq!(cost.as_usd(), 0.01);
```

### TimeToFirstToken
Latency metric from request start to first response token in milliseconds.
- Format: u64 in milliseconds
- Use case: Measure first-token latency (TTFT) for streaming responses
- Header: `x-ttft-ms`

```rust
let ttft = TimeToFirstToken::from_ms(150);
assert_eq!(ttft.as_ms(), 150);
```

### FallbackStep
Provider selection step in failover chains (0 = primary, 1 = secondary, etc.).
- Format: u32
- Use case: Track which provider in the failover chain was used
- Header: `x-fallback-step`

```rust
let primary = FallbackStep::new(0)?;
let secondary = FallbackStep::new(1)?;
assert!(primary.is_primary());
assert!(!secondary.is_primary());
```

## Header Builder

Fluent interface for constructing complete header sets:

```rust
use phenotype_observability::headers::HeaderBuilder;

let headers = HeaderBuilder::new()
    .with_event_id(EventId::new())
    .with_request_id(RequestId::new())
    .with_response_cost(ResponseCost::from_usd(0.05)?)
    .with_ttft(TimeToFirstToken::from_ms(100))
    .with_fallback_step(FallbackStep::new(0)?)
    .build();

// Convert to HTTP header map
let http_headers = headers.to_map();
```

## Telemetry Events

### RequestStartedEvent
Logged when a request initiates:

```rust
let event = TelemetryEvent::request_started(
    RequestId::new(),
    "gpt-4".to_string(),
    150, // prompt tokens
);
```

Fields:
- `request_id`: Correlation ID
- `model`: Model name
- `prompt_tokens`: Estimated input token count
- `timestamp`: Event creation time (UTC)

### ResponseReceivedEvent
Logged when a response completes:

```rust
let event = TelemetryEvent::response_received(
    RequestId::new(),
    250, // completion tokens
    ResponseCost::from_usd(0.05)?,
    TimeToFirstToken::from_ms(120),
);
```

Fields:
- `request_id`: Correlation ID (matches request)
- `completion_tokens`: Output token count
- `cost`: Total cost of request/response
- `ttft_ms`: Time-to-first-token latency
- `timestamp`: Event creation time (UTC)

### ProviderFallbackEvent
Logged during failover transitions:

```rust
let event = TelemetryEvent::provider_fallback(
    RequestId::new(),
    "openai".to_string(),
    "anthropic".to_string(),
    "timeout".to_string(),
);
```

Fields:
- `request_id`: Request triggering the fallback
- `from_provider`: Failed provider name
- `to_provider`: Replacement provider name
- `reason`: Reason for fallback ("timeout", "rate_limited", etc.)
- `timestamp`: Event creation time (UTC)

## Header Format Specification

All headers are transmitted as HTTP header values (strings):

| Header | Format | Example |
|--------|--------|---------|
| `x-event-id` | UUID v4 string | `550e8400-e29b-41d4-a716-446655440000` |
| `x-request-id` | UUID v4 string | `550e8400-e29b-41d4-a716-446655440001` |
| `x-response-cost-microdollars` | Unsigned integer | `50000` (= $0.05) |
| `x-ttft-ms` | Unsigned integer | `150` |
| `x-fallback-step` | Unsigned integer | `0` (primary), `1` (secondary) |

## Complete Request Lifecycle Example

```rust
use phenotype_observability::headers::{HeaderBuilder, EventId, RequestId};
use phenotype_observability::telemetry::TelemetryEvent;

// Create request identifiers
let event_id = EventId::new();
let request_id = RequestId::new();

// Emit request started event
let start_event = TelemetryEvent::request_started(
    request_id.clone(),
    "gpt-4".to_string(),
    150,
);

// Simulate failover
let fallback_event = TelemetryEvent::provider_fallback(
    request_id.clone(),
    "openai".to_string(),
    "anthropic".to_string(),
    "timeout".to_string(),
);

// Emit response completed event
let response_event = TelemetryEvent::response_received(
    request_id.clone(),
    250,
    ResponseCost::from_usd(0.02)?,
    TimeToFirstToken::from_ms(120),
);

// Build response headers
let headers = HeaderBuilder::new()
    .with_event_id(event_id)
    .with_request_id(request_id)
    .with_response_cost(ResponseCost::from_usd(0.02)?)
    .with_ttft(TimeToFirstToken::from_ms(120))
    .with_fallback_step(FallbackStep::new(1)?)
    .build();

// Convert to HTTP headers
let http_headers = headers.to_map();
```

## Testing

All 42 tests pass with full FR traceability:

```bash
cargo test --package phenotype-observability
```

Test categories:
- **Header Tests** (17): Creation, parsing, serialization, roundtrip conversion
- **Telemetry Tests** (13): Event creation, serialization, pattern matching
- **Integration Tests** (12): Complete flows, failover scenarios, cost accumulation

## Design Principles

- **SOLID**: Interface Segregation (minimal headers), Dependency Inversion (traits)
- **DRY**: Reusable header types across all projects
- **KISS**: Simple, focused API surface
- **Safety**: Zero unsafe code, no panics in happy path

## Dependencies

- `serde`: Serialization/deserialization
- `thiserror`: Error handling
- `chrono`: Timestamp handling
- `uuid`: UUID generation

All dependencies are workspace-managed at the latest stable versions.

## Integration with Bifrost

This crate extracts and standardizes patterns from bifrost-routing's metrics and response handling:

- Integrates with bifrost's cost tracking (microdollar precision)
- Supports latency measurement patterns (TTFT)
- Provides fallover tracking for routing decisions

## Use Cases

1. **Request Tracing**: Track requests across multiple services using EventId
2. **Cost Accounting**: Precise cost tracking without floating-point errors
3. **Performance Monitoring**: TTFT measurement for latency analysis
4. **Failover Tracking**: Record which provider handled each request
5. **Audit Logging**: Complete request lifecycle telemetry
6. **Multi-tenant Isolation**: RequestId for request aggregation

## License

MIT
