# Stack defaults

**Status:** adopted · **Applies to:** new projects and major rewrites.

## Default choices

| Layer | Default | Notes |
|-------|---------|-------|
| JS/TS frontend | **TanStack** (Router/Query/etc.) | Start here unless a project has a specific reason not to. |
| Python MCP servers | **FastMCP** | Standard way to expose MCP tools from Python. |
| Docs sites | **VitePress** | Markdown-first docs (this handbook included). |
| .NET tests | **xUnit** | Standard test framework for .NET work. |
| New tooling | **Rust or Go** | Preferred for new CLIs/services/tooling. |

Deviating from a default is allowed but should be a deliberate, noted decision (an ADR in PhenoSpecs for anything load-bearing).

## Config & secrets

- **All config and secrets via `.env`.** Never hardcode secrets, ports, or URLs in source.
- Commit a `.env.example` with every key documented; **`.env` is gitignored.**
- Secrets come from the environment at runtime, not from the repo.

## Why

A small set of defaults means every repo is legible to anyone in the org and to agents; the `.env` rule keeps secrets out of git history and makes ports/URLs environment-specific without code changes.
