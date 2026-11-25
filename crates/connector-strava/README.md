# connector-strava

Strava connector for FocalPoint. Implements OAuth2 code-flow authentication with REST API polling for athletic activity: runs, rides, swims, and performance metrics.

## Purpose

Syncs athletic achievement and movement signals from Strava to FocalPoint rules. Emits `strava:activity_created`, `strava:effort_milestone`, `strava:segment_pr` events with distance, duration, power data.

## Key Types

- `StravaConnector` — implements `Connector` trait (manifest, health, sync)
- `StravaEvent` — models activity, segment effort, performance data
- `auth::StravaOAuth` — OAuth2 code flow with refresh token persistence
- `api::StravaClient` — REST polling of `/athlete/activities`, `/athlete` profile

## Entry Points

- `sync()` — poll `/athlete/activities?after={cursor}`, emit `NormalizedEvent`s
- `health()` — GET `/athlete` to validate token

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-eval::RuleEvaluationPipeline` (health & movement automation)
