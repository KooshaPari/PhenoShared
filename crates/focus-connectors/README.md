# focus-connectors

Connector trait, manifest contract, auth strategy enum, sync mode, and error types. Defines the interface all connectors (Canvas, Fitbit, GitHub, etc.) implement. Includes connector registry and signature verification for webhook payloads.

## Purpose

Central trait and contract for all data-source connectors. Enables plug-and-play connector architecture where new providers are added by implementing the trait. Includes manifest validation, health checks, sync cursor management, and webhook signature verification.

## Key Types

- `Connector` — trait: `manifest()`, `health()`, `sync()` implementations
- `ConnectorManifest` — declares auth_strategy, sync_mode, capabilities, entity_types, event_types
- `AuthStrategy` enum — OAuth2, PAT, Token, ApiKey variants
- `SyncMode` enum — Polling, Webhook, Both
- `ConnectorError` — variants for auth, network, parsing, rate-limit
- `signature_verifiers::*` — HMAC-SHA256 / ed25519 validators for webhooks

## Entry Points

- `Connector::manifest()` — return declared capabilities and contract
- `Connector::health()` — validate token liveness
- `Connector::sync()` — poll and emit `NormalizedEvent`s
- `signature_verifiers::verify_github_webhook()` — validate GitHub webhook HMAC

## Functional Requirements

- FR-CONN-001 (Trait definition)
- FR-CONN-002 (Manifest)
- FR-CONN-005 (Health checks)

## Consumers

- All connector crates (Canvas, Fitbit, GCal, GitHub, Linear, Notion, Readwise, Strava)
- `focus-sync::SyncOrchestrator` (registry and polling)
- `focus-webhook-server` (signature verification, planned)
