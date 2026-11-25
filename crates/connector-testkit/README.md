# connector-testkit

Testing harness and fixtures for FocalPoint connector authors. Provides replay playbooks, mock sync runners, and in-memory event stores for validating connector implementations.

## Purpose

Standardizes connector testing with `FixtureReplay` (plays back recorded API responses), `MockSyncRunner` (executes sync logic against mocks), and `ConnectorTestHarness` (orchestrates full test scenarios). Includes dedupe contract tests and state mutation validation.

## Key Types

- `FixtureReplay` — loads JSON fixture files and replays HTTP responses
- `MockSyncRunner` — runs a connector's `sync()` against mock data
- `ConnectorTestHarness<C>` — generic test harness for any `Connector` impl
- `HelperEventStore` — in-memory event store with dedupe validation

## Entry Points

- `FixtureReplay::load()` — load recorded API responses from YAML/JSON
- `MockSyncRunner::run()` — execute sync logic and collect emitted events
- `ConnectorTestHarness::new()` — initialize harness for a connector type
- `HelperEventStore::ingest()` — insert events with idempotent dedupe

## Functional Requirements

- FR-CONN-001 (Connector contract testing)
- FR-CONN-003 (Dedupe contract validation)

## Consumers

- All connector crates (test modules)
- CI/CD test runs in `focus-mcp-server` and `services/webhooks`
