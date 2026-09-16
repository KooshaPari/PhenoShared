# Implementation Strategy: Cleanup Pass (cliproxyapi-plusplus + thegent)

## Technical Approach

Pure GitHub CLI (`gh`) + shell scripting for all operations. No code changes — purely a PR hygiene and audit session.

## Architecture Decisions

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| `gh pr list` + `gh pr checks` | Structured JSON, no auth burden | Direct GitHub REST API |
| CSV matrix output | Human-readable, diffable artifact | JSON blob |
| Deferred cluster wave | CI gates are shared infrastructure | Touch PRs individually now |

## Workflow Details

### CR Re-review Wave
- Filter PRs where `CodeRabbit` check is failing.
- Post `@coderabbitai full review` comment on each.
- Monitor CR queue for drain before retry wave.

### Cluster Wave (deferred)
- Fix shared CI check manifest/gates in `cliproxyapi-plusplus`.
- Do NOT touch per-feature logic until gates are stable.

### thegent Hold/Serialize
- PRs with infra failures (Build Docs, Build wheels, Benchmark, multi-platform Test) held.
- Wait for shared baseline gates to be stable.

## Performance

- `gh` commands are rate-limited by GitHub API (5000 req/hr).
- ~38 PRs audited → well within limits.
- CSV generation is O(n) on PR count.
