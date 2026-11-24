# connector-fitbit

Fitbit connector for FocalPoint. Implements OAuth2 authentication and REST API polling for health metrics: steps, heart rate, sleep, distance, elevation, calories burned.

## Purpose

Syncs fitness activity and biometric data from Fitbit to FocalPoint rules. Emits `fitbit:activity_logged`, `fitbit:sleep_recorded`, `fitbit:heart_rate_zone_achieved` events with normalized timestamps and confidence scores.

## Key Types

- `FitbitConnector` — implements `Connector` trait (manifest, health, sync)
- `FitbitEvent` — models activity, sleep, heart rate data structures
- `auth::FitbitOAuth` — OAuth2 code flow with client_id/secret
- `api::FitbitClient` — REST polling with rate-limit handling

## Entry Points

- `sync()` — poll `/user/{user_id}/activities/list`, `/user/{user_id}/sleep/list`, emit `NormalizedEvent`s
- `health()` — GET `/user/profile` to validate token and rate-limit status

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)
- FR-CONN-005 (Health transitions)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-eval::RuleEvaluationPipeline` (consumes events for activity-based rules)
