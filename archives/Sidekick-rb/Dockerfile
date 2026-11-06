# syntax=docker/dockerfile:1

# Sidekick workspace — cheap-llm-mcp MCP server
# Build: docker build -f Dockerfile -t sidekick:latest .
# Run:   docker run --rm -i --env-file .env sidekick:latest

# ── Stage 1: build Python package ────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY crates/cheap-llm-mcp/pyproject.toml crates/cheap-llm-mcp/uv.lock ./
COPY crates/cheap-llm-mcp/src ./src

RUN uv pip install --system --no-cache .

# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /bin/bash sidekick
USER sidekick
WORKDIR /home/sidekick

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/cheap-llm-mcp /usr/local/bin/cheap-llm-mcp
COPY --from=builder /usr/local/bin/cheap-llm /usr/local/bin/cheap-llm

ENV PYTHONUNBUFFERED=1 \
    CHEAP_LLM_LOG_LEVEL=INFO \
    SIDEKICK_LOG_JSON=true

# MCP stdio transport — no exposed ports by default
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD cheap-llm doctor || exit 1

ENTRYPOINT ["cheap-llm-mcp"]
