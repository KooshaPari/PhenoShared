# focus-webhook-server

HTTP server for receiving real-time webhook notifications from connectors (GitHub, Notion, etc.). Validates HMAC-SHA256 / ed25519 signatures, parses events, and dispatches to `focus-sync::SyncOrchestrator` for immediate processing.

## Purpose

Complements polling by handling real-time push events. When a GitHub push happens or a Notion page updates, the provider webhooks to FocalPoint, bypassing the polling cadence. Signature verification prevents spoofed events. Reduces latency and connector request volume.

## Key Types

- `WebhookServer` — HTTP server (Axum or Actix-web based)
- `WebhookHandler` — routes per connector type, validates signatures
- Request/response models for each connector (GitHub, Notion, Linear, etc.)

## Entry Points

- `WebhookServer::start()` — bind to port, register handlers
- Per-endpoint handlers: `/webhook/github`, `/webhook/notion`, etc.
- Signature verification via `focus-connectors::signature_verifiers`

## Functional Requirements

- HMAC-SHA256 signature verification (GitHub, Notion)
- Ed25519 verification (custom/internal webhooks)
- Immediate event dispatch to sync orchestrator

## Consumers

- GitHub, Notion, Linear, Strava webhooks (external)
- `focus-sync::SyncOrchestrator` (event dispatch)
- CI/CD integration testing
