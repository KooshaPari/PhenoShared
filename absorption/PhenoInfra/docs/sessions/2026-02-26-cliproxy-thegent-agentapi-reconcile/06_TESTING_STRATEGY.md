# Testing Strategy: PR Reconciliation Audit (v1)

## Test Plan

No automated tests applicable. Session consists of CLI operations and documentation.

## Manual Verification

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| PR enumeration | Inspect `gh pr list` output | All open PRs listed per repo |
| Classification | Review output manually | PRs grouped by failure type |
| Merge candidates | Inspect flagged PRs | Only PRs with passing checks flagged |
| Worktree cleanup | `git worktree list` | No stale entries remain |

## Test Data

None required (live API data only).
