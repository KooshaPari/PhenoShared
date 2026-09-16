# connector-gcal

Google Calendar connector for FocalPoint. Implements OAuth2 authentication and REST API polling for calendar events with configurable lookahead/lookbehind windows.

## Purpose

Syncs calendar availability and events from Google Calendar to FocalPoint's scheduler and rule engine. Emits `gcal:event_created`, `gcal:event_updated`, `gcal:event_deleted` events normalized to `NormalizedEvent` format with dedupe keys.

## Key Types

- `GcalConnector` — implements `Connector` trait (manifest, health, sync)
- `CalendarEvent` — models Google Calendar event (start, end, summary, attendees, transparency)
- `auth::GcalOAuth` — OAuth2 code flow with refresh token persistence
- `api::GcalClient` — REST polling with `DEFAULT_LOOKAHEAD_DAYS=14`, `DEFAULT_LOOKBEHIND_DAYS=1`

## Entry Points

- `sync()` — poll `/calendars/list` + `/events/list` with time-range filters, cap pages at `MAX_PAGES_PER_CALENDAR=10`
- `health()` — GET `/calendars/primary` to validate token

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-scheduler::RigidityScheduler` (integrates calendar availability for task placement)
- `focus-eval::RuleEvaluationPipeline` (rules can trigger on calendar events)
