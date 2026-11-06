# Observability Remediation — Sidekick

**Audit pillar:** G-Obs (33%)  
**Status:** Remediation scaffold — structured logging and tracing contracts.  
**Last updated:** 2026-06-25

## Summary

| Crate | Logging today | Tracing | Metrics | Remediation |
|-------|---------------|---------|---------|-------------|
| `sidekick-messaging` | None | None | None | `sidekick-observability` crate + integration tests |
| `sidekick-dispatch` | None (not in tree) | None | None | Wire on crate landing |
| `sidekick-presence` | Python stdlib (expected) | None | None | Document in cutover |
| `cheap-llm-mcp` | JSON structured (`logging_util`) | None | Ledger aggregates | `observability.py` span helpers |

---

## Target architecture

```
Application code
       │
       ▼
┌──────────────────┐     ┌─────────────────┐
│ tracing (Rust)   │     │ structlog-style │
│ or logging_util  │────►│ JSON stdout     │
│ (Python)         │     │ (single line)   │
└──────────────────┘     └─────────────────┘
       │                           │
       ▼                           ▼
  OpenTelemetry              Log aggregator
  (future)                   (Loki / CloudWatch)
```

**Principles:**

1. **Structured by default** — every log line is JSON with `ts`, `level`, `crate`, `op`, `request_id`.
2. **No secrets in logs** — hash or truncate recipient, token, and prompt fields.
3. **Correlation** — propagate `request_id` across MCP and dispatch boundaries.
4. **Opt-in verbosity** — `RUST_LOG` / `CHEAP_LLM_LOG_LEVEL` env vars.

---

## sidekick-messaging (Rust)

**Gap:** Crate emits no logs or spans.

**Remediation (implemented):**

- New crate: `crates/sidekick-observability/` — `init_tracing()` with `tracing-subscriber` JSON fmt.
- Integration contract tests: `crates/sidekick-messaging/tests/observability_stubs.rs`
- Wire-in step (follow-up PR): add to `sidekick-messaging/Cargo.toml`:

```toml
tracing = { workspace = true }
sidekick-observability = { path = "../sidekick-observability" }
```

Then at library entry or binary `main`:

```rust
sidekick_observability::init_tracing("sidekick-messaging", "info");
```

**Required span fields:**

| Field | Example | Notes |
|-------|---------|-------|
| `crate` | `sidekick-messaging` | Static per binary |
| `op` | `send`, `is_available` | Operation name |
| `provider` | `iMessage` | Enum display |
| `recipient_hash` | `sha256:abc…` | Never log raw recipient |

---

## sidekick-dispatch (Rust, pending)

On crate landing:

1. Depend on `sidekick-observability`.
2. Span per dispatch: `dispatch.start`, `dispatch.provider_select`, `dispatch.complete`.
3. Log provider failures at `WARN`, cap breaches at `ERROR`.

---

## sidekick-presence (Python, pending)

On cutover:

1. Reuse `cheap_llm_mcp.logging_util.JsonFormatter` or extract shared `sidekick_logging` package.
2. Log presence transitions at `INFO`; focus-mode changes at `DEBUG`.
3. Health endpoint: `GET /health` returning `{"status":"ok","updated_at":"…"}`.

---

## cheap-llm-mcp (Python)

**Current:** `logging_util.setup_json_logging()` + `request_scope()` for `request_id`.

**Remediation (implemented):**

- `src/cheap_llm_mcp/observability.py` — `operation_span()` context manager, standard field names.
- Tests: `tests/test_observability_stubs.py`

**Usage:**

```python
from cheap_llm_mcp.observability import operation_span

with operation_span("router.complete", provider="minimax", model="M2"):
    result = await router.complete(prompt)
```

**Standard fields:** `op`, `provider`, `model`, `request_id`, `duration_ms`, `input_tokens`, `output_tokens`.

---

## sidekick-observability crate

Location: `crates/sidekick-observability/`

Provides:

- `init_tracing(crate_name, default_level)` — env-filter + JSON subscriber
- `init_tracing_plain(crate_name, default_level)` — human-readable dev mode

**Workspace wiring (follow-up):** Add to root `Cargo.toml`:

```toml
members = [
    "crates/sidekick-messaging",
    "crates/sidekick-observability",
]
```

---

## Monitoring roadmap (K-Ops alignment)

| Phase | Deliverable | Pillar |
|-------|-------------|--------|
| P0 | Structured JSON logs (this remediation) | G-Obs |
| P1 | Health check binaries / MCP tools | K-Ops |
| P2 | Prometheus metrics (`dispatch_total`, `llm_cost_usd`) | K-Ops |
| P3 | OpenTelemetry trace export | G-Obs |
| P4 | SLO dashboards (dispatch latency p99, ledger cap) | K-Ops |

---

## Remediation checklist

- [x] Document observability contracts (this file)
- [x] Add `sidekick-observability` reference crate
- [x] Add `cheap-llm-mcp` observability helpers
- [x] Add observability integration test stubs
- [ ] Wire `sidekick-observability` into workspace members
- [ ] Instrument `MessagingAdapter::send` with spans
- [ ] Add `/health` to MCP servers
- [ ] Prometheus exporter (dispatch + ledger)

**Traceability:** SIDE-OBS-001 … SIDE-OBS-003 in `docs/specs/SPEC.md`
