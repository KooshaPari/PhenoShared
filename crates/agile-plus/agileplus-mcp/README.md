# agileplus-mcp

FastMCP 3.0 bridge from LLM tooling (Claude, Cursor, IDE agents) to the
AgilePlus spec-driven development engine. Exposes feature, governance, and
status capabilities as Model Context Protocol tools, backed by a gRPC client to
the AgilePlus Rust core.

## Overview

`agileplus-mcp` is a Python service built on [FastMCP](https://github.com/jlowin/fastmcp)
that turns AgilePlus into a first-class context source for LLM agents. It
publishes a stable MCP tool surface (feature lookup, work-package inspection,
governance contract checks, hash-chained audit verification, dashboard /
metrics) so agents can drive AgilePlus workflows without coupling to its
internal storage or transport.

The service is intentionally thin: tool handlers validate inputs, call the
Rust core over gRPC, and shape responses. All durable state lives in the Rust
core.

Status: scaffolding. Tool signatures are stable; bodies currently return
`{"error": "not_implemented"}` until the gRPC stubs land (tracked under WP14).

## Architecture

```
+---------------------+        MCP (stdio / HTTP)        +-------------------+
|  LLM agent client   | <------------------------------> |  agileplus-mcp    |
|  (Claude / IDE)     |                                  |  (FastMCP 3.0)    |
+---------------------+                                  +---------+---------+
                                                                   |
                                                                   | gRPC
                                                                   v
                                                          +-------------------+
                                                          |  AgilePlus core   |
                                                          |  (Rust, :50051)   |
                                                          +-------------------+
```

Key modules under `src/agileplus_mcp/`:

- `server.py` - constructs the `FastMCP` instance and registers tool modules.
- `__main__.py` - entry point for `python -m agileplus_mcp`.
- `tools/features.py` - `get_feature`, `list_features`, `get_work_packages`,
  `get_work_package`, `get_tasks`.
- `tools/governance.py` - `check_governance`, `get_audit_trail`,
  `verify_audit_chain`, `get_governance_rules`.
- `tools/status.py` - `get_dashboard`, `get_metrics`, `health_check`.
- `grpc_client.py` - `AgilePlusCoreClient` (default target `localhost:50051`).
- `prompts/`, `resources/`, `sampling/` - reserved for future MCP surfaces.

Telemetry is wired through OpenTelemetry (`opentelemetry-sdk`,
`opentelemetry-exporter-otlp`); request validation uses Pydantic v2.

## Install

Requires Python 3.12 (`.python-version` pins `3.12`) and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/KooshaPari/agileplus-mcp.git
cd agileplus-mcp
uv sync
```

For development extras (pytest, ruff, mypy, behave, pact, sphinx):

```bash
uv sync --extra dev
```

### Docker

```bash
docker build -t agileplus-mcp .
docker run --rm -i agileplus-mcp
```

The image installs production dependencies via `uv sync --no-dev` and runs
`uv run python -m agileplus_mcp` as its entrypoint.

## Usage

Run the MCP server over stdio (the default FastMCP transport):

```bash
uv run python -m agileplus_mcp
```

Register it with an MCP-aware client (example: Claude Desktop
`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agileplus": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/agileplus-mcp",
               "python", "-m", "agileplus_mcp"]
    }
  }
}
```

### Example tool call

A connected agent can invoke any registered tool by name. Example MCP
`tools/call` request for the health probe:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "health_check",
    "arguments": {}
  }
}
```

Response (current scaffold output):

```json
{
  "status": "healthy",
  "mcp_server": "ok",
  "grpc_core": "unreachable",
  "version": "0.1.0"
}
```

A feature lookup looks like:

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_feature",
    "arguments": { "slug": "001-spec-engine" }
  }
}
```

The gRPC core address is configurable in code via
`AgilePlusCoreClient(host=..., port=...)`; defaults are `localhost:50051`.

## Development

All workflows go through `uv`:

```bash
uv sync --extra dev          # install dev deps
uv run pytest                # run unit tests (tests/unit/)
uv run pytest --cov=agileplus_mcp
uv run ruff check src tests  # lint
uv run ruff format src tests # format
uv run mypy src              # strict type-check (per pyproject)
```

Pytest is configured (`pyproject.toml`) with `asyncio_mode = "auto"` and
`testpaths = ["tests"]`. BDD scaffolding lives under `tests/bdd/` (behave) and
contract tests under `tests/contract/` (pact-python); both are placeholder
directories today.

Documentation source is under `docs/` (Sphinx, `docs/conf.py`,
`docs/index.rst`); build with `uv run sphinx-build docs docs/_build`.

## License

Apache License 2.0. See repository headers; SPDX identifier `Apache-2.0`.
