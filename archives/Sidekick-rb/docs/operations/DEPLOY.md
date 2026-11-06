# Sidekick — Deployment Guide

**Last updated:** 2026-06-26  
**Remediation:** [OPS.md](../remediation/OPS.md)

---

## Local

### Rust workspace

```bash
cd Sidekick
cargo build --release
cargo test --workspace
```

### cheap-llm-mcp (Python)

```bash
cd crates/cheap-llm-mcp
cp ../../.env.example ../../.env   # add API keys
uv sync
uv run cheap-llm doctor          # health probe
uv run cheap-llm-mcp             # MCP stdio server
```

### Observability smoke

```bash
# Python structured logs (JSON to stderr)
CHEAP_LLM_LOG_LEVEL=DEBUG uv run cheap-llm-mcp

# Rust health CLI (after workspace wire-up)
cargo run -p sidekick-obs-core --bin sidekick-healthcheck
```

---

## Docker

Build and run the MCP server container:

```bash
docker build -f deploy/Dockerfile.cheap-llm-mcp -t sidekick/cheap-llm-mcp:latest .
docker run --rm -i --env-file .env sidekick/cheap-llm-mcp:latest
```

One-shot provider health check:

```bash
docker run --rm --env-file .env --entrypoint cheap-llm sidekick/cheap-llm-mcp:latest doctor
```

Compose (build + optional health profile):

```bash
docker compose -f deploy/docker-compose.yml up --build
docker compose -f deploy/docker-compose.yml --profile health run --rm healthcheck
```

---

## MCP stdio

Sidekick MCP servers use **stdio transport** (no HTTP listener by default).

Configure in Claude Desktop / Cursor MCP settings:

```json
{
  "mcpServers": {
    "cheap-llm": {
      "command": "uv",
      "args": ["--directory", "/path/to/Sidekick/crates/cheap-llm-mcp", "run", "cheap-llm-mcp"],
      "env": {
        "MINIMAX_API_KEY": "<from-env>",
        "CHEAP_LLM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Health via MCP tool: `cheapllm_check_health`  
CLI alternative: `cheap-llm doctor`

---

## Production notes

1. **Secrets:** inject via orchestrator secrets manager; never bake into images.
2. **Logs:** scrape container stdout (JSON lines); filter on `request_id` / `trace_id`.
3. **Health:** use Docker `HEALTHCHECK`, K8s `livenessProbe` → `cheap-llm doctor`, or MCP health tool.
4. **Shutdown:** see [GRACEFUL_SHUTDOWN.md](./GRACEFUL_SHUTDOWN.md); allow ≥10s grace period.
5. **Metrics:** in-process registry in `cheap_llm_mcp.metrics`; expose `/metrics` in follow-up PR.

---

## Related

- [OPS.md](../remediation/OPS.md) — remediation checklist
- [OBSERVABILITY.md](../remediation/OBSERVABILITY.md) — logging and tracing
- [OBSERVABILITY_WIREUP.md](../remediation/OBSERVABILITY_WIREUP.md) — integration diffs
