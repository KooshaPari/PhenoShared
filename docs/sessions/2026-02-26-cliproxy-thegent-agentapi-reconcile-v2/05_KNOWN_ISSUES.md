# Known Issues: PR Reconciliation Sprint (v2)

## 1. Current Bugs & Failures

### GH Auth Expiration

- **Severity**: HIGH
- **Impact**: All live PR operations blocked (list, checks, comments, merge).
- **Symptom**: `gh auth status` returns expired/invalid token for `KooshaPari`.
- **Workaround**: Defer live operations; use local-only git state for planning.
- **Fix**: Run `gh auth login` with fresh token.

### CodeRabbit Rate Limit Exceeded

- **Severity**: MEDIUM
- **Impact**: Batch re-review posts fail for many PRs.
- **Symptom**: `Review rate limit exceeded` error on CodeRabbit posts.
- **Workaround**: Retry after 1hr cooldown; log failures and retry in next session.
- **Fix**: Space out re-review requests; consider CodeRabbit workspace plan upgrade.

### Git Remote 404 (thegent upstream)

- **Severity**: HIGH
- **Impact**: Cannot fetch/push to `upstream` remote in `thegent`.
- **Symptom**: `fatal: repository 'https://github.com/...' not found` on `git fetch upstream`.
- **Workaround**: Use `origin` only; `main` synced with `origin/main`.
- **Fix**: Remove or replace `upstream` remote pointing to non-existent repo.

## 2. Technical Debt

### Branch Prefix Classification is Heuristic

- **Severity**: LOW
- **Impact**: `tmp-*`, `ci-fix*` classification may misidentify active work as stale.
- **Workaround**: Never auto-delete; manual confirmation required for all prune candidates.
- **Fix**: Add PR-mapping step to cross-reference each branch against `gh pr list`.

### Worktree Proliferation (cliproxyapi-plusplus)

- **Severity**: MEDIUM
- **Impact**: 200+ branches clutter the local repo; `git worktree list` shows many entries.
- **Workaround**: `git worktree prune` to remove stale entries.
- **Fix**: Establish worktree policy; limit active worktrees per repo.

### PR Merge State Staleness

- **Severity**: LOW
- **Impact**: Local snapshot of PR states may be stale when live execution resumes.
- **Workaround**: Re-run `gh pr list` after auth is restored.
- **Fix**: Implement near-real-time PR state tracking in session docs.

### Missing PR-to-Branch Mapping

- **Severity**: MEDIUM
- **Impact**: Cannot determine if a local branch has an open PR without live `gh`.
- **Workaround**: Offline heuristic based on branch name patterns.
- **Fix**: Build PR-to-branch lookup table from `gh pr list --json number,headRefName`.

## 3. Future Work Recommendations

1. **Automate PR-to-branch mapping**: Build a script that syncs local branches to open PRs using `gh pr list --json headRefName`.

2. **Shared CI health dashboard**: Monitor `template-commons` workflow health to catch drift before it propagates to all PRs.

3. **CodeRabbit rate limit management**: Implement exponential backoff for re-review posts; consider a queue system.

4. **Branch lifecycle policy**: Define max age for `tmp-*`, `ci-fix*` branches; auto-flag for cleanup after N days of inactivity.

5. **Merge queue automation**: Once CI is stable, use GitHub's merge queue feature to automate stacked PR merges.
