# Tracera API — pheno-harness integration reference

> **Status:** draft (v0.12 task 7, Phase 1 — Tracera adapter)
> **Owner:** forge. **Source-of-truth:** Grapheon
> `crates/tracera-server/src/main.rs` + `persistence_api.rs` +
> `governance_api.rs` + `analysis_api.rs` (commit `e1f905693`).
> **Refs:** v0.12 WBS-PERT-100 task 7.

## Endpoint

| Field              | Value                                                       |
| ------------------ | ----------------------------------------------------------- |
| Base URL (default) | `http://127.0.0.1:8080`                                     |
| Host env var       | `TRACERA_HOST` (canonical) / `GRAPHEON_HOST` (legacy alias) |
| Port env var       | `TRACERA_PORT` (canonical) / `GRAPHEON_PORT` (legacy alias) |
| Default port       | `8080`                                                      |
| Default host       | `127.0.0.1` (LOCALHOST)                                     |
| Bind interface     | `TRACERA_HOST:TRACERA_PORT` (`SocketAddr`)                  |
| Process            | `tracera-server` binary (axum v0.7)                         |
| Storage backend    | `SqliteTraceRepository` (rusqlite 0.40)                     |

## Authentication

None at the API level (local-only service; bound to localhost by
default). The launchd plist in `~/Library/LaunchAgents/com.phenoforge.*`
holds the bind address in `EnvironmentVariables` (Grapheon AGENTS.md
hard rule #4).

For non-local bind (`GRAPHEON_BIND_ADDR=0.0.0.0:8080`), authentication
must be added by the operator — not currently implemented in tracera-server.

## HTTP routes (20 endpoints)

### Health (4)

| Method | Path       | Response                                 |
| ------ | ---------- | ---------------------------------------- |
| GET    | `/healthz` | `{"status":"ok"}`                        |
| GET    | `/health`  | `{"status":"ok"}`                        |
| GET    | `/readyz`  | `{"status":"ready","version":"<x.y.z>"}` |
| GET    | `/ready`   | `{"status":"ready","version":"<x.y.z>"}` |

### Analysis (`/api/v1/*`)

| Method | Path                   | Module                       | Purpose                      |
| ------ | ---------------------- | ---------------------------- | ---------------------------- |
| POST   | `/api/v1/impact`       | `analysis_api::impact`       | blast-radius impact analysis |
| POST   | `/api/v1/confidence`   | `analysis_api::confidence`   | claim confidence scoring     |
| POST   | `/api/v1/blast-radius` | `analysis_api::blast_radius` | direct blast-radius query    |

### Tracing (3)

| Method | Path                          | Purpose                     |
| ------ | ----------------------------- | --------------------------- |
| GET    | `/api/v1/trace/forward/:id`   | forward trace from claim id |
| GET    | `/api/v1/trace/reverse/:id`   | reverse trace to claim id   |
| GET    | `/api/v1/trace/neighbors/:id` | bidirectional neighbors     |

### Evidence (`/evidence/*`)

| Method | Path               | Purpose                    |
| ------ | ------------------ | -------------------------- |
| POST   | `/evidence`        | create evidence record     |
| GET    | `/evidence`        | list evidence (filterable) |
| GET    | `/evidence/health` | evidence service health    |

### Ingest (`/ingest/*`)

| Method | Path             | Purpose                                    |
| ------ | ---------------- | ------------------------------------------ |
| POST   | `/ingest/github` | GitHub event ingest (commits, PRs, issues) |
| POST   | `/ingest/jira`   | Jira event ingest (issues, sprints)        |

### SDLC-PM (`/sdlc-pm/*`)

| Method | Path               | Purpose                |
| ------ | ------------------ | ---------------------- |
| GET    | `/sdlc-pm/sprints` | list sprints           |
| POST   | `/sdlc-pm/sprints` | create sprint          |
| GET    | `/sdlc-pm/stories` | list stories           |
| GET    | `/sdlc-pm/health`  | SDLC-PM service health |

### Org-Intel (`/org-intel/*`)

| Method | Path                | Purpose                  |
| ------ | ------------------- | ------------------------ |
| GET    | `/org-intel/teams`  | list teams + members     |
| GET    | `/org-intel/health` | org-intel service health |

## Schema (selected)

### Sprint

```json
{
  "id": "uuid-v4",
  "name": "string",
  "goal": "string",
  "start_date": "ISO8601 datetime",
  "end_date": "ISO8601 datetime",
  "status": "string",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### Story

```json
{
  "id": "uuid-v4",
  "sprint_id": "uuid-v4 or null",
  "title": "string",
  "description": "string",
  "status": "string",
  "story_points": "i64 or null",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### TraceEvent (inferred; full schema pending inspect of `store.rs`)

```json
{
  "id": "uuid-v4",
  "kind": "claim | evidence | trace | sprint | story",
  "ts": "ISO8601 datetime",
  "actor": "string",
  "payload": "object"
}
```

## Absorption destination (2026-09-05)

Tracera is the successor destination for Grapheon absorption. The Python
consumer resolves explicit constructor/YAML values first, then `TRACERA_*`,
then `GRAPHEON_*` compatibility fallbacks. Set `TRACERA_BASE_URL` and
`TRACERA_API_TOKEN` to the owner-approved destination; the localhost default
is not deployment discovery or proof of readiness. Explicit custom
`api_token_env` names remain authoritative.

The current Tracera server retains `POST /evidence`, `GET /evidence`, and
`GET /healthz` in `crates/tracera-server/src/main.rs`. Local adapter tests
verify configuration and mocked HTTP behavior only. Authenticated append,
query, health, telemetry, and compliance evidence remain retirement gates.

## Historical authorship

Tracera was renamed to Grapheon on 2026-07-14. The `TRACERA_*` env
var aliases are honored for back-compat per Grapheon AGENTS.md hard
rule #2. The `TRACERA_API_URL` env var is a deprecated alias for
`GRAPHEON_API_URL` — `thegent/benchmark/forge_eval/ai_dd/claims_graph.py`
writes there.

## Next (task 8+)

Task 8: scaffold `pheno/trace_store/tracera.py` (TraceraAdapter skeleton)
using this API surface.
