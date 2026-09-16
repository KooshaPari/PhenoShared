# Specifications: PR Reconciliation Audit Snapshot (v1)

## 1. Feature Specifications

### 1.1 PR Audit System

**Goal**: Audit open PRs across 3 repos.

**Acceptance Criteria**:
- [ ] All open PRs enumerated with: number, branch, merge state, check status.
- [ ] PRs classified by failure type.
- [ ] Clean merge candidates flagged.

### 1.2 Worktree Cleanup

**Goal**: Remove stale worktrees from cliproxyapi-plusplus.

**Acceptance Criteria**:
- [ ] `git worktree prune` executed successfully.
- [ ] No stale worktree entries remain.

## 2. ARUs

| ID | Type | Description | Mitigation |
|----|------|-------------|------------|
| ARU-1 | **Risk** | Worktree prune may remove active worktrees. | Review `git worktree list` before pruning. |
| ARU-2 | **Assumption** | PR #243 still open when re-review triggered. | Verify before executing. |
