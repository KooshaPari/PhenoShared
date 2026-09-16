# Specifications: Cleanup Pass (cliproxyapi-plusplus + thegent)

## 1. Feature Specifications

### 1.1 PR Failure Audit

**Goal**: Enumerate all open PRs and classify by failure type.

**Acceptance Criteria**:
- [ ] All open PRs enumerated for `cliproxyapi-plusplus` and `thegent`.
- [ ] Each PR has failure cluster identified.
- [ ] CR-clean PRs identified separately.

### 1.2 CodeRabbit Re-review Request

**Goal**: Post `@coderabbitai full review` comments on CodeRabbit-failing PRs.

**Acceptance Criteria**:
- [ ] All CodeRabbit-failing PRs received re-review comment.
- [ ] Comments posted successfully.

### 1.3 Branch Health Audit

**Goal**: Detect stale local branches with no open PR.

**Acceptance Criteria**:
- [ ] All open PR head branches verified against upstream refs.
- [ ] No safe prune candidates identified (held).

## 2. ARUs

| ID | Type | Description | Mitigation |
|----|------|-------------|------------|
| ARU-1 | **Assumption** | CodeRabbit will drain rate limit before retry wave. | Monitor CR queue before retry. |
| ARU-2 | **Risk** | Shared CI gates must be fixed before cluster wave. | Cluster wave deferred until gates stable. |
| ARU-3 | **Uncertainty** | No safe local prune candidates per current heuristic. | Branch deletion deferred. |
