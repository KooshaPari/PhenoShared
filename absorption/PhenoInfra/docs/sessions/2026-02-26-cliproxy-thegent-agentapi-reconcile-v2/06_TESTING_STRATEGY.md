# Testing Strategy: PR Reconciliation (v2)

## 1. Test Plan & Coverage Goals

### 1.1 Validation Testing (Manual)

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| Auth check | `gh auth status` returns logged in | `Logged in to github.com` visible |
| PR listing | `gh pr list` returns non-empty list | At least 1 PR returned |
| Check query | `gh pr checks <n>` returns structured JSON | Contains `name`, `state` fields |
| Comment post | `@coderabbitai full review` posted | Comment visible on PR page |
| Branch listing | `git branch --no-merged main` returns list | All non-merged branches listed |
| Worktree prune | `git worktree prune` removes stale entries | Stale worktrees removed |

### 1.2 Smoke Tests

| Test | Command | Expected |
|------|---------|----------|
| Auth alive | `gh auth status -h github.com` | `Logged in` |
| Repo reachable | `gh repo view KooshaPari/cliproxyapi-plusplus` | No error |
| PR accessible | `gh pr view 1 -R KooshaPari/thegent` | Returns PR data |
| Branch list | `git branch -a` | Lists all remotes |

## 2. Test Data Strategies

### 2.1 Dry-Run Mode

All destructive operations (branch deletion, PR closure) use dry-run flags:
```bash
git branch -d -n <branch>  # dry-run only
gh pr close <n> --dry-run   # if supported
```

### 2.2 Snapshot Before Changes

Before any live operation:
1. Record current PR state: `gh pr list --json number,mergeStateStatus > pr_snapshot_before.jsonl`
2. Record current branch list: `git branch > branches_before.txt`
3. Run the operation
4. Compare before/after to verify expected changes

### 2.3 Synthetic Test Data

For offline testing:
- PR numbers from known snapshots (e.g., #494 for thegent, #618 for cliproxyapi++)
- Branch names from local inventory
- Merge states from documented audit

## 3. Acceptance Test Scenarios

### Scenario 1: CodeRabbit Re-Review on Single PR

**Setup**: `gh auth` valid, PR #494 on `thegent`.
**Action**: Post `@coderabbitai full review`.
**Expected**: Comment appears on PR; within 5min, CodeRabbit check re-runs.
**Verification**: `gh pr checks 494 -R KooshaPari/thegent --json name,state` shows updated `CodeRabbit` status.

### Scenario 2: Batch CodeRabbit Re-Review

**Setup**: 10 PRs with CodeRabbit failures.
**Action**: Run batch re-review script.
**Expected**: Comment posted on all 10 PRs; rate limit errors logged but not fatal.
**Verification**: All 10 PRs show new CodeRabbit comment; error log has 0 rate-limit entries.

### Scenario 3: Branch Prune Candidate Identification

**Setup**: 207 local branches in cliproxyapi-plusplus.
**Action**: Run prefix-classification script.
**Expected**: `tmp-*`, `ci-fix-tmp-*`, `archive/*` branches flagged as prune candidates.
**Verification**: Cross-reference with `gh pr list` to confirm no open PRs for flagged branches.

### Scenario 4: Shared CI Template Fix Propagation

**Setup**: `verify-required-check-names` drift in template.
**Action**: Fix template, push to `template-commons`, trigger re-run on affected PR.
**Expected**: All affected PRs get updated CI status without per-PR code changes.
**Verification**: `gh pr checks` shows green `verify-required-check-names` across affected PRs.

## 4. Test Execution Schedule

- **Pre-session**: Verify `gh auth` and connectivity.
- **During session**: After each batch operation, verify snapshot diff.
- **Post-session**: Full smoke test to confirm no regressions.
