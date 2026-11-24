# DAG & WBS: Open PR Waves (v3)

## 1. Task Dependency Graph (DAG)

```
[Verify live gh connectivity]
         │
         ▼
[Fetch PR snapshots (all 4 repos)]
         │
    [if 502/timeout]
         │
         ▼
[Use local snapshot as fallback]
         │
         ▼
[Flag clean merge candidates]
         │
         ├──────────────────────────────┐
         ▼                              ▼
[cliproxyapi++ audit]      [thegent audit]
   (no open PRs)              │
                               ▼
                    [Flag CodeRabbit failures]
                               │
                               ▼
                    [Post @coderabbitai full review]
                               │
         ├──────────────────────┤
         ▼                      ▼
  [#478 re-review]      [#494 re-review]
         │                      │
         ▼                      ▼
[Review threads         [Review threads
 unresolved]            unresolved]
         │                      │
         └──────────┬───────────┘
                    ▼
           [Promote clean PRs]
                    │
                    ▼
         [Create governance doc]
```

## 2. Work Breakdown Structure (WBS)

### Phase 1: Reconnaissance

| Task | ID | Status | Duration |
|------|----|--------|----------|
| GH API stability check | W-01 | Done | 2min |
| cliproxyapi++ snapshot | W-02 | Done (no open PRs) | 2min |
| cliproxyapi-plusplus snapshot | W-03 | Done (101 PRs, 502 on fresh) | 10min |
| thegent snapshot | W-04 | Done (8 open, 2 CodeRabbit failures) | 5min |
| agentapi-plusplus snapshot | W-05 | Done (no open PRs) | 2min |

### Phase 2: CodeRabbit Re-Review

| Task | ID | Status | Duration |
|------|----|--------|----------|
| cliproxyapi-plusplus batch re-review (86 PRs) | CR-01 | Done | 30min |
| thegent #478 re-review | CR-02 | Done | 2min |
| thegent #494 re-review | CR-03 | Done | 2min |

### Phase 3: Governance Documentation

| Task | ID | Status | Duration |
|------|----|--------|----------|
| Create 05-pr-reconciliation.md | G-01 | Done | 15min |
| Update stacked-prs/README.md index | G-02 | Done | 5min |

### Phase 4: Follow-Up (Deferred)

| Task | ID | Status | Dependency | Estimate |
|------|----|--------|------------|----------|
| Live re-fetch after API stability | F-01 | BLOCKED | API stable | 5min |
| Verify clean PRs (#618, #508, #514) | F-02 | BLOCKED | F-01 | 10min |
| Merge clean PRs in dependency order | F-03 | BLOCKED | F-02 | 20min |
| Resolve review thread debt | F-04 | BLOCKED | CR-02/03 | 30min |

## 3. Critical Path

```
GH API stability → PR snapshot → CodeRabbit batch → Governance doc
```

Total: ~75min session execution.

## 4. Blockers

| Blocker | Severity | Resolution |
|---------|----------|------------|
| GitHub API 502 during pagination | HIGH | Use snapshot; retry live fetch later |
| CodeRabbit rate limit | MEDIUM | 2s sleep; log failures |
| Auth token expired | HIGH | `gh auth login` |
