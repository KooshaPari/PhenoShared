# Graceful Shutdown — Sidekick

**Last updated:** 2026-06-26  
**Remediation:** [OPS.md](../remediation/OPS.md)

Sidekick components are libraries and MCP servers. Shutdown behavior differs by runtime.

---

## cheap-llm-mcp (Python MCP server)

### Current behavior

`server.py` `main()`:

```python
def main() -> None:
    setup_json_logging("INFO")
    try:
        mcp.run()
    finally:
        if _router is not None:
            asyncio.run(_router.aclose())
```

- **SIGINT / SIGTERM** (Ctrl+C, Docker stop) terminates the FastMCP event loop.
- The `finally` block closes the HTTP client pool via `Router.aclose()`.
- In-flight MCP tool calls should complete or raise; no explicit drain timeout today.

### CLI (`cheap-llm`)

`_run()` and `_doctor()` wrap router usage:

```python
try:
    ...
finally:
    await r.aclose()
```

### Recommendations

| Context | Action |
|---------|--------|
| Docker | `STOPSIGNAL SIGTERM`, `stop_grace_period: 10s` (see `deploy/docker-compose.yml`) |
| K8s | `terminationGracePeriodSeconds: 15`, `preStop` optional |
| Local | Ctrl+C once; wait for `aclose` log line |

### Follow-up (wire-up diff)

Add signal handlers for explicit drain:

```python
import signal

def _shutdown_handler(signum, frame):
    log.info("shutdown.signal", extra={"signal": signum})
    # trigger mcp shutdown if API supports it

signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)
```

---

## sidekick-messaging (Rust library)

No long-running server. Consumers SHOULD:

1. Drop in-flight `MessagingAdapter` calls before process exit.
2. Flush tracing subscribers (`tracing_subscriber` flushes on drop).

---

## sidekick-obs-core / sidekick-healthcheck

Stateless CLI. Exits immediately after printing JSON health report. No shutdown hook required.

---

## Docker

Root `Dockerfile` and `deploy/Dockerfile.cheap-llm-mcp`:

- `STOPSIGNAL SIGTERM` — orchestrators send SIGTERM before SIGKILL
- `HEALTHCHECK` — failing health does not block shutdown
- Non-root `sidekick` user — no privilege escalation on stop

---

## Checklist for operators

- [ ] Set `stop_grace_period` ≥ 10s for MCP containers
- [ ] Confirm logs show clean exit (no orphaned httpx warnings)
- [ ] Do not `kill -9` during active LLM completions (ledger may be mid-write)
- [ ] Use `cheap-llm doctor` before deploy to verify provider connectivity
