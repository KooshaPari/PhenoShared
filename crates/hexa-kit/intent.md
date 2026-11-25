# Intent — HexaKit

## Problem statement

The Phenotype org has dozens of repos with duplicated governance, unclear scope (especially HexaKit as both template shelf and crate warehouse), and no deterministic record of **why** each project exists. Agents cannot reliably infer user goals or enforce consistent PR review.

## Success criteria

- [ ] Every new repo bootstraps `intent.md`, `charter.md`, `review.md`, `SOTA.md`, `okf/`, `docs/intent/`, `docs/sota/`
- [ ] User prompts recoverable from Cursor / forge / Claude / Codex session logs
- [ ] HexaKit charter restricts it to **genesis**; domain code lives in SDK workspaces
- [ ] Kilo Code Stand applied on all PRs via `review.md`

## Non-goals

See [charter.md](charter.md). HexaKit does **not** own telemetry, auth, MCP, or full linters.

## Originating prompts

| Date | Tool | Session | Summary |
|------|------|---------|---------|
| 2026-06-16 | cursor | b561a593… | [genesis standard + scrape requirement](docs/intent/prompts/cursor/20260616-genesis-standard-manual.md) |
| 2026-06-16 | cursor | b561a593… | [HexaKit = scaffolding not lib collection](docs/intent/prompts/cursor/20260616-genesis-standard-manual.md) |
| 2026-06-16 | cursor | b561a593… | [subagent + forge -p orchestration](docs/intent/prompts/cursor/20260616-genesis-standard-manual.md) |

Refresh: `python scripts/extract-intent-prompts.py --out-dir docs/intent/prompts --repo HexaKit`

## Synthesized goals

[docs/intent/synthesis.md](docs/intent/synthesis.md)

**Confirmed:**

1. Per-repo genesis doc set with OKF + LLM wiki adaptations
2. HexaKit = templates/scaffolding; SDKs = domain with optional installs
3. Intent prompts scraped verbatim from four agent tools

**Inferred (validate):**

1. `phenotype-rust-sdk` should absorb transitional `crates/` from HexaKit
2. `hexakit genesis init` CLI should copy `templates/genesis/`

## Agent assumptions log

| Assumption | Action | Validated? |
|------------|--------|------------|
| User wants fleet-wide template in HexaKit first | Created `docs/genesis/` + `templates/genesis/` | pending |
| RATIONALIZATION_PLAN HexaKit-as-all-rust-crates is wrong | New charter + SOTA note | pending |
