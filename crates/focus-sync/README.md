# focus-sync

Polling scheduler, cursor, dedupe, retries, backoff. The `SyncOrchestrator` owns a registry of `Connector` implementations plus their polling cadence, next-sync deadline, and last cursor. Callers drive it via `SyncOrchestrator::tick()`, passing in the current timestamp (clock injection). Traces to FR-CONN-003, FR-EVT-002.

## Purpose

Orchestrates multi-connector polling with separate cadences and state per connector. Handles cursor persistence (resume from last event), event deduplication (across restarts), retries with exponential backoff, and rate limiting. Decouples polling logic from individual connectors.

## Key Types

- `SyncOrchestrator` — registry + polling coordination
- `Cursor(String)` — persisted sync position per connector/entity_type
- `SyncTrigger` enum — Polling, Webhook, Manual
- `CursorStore` trait / `InMemoryCursorStore` / `NoopCursorStore`
- `EventSink` trait / `NoopEventSink` — where connectors emit events
- `RetryPolicy` / `next_delay()` — exponential backoff logic

## Entry Points

- `SyncOrchestrator::new()` — initialize with empty registry
- `SyncOrchestrator::register()` — add connector with cadence_ms
- `SyncOrchestrator::tick()` — poll due connectors, persist cursors
- Cursor stores and event sinks are pluggable

## Functional Requirements

- FR-CONN-003 (Dedupe via key)
- FR-EVT-002 (Dedupe across restarts)
- FR-EVT-003 (Cursor persistence per connector/entity_type)

## Consumers

- Scheduled runners (invoke `tick()` on interval, e.g., every 1 minute)
- `focus-eval::RuleEvaluationPipeline` (consumes events)
- `focus-storage::sqlite` (persists cursors and events)
