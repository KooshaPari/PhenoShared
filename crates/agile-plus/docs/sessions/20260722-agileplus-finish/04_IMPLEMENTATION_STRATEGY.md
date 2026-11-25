# AgilePlus Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans task-by-task. Every task is test-first and commits only its scoped files.

**Goal:** Ship one real, secure AgilePlus control plane and prove it through project-scoped consumption, usage, observability, and compliance evidence for AgilePlus, Tracera, and Grapheon.

**Architecture:** `agileplus-proto` is the sole generated-contract boundary; the Rust API/gRPC processes share one resolved runtime configuration; SQLite owns durable events and evidence metadata; MinIO owns artifact bytes; Python MCP forwards the authenticated API cursor stream. Credentials and API-key material are reference-only outside a keychain-first encrypted store. The evidence verifier is the rollout authority.

**Tech stack:** Rust/Cargo/tonic/axum/sqlx, SQLite, MinIO S3, Python FastMCP, process-compose, Docker Compose.

---

## File map

| Concern | Production files | Tests / proof |
|---|---|---|
| build + runtime | `crates/agileplus-proto/build.rs`, `crates/agileplus-proto/src/{lib.rs,stubs.rs}`, `crates/agileplus-cli/src/runtime.rs`, `crates/agileplus-api/src/{main.rs,state.rs,router/health.rs}`, `crates/agileplus-grpc/src/server/bootstrap.rs`, `process-compose.yml` | `crates/agileplus-cli/tests/cli_smoke.rs`, `crates/agileplus-api/tests/api_integration.rs`, `crates/agileplus-grpc/tests/grpc_integration.rs` |
| secrets | `crates/agileplus-domain/src/credentials/{factory.rs,file.rs,keychain.rs,keys.rs,store.rs}`, `crates/agileplus-api/src/api_key.rs`, `crates/agileplus-sqlite/src/migrations/013_create_api_keys.sql` | new `crates/agileplus-domain/tests/credentials_store.rs`, `crates/agileplus-api/tests/api_key_security.rs` |
| events | `crates/agileplus-events/src/{query.rs,store.rs}`, `crates/agileplus-sqlite/src/{event_store.rs,repository/events.rs}`, `crates/agileplus-api/src/routes/events.rs` | `tests/contracts/events_sqlite_contract.rs`, `tests/contracts/api_events_contract.rs` |
| artifacts + stream | `crates/agileplus-artifacts/src/{lib.rs,store.rs}`, `crates/agileplus-api/src/routes/stream.rs`, `crates/agileplus-grpc/src/streaming.rs`, `python/src/agileplus_mcp/{grpc_backlog.py,__main__.py}` | new `crates/agileplus-artifacts/tests/minio_store.rs`, API/gRPC integration tests, Python MCP stream test |
| evidence + rollouts | `crates/agileplus-cli/src/commands/{validate.rs,ship.rs}`, `crates/agileplus-sqlite/src/repository/evidence.rs`, `crates/agileplus-fixtures/src/dogfood.rs` | new `crates/agileplus-cli/tests/evidence_manifest.rs`, `tests/integration/dogfood_{agileplus,tracera,grapheon}.rs` |

## Execution order

### Task 1: Make the build and runtime contract real

**Files:** modify the build/runtime files in the first map row; add focused test modules beside their existing test files.

- [ ] Write failing tests for (a) a missing `protoc` release build failing with installation guidance, (b) one resolved HTTP/gRPC endpoint shared by CLI/API/gRPC, and (c) health plus graceful shutdown.
- [ ] Run `cargo test -p agileplus-proto -p agileplus-cli -p agileplus-api -p agileplus-grpc --locked`; record the expected failures.
- [ ] Remove runnable stub fallback from `build.rs`; use generated tonic code for release/test builds and only isolate static-analysis stubs behind a non-runnable cfg. Implement `ResolvedRuntime` once in `agileplus-cli/src/runtime.rs`; pass it to API, gRPC, `process-compose.yml`, health probes, and launcher diagnostics.
- [ ] Run `cargo fmt --check && cargo test -p agileplus-proto -p agileplus-cli -p agileplus-api -p agileplus-grpc --locked`; then start the isolated compose profile and prove `GET /health`, a gRPC read, and SIGTERM shutdown.
- [ ] Commit: `fix(runtime): enforce generated proto and resolved endpoint contract`.

### Task 2: Protect credentials and API keys at rest

**Files:** modify the secrets row; add `credentials_store.rs` and `api_key_security.rs`.

- [ ] Write failing tests proving keychain preference, unavailable-keychain AES-256-GCM/Argon2id fallback, ciphertext-only disk bytes, wrong passphrase/tamper fail-closed, rotate/delete, API-key redaction, and no plaintext token in an audit event.
- [ ] Run `cargo test -p agileplus-domain --test credentials_store -p agileplus-api --test api_key_security --locked`; record failures.
- [ ] Implement a versioned encrypted file envelope with authenticated metadata and Argon2id-derived key; make the factory reject missing/invalid material and remove plaintext production storage. Store only key references and fingerprints in SQLite/API/audit payloads.
- [ ] Run the two targeted tests, `rg -n --glob '!**/tests/**' '(api[_-]?key|token|secret).*=.*["'\''`]' crates`, and `cargo test -p agileplus-domain -p agileplus-api --locked`.
- [ ] Commit: `feat(security): encrypt credential and api-key persistence`.

