# connector-linear

Linear connector for FocalPoint. Implements OAuth2 and PAT authentication with GraphQL API client for issue tracking, status changes, and team activity.

## Purpose

Syncs issue lifecycle and project activity from Linear to FocalPoint rules. Emits `linear:issue_created`, `linear:issue_closed`, `linear:issue_updated`, `linear:assignee_changed` events with dedupe keys and timestamps.

## Key Types

- `LinearConnector` — implements `Connector` trait (manifest, health, sync)
- `LinearEvent` — models issue, comment, status change data
- `auth::LinearOAuth` / `auth::LinearPAT` — OAuth2 code flow or PAT authentication
- `api::LinearGqlClient` — GraphQL client for issue queries and mutations

## Entry Points

- `sync()` — query `GET /graphql` for issues updated in window, emit `NormalizedEvent`s
- `health()` — query viewer profile to validate API key/token

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-eval::RuleEvaluationPipeline` (project management automation)
