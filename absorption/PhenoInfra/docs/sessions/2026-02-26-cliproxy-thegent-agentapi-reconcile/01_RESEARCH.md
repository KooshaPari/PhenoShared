# Research: PR Reconciliation Audit Snapshot (v1)

## 1. External Research

### GitHub CLI Patterns

- `gh pr list` — lists open PRs; `--json` for structured output.
- `gh pr checks <n>` — per-PR status combining check runs + status contexts.
- `gh pr view <n> --json reviewDecision,mergeStateStatus,comments,reviews` — full PR state.
- `gh pr comment <n> --body "@coderabbitai full review"` — re-triggers CodeRabbit.

### Git Worktree Management

- `git worktree add <path> <branch>` — parallel PR work without switching branches.
- `git worktree prune` — removes stale worktree references.

## 2. Precedents from Codebase

### PR Failure Patterns

- `cliproxyapi-plusplus`: stacked migration PRs, CI/build/lint failures.
- `thegent`: infra gates failing, review thread debt.
- `agentapi-plusplus`: CodeRabbit rate limits, merge conflicts.

### Worktree Usage

- Many stale worktrees across repos; `git worktree prune` cleans them.
- Prunable worktrees should be reconciled but not force-deleted.

## 3. Key Decisions

### Decision 1: Worktree prune before any branch cleanup

**Rationale**: Stale worktrees can cause confusion in branch listings. Clean them first.

### Decision 2: Re-review trigger before merge

**Rationale**: Bot reviews are cheaper than manual; clear them first.

## 4. URLs & References

- `https://github.com/KooshaPari/cliproxyapi-plusplus`
- `https://github.com/KooshaPari/thegent`
- `https://github.com/KooshaPari/agentapi-plusplus`
