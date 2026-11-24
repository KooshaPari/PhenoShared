# PhenoMCP — Functional & Non-Functional Requirements

**Scope:** Backfilled catalog for Tracera + AgilePlus ingestion.
**Schema version:** 1.
**Test baseline:** 204 Python tests + 19 Rust tests = 223 total passing (2026-05-29).
**ID namespace:** FR-MCP-NNN / NFR-MCP-NNN.

---

## Functional Requirements

### FR-MCP-001 — pheno_mcp Python Package

**Title:** `pheno_mcp` installable Python package exposing Server, Tool, Resource, Prompt, Client.

**Description:** The `pheno_mcp` package (under `python/src/pheno_mcp/`) is the primary
FastMCP-convention Python surface for PhenoMCP. It provides `Server`, `ServerConfig`,
`Tool`, `Resource`, `Prompt`, and `Client` as first-class public symbols re-exported from
`python/src/pheno_mcp/__init__.py`. The package is managed by `uv`/`pyproject.toml` with
`py.typed` marker for static-analysis compatibility.

**Acceptance criteria:**
- `from pheno_mcp import Server, Tool, Resource, Prompt, Client` succeeds after `uv sync`.
- `pyproject.toml` declares the package and its entry points; `uv.lock` is committed.
- `py.typed` is present and `mypy` resolves types without `--ignore-missing-imports`.
- CI (`ubuntu-24.04`, SHA-pinned) runs `uv run pytest` and all tests pass.

**Traceability:**
- PR #76 (pheno_mcp Python package + workflow hygiene ubuntu-24.04 + SHA pins)
- Tests: `python/tests/test_init.py`

---

### FR-MCP-002 — MCP Server Registration (Tools / Resources / Prompts)

**Title:** `Server` registers and lists Tools, Resources, and Prompts by unique key.

**Description:** `Server` maintains three in-memory registries keyed by `tool.name`,
`resource.uri`, and `prompt.name`. Registration is idempotent — re-registering the same
key overwrites the existing entry. `list_tools()`, `list_resources()`, `list_prompts()`
return serialised dicts suitable for a JSON-RPC `tools/list` response. Each object's
`to_dict()` maps to the MCP wire format (`inputSchema`, `mimeType`, etc.).

**Acceptance criteria:**
- `register_tool(t)` followed by `list_tools()` returns exactly one entry with matching name.
- Re-registering the same key replaces the prior entry (no duplicates).
- `list_resources()` / `list_prompts()` follow the same contract.
- All three `to_dict()` methods serialise correctly to expected MCP field names.

**Traceability:**
- PR #76, PR #78 (registration wiring)
- Tests: `python/tests/test_server.py`, `python/tests/test_server_comprehensive.py`

---

### FR-MCP-003 — JSON-RPC Request Dispatch (tools/list, resources/list, prompts/list, tools/call)

**Title:** `Server.handle_request` dispatches MCP JSON-RPC method names to correct handlers.

**Description:** `handle_request(method, params)` is the single async entry point for all
MCP wire requests. It routes `tools/list`, `resources/list`, `prompts/list`, and
`tools/call` to the appropriate internal handler. Unknown methods return a
`-32601 Method not found` error object. Both sync and async tool handlers are supported
via `inspect.iscoroutinefunction`.

**Acceptance criteria:**
- `handle_request("tools/list", {})` returns `{"tools": [...]}`.
- `handle_request("resources/list", {})` returns `{"resources": [...]}`.
- `handle_request("prompts/list", {})` returns `{"prompts": [...]}`.
- `handle_request("tools/call", {"name": "x", "arguments": {}})` invokes the registered handler.
- `handle_request("unknown/method", {})` returns `{"jsonrpc": "2.0", "error": {"code": -32601, ...}}`.
- Both sync and async handlers execute correctly.

**Traceability:**
- PR #76, PR #80 (request validation hardening)
- Tests: `python/tests/test_server.py`, `python/tests/test_server_comprehensive.py`, `python/tests/test_integration.py`

---

### FR-MCP-004 — Request Validation + Structured JSON-RPC Errors

**Title:** Invalid requests return structured JSON-RPC error objects; the server never raises.

