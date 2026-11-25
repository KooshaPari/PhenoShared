# connector-notion

Notion connector for FocalPoint. Implements integration token authentication with REST API polling for page updates, database changes, and task completion events.

## Purpose

Syncs knowledge management and task state from Notion to FocalPoint. Emits `notion:page_updated`, `notion:database_item_modified`, `notion:task_completed` events with page IDs and property snapshots.

## Key Types

- `NotionConnector` — implements `Connector` trait (manifest, health, sync)
- `NotionEvent` — models page, database, property-change data
- `auth::NotionAuth` — integration token stored in keychain
- `api::NotionClient` — REST polling of `GET /databases/{id}`, `GET /pages/{id}`

## Entry Points

- `sync()` — query `/databases/{id}` for items updated in window, emit `NormalizedEvent`s
- `health()` — GET `/users/me` to validate integration token

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (REST polling)
- `focus-eval::RuleEvaluationPipeline` (knowledge management automation)
- `focus-planning::TaskModel` (Notion task imports)
