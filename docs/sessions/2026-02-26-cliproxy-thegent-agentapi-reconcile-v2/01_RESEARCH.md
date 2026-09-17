# Research: CLIProxy++, thegent, agentapi++ PR Reconciliation (v2)

## 1. External Research

### GitHub API & CLI Patterns

- **`gh pr list`** — paginated open PR listing; `--json` + `--jq` for shell-parsable output.
- **`gh pr checks <n>`** — per-PR status; combines check runs + status contexts.
- **`gh pr view <n> --json reviewDecision,mergeStateStatus,comments,reviews`** — full state including merge metadata and comment threads.
- **`gh pr comment <n> --body "@coderabbitai full review"`** — re-triggers CodeRabbit review on a PR.

### CodeRabbit Integration

- CodeRabbit reviews are bot-generated and subject to rate limits per workspace.
- `@coderabbitai full review` re-triggers the full review pipeline.
- CodeRabbit failures on PRs are the dominant merge blocker across all four repos.
- Review-rate-limit exceeded errors are transient; retry after cooldown.

### Git Workflow Patterns

- **Local branch vs. remote head**: `headRefName` maps remote branch to local branch name.
- **Worktree management**: `git worktree prune` cleans stale worktree references.
- **Branch deletion safety**: only delete after confirming upstream PR is closed/merged.
- **`.airlock` pattern**: indicator file marking a branch in a locked/paused state.

## 2. Precedents from Codebase

### Shared CI Failure Patterns

| Repo | Failure class | Root cause |
|------|---------------|------------|
| `cliproxyapi-plusplus` | `Analyze (Go)` + `build` | Lint/template drift in Go CI workflow |
| `cliproxyapi-plusplus` | `verify-required-check-names` | Workflow name vs. manifest mismatch |
| `cliproxyapi-plusplus` | `Build Docs` | Sphinx/Docsy build failure |
| `cliproxyapi-plusplus` | `CodeQL` | Static analysis violations |
| `thegent` | `Build wheels`, `Build Docs`, `Comprehensive Benchmark` | Platform-specific infra stack failures |
| `agentapi-plusplus` | Mixed `CodeRabbit` + infra | Bot review rate limits + test infra |

### Branch Naming Conventions Observed

- `archive/*` — completed/stale migration branches
- `ci/*`, `ci-fix/*` — CI repair branches
- `migrated/*`, `replay/*`, `reintegrate/*` — stacked migration tooling branches
- `feat/*`, `feature/*` — feature work
- `fix/*` — bug fixes
- `garden/*` — exploratory/stabilization branches
- `stack/*` — agent-api stacked PRs
- `tmp-*` — temporary实验 branches

### Merge State Taxonomy

| State | Meaning | Action |
|-------|---------|--------|
| `MERGEABLE` | Ready to merge if checks pass | Promote if checks green |
| `BLOCKED` | Checks failing or reviews pending | Fix checks/reviews |
| `DIRTY` | Merge conflicts present | Rebase/resolve |
| `CONFLICTING` | Git conflicts with base | Rebase onto latest main |
| `UNKNOWN` | PR already merged or state indeterminate | Skip |

## 3. Key Decisions and Rationale

### Decision 1: Batch-first stabilization over per-PR chase

**Rationale**: The root cause of most check failures is shared template/workflow drift rather than per-PR bugs. Fix the template once, propagate to all affected PRs via base-branch update.

### Decision 2: CodeRabbit re-review before manual review

**Rationale**: 86 of 96 failing PRs in `cliproxyapi-plusplus` had only CodeRabbit failures. Re-triggering bot review is cheaper than manual review and clears most debt automatically.

### Decision 3: No force-delete of canonical branches

**Rationale**: `main` branches across all repos have uncommitted local edits. Forcing resets would lose work. Use rebase/merge instead.

### Decision 4: Offline-safe execution until `gh auth` is valid

**Rationale**: `gh auth` was invalid during the session. All branch inventory and planning was done locally. Live operations deferred until auth restored.

## 4. URLs & References

- `https://github.com/KooshaPari/cliproxyapi-plusplus`
- `https://github.com/KooshaPari/cliproxyapi++`
- `https://github.com/KooshaPari/thegent`
- `https://github.com/KooshaPari/agentapi-plusplus`
- `https://github.com/KooshaPari/template-commons` (source of shared workflows)
