# Implementation Strategy: Open PR Waves (v3)

## 1. Technical Approach

### 1.1 Snapshot-First Execution

When GitHub API is unstable (502 errors), fall back to the most recent local snapshot of PR data rather than blocking entirely.

```bash
# Retry with backoff for 502 errors
fetch_with_retry() {
  local repo="$1"; local attempt=1
  while [ $attempt -le 3 ]; do
    result=$(gh pr list --repo "$repo" --state open 2>&1)
    if echo "$result" | grep -q "502"; then
      sleep $((attempt * 5))
      attempt=$((attempt + 1))
    else
      echo "$result"
      return 0
    fi
  done
  echo "FAILED: all retry attempts exhausted" >&2
  return 1
}
```

### 1.2 Batch CodeRabbit Trigger

Use shell loop with 2s sleep to post `@coderabbitai full review` across all failing PRs:

```bash
post_coderabbit_batch() {
  local repo="$1"; shift; local prs=("$@")
  local failed=0
  for pr in "${prs[@]}"; do
    if gh pr comment "$pr" -R "$repo" --body "@coderabbitai full review" 2>/dev/null; then
      echo "OK: $pr"
    else
      echo "FAIL: $pr"
      failed=$((failed + 1))
    fi
    sleep 2
  done
  echo "Batch complete: $failed failures"
}
```

### 1.3 Clean PR Identification

A PR is a clean merge candidate when:
- `mergeStateStatus == "MERGEABLE"`
- `reviewDecision != "CHANGES_REQUESTED"`
- `failingChecks == []`

## 2. Architecture Decisions

### 2.1 Snapshot vs Live Trade-off

- **Snapshot**: Always available; may be stale.
- **Live**: Accurate; may be blocked by API errors.
- **Decision**: Use snapshot when live fails; attach freshness metadata.

### 2.2 Batch vs Per-PR Trade-off

- **Per-PR**: Precise; too slow for 100+ PRs.
- **Batch**: Fast; may hit rate limits.
- **Decision**: Batch with sleep; log failures for retry.

## 3. Governance Documentation

Created `docs/governance/stacked-prs/05-pr-reconciliation.md` covering:
- Merge order for stacked PRs (leaf → root)
- Conflict resolution procedures
- CI gating strategy
- Review debt management

Updated `docs/governance/stacked-prs/README.md` index to reference the new module.
