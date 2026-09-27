# Specifications: CLIProxy++, thegent, agentapi++ PR Reconciliation (v2)

## 1. Feature Specifications

### 1.1 Reconcile PR Audit System

**Goal**: Systematically audit and triage all open PRs across 4 repos (`cliproxyapi++`, `cliproxyapi-plusplus`, `thegent`, `agentapi-plusplus`).

**Acceptance Criteria**:
- [ ] All open PRs per repo are enumerated with: PR number, branch name, merge state, check status, comment count.
- [ ] PRs are classified by failure type: infra (CI/build/docs), CodeRabbit, merge conflict, review thread debt.
- [ ] Clean merge candidates (0 failing checks, 0 unresolved threads) are flagged separately.
- [ ] Execution queue is produced in priority order.

### 1.2 CodeRabbit Re-Review Trigger System

**Goal**: Clear CodeRabbit failures en masse across all affected PRs.

**Acceptance Criteria**:
- [ ] For every PR with `CodeRabbit` failure, `@coderabbitai full review` is posted.
- [ ] Rate-limit errors are caught and logged; operation retries after cooldown.
- [ ] Batch execution completes without timing out.

### 1.3 Local Branch Inventory & Cleanup System

**Goal**: Audit and classify all local non-merged branches by type, age, and PR mapping.

**Acceptance Criteria**:
- [ ] All non-merged branches are listed per repo with prefix classification.
- [ ] Stale branches (confirmed closed upstream) are identified.
- [ ] Safe prune candidates (tmp-*, archive-*, ci-fix-tmp-*) are flagged.
- [ ] Worktree branches are kept untouched.

### 1.4 Shared CI Template Normalization

**Goal**: Fix root-cause CI drift in shared workflows before per-PR fixes.

**Acceptance Criteria**:
- [ ] `verify-required-check-names` drift is identified and fixed in the template repo.
- [ ] Go `analyze`/`build` failures are traced to workflow template changes.
- [ ] `Build Docs` failures are traced to Sphinx/Docsy config drift.
- [ ] Fix propagates to all PRs via base-branch update.

## 2. API Contracts

### 2.1 PR State Enumeration

```
gh pr list --repo <owner/repo> --state open \
  --json number,headRefName,mergeStateStatus,reviewDecision,isDraft,updatedAt
```

Output shape:
```json
{
  "number": 494,
  "headRefName": "fix/orjson-v2",
  "mergeStateStatus": "DIRTY",
  "reviewDecision": "CHANGES_REQUESTED",
  "isDraft": false,
  "updatedAt": "2026-02-26T00:00:00Z"
}
```

### 2.2 Check Status Query

```
gh pr checks <n> --repo <owner/repo> --json name,state,conclusion
```

Output shape:
```json
[
  {"name": "CodeRabbit", "state": "FAILURE", "conclusion": "FAILURE"},
  {"name": "Build", "state": "SUCCESS", "conclusion": "SUCCESS"}
]
```

### 2.3 Comment Post

```
gh pr comment <n> --repo <owner/repo> --body "@coderabbitai full review"
```

## 3. Data Models

### 3.1 PR Audit Record

| Field | Type | Description |
|-------|------|-------------|
| `number` | int | PR number |
| `headRefName` | string | Branch name |
| `mergeStateStatus` | enum | MERGEABLE, BLOCKED, DIRTY, CONFLICTING, UNKNOWN |
| `reviewDecision` | enum | APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED |
| `isDraft` | bool | Draft flag |
| `updatedAt` | timestamp | Last update time |
| `failingChecks` | string[] | List of failing check names |
| `issueComments` | int | Non-review issue comments |
| `reviewComments` | int | Review thread comments |
| `failingChecks` | string[] | Names of failing checks |
| `classification` | enum | INFRA, CODERABBIT, CONFLICT, REVIEW_DEBT, CLEAN |

### 3.2 Branch Inventory Record

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Branch name |
| `prefix` | string | Classification prefix (ci/, feat/, etc.) |
| `repo` | string | Repository name |
| `lastCommit` | timestamp | Last commit date |
| `hasOpenPR` | bool | Whether a PR is open for this branch |
| `pruneCandidate` | bool | Safe to delete locally |
| `worktree` | bool | Is a worktree branch |

## 4. ARUs (Assumptions, Risks, Uncertainties)

| ID | Type | Description | Mitigation |
|----|------|-------------|------------|
| ARU-1 | **Risk** | `gh auth` may expire mid-session, blocking live operations. | Use local-only audit when auth is invalid; defer live ops. |
| ARU-2 | **Risk** | Batch CodeRabbit re-review hits rate limit, leaving many PRs unreviewed. | Log rate-limit errors; retry in next session. |
| ARU-3 | **Risk** | Branch prefix classification is heuristic; some `tmp-*` or `ci-fix*` may be active work. | Never auto-delete; only flag candidates for manual review. |
| ARU-4 | **Uncertainty** | `cliproxyapi-plusplus` has 207 local branches; mapping to open PRs is incomplete. | Defer cleanup until live PR-to-branch mapping is verified. |
| ARU-5 | **Assumption** | All 4 repos use the same shared CI template from `template-commons`. | Verify template-commons workflow sync before assuming. |
| ARU-6 | **Assumption** | CodeRabbit failures are transient and re-review will clear them. | If re-review also fails, escalate to manual review. |
