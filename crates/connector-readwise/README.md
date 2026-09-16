# connector-readwise

Readwise Reader connector for FocalPoint. Implements token-based authentication with REST API polling for reading activity: highlights, articles, and reading list updates.

## Purpose

Syncs reading engagement and learning signals from Readwise Reader to FocalPoint rules. Emits `readwise:highlight_created`, `readwise:article_saved`, `readwise:article_read` events with excerpt and metadata.

## Key Types

- `ReadwiseConnector` — implements `Connector` trait (manifest, health, sync)
- `ReadwiseEvent` — models highlight, article, document data
- `auth::ReadwiseAuth` — token-based auth persisted in keychain
- `api::ReadwiseClient` — REST polling of `/list`, `/documents`, `/highlights` endpoints

## Entry Points

- `sync()` — poll `/list`, `/documents?updated_after={cursor}`, emit `NormalizedEvent`s
- `health()` — GET `/auth/profile` to validate API token

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (invokes `sync()`)
- `focus-eval::RuleEvaluationPipeline` (learning engagement rules)