**Description:** `handle_request` validates that `method` is a non-empty string (`-32600`)
and that `params` is a dict or `None` (`-32600`). `_handle_tools_call` validates that
`name` is a non-empty string (`-32602`) and that `arguments` is a dict (`-32602`). An
unknown tool name returns `-32601`. Unhandled exceptions inside a handler are caught and
return `-32603 Internal error` (defensive guard). Every error response carries the
canonical `{"jsonrpc": "2.0", "error": {"code": N, "message": "...", "data": {...}}, "id": null}` shape.

**Acceptance criteria:**
- `handle_request(None, {})` → code `-32600`.
- `handle_request("tools/call", {"name": "", "arguments": {}})` → code `-32602`.
- `handle_request("tools/call", {"name": "x", "arguments": "bad"})` → code `-32602`.
- `handle_request("tools/call", {"name": "missing"})` → code `-32601`.
- Error response always has `jsonrpc`, `error.code`, `error.message`, and `id` fields.
- A tool handler that raises still returns an error dict (no exception propagated to caller).

**Traceability:**
- PR #80 (`[codex] harden MCP request validation`)
- Tests: `python/tests/test_server_comprehensive.py`, `python/tests/test_server.py`

---

### FR-MCP-005 — Governance Tool Bundle (ledger_query + ledger_verify)

**Title:** `governance_tools` bundle exposes `ledger_query` and `ledger_verify` MCP tools backed by Parpoura API.

**Description:** `python/src/pheno_mcp/tools/governance_tools.py` defines two tools:
`ledger_query` (GET `/api/v1/governance/ledger` with optional filters `from_entry`,
`to_entry`, `action`, `actor`, `workflow_id`, `limit`) and `ledger_verify`
(POST `/api/v1/governance/ledger/verify` with required `from_entry`/`to_entry`).
The Parpoura base URL is read from `PARPOURA_BASE_URL` env var (default `http://localhost:8001`).
HTTP errors are caught and returned as `{"error": ..., "status_code": ...}` — not raised.
`register_governance_tools(server)` wires both tools onto any `Server` instance.

**Acceptance criteria:**
- `ledger_query` input schema has zero required fields; all six filter fields are optional.
- `ledger_verify` input schema requires exactly `from_entry` and `to_entry`.
- `handle_ledger_query` issues `GET /api/v1/governance/ledger` and returns parsed JSON.
- `handle_ledger_verify` issues `POST /api/v1/governance/ledger/verify` and returns parsed JSON.
- HTTP 4xx/5xx errors return `{"error": ..., "status_code": N}` not an exception.
- `register_governance_tools(server)` makes both tools visible in `server.list_tools()`.

**Traceability:**
- PR #77 (wire ledger_query governance tool end-to-end)
- Tests: `python/tests/test_governance_tools.py`

---

### FR-MCP-006 — Session Tool Bundle (session_suspend + session_resume)

**Title:** `session_tools` bundle exposes `session_suspend` and `session_resume` MCP tools backed by Parpoura API.

**Description:** `python/src/pheno_mcp/tools/session_tools.py` defines:
`session_suspend` (POST `/api/v1/sessions/{session_id}/suspend` → `bundle_ref`) and
`session_resume` (POST `/api/v1/sessions/resume` with `bundle_ref` body → new `session_id`).
Both read `PARPOURA_BASE_URL`. HTTP errors are caught and returned as
`{"error": ..., "status_code": ...}`.

**Acceptance criteria:**
- `session_suspend` requires exactly `session_id`.
- `session_resume` requires exactly `bundle_ref`.
- `handle_session_suspend` issues `POST /api/v1/sessions/{session_id}/suspend`.
- `handle_session_resume` issues `POST /api/v1/sessions/resume` with `{"bundle_ref": ...}` body.
- HTTP errors returned as dict, not raised.
- `register_session_tools(server)` makes both tools visible in `server.list_tools()`.

**Traceability:**
- PR #78 (wire all tool bundles + `create_configured_server`)
- Tests: `python/tests/test_session_tools.py`

---

### FR-MCP-007 — Workflow Tool Bundle (workflow_execute / status / cancel / list)

**Title:** `workflow_tools` bundle exposes four workflow-lifecycle MCP tools backed by Parpoura API.

