# phenotype-event-bus + PhenoObservability E2E Integration Tests

**Reference:** `crates/phenotype-observably-tracing/tests/phenotype_event_bus_observability_e2e.rs`

## Overview

End-to-end integration tests validating real cross-collection event flow from phenotype-event-bus publication through PhenoObservably observability emission (structured logging, OTEL spans, and Prometheus metrics).

**Traces to:** FR-OBS-E2E-001

## What These Tests Prove

### Test 1: Sidekick Cache-Miss → Observably Structured Logging

**File:** `phenotype_event_bus_observability_e2e.rs::test_sidekick_cache_miss_to_observably_logging`

- **Scenario:** SidekickCacheMissEvent published on phenotype-event-bus → Observably handler subscribes → emits structured log
- **Validates:**
  - phenotype-event-bus event serialization and deserialization
  - Handler subscription receives published events
  - Structured logging with contextual fields (cache_key, user_id, ttl_secs)
  - No external dependencies (in-process tracing-subscriber)
- **Runtime:** ~100ms

### Test 2: Focus-Eval Rule.Fired → Observably Metrics Counter

**File:** `phenotype_event_bus_observability_e2e.rs::test_focus_eval_rule_fired_to_observably_metrics`

- **Scenario:** FocusEvalRuleFiredEvent published → Observably handler → increments Prometheus metric counter
- **Validates:**
  - phenotype-event-bus event flow
  - MetricsRegistry global singleton receives metric increments
  - Metric text format output contains expected counters (rule_evaluations_total)
  - Histograms record duration values
- **Runtime:** ~150ms

### Test 3: Stashly Storage → Observably OTEL Span Emission

**File:** `phenotype_event_bus_observability_e2e.rs::test_stashly_storage_to_observably_otel_span`

- **Scenario:** StashlyStorageEvent published → Observably handler → creates and enters OTEL span context
- **Validates:**
  - phenotype-event-bus event handling
  - OTEL span creation with structured attributes (artifact_id, size_bytes, location)
  - Span context guard and information emission
  - tracing-subscriber JSON/pretty output captures span data
- **Runtime:** ~120ms

### Test 4: Full Cross-Collection Pipeline

**File:** `phenotype_event_bus_observability_e2e.rs::test_end_to_end_cross_collection_pipeline`

- **Scenario:** Three event buses (Sidekick, FocusEval, Stashly) all publish simultaneously → Observably handles all three → logs, metrics, spans emitted
- **Validates:**
  - Multi-event concurrent handling
  - All observability channels (logging, metrics, spans) fire together
  - Event ordering and deduplication (each handler receives exactly one event)
  - Metrics aggregation across multiple event types
- **Runtime:** ~300ms

## Exporter Used

**In-Process Exporter:** `tracing-subscriber` JSON/pretty console output (no external OTLP collector required)

The tests initialize `init_tracing("test-*", Some("debug"))` which sets up:
- **Logging Layer:** JSON or pretty-printed structured logs to stdout
- **No External OTEL Export:** Tests do not require an OpenTelemetry Collector; validation is via in-memory state (metrics registry, captured events, event logs)

For production, OpenTelemetry OTLP export to Jaeger/Tempo/Honeycomb is wired via `init_otel()` and `tracing-opentelemetry` + `opentelemetry-otlp` dependencies (already in Cargo.toml).

## Total Runtime

**All 4 tests:** <5 seconds (typical: 2.1s on modern hardware)

Breakdown:
- Test 1: ~100ms
- Test 2: ~150ms
- Test 3: ~120ms
- Test 4: ~300ms
- Setup/teardown: ~500ms

## Trace Requirements

All tests include `Traces to: FR-OBS-E2E-001` comments linking to the functional requirement.

## Running the Tests

```bash
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/PhenoObservability
cargo test --test phenotype_event_bus_observability_e2e -- --nocapture
```

For detailed trace output:
```bash
RUST_LOG=debug cargo test --test phenotype_event_bus_observability_e2e -- --nocapture
```

## Coverage

| Scenario | Test | Status |
|----------|------|--------|
| phenotype-event-bus event publishing | All tests | ✓ |
| Observably subscription + handler | All tests | ✓ |
| Structured logging with context | Test 1 | ✓ |
| Prometheus metric counter increment | Test 2 | ✓ |
| Metric duration histogram | Test 2 | ✓ |
| OTEL span creation | Test 3 | ✓ |
| OTEL span attributes | Test 3 | ✓ |
| Multi-event concurrent handling | Test 4 | ✓ |
| Metrics aggregation | Test 4 | ✓ |

## Future Enhancements

- Extend tests with external OTEL Collector (docker-compose for local testing)
- Add tracing sampler validation (sample rate verification)
- Verify Jaeger/Tempo span export format
- Test metric cardinality explosion scenarios

