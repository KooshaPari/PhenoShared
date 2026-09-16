# Reconcile Sprint: Open PR Waves (2026-02-26)

## Scope

- Reconcile and stabilize open PRs for: `cliproxyapi++`, `cliproxyapi-plusplus`,
  `thegent`, `agentapi-plusplus`.

- Primary outputs:

  - Stacked-PR governance handbook update.

  - Concrete merge/resolve sequence for active open PR sets.

  - Git-backed documentation checkpoint for future handoff.

## Current Audit Snapshot

- `cliproxyapi++`: no open PRs.

- `agentapi-plusplus`: no open PRs.

- `thegent`: 8 open PRs.

  - Clean: #493, #496

  - `CodeRabbit` failures currently visible on: #494

- `cliproxyapi-plusplus`: last stable snapshot observed 101 open PRs (live fetch
  blocked by transient GitHub API 502).

  - Clean candidates from that snapshot: #618, #508, #514

  - Total unresolved threads: 27

  - Total check-failing PRs: 96

  - Total CodeRabbit-failing PRs: 86

## Immediate Actions

1. Re-run live `gh` fetch for `cliproxyapi-plusplus` once API is stable.

2. Promote known clean PRs only when:

   - failing checks = none

   - unresolved review threads = 0

3. For all PRs with `CodeRabbit` failure, post:

   - `@coderabbitai full review`

4. Resolve review-thread debt in stack order, then merge by dependency chain.

5. Keep canonical `main` branches untouched until explicit upstream pull/merge
  step.

## Executed Sweep

- `cliproxyapi-plusplus`: posted `@coderabbitai full review` to 86
  `CodeRabbit`-failing PRs from the latest local snapshot.

- `thegent`: posted `@coderabbitai full review` to 2 `CodeRabbit`-failing PRs
  (#494, #478).

- Snapshot-driven run was intentionally used while API pagination intermittently
  returned 502 for fresh listing.

## Canonical Docs

- Added module:
  [`docs/governance/stacked-prs/05-pr-reconciliation.md`](../../governance/stacked-prs/05-pr-reconciliation.md)

- Updated index:
  [`docs/governance/stacked-prs/README.md`](../../governance/stacked-prs/README.md)
