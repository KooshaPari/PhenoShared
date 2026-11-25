# AX — Agent experience (SOTA)

## Use case

Agents (Cursor, forge `-p`, Claude Code, Codex) bootstrap and maintain repos using HexaKit genesis docs.

## Requirements

| Req | Weight |
|-----|--------|
| Deterministic intent from session logs | must |
| Charter/review loaded before mutating | must |
| OKF chunking for RAG | should |
| Subagent → forge fanout for long tasks | should |

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| README-only scope | Rejected — agents ignore |
| AGENTS.md alone | Rejected — no SOTA/review linkage |
| Backstage/Cortex service catalog | Rejected — overkill for git-native org |
| **Genesis doc set + OKF** | **Chosen** |

## Chosen strategy

- `templates/genesis/` copied on `hexakit genesis init`
- `scripts/extract-intent-prompts.py` for provenance
- Manager pattern: Cursor subagent → `forge -p` workers (see forge-fanout skill)

## Orchestration topology

```
User
 └── Cursor parent (Composer)
      ├── Subagent A — templates / specs (manager horizon: hours)
      │    └── forge -p lane A1, A2 — scrape, SOTA research
      ├── Subagent B — intent extraction
      └── Subagent C — registry / fleet rollout
```

## Evolution triggers

- New agent tool (add `prompts/<tool>/` + scraper module)
