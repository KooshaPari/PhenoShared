# Specifications: Open PR Waves (v3)

## 1. Feature Specifications

### 1.1 Snapshot-Driven PR Audit

**Goal**: Audit all open PRs across 4 repos using a locally cached snapshot when live API is unstable.

**Acceptance Criteria**:
- [ ] Snapshot covers all 4 repos: cliproxyapi++, cliproxyapi-plusplus, thegent, agentapi-plusplus.
- [ ] Snapshot includes: PR number, merge state, failing checks, CodeRabbit status.
- [ ] Clean merge candidates are flagged (0 failing checks, 0 unresolved threads).
- [ ] Check freshness note is attached to snapshot metadata.

### 1.2 Batch CodeRabbit Re-Review

**Goal**: Clear CodeRabbit failures across all affected PRs in a single session.

**Acceptance Criteria**:
- [ ] All PRs with `CodeRabbit` failure in snapshot receive `@coderabbitai full review`.
- [ ] Batch execution handles rate-limit errors gracefully (log + continue).
- [ ] Total PRs re-reviewed: 88 (86 cliproxyapi-plusplus + 2 thegent).

### 1.3 Canonical Governance Documentation

**Goal**: Document PR reconciliation workflow in the governance handbook.

**Acceptance Criteria**:
- [ ] New module `docs/governance/stacked-prs/05-pr-reconciliation.md` created.
- [ ] Index `docs/governance/stacked-prs/README.md` updated to reference the new module.
- [ ] Document covers: merge order, conflict resolution, CI gating, review debt.

## 2. API Contracts

### 2.1 PR Listing (Snapshot)

```bash
gh pr list --repo <owner/repo> --state open \
  --json number,headRefName,mergeStateStatus,reviewDecision,isDraft,updatedAt
```

### 2.2 Check Query

```bash
gh pr checks <n> --repo <owner/repo> --json name,state,conclusion
```

### 2.3 Comment Post

```bash
gh pr comment <n> --repo <owner/repo> --body "@coderabbitai full review"
```

## 3. ARUs (Assumptions, Risks, Uncertainties)

| ID | Type | Description | Mitigation |
|----|------|-------------|------------|
| ARU-1 | **Risk** | Snapshot may be stale by time of merge. | Re-run live fetch before merge operations. |
| ARU-2 | **Risk** | Batch CodeRabbit re-review hits rate limit. | 2s sleep between posts; log and continue. |
| ARU-3 | **Assumption** | 86 cliproxyapi-plusplus PRs still open at execution time. | Confirm count before batch post. |
| ARU-4 | **Assumption** | CodeRabbit re-review clears failures. | If not, escalate to manual review. |
| ARU-5 | **Uncertainty** | Whether cliproxyapi++ and agentapi++ truly have 0 open PRs. | Verify with live fetch. |