**Description:** `python/src/pheno_mcp/tools/workflow_tools.py` defines four tools:
`workflow_execute` (POST `/workflows/{id}/execute`),
`workflow_status` (GET `/workflows/{id}`),
`workflow_cancel` (POST `/workflows/{id}/cancel`),
`workflow_list` (GET `/workflows`).
`workflow_execute` accepts optional `workflow_type` (default `"default"`).
`workflow_status` reports lifecycle states `PENDING | RUNNING | SUSPENDED | COMPLETED | FAILED | CANCELLED`.
HTTP errors are caught and returned as `{"error": ..., "status_code": ...}`.

**Acceptance criteria:**
- `workflow_execute` requires `workflow_id`; `workflow_type` is optional.
- `workflow_status` and `workflow_cancel` each require exactly `workflow_id`.
- `workflow_list` requires no arguments.
- Each handler issues the correct HTTP verb + path to `PARPOURA_BASE_URL`.
- HTTP errors returned as dict, not raised.
- `register_workflow_tools(server)` makes all four tools visible in `server.list_tools()`.

**Traceability:**
- PR #78
- Tests: `python/tests/test_workflow_tools.py`

---

### FR-MCP-008 — `create_configured_server` Factory

**Title:** `create_configured_server(config?)` returns a fully-wired `Server` with all 8 tools pre-registered.

**Description:** `server.py::create_configured_server` is a zero-boilerplate factory that
instantiates a `Server` and calls `register_governance_tools`, `register_session_tools`,
and `register_workflow_tools` in sequence. This gives callers a ready-to-use server with
all 8 tools (`ledger_query`, `ledger_verify`, `session_suspend`, `session_resume`,
`workflow_execute`, `workflow_status`, `workflow_cancel`, `workflow_list`) without
importing individual bundle modules.

**Acceptance criteria:**
- `create_configured_server()` returns a `Server` with exactly 8 tools registered.
- `create_configured_server(ServerConfig(name="test"))` propagates the config to the server.
- Returned server handles `tools/list` and returns all 8 tool names.
- No exception raised on construction with default config.

**Traceability:**
- PR #78 (`feat(tools): wire all tool bundles + create_configured_server factory`)
- Tests: `python/tests/test_configured_server.py`

---

### FR-MCP-009 — SearchPort Hexagonal Port Trait (Rust)

**Title:** Object-safe `SearchPort` trait with `ensure_index / index_documents / search / delete_document`.

**Description:** `crates/pheno-ports/src/lib.rs` defines `SearchPort` as an async
object-safe Rust trait (`Box<dyn SearchPort>` compiles). Methods: `ensure_index(index, pk)`,
`index_documents(index, docs)`, `search(index, query) -> SearchResults`,
`delete_document(index, id)`. Domain types `SearchDocument` (id + flattened fields) and
`SearchResults` (hits, estimated_total_hits, processing_time_ms, query) are serde-serialisable.
`SearchPortError` variants: `Index`, `Search`, `Delete`, `Transport`.

**Acceptance criteria:**
- `Box<dyn SearchPort>` compiles (object-safety smoke test passes).
- `InMemorySearchStore` in `doubles` module fully implements the trait.
- `ensure_index` is idempotent — calling twice on the same index name succeeds.
- `index_documents` stores all documents; subsequent `search` finds them by substring.
- `delete_document` removes the document; subsequent search finds nothing.
- `SearchResults.estimated_total_hits` matches the actual hit count.

**Traceability:**
- PR #81 (`feat: hexagonal port traits — SearchPort + SkillStoragePort (audit #4)`)
- Tests: `crates/pheno-ports/src/doubles.rs` (test series `search_double_*`)

---

### FR-MCP-010 — SkillStoragePort Hexagonal Port Trait (Rust)

**Title:** Object-safe `SkillStoragePort` trait with `put / get / list / delete` for `SkillEntry` records.

**Description:** `crates/pheno-ports/src/lib.rs` defines `SkillStoragePort` as an async
object-safe trait. `SkillEntry` fields: `id`, `name`, `version`, `code`, `runtime`,
`metadata (serde_json::Value)`. Methods: `put(entry) -> SkillEntry`, `get(id) -> SkillEntry`,
`list() -> Vec<SkillEntry>`, `delete(id)`. `StoragePortError` variants: `NotFound`,
`Serialise`, `Backend`.

**Acceptance criteria:**
- `Box<dyn SkillStoragePort>` compiles (object-safety smoke test passes).
- `InMemorySkillStore` in `doubles` module fully implements the trait.
- `put` then `get` returns bit-identical entry.
- `put` on an existing id replaces the entry (upsert semantics).
- `get` on a missing id returns `StoragePortError::NotFound`.
- `list` returns all previously `put` entries.
- `delete` removes the entry; subsequent `get` returns `NotFound`.

