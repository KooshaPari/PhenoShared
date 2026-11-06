# Operations & Deploy Remediation — Sidekick

**Audit pillar:** K-Ops (L27 Infrastructure 35%, L29 Monitoring 30%)  
**Status:** Docker, env templates, and deploy docs added  
**Last updated:** 2026-06-26

## Summary

| Area | Before | After (this remediation) |
|------|--------|---------------------------|
| Dockerfile | None | Multi-stage `Dockerfile` + `deploy/Dockerfile.cheap-llm-mcp` |
| Health checks | MCP tool only | CLI `doctor`, `sidekick-healthcheck`, Docker `HEALTHCHECK` |
| Env template | Crate-local only | Root `.env.example` + existing `cheap-llm-mcp/.env.example` |
| Deploy docs | None | `docs/operations/DEPLOY.md` |
| Graceful shutdown | Partial (`aclose` in CLI) | `docs/operations/GRACEFUL_SHUTDOWN.md` |
| Compose | None | `deploy/docker-compose.yml` |

---

## Stack

| Component | Runtime | Deploy unit |
|-----------|---------|-------------|
| `sidekick-messaging` | Rust library | Embedded in consumers |
| `sidekick-obs-core` | Rust library + CLI | Sidecar health probe |
| `cheap-llm-mcp` | Python 3.12 + FastMCP | Container / MCP stdio |

---

## Environment variables

See root [`.env.example`](../../.env.example) and [`crates/cheap-llm-mcp/.env.example`](../../crates/cheap-llm-mcp/.env.example).

| Variable | Component | Default | Purpose |
|----------|-----------|---------|---------|
| `RUST_LOG` | Rust | `sidekick-messaging=info` | Tracing filter |
| `SIDEKICK_LOG_LEVEL` | All | `info` | Unified log level override |
| `SIDEKICK_LOG_JSON` | Rust | `true` | JSON vs plain logs |
| `CHEAP_LLM_LOG_LEVEL` | Python MCP | `INFO` | Python log level |
| `MINIMAX_API_KEY` | cheap-llm-mcp | — | Provider auth |
| `MOONSHOT_API_KEY` | cheap-llm-mcp | — | Provider auth |
| `FIREWORKS_API_KEY` | cheap-llm-mcp | — | Provider auth |
| `SIDEKICK_SERVICE` | healthcheck | `sidekick` | Health JSON service name |
| `SIDEKICK_HEALTH_MODE` | healthcheck | `ready` | `live` or `ready` |

**Never commit secrets.** Copy `.env.example` → `.env` locally; use CI secrets for deploy.

---

## Docker

### Build cheap-llm-mcp (from repo root)

```bash
docker build -f deploy/Dockerfile.cheap-llm-mcp -t sidekick/cheap-llm-mcp:latest .
```

### Run (stdio MCP — typical for Claude Desktop / Cursor)

```bash
docker run --rm -i \
  --env-file .env \
  sidekick/cheap-llm-mcp:latest
```

### Health check

```bash
# In-container probe (exits 0 when providers respond)
docker run --rm --env-file .env sidekick/cheap-llm-mcp:latest cheap-llm doctor
```

Docker `HEALTHCHECK` runs `cheap-llm doctor` every 30s (see Dockerfile).

---

## Deploy paths

| Target | Doc | Notes |
|--------|-----|-------|
| Local dev | [DEPLOY.md](../operations/DEPLOY.md#local) | `uv run`, `cargo test` |
| Docker | [DEPLOY.md](../operations/DEPLOY.md#docker) | Multi-stage image |
| MCP stdio | [DEPLOY.md](../operations/DEPLOY.md#mcp-stdio) | No HTTP port required |
| CI | `.github/workflows/ci.yml` | fmt, clippy, test |

---

## Graceful shutdown

See [GRACEFUL_SHUTDOWN.md](../operations/GRACEFUL_SHUTDOWN.md).

Key points:

- `cheap-llm-mcp` `main()` calls `_router.aclose()` in `finally`
- CLI `_run()` uses `try/finally` with `await r.aclose()`
- Docker: send `SIGTERM`, allow 10s (`STOPSIGNAL SIGTERM`, `stop_grace_period`)

---

## Monitoring alignment (G-Obs + K-Ops)

| Signal | Source | Export |
|--------|--------|--------|
| Structured logs | `logging_util`, `sidekick-observability` | stdout JSON |
| Request correlation | `request_id`, `trace_id` | Log fields |
| Metrics | `cheap_llm_mcp.metrics` | Prometheus text (in-process) |
| Health | `cheapllm_check_health` MCP tool, `cheap-llm doctor` | JSON |
| Readiness | `health_probe.build_readiness_response` | `/ready` (wire-up) |

---

## Remediation checklist

- [x] Multi-stage Dockerfile with HEALTHCHECK
- [x] `docker-compose.yml` for local smoke
- [x] Root `.env.example` (no secrets)
- [x] Deploy documentation
- [x] Graceful shutdown documentation
- [x] `sidekick-healthcheck` CLI binary
- [ ] Wire `sidekick-obs-core` into workspace (see OBSERVABILITY_WIREUP.md)
- [ ] HTTP `/metrics` endpoint (Prometheus scrape)
- [ ] K8s manifests (deferred — library-first repo)

**Traceability:** SIDE-OPS-004 … SIDE-OPS-006 in wire-up NFR table

---

## Follow-up diffs (not applied — additive-only PR)

### Root `justfile` — add health target

```diff
+health:
+    cd crates/cheap-llm-mcp && uv run cheap-llm doctor
+    cargo run -p sidekick-obs-core --bin sidekick-healthcheck
```

### `ci.yml` — optional health smoke

```diff
+      - name: Health probe smoke
+        run: cargo run -p sidekick-obs-core --bin sidekick-healthcheck
```
