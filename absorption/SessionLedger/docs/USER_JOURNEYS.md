# User Journeys

This catalog names the main local SessionLedger journeys and maps each one to
the functional requirements and acceptance evidence that already exists in the
repository.

## OKF Roundtrip: Compile to Viewer Contract

**Actor / role:** Local developer or integration reviewer proving that a raw
agent transcript can become a stable viewer-facing artifact.

**FR IDs touched:** FR-001, FR-012, FR-013, FR-010, FR-014.

**Primary acceptance path:**

1. Place or synthesize a JSONL session with a stable `source_id`.
2. Ingest the JSONL into the normalized `Session` model.
3. Compile the session into a `ContinuationBundle`.
4. Export the bundle as `<source_id>.okf.json`.
5. Deserialize the OKF back through the canonical `OkfDocument` type.
6. Confirm the viewer-facing contract is preserved: OKF version, provenance,
   entity/relation integrity, idempotency, and filename stem.

**Mapped automated tests / scripts already present:**

- `tests/okf_roundtrip.rs` is the primary FR-013 smoke suite for
  JSONL -> daemon contract -> OKF -> viewer contract.
- `tests/skeleton.rs` covers JSONL ingestion -> distill compilation -> OKF
  export, including a focused Forge JSONL roundtrip fixture.
- `tests/properties.rs` checks OKF JSON roundtrip invariants with generated
  sessions.
- `tests/okf_golden.rs` locks deterministic OKF snapshots for the golden corpus.
- `crates/sl-daemon/tests/pipeline.rs` mirrors the daemon's ingest -> compile
  -> export path from an on-disk JSONL file.
- `docs/OKF-ROUNDTRIP.md` documents the reproducible command path and the
  conformance assertions.

## Unfinished-Work Recovery: Resume Lost Work

**Actor / role:** Developer returning after an interrupted or incomplete agent
session and looking for the next recoverable unit of work.

**FR IDs touched:** FR-011, FR-012, FR-007, FR-010.

**Primary acceptance path:**

1. Ingest one or more normalized sessions from Forge, Codex, Claude Code, or
   Cursor sources.
2. Detect sessions whose final transcript state indicates unfinished work, such
   as an unanswered user turn, interrupted execution, or missing completion
   marker.
3. Project unfinished items into a serializable worklog with reason, summary,
   corpus, message count, and last activity metadata.
4. Order the projected items by most recent activity for the viewer.
5. Use the unfinished tab or merge localization evidence to resume the smallest
   safe scope.

**Mapped automated tests / scripts already present:**

- `src/domain/worklog.rs` unit tests cover the unfinished-work detector,
  projection filtering, JSON serialization, and summary truncation behavior.
- `tests/merge_recovery.rs` verifies that merged scope localizes unfinished work
  from one of many sessions.
- `crates/sl-viewer/src/unfinished_tab.rs` unit tests verify viewer ordering for
  unfinished items.
- `src/domain/merge.rs` tests exercise merge behavior used by lost-work
  localization.
- `PLAN.md` maps T-024, T-035, and T-036 to the FR-011 recovery surface.

## Live Daemon Ingest to Viewer Replay

**Actor / role:** Local operator running the daemon and viewer to inspect live
session activity, validate ingest, and replay bundle events.

**FR IDs touched:** FR-002, FR-004, FR-009, FR-010, FR-014, FR-015.

**Primary acceptance path:**

1. Start the local daemon with a watch directory, output directory, and loopback
   HTTP bind.
2. Submit a bundle through `POST /api/ingest` or drop a JSONL session into the
   watched directory.
3. Confirm `/healthz` and `/readyz` report the local daemon as live and ready.
4. Observe new OKF paths through `GET /api/stream` / the viewer live feed.
5. Replay a selected bundle through `GET /api/replay/:id` or `sl replay`.
6. Inspect aggregate health through `GET /api/metrics` or Prometheus `/metrics`.

**Mapped automated tests / scripts already present:**

- `crates/sl-daemon/src/validation.rs` unit tests cover FR-002 ingest payload
  validation rules used by `POST /api/ingest`.
- `crates/sl-daemon/tests/sse_bridge.rs` covers daemon liveness and adjacent
  HTTP/SSE contracts for bundle streaming.
- `crates/sl-daemon/src/main.rs` tests cover replay formatting helpers and
  loopback-only HTTP bind validation.
- `crates/sl-daemon/src/metrics.rs` unit tests cover aggregate metrics and the
  Prometheus RED counter snapshot.
- `tests/okf_roundtrip.rs` checks live-feed metadata expectations for emitted
  OKF bundle filenames and document identifiers.
- `tests/visual/harness/a11y.spec.js` exercises the built viewer tab navigation,
  including the Replay tab, against the production web target.
- `process-compose.yaml` and `crates/sl-daemon/process-compose.yaml` are the
  existing local orchestration scripts for daemon/viewer and daemon-only flows.
