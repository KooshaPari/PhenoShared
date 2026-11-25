# ARCHIVED — `<REDACTED>/zen`

## Tombstone (user absolute-path allowed)

| field | value |
|-------|-------|
| source | `<REDACTED>/zen` (Public, deprecated minimal template, 2025-04-03) |
| absorbed into | `HexaKit/` (governance + bifrost + 46 crates supersede the zen template) |
| absorbed date | 2026-04-03 (per `projects/zen.json`: 'functionality in HexaKit') |
| docket | `phenotype-registry/docs/absorption/zen/SUPERSEDES.md` |
| target evidence | `HexaKit/bifrost/` + `HexaKit/python/src/agileplus_mcp/tools/governance.py` + `HexaKit/docs/adr/2026-06-20/ADR-050-absorb-l72-l73-l74-governance-tools.md` |
| source clone | `~/.forge/audit/repo-evidence/zen` (deep-verified) |

## Diff summary (source vs target)

- Source: `~/.forge/audit/repo-evidence/zen/` (5 files: SPEC.md, README.md, mise.toml, .gitignore, TODO.md — pure template)
- Target: `HexaKit/` — 46+ crates, 20+ governance files, full Bifrost transport, full AgilePlus MCP server
- Result: **HexaKit completely supersedes zen** — zen is a deprecated minimal template; its content (3 commits, 5 files, no code) is absorbed by HexaKit's full superset
- Source-side: GH-archived (per registry); cloned in this session for audit verification

## Status

Source-side: GH-archived (per registry). Cloned in this session for audit verification.

Target-side: HexaKit is the documented replacement per `projects/zen.json`. zen described
itself as "DEPRECATED: Minimal template — functionality in <REDACTED>/HexaKit."

User approved on 2026-07-28: *"zen Y"* + *"proc w\ all nxt"* (apply all pending).
