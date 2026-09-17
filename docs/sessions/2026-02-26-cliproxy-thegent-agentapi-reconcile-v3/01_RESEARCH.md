# Research: Open PR Waves — Reconcile Sprint (v3)

## 1. External Research

### 1.1 GitHub API Pagination & Stability

- `gh pr list` uses cursor-based pagination; large result sets (100+ PRs) may intermittently return HTTP 502 during cursor transitions.
- Retry pattern: exponential backoff with max 3 attempts for transient 5xx errors.
- Snapshot-based execution is acceptable fallback when live pagination is unstable.

### 1.2 CodeRabbit Workspace Rate Limits

- Rate limits apply per workspace, not per PR.
- `@coderabbitai full review` triggers async re-review; result is not immediate.
- Batch posting with 2s sleep between calls is sufficient to stay under typical rate limits.

### 1.3 GitHub PR State Model

- `mergeStateStatus`: MERGEABLE, BLOCKED, DIRTY, CONFLICTING, UNKNOWN
- `reviewDecision`: APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED
- A PR is "clean" when: `mergeStateStatus == MERGEABLE` AND `reviewDecision != CHANGES_REQUESTED` AND no failing checks.

## 2. Precedents from Codebase

### 2.1 Stacked PR Governance

- When multiple PRs target the same base, merge order follows dependency chain (leaf → root).
- Re-base onto latest `main` before merging each stacked PR.
- Use GitHub's merge queue feature to automate ordered merges.

### 2.2 Git Worktree for Parallel PR Work

- `git worktree add <path> <branch>` enables parallel PR work without branch switching.
- `git worktree prune` removes stale worktree entries after branch deletion.
- Worktree branches should not be auto-deleted.

## 3. Key Decisions & Rationale

### Decision 1: Snapshot-driven execution over live pagination

**Rationale**: GitHub API 502 errors during cursor pagination caused live listing to fail. A locally cached snapshot of PRs was used instead to continue work.

### Decision 2: Batch CodeRabbit re-review for cliproxyapi-plusplus

**Rationale**: 86 of 101 open PRs in cliproxyapi-plusplus had only CodeRabbit failures. Batch re-review clears the majority of failures without per-PR manual effort.

### Decision 3: Defer live re-check until API is stable

**Rationale**: PR check status can only be verified via live API. Post-execution re-check is deferred until pagination is stable.

## 4. URLs & References

- `https://github.com/KooshaPari/cliproxyapi-plusplus` — 101 open PRs snapshot
- `https://github.com/KooshaPari/thegent` — 8 open PRs, 2 CodeRabbit failures
- `https://github.com/KooshaPari/agentapi-plusplus` — no open PRs
- `https://github.com/KooshaPari/cliproxyapi++` — no open PRs
- `https://github.com/KooshaPari/phenodocs/blob/main/docs/governance/stacked-prs/05-pr-reconciliation.md` — canonical governance doc
