---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
last_audit: 2026-06-05
plan_status: REQUIRED
slug: eco-028-commit-hygiene
spec_id: eco-028
state: PENDING
status: active
superseded_by: null
title: Commit / Branch Hygiene
type: operational
---
# Specification: Commit / Branch Hygiene

## Problem Statement
`worklogs/worktree-hygiene-20260605.json` reports 130 stale worktrees (>14d, clean) and 14 merged-branch candidates. `worklogs/oldest-<REDACTED>-20260605.json` shows 17 local/remote divergences, some with dirty working trees ahead of remote. The fleet drifts silently.

## Target Users
- **Repo stewards** who need a clean baseline.
- **PR reviewers** who need to know whether a branch is stale before merging.
- **CI** which should refuse merges from stale or dirty branches.

## Functional Requirements
- **FR-1**: Commit messages MUST follow Conventional Commits (`<type>(<scope>): <subject>`); lint enforced by `commitlint` or equivalent.
- **FR-2**: Branches MUST be named `<type>/<scope>-<repo>` (e.g. `fix/build-phenoAI`, `chore/worklog-seed-FocalPoint`).
- **FR-3**: A worktree older than 14 days with no new commits MUST be either refreshed or removed (per `worktree-cleanup.sh`).
- **FR-4**: A branch ahead of remote with a dirty working tree MUST be either pushed or reset; CI flags it on PR creation.
- **FR-5**: A weekly script (`scripts/sweep-stale-worktrees.sh`) MUST emit `worklogs/worktree-hygiene-<date>.json`.
- **FR-6**: The commit-msg hook MUST refuse any commit whose body is `WIP` or `TODO` alone.

## Acceptance Criteria
- `scripts/sweep-stale-worktrees.sh` reports 0 stale and 0 dirty-ahead on the live tree after one pass.
- A test commit with message `fix: bug` is accepted; `WIP` is rejected.

## Constraints & Dependencies
- Depends on eco-019 (worktree-isolation) — every change lands in a worktree.
- Depends on eco-017 (disk-recovery gate) — sweep runs in a healthy disk state.
- Depends on eco-024 (traceability) — every change references an FR ID in the body.
