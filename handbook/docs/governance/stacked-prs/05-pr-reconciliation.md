# PR Reconciliation Playbook

Use this module for PR cleanup where open work is noisy, stacked, or review-debt
heavy.

## Scope and Priority

- Canonical branch: keep `main` clean and reserved for upstream sync + final
  merge.
- Work branches: `PROJECT-wtrees/<topic>` for triage, fixes, and PR prep.
- Priority rule: shared-failure roots first (workflow, check-name gates), then
  review debt, then branch churn.

## Merge Stack Contracts

Every PR should include:

- `Depends-on`
- `Stack-Layer` (L1/L2/L3)
- `Release-Channel` (alpha/beta/rc/canary/release)
- `Rollback-Plan`
- `API-Shape-Impact`

Hard rule:

- Do not merge a child PR if parent API-shaping PR is not merged first.
- If a child PR includes the same feature family but different risk profile,
  treat it as a separate stack lane.

## WBS / Channel Pattern

Example for one feature family:

- `1.0` (alpha): Playback core
- `1.1` (beta): Offline cache (`depends_on: 1.0`)
- `1.2` (rc): web renderer (`depends_on: 1.0`, higher risk, beta/rc-only)

Interpretation:

- `1.1` is same feature family as `1.0`; same merge path dependency.
- `1.2` may ship later than `1.1` if risk requires `rc`.

## Reconciliation Workflow (Wave Pattern)

1. Refresh PR inventory (open PRs + check summary + review threads).
2. Identify clean PRs (`failing_checks=0`, `unresolved_threads=0`) and promote
   first.
3. Fix shared CI check-name / workflow failures before touching individual PR
   logic.
4. For each PR with unresolved threads: resolve all required comments first,
   then re-run checks.
5. For `CodeRabbit` failures: comment `@coderabbitai full review` and wait for
   fresh result.
6. Merge only when gates align with stack dependencies and release channel
   policy.

## Recorded Reconciliation Snapshot (2026-02-26)

- `cliproxyapi++`:
  - open PRs (authoritative snapshot): 0
- `cliproxyapi-plusplus`:
  - open PRs from snapshot: 101
  - clean candidates: 3
  - unresolved threads: 27
  - check-failing PRs: 96
  - CodeRabbit failures: 86
- `thegent`:
  - open PRs: 8
  - clean: 2
  - unresolved threads: 4
  - check-failing PRs: 6
  - CodeRabbit failures: 2
- `agentapi-plusplus`:
  - open PRs: 0

Action note:
If this dataset cannot be refreshed via `gh` due to transient API 502, proceed
with the last stable snapshot and re-run before merge.

## Gate Templates and Labels

- Blockers in stack lanes: `ci-check`, `review-debt`, `dependency-hold`.
- Channel labels:
  - `release/alpha`
  - `release/beta`
  - `release/rc`
  - `release/canary`
  - `release/release`
- PR naming:
  - `stack/<layer>/<feature-slug>`
  - `merge/<lane>/<timestamp>`
