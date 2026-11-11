# Functional requirements — SessionLedger

Machine-readable FR catalog for agent readiness (C03 / v38). Derived from
[`DESIGN.md`](DESIGN.md) and [`README.md`](../README.md). Each FR has a stable
ID, status, and acceptance references (tests and/or API surfaces).

Status vocabulary matches the ops traceability SSOT: `done`, `partial`, `todo`,
`blocked`, or `na`.

Roles used in stories: **operator** (runs local daemon/ops), **developer**
(integrates ingest/compile/inject), **viewer-user** (uses the desktop viewer).

---

| ID     | Title                                                     | Status | Acceptance refs                                                                                                                                                  |
| ------ | --------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | JSONL / corpus ingest into normalized Session             | done   | `crates/sl-daemon` ETL (`etl.rs`, `watcher.rs`); `tests/skeleton.rs`; `crates/sl-daemon/tests/pipeline.rs`                                                       |
| FR-002 | OKF bundle schema validation on ingest                    | done   | `POST /api/ingest`; `crates/sl-daemon/src/validation.rs`; `sl validate` CLI                                                                                      |
| FR-003 | Bundle list + search/filter                               | done   | `GET /api/bundles`, `GET /api/search`; `--since/--until/--model/--min-tokens/--tag/--limit`; `filter.rs`, `tag.rs`                                               |
| FR-004 | Session replay via SSE                                    | done   | `GET /api/replay/:id`; `crates/sl-daemon/tests/sse_bridge.rs`; `sl replay`; `crates/sl-viewer/src/replay_view.rs`                                                |
| FR-005 | Aggregated session metrics                                | done   | `GET /api/metrics`; `crates/sl-daemon/src/metrics.rs` (unit tests)                                                                                               |
| FR-006 | Archive / restore (gzip)                                  | done   | `sl archive` / `sl restore`; `crates/sl-daemon/src/archive.rs`                                                                                                   |
| FR-007 | Viewer Timeline                                           | done   | `crates/sl-viewer/src/timeline.rs`                                                                                                                               |
| FR-008 | Viewer Search                                             | done   | `crates/sl-viewer/src/search_view.rs` → `GET /api/search`                                                                                                        |
| FR-009 | Viewer Replay                                             | done   | `crates/sl-viewer/src/replay_view.rs` → `GET /api/replay/:id`                                                                                                    |
| FR-010 | Viewer LiveFeed                                           | done   | `crates/sl-viewer/src/live_feed.rs` → `GET /api/stream`; `docs/OKF-ROUNDTRIP.md`                                                                                 |
| FR-011 | Crash recovery / unfinished work surface                  | done   | DESIGN §5.1; T-024 detector in `src/domain/worklog.rs`; T-036 unfinished viewer tab in `crates/sl-viewer/src/unfinished_tab.rs`; #97                             |
| FR-012 | ContinuationBundle compile + inject gate                  | done   | `src/domain/bundle.rs`; `src/distill`; Acceptance slice gate (DESIGN §2)                                                                                         |
| FR-013 | OKF roundtrip smoke (JSONL→daemon→OKF→viewer contract)    | done   | `tests/okf_roundtrip.rs`; `docs/OKF-ROUNDTRIP.md`; fixtures under `tests/fixtures/okf/`                                                                          |
| FR-014 | Daemon liveness + local ops stack                         | done   | `GET /healthz + GET /readyz`; `process-compose.yaml`; `make dev`; `docs/ops/runbook.md`                                                                          |
| FR-015 | Observability surfaces (metrics, OTLP traces, dashboards) | done   | `/healthz`, `/readyz`, `/api/metrics`, Prometheus `/metrics`; feature-gated OTLP in `crates/sl-daemon/src/otel.rs`; `docs/ops/dashboards/sessionledger-red.json` |

## User stories (role form)

| ID     | Story                                                                                                                                                |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | As a developer, I want JSONL and corpus transcripts ingested into a normalized Session so that every source shares one model for distill and export. |
| FR-002 | As an operator, I want OKF bundle schema validation on ingest so that invalid payloads are rejected before they enter the store.                     |
| FR-003 | As a viewer-user, I want to list and search/filter bundles so that I can find sessions by time, model, tokens, and tags.                             |
| FR-004 | As a viewer-user, I want session replay over SSE so that I can stream events without loading the full transcript up front.                           |
| FR-005 | As an operator, I want aggregated session metrics so that I can see bundle volume, models, and token usage at a glance.                              |
| FR-006 | As an operator, I want gzip archive and restore so that old bundles can be compacted and recovered later.                                            |
| FR-007 | As a viewer-user, I want a Timeline view so that I can browse session history chronologically.                                                       |
| FR-008 | As a viewer-user, I want Search in the viewer so that I can query sessions without leaving the UI.                                                   |
| FR-009 | As a viewer-user, I want Replay in the viewer so that I can watch a selected bundle stream from the daemon.                                          |
| FR-010 | As a viewer-user, I want a LiveFeed so that newly emitted OKF paths appear as the daemon processes work.                                             |
| FR-011 | As a developer, I want unfinished and crash-recovery surfaces so that I can resume the next recoverable unit of work.                                |
| FR-012 | As a developer, I want ContinuationBundle compile with an inject gate so that only acceptance-complete bundles become injectable prompts.            |
| FR-013 | As a developer, I want an OKF roundtrip smoke path so that the JSONL→daemon→OKF→viewer contract stays proven.                                        |
| FR-014 | As an operator, I want daemon liveness and a local ops stack so that healthz/readyz and `make dev` keep the system runnable.                         |
| FR-015 | As an operator, I want observability surfaces so that metrics, optional OTLP traces, and dashboards show daemon health.                              |

---

## API surface (daemon)

| Method | Path              | FR             |
| ------ | ----------------- | -------------- |
| GET    | `/healthz`        | FR-014         |
| GET    | `/api/bundles`    | FR-003         |
| GET    | `/api/search`     | FR-003, FR-008 |
| GET    | `/api/stream`     | FR-010         |
| GET    | `/api/replay/:id` | FR-004, FR-009 |
| POST   | `/api/ingest`     | FR-002         |
| GET    | `/api/metrics`    | FR-005, FR-015 |

Default listen: `SL_PORT=8080` (see `process-compose.yaml`).

## Notes

- FR-011 is complete: T-024 classifies normalized sessions and serializes
  `WorklogProjection` items; T-036 displays them in the viewer's unfinished tab.
- FR-015 is complete at its FR scope: structured traces, feature-gated OTLP
  export, Prometheus RED metrics, and an importable dashboard are shipped.
  Provisioning, alert routing, endpoint labels, and histogram depth remain C05
  audit gaps in `ops/GAP_QA_MATRIX.md`, not unfinished FR acceptance.
