# Known Issues: Open PR Waves (v3)

## 1. Current Issues

### GitHub API Pagination 502 Errors

- **Severity**: HIGH
- **Impact**: Fresh PR listing for cliproxyapi-plusplus blocked during cursor pagination.
- **Symptom**: `502 Bad Gateway` during `gh pr list --limit 500`.
- **Workaround**: Used snapshot-based execution; 86 CodeRabbit re-reviews posted from snapshot.
- **Fix**: Re-run live fetch after API stability confirmed.

### CodeRabbit Rate Limit

- **Severity**: MEDIUM
- **Impact**: Some re-review posts may fail during batch execution.
- **Workaround**: 2s sleep between posts; log failures for retry.
- **Fix**: Space out posts; upgrade CodeRabbit workspace plan.

## 2. Technical Debt

### Snapshot Staleness

- **Severity**: LOW
- **Impact**: 86 PR re-reviews based on snapshot that may have changed.
- **Fix**: Re-verify PR states before merge.

### Missing Merge Order for Stacked PRs

- **Severity**: MEDIUM
- **Impact**: cliproxyapi-plusplus stacked PRs may merge in wrong order.
- **Fix**: Document dependency chain; use GitHub merge queue.

## 3. Future Work

1. **Merge queue automation**: Configure GitHub merge queue for stacked PRs.
2. **Live PR state tracking**: Near-real-time PR state monitoring.
3. **Automated re-base**: Script to rebase all stacked PRs onto latest main.
