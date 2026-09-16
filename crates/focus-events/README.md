# focus-events

Normalized event schema, dedupe keys, trace references. Defines the canonical `NormalizedEvent` struct that all connectors emit. Events include timestamp metadata, confidence scores, and flat JSON payloads.

## Purpose

Provides a single event schema that all connectors normalize to, enabling rules to match on a consistent shape. Handles dedupe key uniqueness validation, event_id generation, and confidence scoring (High/Medium/Low).

## Key Types

- `NormalizedEvent` — event_id, connector_id, account_id, event_type, occurred_at, effective_at, dedupe_key, confidence, payload
- `Confidence` enum — High, Medium, Low (affects rule firing threshold)
- `EventError` — variants for missing fields, invalid timestamps, format errors
- Dedupe key construction helpers per connector

## Entry Points

- `NormalizedEvent::builder()` — fluent construction
- `NormalizedEvent::validate()` — check required fields and timestamp consistency
- Connector-specific dedupe key generation (in each connector crate)

## Functional Requirements

- FR-EVT-001 (Event schema)
- FR-EVT-002 (Dedupe by key)
- FR-EVT-003 (Cursor progress per connector/entity_type)

## Consumers

- All connector crates (emit normalized events)
- `focus-sync::SyncOrchestrator` (stores events)
- `focus-eval::RuleEvaluationPipeline` (consumes for rule matching)
