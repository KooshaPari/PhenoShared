# Observability Wire-Up — Exact Diffs

**Audit pillar:** G-Obs  
**Status:** Additive modules landed; wire-up pending (follow-up PR)  
**Last updated:** 2026-06-26  
**Parent:** [OBSERVABILITY.md](./OBSERVABILITY.md)

This document contains exact diffs to integrate the new `sidekick-obs-core` crate and Python
`health_probe` / `metrics` modules. Apply in a single follow-up PR after this remediation lands.

---

## 1. Workspace membership

**File:** `Cargo.toml`

```diff
 [workspace]
 members = [
     "crates/sidekick-messaging",
+    "crates/sidekick-observability",
+    "crates/sidekick-obs-core",
 ]
```

---

## 2. sidekick-messaging — tracing + correlation

**File:** `crates/sidekick-messaging/Cargo.toml`

```diff
 [dependencies]
 thiserror = { workspace = true }
 serde = { workspace = true, features = ["derive"] }
+tracing = { workspace = true }
+sidekick-obs-core = { path = "../sidekick-obs-core" }
```

**File:** `crates/sidekick-messaging/src/lib.rs` (top of file, after imports)

```diff
+use sidekick_obs_core::{CorrelationContext, NoopMetrics, METRIC_MESSAGING_SEND_TOTAL};
+use tracing::{info, instrument};
```

**File:** `crates/sidekick-messaging/src/lib.rs` (`MessagingAdapter` impl sites)

```diff
+#[instrument(skip(self, message), fields(
+    request_id = %ctx.request_id,
+    trace_id = %ctx.trace_id,
+    provider = %message.provider,
+))]
+fn send_instrumented(&self, message: &Message, ctx: &CorrelationContext) -> Result<String> {
+    let metrics = NoopMetrics;
+    metrics.counter(METRIC_MESSAGING_SEND_TOTAL).inc();
+    info!(op = "send", "messaging.send.start");
+    self.send(message)
+}
```

---

## 3. cheap-llm-mcp — metrics on complete path

**File:** `crates/cheap-llm-mcp/src/cheap_llm_mcp/server.py`

```diff
+from .metrics import METRIC_LLM_COST_USD, METRIC_LLM_REQUESTS, default_registry, RequestTimer
+from .health_probe import build_readiness_response, ComponentProbe
```

Inside `complete()`:

```diff
+    with RequestTimer(default_registry, labels={"provider": provider, "op": "complete"}):
+        default_registry.inc(METRIC_LLM_REQUESTS, labels={"provider": provider})
         result = await r.complete(...)
+    default_registry.inc(METRIC_LLM_COST_USD, value=entry.cost_usd)
```

---

## 4. cheap-llm-mcp — HTTP /health + /ready (optional FastMCP extension)

If FastMCP exposes custom routes, add:

```python
# crates/cheap-llm-mcp/src/cheap_llm_mcp/http_health.py
from .health_probe import HEALTH_PATH, READY_PATH, build_health_response, build_readiness_response, ComponentProbe

_started_at = time.monotonic()

async def health_handler():
  checks = [ComponentProbe("router", "ok")]
  return build_health_response(checks, started_at=_started_at).to_dict()

async def ready_handler():
  # probe providers via Router.health()
  return build_readiness_response(checks).to_dict()
```

Wire in `server.py` when HTTP transport is enabled.

---

## 5. Structured log levels (Python)

**File:** `crates/cheap-llm-mcp/src/cheap_llm_mcp/server.py` — `main()`

```diff
 def main() -> None:
-    setup_json_logging("INFO")
+    level = os.environ.get("CHEAP_LLM_LOG_LEVEL", os.environ.get("SIDEKICK_LOG_LEVEL", "INFO"))
+    setup_json_logging(level)
```

---

## 6. CLI healthcheck (Rust)

After workspace wire-up:

```bash
cargo run -p sidekick-obs-core --bin sidekick-healthcheck
# SIDEKICK_HEALTH_MODE=live for liveness-only JSON
```

---

## 7. New NFR traceability

| ID | Requirement | Module |
|----|-------------|--------|
| SIDE-OBS-005 | Metrics hooks SHALL exist for LLM and messaging | `metrics.py`, `sidekick-obs-core/src/metrics.rs` |
| SIDE-OBS-006 | Health/readiness JSON contracts SHALL be defined | `health_probe.py`, `sidekick-obs-core/src/health.rs` |
| SIDE-OBS-007 | Trace IDs SHALL complement request_id | `sidekick-obs-core/src/correlation.rs` |
| SIDE-OPS-004 | Health probes SHALL be runnable via CLI | `sidekick-healthcheck` binary |

---

## Remediation checklist (this PR)

- [x] `sidekick-obs-core` crate (correlation, health, metrics, log levels)
- [x] `sidekick-healthcheck` CLI binary
- [x] `cheap_llm_mcp.health_probe` module
- [x] `cheap_llm_mcp.metrics` module
- [x] Integration tests for new Python modules
- [ ] Apply diffs in this document (follow-up PR)
