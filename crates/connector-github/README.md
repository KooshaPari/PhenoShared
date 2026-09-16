# connector-github

GitHub contributions connector for FocalPoint. Implements Personal Access Token (PAT) auth and REST API polling for user activity: push events, PR merges, issue closures, code reviews.

## Purpose

Syncs developer productivity signals from GitHub to FocalPoint rules. Emits `github:push`, `github:pr_merged`, `github:issue_closed`, `github:code_review` events with timestamps and payload metadata.

## Key Types

- `GitHubConnector` — implements `Connector` trait (manifest, health, sync)
- `GitHubEvent` — models push, PR, issue, review activity
- `auth::GitHubPAT` — stores PAT in OS keychain; validates via `GET /user`
- `api::GitHubClient` — REST polling of `GET /users/{login}/events`
- `webhook::GitHubWebhookVerifier` — validates X-Hub-Signature for real-time push (future)

## Entry Points

- `sync()` — poll `/users/{login}/events`, filter to relevant types, emit `NormalizedEvent`s
- `health()` — GET `/user` to check token validity; on 401, surface `Unauthorized` for UI re-auth prompt
- `webhook::verify()` — validate GitHub webhook HMAC-SHA256 signature (async path)

## Functional Requirements

- FR-CONN-001 (Connector trait)
- FR-CONN-002 (Manifest)
- FR-CONN-003 (Dedupe)

## Consumers

- `focus-sync::SyncOrchestrator` (REST polling)
- `focus-eval::RuleEvaluationPipeline` (workflow automation rules)
- `focus-webhook-server` (real-time webhook delivery, planned)
