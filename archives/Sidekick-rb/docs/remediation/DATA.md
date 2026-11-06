# Data & Persistence Remediation — Sidekick

**Audit pillar:** I-Data (16%)  
**Status:** Remediation scaffold — documents persistence contracts per crate and migration path.  
**Last updated:** 2026-06-25

## Summary

Sidekick is a polyglot agent-utility workspace. Persistence is **intentionally decentralized**: each crate owns its storage story. No shared ORM or global database. This document is the single source of truth for data-layer expectations until unified migration tooling lands.

| Crate | Language | Persistence model | Migration status |
|-------|----------|-------------------|------------------|
| `sidekick-messaging` | Rust | Stateless adapter (in-memory / provider-delegated) | v0 — no local store |
| `sidekick-dispatch` | Rust | Job queue + dispatch log (JSONL / SQLite planned) | v0 — copied, workspace pending |
| `sidekick-presence` | Python | User status file + launchd state | v0 — gitignored vendored copy |
| `cheap-llm-mcp` | Python | JSONL ledger, TTL cache, config YAML | v1 — operational |

---

## sidekick-messaging

**Current state:** Pure library. `Message` and `MessagingAdapter` have no durable storage.

**Persistence contract (target):**

- Outbound messages: ephemeral until `MessagingAdapter::send` succeeds; provider owns delivery receipts.
- No PII at rest in the crate; recipient/body pass through to MCP skill (`agent-imessage`).
- Availability checks (`is_available`) are live queries, not cached.

**Schema (logical):**

```
Message {
  recipient: String,
  body: String,
  provider: MessageProvider  // IMessage | SMS | Email
}
```

**Migration plan:**

1. **M1 (v0.1):** Add optional `MessageStore` trait + in-memory impl for tests (see `tests/storage_stubs.rs`).
2. **M2 (v0.2):** SQLite-backed outbox for retry / idempotency keys (`message_id`, `sent_at`, `status`).
3. **M3 (v1.0):** Provider-specific receipt tables via adapter plugins.

**Test coverage:** `crates/sidekick-messaging/tests/storage_stubs.rs`

---

## sidekick-dispatch

**Current state:** Crate referenced in docs/consolidation; not yet in workspace `members` on `main`.

**Persistence contract (from `thegent-dispatch` lineage):**

- Dispatch requests: append-only JSONL log (`~/.sidekick/dispatch.jsonl`).
- Provider routing table: TOML config, hot-reloadable.
- Job state: in-process; durable queue planned (SQLite `dispatch_jobs`).

**Schema (planned — SQLite):**

```sql
CREATE TABLE dispatch_jobs (
  id            TEXT PRIMARY KEY,
  provider      TEXT NOT NULL,
  payload_json  TEXT NOT NULL,
  status        TEXT NOT NULL,  -- pending | running | done | failed
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

CREATE INDEX idx_dispatch_jobs_status ON dispatch_jobs(status);
```

**Migration plan:**

1. **M0:** Document JSONL path and rotation policy (this file).
2. **M1:** Introduce `storage` module with JSONL append + read helpers.
3. **M2:** SQLite backend behind `DispatchStore` trait; JSONL as export format.
4. **M3:** Workspace membership + `sqlx` migrations in `crates/sidekick-dispatch/migrations/`.

**Test coverage:** `crates/sidekick-dispatch/tests/storage_stubs.rs` (scaffold until crate lands).

---

## sidekick-presence

**Current state:** Vendored from `agent-user-status`; directory gitignored pending cutover.

**Persistence contract:**

- User presence snapshot: JSON file (`~/.sidekick/presence.json`).
- Focus-mode history: optional rotating JSONL (`presence-events.jsonl`).
- launchd plist references state path; no network persistence.

**Schema (presence.json):**

```json
{
  "user_id": "string",
  "status": "available | busy | away | dnd",
  "focus_mode": "boolean",
  "updated_at": "ISO-8601",
  "ttl_seconds": 300
}
```

**Migration plan:**

1. **M0:** Un-ignore crate path after cutover verification (`CUTOVER_STEPS.md`).
2. **M1:** JSON Schema validation on read/write.
3. **M2:** Optional Redis pub/sub for multi-device sync (out of scope for v1).

---

## cheap-llm-mcp

**Current state:** Operational persistence via `Ledger` (JSONL) and `TTLCache` (in-memory).

| Component | Store | Path / scope | Retention |
|-----------|-------|--------------|-----------|
| `Ledger` | Append-only JSONL | Configurable `ledger_path` | Indefinite; monthly cap enforced |
| `TTLCache` | In-memory SHA-256 keyed | Process-local | TTL default 300s, max 256 entries |
| `Config` | YAML file | `~/.config/cheap-llm-mcp/config.yaml` | Manual |

**Ledger entry schema:**

```json
{
  "ts": "ISO-8601",
  "provider": "string",
  "model": "string",
  "input_tokens": 0,
  "output_tokens": 0,
  "cost_usd": 0.0
}
```

**Migration plan:**

1. **M1:** Ledger compaction job (monthly roll-up to `MonthAggregate` sidecar).
2. **M2:** Optional SQLite mirror for query / dashboard use.
3. **M3:** Encrypt ledger at rest when `SIDEKICK_LEDGER_KEY` is set.

**Test coverage:** `crates/cheap-llm-mcp/tests/test_storage_stubs.py`

---

## Cross-crate data boundaries

```
┌─────────────────┐     MCP / HTTP      ┌──────────────────┐
│ sidekick-       │ ──────────────────► │ agent-imessage   │
│ messaging       │   (no local DB)     │ (external)       │
└─────────────────┘                     └──────────────────┘

┌─────────────────┐     JSONL / SQLite  ┌──────────────────┐
│ sidekick-       │ ──────────────────► │ Provider APIs    │
│ dispatch        │                     │ (Claude, etc.)   │
└─────────────────┘                     └──────────────────┘

┌─────────────────┐     JSON file       ┌──────────────────┐
│ sidekick-       │ ──────────────────► │ launchd / OS     │
│ presence        │                     │ notifications  │
└─────────────────┘                     └──────────────────┘

┌─────────────────┐     JSONL + cache   ┌──────────────────┐
│ cheap-llm-mcp   │ ──────────────────► │ LLM providers    │
└─────────────────┘                     └──────────────────┘
```

**Rule:** Crates MUST NOT share database files. Integration is via traits, MCP, or documented file paths under `~/.sidekick/`.

---

## Remediation checklist

- [x] Document per-crate persistence story (this file)
- [x] Add storage test stubs for `sidekick-messaging` and `cheap-llm-mcp`
- [x] Add dispatch storage scaffold for future crate landing
- [ ] Wire `sidekick-dispatch` into workspace `members`
- [ ] Un-ignore `sidekick-presence` after cutover
- [ ] Implement `MessageStore` trait (messaging M1)
- [ ] Add `sqlx` migrations for dispatch (dispatch M2)
- [ ] Ledger compaction (cheap-llm-mcp M1)

**Traceability:** SIDE-DATA-001 … SIDE-DATA-004 in `docs/specs/SPEC.md`
