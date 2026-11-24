# AX — Agent experience (SOTA)

## Use case

Agents (Cursor, forge `-p`, Claude Code, Codex) bootstrap, review, and maintain this repo using genesis docs and org skills.

## Requirements

| Req | Weight |
|-----|--------|
| Deterministic intent from session logs | must |
| Charter/review loaded before mutating scope | must |
| OKF chunking for RAG context | should |
| Subagent → forge fanout for long parallel work | should |
| Doc-only PRs avoid heavy build gates | should (genesis repos) |

## Context load order

1. [charter.md](../../../charter.md)
2. [review.md](../../../review.md)
3. [intent.md](../../../intent.md) + [../intent/synthesis.md](../intent/synthesis.md)
4. Relevant [docs/sota/](.) slice
5. [okf/manifest.okf.yaml](../../../okf/manifest.okf.yaml)

## Session log locations (intent scrape)

| Tool | Path |
|------|------|
| Cursor | `~/.cursor/projects/<project>/agent-transcripts/*.jsonl` |
| forge | `forge conversation export` |
| Claude | `~/.claude/projects/` |
| Codex | `~/.codex/` |

See [../intent/prompts/README.md](../intent/prompts/README.md).

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| README-only scope | Rejected — agents ignore informal scope |
| AGENTS.md alone | Rejected — no SOTA/review linkage |
| Backstage / Cortex service catalog | Rejected — overkill for git-native org |
| Ad-hoc per-session prompts | Rejected — no provenance |
| **Genesis doc set + OKF + scraper** | **Chosen** |

## Chosen strategy

- Copy [`templates/genesis/`](https://github.com/KooshaPari/HexaKit/tree/main/templates/genesis) at bootstrap
- Run `scripts/extract-intent-prompts.py` after significant sessions
- Manager pattern: Cursor subagent → `forge -p` workers for parallel lanes (forge-fanout skill)
- Kilo Code Stand enforces scope on every PR

## Failure modes and mitigations

| Failure | Mitigation |
|---------|------------|
| Scope creep | charter Block tier in review.md |
| Lost user intent | scrape prompts before large pivots |
| Branch / worktree conflicts | parallel-worktrees skill; single canonical merge |
| Build gate on doc PRs | ops.md targeted smoke only |

## Evolution triggers

- New agent tool → add `prompts/<tool>/` + scraper module
- Fleet changes `kilo-code-stand@1` → update review.md across repos
