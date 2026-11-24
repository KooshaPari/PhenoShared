# AgilePlus REST API — HTTP route reference

> **Status:** authoritative for v0.12 (task 21 ac_v1).
> **Owner:** forge. **Source-of-truth:** `AgilePlus/crates/agileplus-api/`
> (`compose.rs` router + per-resource `routes/*.rs` handlers).
> **Companion docs:** `agileplus-events.md` (field-mapping reference, task 33).

## 1. Overview

The AgilePlus HTTP API is an axum-based server exposing project
management primitives (features, work packages, cycles, modules,
projects, epics, stories, branches, worktrees, audit, governance,
events) over a REST/JSON surface. Authentication is via Bearer token
or X-API-Key header. Health endpoints are unauthenticated.

The base URL is configurable; default for local development is
`http://127.0.0.1:8080`. The server is normally launched via the
`agileplus` CLI's `platform start` subcommand, but `cargo run -p
agileplus-api` is the canonical dev entrypoint.

## 2. Authentication

All `/api/*` endpoints (other than `/health`, `/info`, `/webhooks`)
require a valid token. Three token-presenting methods are accepted
by `middleware::auth::extract_token`:

```http
Authorization: Bearer <token>
```
```http
X-API-Key: <token>
```
```http
GET /api/v1/features?api_key=<token>
```

Tokens are verified by `middleware::token_verifier::DynTokenVerifier`
(Bearer / shared-secret path) or `CredentialStore` (legacy API-key
path). The raw token value is never logged. See
`crates/agileplus-api/src/middleware/auth.rs` for the exact
extraction logic.

**Public paths (no auth required):** `/health`, `/detailed-health`,
`/info`, `/webhooks/*`, `/modules`, `/cycles`, `/cycles/{id}` (HTML
dashboard pages).

## 3. Health & metadata

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | no | Simple liveness probe |
| GET | `/detailed-health` | no | Dependency probes (DB, VCS, OTel) |
| GET | `/info` | no | Server version + module manifest |
| GET | `/modules` | no | HTML module tree page |
| GET | `/cycles` | no | HTML cycle kanban page |
| GET | `/cycles/{id}` | no | HTML cycle detail page |

## 4. Features (`/api/v1/features`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/features` | List features (filterable by state) |
| POST | `/api/v1/features` | Create feature |
| GET | `/api/v1/features/{slug}` | Get feature by slug |
| PATCH | `/api/v1/features/{slug}` | Update feature |
| POST | `/api/v1/features/{slug}/transition` | Transition feature state |
| GET | `/api/v1/features/{slug}/work-packages` | List feature's WPs |
| POST | `/api/v1/features/{slug}/work-packages` | Create WP under feature |
| GET | `/api/v1/features/{slug}/audit` | Audit trail |
| POST | `/api/v1/features/{slug}/audit/verify` | Verify hash-chained audit log |
| GET | `/api/v1/features/{slug}/governance` | Governance contract |
| POST | `/api/v1/features/{slug}/validate` | Run governance validation |

## 5. Work packages (`/api/v1/work-packages`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/work-packages/{id}` | Get WP by ID |
| PATCH | `/api/v1/work-packages/{id}` | Update WP |
| POST | `/api/v1/work-packages/{id}/transition` | Transition WP state |

## 6. Events (`/api/v1/events`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/events` | Query events (cursor-based pagination) |
| GET | `/api/v1/events/{id}` | Single event by ID |
| GET | `/api/v1/stream` | SSE real-time event stream |

## 7. Branches & worktrees

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/branches/checkout` | Checkout a branch |
| POST | `/api/v1/branches/delete` | Delete a branch |
| POST | `/api/v1/branches/sync` | Sync branches with VCS |
| POST | `/api/v1/worktrees/` | Add worktree |
| DELETE | `/api/v1/worktrees/` | Remove worktree |

## 8. Modules (`/api/modules`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/modules/` | List modules |
| GET | `/api/modules/{id}/tree` | Module dependency tree |

## 9. Cycles (`/api/cycles`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/cycles/` | List cycles |
| GET | `/api/cycles/{id}` | Get cycle |
| POST | `/api/cycles/{id}/transition` | Transition cycle |

## 10. Domain: projects, epics, stories, users (`/api/v1/*`)

| Resource | Routes |
|----------|--------|
| Projects | GET/POST `/api/v1/projects/`, GET `/api/v1/projects/{slug}`, GET `/api/v1/projects/{slug}/epics` |
| Epics | POST `/api/v1/epics/`, GET `/api/v1/epics/{id}`, POST `/api/v1/epics/{id}/transition`, GET `/api/v1/epics/{id}/stories` |
| Stories | POST `/api/v1/stories/`, GET `/api/v1/stories/{id}`, POST `/api/v1/stories/{id}/transition` |
| Users | GET/POST `/api/v1/users/`, GET `/api/v1/users/{id}` |

## 11. Backlog (`/api/v1/backlog`)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/backlog/import` | Bulk-import backlog items |
| GET | `/api/v1/backlog/{id}` | Get backlog item |
| POST | `/api/v1/backlog/{id}/transition` | Transition item state |
| POST | `/api/v1/backlog/pop` | Pop next work item |

## 12. Bundle / batch (`/api/v1/bundle`)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/bundle` | Import bundle (multi-resource) |
| POST | `/api/v1/batch-projects` | Batch create projects |

## 13. Schema conventions

Every request body uses serde-derived JSON; date-times are RFC 3339
strings (e.g., `2026-08-10T07:30:53Z`). Identifiers are slugs
(`feature.slug`) for features and projects, opaque IDs (`wp.id`) for
work packages, epics, stories, and users.

Errors are returned as `ApiError` (see `crates/agileplus-api/src/error.rs`):

```json
{
  "error": "validation",
  "message": "transition not allowed from state=created to state=done"
}
```

Success responses are wrapped via `responses.rs` (status code + body)
to ensure a uniform envelope.

## 14. Streaming & real-time

`GET /api/v1/stream` is a Server-Sent Events endpoint that streams
events as they are appended to the audit/event log. Use it for
live-tail UIs (cockpit dashboards, bead-ctl watchers).

## 15. Versioning

The current API prefix is `/api/v1`. The `/api/v1` prefix is
considered stable; breaking changes require a new `/api/v2` prefix.
Additive changes (new fields, new optional query params) may ship
under `/api/v1` without a version bump, provided they don't
re-shape existing response envelopes.

## 16. Operational notes

- **Default port:** 8080 (override via `AGILEPLUS_API_PORT` env).
- **Default bind:** `0.0.0.0` (override via `AGILEPLUS_API_BIND`).
- **Audit chain:** all write endpoints append a hash-chained event
  to the feature-scoped audit log; verify via
  `POST /api/v1/features/{slug}/audit/verify`.
- **Rate limits:** none at the API layer; rely on upstream
  ingress (e.g., nginx) for throttling.
- **CORS:** permissive by default (`tower_http::cors::CorsLayer::permissive`).

## See also

- `docs/integrations/agileplus-events.md` — field-mapping reference (task 33)
- `AgilePlus/crates/agileplus-api/src/router/compose.rs` — route definitions
- `AgilePlus/crates/agileplus-api/src/middleware/auth.rs` — auth middleware
- `AgilePlus/crates/agileplus-api/src/openapi.rs` — OpenAPI doc generation
- `AgilePlus/AGENTS.md` — AgilePlus project conventions
