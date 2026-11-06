# Changelog

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## 0.4.0 — 2026-04-22 (audit pass 8)

### Added
- `logging_util.py`: JSON formatter + `request_scope()` contextvar for request_id correlation.
- `complete()` MCP tool now emits structured `complete.start` / `complete.done` logs with request_id + usage + cost; returns `request_id` in response.
- Server bootstrap switches to structured JSON logging via `setup_json_logging()`.

### Metrics
- 37 tests passing (+4 new logging tests). Ruff + format clean.

## 0.3.0 — 2026-04-22 (audit pass 3)

### Added
- `cheap-llm doctor` subcommand: health-probes all providers, shows month-to-date cost + cap remaining.
- `ruff.toml` with strict lint rules (E, F, I, B, UP, SIM, RUF).
- Ruff auto-formatter applied; `ruff check` + `ruff format --check` both clean.

### Changed
- Imports updated to modern idioms: `collections.abc` for `AsyncIterator`/`Awaitable`/`Callable`, `datetime.UTC` instead of `timezone.utc`.

## 0.2.0 — 2026-04-22 (audit pass 1)

### Added
- TTL response cache (`cache.py`) for repeated temp=0 queries — disabled by default; enable via `cache_ttl_seconds` in config.
- TOML config schema validation: required-keys check, helpful error messages with file path and provider name.
- Streaming path tests (SSE chunk aggregation, non-JSON line tolerance).
- `.env.example` with all three provider keys.
- `tests/conftest.py` auto-sets fake keys for provider fixtures.

### Fixed
- `router.py` threads the cache through from config; TTL=0 disables.

### Metrics
- 30 passing tests (up from 12 → 18 → 30 across audit passes).

## 0.1.0 — 2026-04-22

Initial scaffold.

### Added
- FastMCP server exposing `complete`, `stream_complete`, `providers`, `list_live_models`, `health`, `cost_summary` tools.
- OpenAI-compatible provider client (shared across Minimax, Kimi, Fireworks).
- Router with auto-provider selection + fallback chain.
- Exponential-backoff retry on 408/425/429/5xx + transient httpx errors.
- Append-only JSONL cost ledger with monthly-cap enforcement.
- CLI (`cheap-llm`) for direct terminal use, stream + non-stream modes.
- `cheap-llm` skill registered in `~/.claude/skills/`.
- `cheap-reasoner` subagent template in `claude/agents/`.
- Defaults wired to **MiniMax-M2.7 / MiniMax-M2.7-highspeed** (verified live, April 2026). No dedicated `-codex` variant exists — M2.7 is strong at code already.
- Fireworks mirror: `accounts/fireworks/models/minimax-m2p7` and `kimi-k2-instruct`.
- 12 unit tests covering router fallback, ledger, retry.

### Motivation
Anthropic has tightened detection of third-party clients on Max subscription OAuth tokens. Intercepting Haiku calls via a local proxy carries medium-high account-action risk. This server keeps Claude Code's own API traffic untouched; subagents route cheap work through MCP tool calls instead of replacing the model.
