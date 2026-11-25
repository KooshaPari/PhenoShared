# Reconciliation Audit Snapshot (2026-02-26)

## Repos covered

- `cliproxyapi-plusplus`
- `thegent`
- `agentapi-plusplus`

## Child-agent outputs

- `cliproxyapi-plusplus`: 1 open PR (`#11`, draft, conflicting), main not
  checked out in canonical, upstream/main diverges, prunable worktree detected.
- `thegent`: 5 open PRs (`478,480,482,493,494`) with mixed
  `MERGEABLE/BLOCKED/DIRTY` states and bot review pressure.
- `agentapi-plusplus`: 3 open PRs (`242,243,246`), including conflicts and
  rate-limits in bot checks.

## Current hard blockers

1) `cliproxy` canonical branch is currently not on `main` in this worktree and
has detached canonical branch mappings.
2) `cliproxy` and other repos have heavy `worktree` proliferation; one
prunable/reconcilable path remains.
3) `thegent` upstream remote points to a 404.
4) Several PRs remain in `CONFLICTING`/`DIRTY` with unresolved review comments
and/or check failures.

## Commands applied this cycle

- `git worktree prune` executed in `cliproxyapi-plusplus`.
- Re-review trigger on PR #243: `coderabbitai full review`
  (posted as `@coderabbitai full review`).

## Immediate next sequence

1. Stabilize `thegent` topology: repair/remove broken `upstream` and resolve the
  PR check-fail groups before rebases.
2. Close/rebase superseded PRs in `cliproxy` (start with conflict-minimized
  branch #11 context).
3. Resolve `agentapi++` open PR conflicts in small stacked order and rerun
  blocked checks.
4. Re-run branch inventory + PR state check and produce an execution-ready merge
  order once reviews are fresh.
