# connector-canvas

Canvas LMS connector for FocalPoint. Implements OAuth2 code-flow authentication, REST API polling, and event mapping for course assignments, submissions, and announcements.

## Purpose

Syncs learning activity from Canvas to FocalPoint's rule engine. Emits `canvas:assignment_opened`, `canvas:assignment_submitted`, `canvas:announcement_posted` events with dedupe keys and confidence scores.

## Key Types

- `CanvasConnector` — implements `Connector` trait (manifest, health, sync)
- `CanvasEvent` — models Canvas course, assignment, submission, announcement structs
- `auth::CanvasOAuth` — OAuth2 flow with code → token exchange
- `api::CanvasClient` — REST polling with pagination (capped at `MAX_PAGES_PER_COURSE=10`)

## Entry Points

- `sync()` — poll `/api/v1/users/self/courses` + assignments/submissions/announcements, emit `NormalizedEvent`s
- `health()` — GET `/api/v1/users` to validate token liveness

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)
- FR-CONN-004 (Canvas OAuth + cursor sync)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-eval::RuleEvaluationPipeline` (consumes `NormalizedEvent`s)