**Traceability:**
- PR #81
- Tests: `crates/pheno-ports/src/doubles.rs` (test series `skill_store_*`),
  `crates/phenotype-surrealdb/src/lib.rs` (test series `test_port_*`, `test_pheno_surreal_*`)

---

### FR-MCP-011 — phenotype-surrealdb SkillStoragePort Adapter (Stub)

**Title:** `PhenoSurreal` implements `SkillStoragePort` via in-memory delegation pending real SurrealDB wiring.

**Description:** `crates/phenotype-surrealdb/src/lib.rs` provides `PhenoSurreal::new(path)`
which implements `SkillStoragePort` by delegating to `InMemorySkillStore`. The `path`
parameter is accepted for forward-compatibility but not yet used. Legacy helpers
`store_skill`, `query_skills`, and `store_embedding` are preserved for callers that
pre-date the port trait. A `TODO(surreal)` comment marks the delegation site for the
real SurrealDB driver swap.

**Acceptance criteria:**
- `PhenoSurreal::new(path).await` succeeds without a running SurrealDB instance.
- `Box<dyn SkillStoragePort> = Box::new(PhenoSurreal::new(...).await.unwrap())` compiles.
- Legacy `store_skill` round-trips correctly via `store_skill` → `query_skills`.
- `SkillStoragePort::put/get/list/delete` all work correctly via in-memory delegation.
- `store_embedding` returns an `EmbeddingRecord` with a prefixed id (stub).

**Traceability:**
- PR #81 (SurrealDB stub introduced alongside port traits)
- Tests: `crates/phenotype-surrealdb/src/lib.rs` (all `#[tokio::test]` functions)

---

## Non-Functional Requirements

### NFR-MCP-001 — Object-Safe Port Traits

**Title:** All hexagonal port traits in `pheno-ports` must be usable as `Box<dyn Trait>`.

**Description:** Rust's object-safety rules require that async methods use `async_trait`
macro and that no associated-type ambiguity exists. Both `SearchPort` and `SkillStoragePort`
carry the `#[async_trait]` attribute. Object-safety is verified by a compilation smoke test
in each crate's test suite: `let _: Box<dyn SearchPort> = Box::new(InMemorySearchStore::new())`.

**Evidence:** `search_double_is_object_safe` and `skill_store_is_object_safe` tests in
`crates/pheno-ports/src/doubles.rs`; `test_pheno_surreal_is_skill_storage_port` in
`crates/phenotype-surrealdb/src/lib.rs`.

---

### NFR-MCP-002 — FastMCP / MCP Convention Compliance

**Title:** Python package follows FastMCP naming and structural conventions for compatibility with MCP clients.

**Description:** Tool `input_schema` is returned under the key `inputSchema` (camelCase)
per MCP wire format. Resource `mime_type` is serialised as `mimeType`. Handler dispatch
detects async callables via `inspect.iscoroutinefunction` to avoid blocking the event loop.
`PARPOURA_BASE_URL` is an env-var override, not a hard-coded URL, matching Phenotype
config-via-env policy.

**Evidence:** `Server.to_dict()` in `server.py`; async dispatch in `_handle_tools_call`;
`governance_tools._client()` env-var pattern replicated in all three tool bundles.

---

### NFR-MCP-003 — Errors Never Crash the Server

**Title:** No unhandled exception from a tool handler may propagate past `handle_request`.

**Description:** `_handle_tools_call` wraps handler invocation in a `try/except Exception`
guard. Any exception returns a `-32603 Internal error` JSON-RPC object. The server process
continues normally. This rule applies to both sync and async handlers.

**Evidence:** `server.py` lines 294–298 (defensive guard); `python/tests/test_server_comprehensive.py`
covers handler-exception path.

---

### NFR-MCP-004 — Test Suite Coverage (223+ Tests Green)

**Title:** All 223 tests (204 Python + 19 Rust) pass on every merge to `main`.

**Description:** CI must run `uv run pytest python/` (≥ 204 passing) and
`cargo test --workspace` (≥ 19 passing) on every PR. Failures block merge.
Test files trace to at least one FR via naming convention (`test_governance_tools.py` → FR-MCP-005, etc.).

