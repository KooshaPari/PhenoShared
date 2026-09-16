# Testing Strategy: Open PR Waves (v3)

## 1. Acceptance Test Scenarios

### Scenario 1: Batch CodeRabbit Re-Review

**Setup**: 86 PRs with CodeRabbit failure in cliproxyapi-plusplus snapshot.
**Action**: Run `post_coderabbit_batch` script.
**Expected**: Comment posted on all 86 PRs within 30min.
**Verification**: `gh pr view <n> --json comments` shows new comment from bot.

### Scenario 2: Snapshot Fallback

**Setup**: GitHub API returns 502 during live PR listing.
**Action**: Run `fetch_with_retry` with fallback to snapshot.
**Expected**: Script completes; snapshot data used without blocking.
**Verification**: Output confirms snapshot mode was used; no 502 errors in output.

### Scenario 3: Clean PR Verification

**Setup**: PRs #618, #508, #514 flagged as clean in snapshot.
**Action**: `gh pr view <n> --json mergeStateStatus,reviewDecision,statusCheckRollup`.
**Expected**: All three show MERGEABLE + no CHANGES_REQUESTED + all checks green.
**Verification**: PR merge button is enabled on GitHub UI.

## 2. Manual Verification Checklist

- [ ] `gh auth status` shows logged in
- [ ] `gh pr list -R KooshaPari/cliproxyapi-plusplus --state open | wc -l` confirms expected count
- [ ] Sample 5 PRs: `gh pr checks <n>` returns green for all checks
- [ ] Governance doc accessible at `docs/governance/stacked-prs/05-pr-reconciliation.md`
- [ ] Index updated at `docs/governance/stacked-prs/README.md`
