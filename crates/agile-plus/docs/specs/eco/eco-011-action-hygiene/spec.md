---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-011-action-hygiene
spec_id: eco-011
state: PENDING
status: active
superseded_by: null
title: Action Hygiene
type: operational
---
# Action Hygiene

## Problem

`worklogs/action-pin-audit-20260605.json` reports 1071 unpinned and 384 malformed
GitHub Actions `uses:` refs across the Phenotype org. The five most-frequent
offenders account for the majority of unpinned refs:

| Action | Count | Form |
|---|---|---|
| `actions/checkout@v4` | 136 | tag, unpinned |
| `actions/checkout@v6` | 92 | tag, unpinned |
| `dtolnay/rust-toolchain@stable` | 70 | tag, unpinned |
| `github/codeql-action/upload-sarif@v4` | 45 | tag, unpinned |
| `Swatinem/rust-cache@v2` | 38 | tag, unpinned |

The 384 malformed refs are consistent with a botched bulk rewrite (truncated
SHAs, missing `@` separator, and refs that lost the `action.yml` path). They
parse to nothing useful and break resolution on push.

Unpinned refs permit supply-chain substitution attacks: any upstream retag,
recompile, or repo transfer changes the resolved action body on the next CI
run. Given the org's billing posture (CI is not a verification gate), the only
defence is pinning at source.

## Target Users

- Phenotype maintainers consuming shared workflows
- Operators auditing supply-chain risk across repos
- Agent sweeps that bulk-edit `uses:` lines

## Functional Requirements

FR-1: Every `uses:` line referencing a third-party action MUST pin to a
40-character commit SHA resolved against the action's upstream default branch.
FR-2: Tag-style refs (e.g. `@v4`, `@stable`, `@main`) are forbidden in
`uses:` lines; the only permitted trailing token is a 40-char SHA.
FR-3: First-party actions owned by the org (under `<REDACTED>/*`) follow the
same SHA rule.
FR-4: A pre-commit or pre-merge check MUST fail the build when an unpinned or
malformed `uses:` is introduced.
FR-5: An audit script MUST emit a JSON report with counts of unpinned, pinned,
and malformed refs per repo.

## Acceptance Criteria

AC-1: Unpinned ref count across the org is below 5 (down from 1071).
AC-2: Malformed ref count is exactly 0 (down from 384).
AC-3: All five top unpinned actions are pinned to 40-char SHAs in every
workflow file that references them.
AC-4: CI on each touched repo continues to pass locally (the org's GitHub
Actions billing is disabled; local `task quality` and `cargo test --workspace`
stand in).
AC-5: The audit script re-runs clean within 60s.

## Constraints

- CI must continue to pass after the rewrite.
- No `git reset --hard`; per-worktree, per-provenance commits.
- Disk is full; no new worktrees, no new git operations beyond commits.
- Do not retag upstream actions; pin only.
