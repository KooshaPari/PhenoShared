# DAG & WBS: PR Reconciliation Sprint (v2)

## 1. Task Dependency Graph (DAG)

```
[gh auth validation]
        │
        ▼
[PR state enumeration (all 4 repos)]
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼
[thegent audit]     [agentapi++ audit]   [cliproxyapi++ audit]
        │                      │                      │
        ▼                      ▼                      ▼
[CodeRabbit       [CodeRabbit           [CodeRabbit
 re-review #494]   re-review batch]      re-review batch]
        │                      │                      │
        ▼                      ▼                      ▼
[Resolve review    [Rebase conflicting  [Fix shared CI
 threads #478/480]  PRs #261/#260]      template drift]
        │                                         │
        ▼                                         ▼
[Infra gate fix    [Promote clean PRs from snapshot]
 for #482]
        │
        ▼
[Merge queue execution]
```

## 2. Work Breakdown Structure (WBS)

### Phase 1: Reconnaissance (already executed in session)

| Task | ID | Status | Duration |
|------|----|--------|----------|
| Auth check (`gh auth status`) | R-01 | Done | <1min |
| PR listing per repo | R-02 | Done | 5min |
| Check status per PR | R-03 | Done | 10min |
| Review thread count | R-04 | Done | 5min |
| Local branch inventory | R-05 | Done | 10min |
| Worktree audit | R-06 | Done | 2min |

### Phase 2: CodeRabbit Re-Review (already executed)

| Task | ID | Status | Duration |
|------|----|--------|----------|
| CodeRabbit batch (cliproxyapi++) | CR-01 | Done | 30min |
| CodeRabbit batch (thegent) | CR-02 | Done | 5min |
| CodeRabbit batch (agentapi++) | CR-03 | Skipped | — |

### Phase 3: PR Resolution (deferred — requires live auth)

| Task | ID | Status | Dependency | Estimate |
|------|----|--------|------------|----------|
| Resolve #478 review threads | P-01 | BLOCKED | gh auth | 30min |
| Rebase #480 conflict PR | P-02 | BLOCKED | P-01 | 20min |
| Rebase #482 conflict PR | P-03 | BLOCKED | infra gate fix | 20min |
| Fix CodeRabbit on #494 | P-04 | BLOCKED | CR-02 | 10min |
| Promote clean PRs (thegent) | P-05 | BLOCKED | P-01, P-04 | 15min |
| Rebase agentapi++ conflicts | P-06 | BLOCKED | gh auth | 30min |
| cliproxyapi++ CI fix | P-07 | BLOCKED | template-commons | 60min |
| cliproxyapi++ PR queue | P-08 | BLOCKED | P-07 | 60min |

### Phase 4: Branch Cleanup (deferred)

| Task | ID | Status | Dependency | Estimate |
|------|----|--------|------------|----------|
| Map local branches to PR heads | B-01 | BLOCKED | gh auth | 20min |
| Flag stale branches | B-02 | BLOCKED | B-01 | 10min |
| Prune confirmed-closed branches | B-03 | BLOCKED | B-02 + manual review | 15min |
| Push canonical main updates | B-04 | BLOCKED | all PR merges done | 10min |

## 3. Critical Path

```
gh auth → R-02/R-03 → CR-01 → P-07 → P-08
```

Total estimated: ~90min live execution + 20min for auth + 30min CodeRabbit.

## 4. Blockers

| Blocker | Severity | Resolution |
|---------|----------|------------|
| `gh auth` invalid for `KooshaPari` | HIGH | Run `gh auth login` |
| CodeRabbit rate limit exceeded | MEDIUM | Wait 1hr cooldown, retry |
| cliproxyapi++ shared CI drift | HIGH | Fix template-commons workflow |
| `thegent` `upstream` remote 404 | HIGH | Reconfigure git remotes |