### Task 3: Make events durable, queryable, and cursor-safe

**Files:** modify the events row; add migration `027_event_query_cursor.sql` if schema changes are required.

- [ ] Write failing contract tests for append/restart persistence, project/type/time filters, stable cursor pagination, invalid cursor rejection, and hash-chain verification failure.
- [ ] Run `cargo test --test events_sqlite_contract --test api_events_contract --locked`; record failures.
- [ ] Define one `EventQuery`/`EventPage` in `agileplus-events`; implement it in SQLite with indexed `(project_id, occurred_at, event_id)` ordering; bind the API route to that repository rather than memory state.
- [ ] Run the contract tests plus `cargo test -p agileplus-events -p agileplus-sqlite -p agileplus-api --locked` against a temporary database.
- [ ] Commit: `feat(events): persist filtered cursor event queries`.

### Task 4: Store verified artifacts and stream the same event source

**Files:** modify the artifacts + stream row; add `crates/agileplus-artifacts/tests/minio_store.rs` and `python/tests/test_stream.py`.

- [ ] Write failing tests for project-scoped MinIO put/get, SHA-256 mismatch rejection, denied cross-project read, unavailable-object-store failure, stream heartbeat, authenticated resume from cursor, and no duplicate resumed event.
- [ ] Run `cargo test -p agileplus-artifacts --test minio_store -p agileplus-api -p agileplus-grpc --locked` and `uv run pytest python/tests/test_stream.py -q`; record failures.
- [ ] Implement the S3 adapter with immutable digest-addressed keys and metadata in SQLite; map API SSE, gRPC streaming, and MCP forwarding to the Task 3 cursor source. Do not introduce a separate in-memory stream.
- [ ] Run the targeted suites with MinIO started from the isolated compose profile; capture put/get digest and authenticated stream transcript.
- [ ] Commit: `feat(evidence): add verified artifacts and resumable event streaming`.

### Task 5: Add the AgilePlus evidence verifier and self-dogfood journey

**Files:** modify the evidence row; create `docs/sessions/20260722-agileplus-finish/artifacts/agileplus/manifest.json` only from real command output.

- [ ] Write failing verifier tests rejecting absent files, wrong project, secret-like strings, failed audit chain, invalid event ordering, and artifact digest mismatch; write one passing fixture with usage, trace, compliance, event, and artifact references.
- [ ] Run `cargo test -p agileplus-cli --test evidence_manifest --locked`; record failures.
- [ ] Implement schema/version validation and `agileplus validate evidence`; build the self-dogfood fixture through the real API/MCP/CLI path, not seeded SQLite rows.
- [ ] Run `cargo run -p agileplus-cli -- validate evidence --manifest docs/sessions/20260722-agileplus-finish/artifacts/agileplus/manifest.json`, `cargo test --workspace --locked`, and the secret scan from Task 2.
- [ ] Commit: `feat(compliance): verify project evidence manifests`.

### Task 6: Dogfood Tracera

**Files:** create `docs/sessions/20260722-agileplus-finish/artifacts/tracera/{commands.md,manifest.json}`; add `tests/integration/dogfood_tracera.rs`; make only integration configuration edits required by the verified API contract.

- [ ] Write the failing dogfood test: provision a `tracera` project, consume API/MCP, emit usage and trace, attach an artifact, read a resumed stream, and verify a compliance evidence pack.
- [ ] Run `cargo test --test dogfood_tracera --locked`; record the failing gate.
- [ ] Execute the journey against the live AgilePlus runtime with non-production credentials; retain redacted command output, trace ID, event cursor range, artifact digest, policy result, and manifest.
- [ ] Run the test and `agileplus validate evidence --manifest .../tracera/manifest.json`; require all references to be project-scoped to `tracera`.
- [ ] Commit: `test(dogfood): prove Tracera consumption and compliance`.

### Task 7: Recover and dogfood Grapheon

**Files:** Grapheon checkout conflict files discovered by `git -C <grapheon> diff --check`; create `docs/sessions/20260722-agileplus-finish/artifacts/grapheon/{commands.md,manifest.json}` and `tests/integration/dogfood_grapheon.rs`.

- [ ] First prove the recovery gate fails: `git -C <grapheon> diff --check`, `rg -n '^(<<<<<<<|=======|>>>>>>>)' <grapheon>`, and its canonical build/test command.
- [ ] Resolve every conflict using the intended current API consumer, delete obsolete duplicate paths, and add/adjust the Grapheon integration test for the same full evidence journey as Task 6.
- [ ] Run its clean build/test, `cargo test --test dogfood_grapheon --locked`, and the evidence verifier; retain the exact redacted outputs and evidence references.
- [ ] Commit the Grapheon recovery separately from its AgilePlus dogfood wiring; snapshot both repositories after their commits.

## Release gate

Only declare a project passed when: locked workspace tests, targeted lane tests, live health/API/gRPC/MCP proof, redacted secret scan, event-chain verification, artifact digest verification, and `agileplus validate evidence` all succeed. A failure retains its evidence pack and produces a no-go record; it is not converted to a pass by skipping any gate.
