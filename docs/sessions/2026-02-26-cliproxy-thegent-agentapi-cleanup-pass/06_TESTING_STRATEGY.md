# Testing Strategy: Cleanup Pass (cliproxyapi-plusplus + thegent)

## Test Plan

No automated tests applicable. Session consists of CLI operations and documentation.

## Manual Verification

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| PR enumeration accuracy | Compare CSV vs `gh pr list` output | All PRs present, no duplicates |
| Failure classification | Spot-check 3–5 PRs manually via `gh pr checks` | Classification matches actual state |
| CR re-review comments | `gh pr view <n> --comments` | Comments visible on target PRs |
| Branch audit | Compare local `git branch` vs open PR heads | No missed refs |
| CSV completeness | Count rows vs expected totals | 30 cliproxy + 8 thegent |

## Acceptance Test Scenarios

1. **PR enumeration**: All 38 open PRs appear in `cleanup_matrix.csv` with correct repo.
2. **Cluster correctness**: PRs sharing failures are grouped by shared check names.
3. **CR re-review**: `gh pr view 478` and `gh pr view 494` (thegent) show `@coderabbitai full review` comment.
4. **No safe prune**: Local `git branch` lists branches whose heads are not in open PR list.

## Test Data

Live GitHub API data — no synthetic test data used.