**Evidence:** `uv run pytest` output: `204 passed in 2.23s`; `cargo test --workspace` output:
`19 passed` across `pheno-ports` (11) + `phenotype-surrealdb` (5) + `pheno-meilisearch` (2) + `pheno_mcp` crate (1).

---

### NFR-MCP-005 — SurrealDB Stub Annotated with TODO

**Title:** The in-memory SurrealDB stub is clearly labelled as temporary and upgrade path documented.

**Description:** `phenotype-surrealdb/src/lib.rs` carries a `TODO(surreal)` comment at every
site where the real `surrealdb::Surreal<…>` driver replaces in-memory delegation. The `surrealdb`
crate dependency is already declared in `Cargo.toml` so the swap requires only source changes,
not a dependency addition. Existing callers compile and test against the stub without modification.

**Evidence:** `TODO(surreal)` annotations in `crates/phenotype-surrealdb/src/lib.rs` (two sites);
`surrealdb` listed in workspace `Cargo.toml`; PR #81 description.

---

### NFR-MCP-006 — CI Security Baseline (SHA-Pinned Actions, ubuntu-24.04)

**Title:** All GitHub Actions workflows use SHA-pinned action references on ubuntu-24.04 runners.

**Description:** Per Phenotype org governance, all `uses:` references in `.github/workflows/`
must be pinned to full commit SHAs. The main CI pipeline targets `ubuntu-24.04` (not
`ubuntu-latest`) for reproducibility. TruffleHog secret scanning and Scorecard action
are required CI steps.

**Evidence:** PR #76 (`chore: PhenoMCP workflow hygiene ubuntu-24.04 + SHA pins`);
`.github/workflows/` files contain SHA-format action pins.

---

## Test-ID to Catalog Mapping

| Test file / series | Catalog FR/NFR |
|---|---|
| `test_init.py` | FR-MCP-001 |
| `test_server.py`, `test_server_comprehensive.py` | FR-MCP-002, FR-MCP-003, FR-MCP-004, NFR-MCP-003 |
| `test_integration.py` | FR-MCP-003 |
| `test_governance_tools.py` | FR-MCP-005 |
| `test_session_tools.py` | FR-MCP-006 |
| `test_workflow_tools.py` | FR-MCP-007 |
| `test_configured_server.py` | FR-MCP-008 |
| `test_client.py`, `test_client_connected.py` | FR-MCP-001 (Client symbol) |
| `test_models.py`, `test_models_edge_cases.py` | FR-MCP-002 (domain types) |
| `doubles.rs :: search_double_*` | FR-MCP-009, NFR-MCP-001 |
| `doubles.rs :: skill_store_*` | FR-MCP-010, NFR-MCP-001 |
| `phenotype-surrealdb :: test_*` | FR-MCP-010, FR-MCP-011, NFR-MCP-001, NFR-MCP-005 |

---

## Gaps / PLANNED

| ID | Title | Notes |
|---|---|---|
| PLAN-MCP-001 | Real SurrealDB client wiring | `TODO(surreal)` in `phenotype-surrealdb/src/lib.rs`; `surrealdb` crate already in `Cargo.toml`; only source swap needed |
| PLAN-MCP-002 | pheno-qdrant SearchPort adapter | `crates/pheno-qdrant/` exists (stub); needs `SearchPort` impl backed by `qdrant_client` |
| PLAN-MCP-003 | pheno-meilisearch SearchPort adapter | `crates/pheno-meilisearch/` exists (stub); needs `SearchPort` impl backed by `meilisearch-sdk` |
| PLAN-MCP-004 | Additional Parpoura tool bundles | Only governance/session/workflow wired; agent, knowledge, policy tool groups are PLANNED epics |
| PLAN-MCP-005 | MCP ↔ Claude SDK contract hardening | No schema-level validation between MCP request shape and SDK client expectations; property-based tests needed |
| PLAN-MCP-006 | Transport layer (stdio / HTTP / WS) | `Server.handle_request` has no transport binding yet; wire to FastMCP transport adapters |
| PLAN-MCP-007 | Resource + Prompt handler end-to-end | Registration is wired; no Parpoura-backed handlers exist for `resources/read` or `prompts/get` |
| PLAN-MCP-008 | FR coverage matrix auto-update | `docs/reference/fr_coverage_matrix.md` is empty; auto-population from test annotations needed |
