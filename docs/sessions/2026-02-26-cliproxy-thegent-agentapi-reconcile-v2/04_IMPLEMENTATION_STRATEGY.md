# Implementation Strategy: PR Reconciliation (v2)

## 1. Technical Approach

### 1.1 GitHub CLI Wrapper Pattern

All GitHub API interactions use `gh` CLI as the primary interface. Each command is wrapped in a shell function that:
1. Checks `gh auth status` before any write operation.
2. Captures stderr for error classification (auth failure vs. rate limit vs. not found).
3. Returns structured output (JSON) for downstream parsing.
4. Times out after 30s per call to prevent session hangs.

### 1.2 Batch Execution Strategy

- **CodeRabbit re-review**: iterate PR numbers in chunks of 10, sleep 2s between batches to avoid rate limiting.
- **Check enumeration**: use `gh pr list --json number` + `gh pr checks <n>` in parallel with `xargs -P 4`.
- **Branch mapping**: `gh pr list --json number,headRefName` produces a lookup table; cross-reference with `git branch --list`.

### 1.3 Offline-First Planning

When `gh auth` is invalid, all planning is done from local git state:
- `git branch --no-merged main` → non-merged branch list.
- `git worktree list` → worktree inventory.
- `git remote -v` → remote topology validation.
- All findings stored in session docs; live execution deferred.

## 2. Architecture Decisions

### 2.1 Adopted: Batch CodeRabbit re-review over per-PR manual chase

**Rationale**: 86 of 96 failing PRs had only CodeRabbit failures. Bot re-review is faster and cheaper than manual review.

**Rejected alternative**: Manual review of each failing PR. Too time-intensive at scale.

### 2.2 Adopted: Template-root CI fix before per-PR chasing

**Rationale**: Shared workflow drift in `template-commons` affects all PRs simultaneously. One template fix resolves all.

**Trade-off**: Requires `template-commons` write access and careful change management.

### 2.3 Adopted: Offline-safe local planning

**Rationale**: `gh auth` was unreliable during the session. Local-only audit ensures progress without live API.

**Trade-off**: Some findings (PR state, check status) may be stale by time of live execution.

### 2.4 Deferred: Branch deletion automation

**Rationale**: Auto-deleting branches from local inventory risks losing active work misclassified by prefix heuristics.

**Decision**: Only flag prune candidates; require manual confirmation before any `git branch -D`.

## 3. Code Organization

### 3.1 Session Structure

```
docs/sessions/<date>-<slug>/
├── 00_SESSION_OVERVIEW.md       # Goals, decisions, current state
├── 01_RESEARCH.md              # External docs, patterns, precedents
├── 02_SPECIFICATIONS.md         # Feature specs, API contracts, ARUs
├── 03_DAG_WBS.md               # Task graph, WBS, blockers
├── 04_IMPLEMENTATION_STRATEGY.md # This file
├── 05_KNOWN_ISSUES.md          # Bugs, workarounds, tech debt
└── 06_TESTING_STRATEGY.md      # Test plan, coverage, acceptance criteria
```

### 3.2 Reusable Shell Patterns

```bash
# Auth guard
gh_auth_or_die() {
  gh auth status -h github.com | grep -q "Logged in" || { echo "ERROR: gh auth invalid"; exit 1; }
}

# Batch CodeRabbit trigger
gh_batch_coderabbit() {
  local repo="$1"; shift; local numbers=("$@")
  for n in "${numbers[@]}"; do
    gh pr comment "$n" -R "$repo" --body "@coderabbitai full review" 2>/dev/null || true
    sleep 2
  done
}

# PR check summary
gh_pr_check_summary() {
  local repo="$1"; local pr="$2"
  gh pr checks "$pr" -R "$repo" --json name,state 2>/dev/null
}
```

## 4. Performance & Security Considerations

### Performance
- Parallel PR checks via `xargs -P 4` for check enumeration.
- 2s sleep between CodeRabbit re-review posts to respect rate limits.
- 30s timeout per `gh` call to prevent indefinite hangs.

### Security
- `gh auth` uses token-scoped access; no raw credentials stored.
- No secrets in session docs; only public PR metadata.
- Branch deletion requires manual confirmation; no auto-force.
