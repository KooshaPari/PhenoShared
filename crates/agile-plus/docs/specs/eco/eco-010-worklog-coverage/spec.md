---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-010-worklog-coverage
spec_id: eco-010
state: PENDING
status: active
superseded_by: null
title: Worklog Coverage
type: operational
---
# Worklog Coverage

## Problem

Worklog coverage of the Phenotype fleet is **1/156**: only one active repository carries a `worklogs/` directory. Spec-driven governance requires every active repo to have one, because:

- worklog entries are the auditable record of decisions, research, and findings.
- cross-repo grep / aggregate tooling depends on the directory existing.
- the spec protocol's "evidence" requirement is unfulfilled fleet-wide.

Closing the gap is operational, not architectural.

## Target Users

- Repository stewards operating multi-repo governance.
- Subagents that need to write research / decision / issue worklogs.
- Aggregate tooling (`worklogs/aggregate.sh`) that depends on uniform layout.

## Functional Requirements

- FR-1: Every active repo (156) has a `worklogs/` directory at its root.
- FR-2: Each `worklogs/` directory contains at least one dated entry.
- FR-3: The dated entry references the date `2026-06-05` and the fleet-readiness scope.
- FR-4: A `worklogs/README.md` index exists in every active repo.

## Acceptance Criteria

- AC-1: Worklog coverage is `156/156` per `worklogs/worklog-coverage-20260605.json`.
- AC-2: Each entry validates as UTF-8 and contains a `# YYYY-MM-DD` header.
- AC-3: No repo in the gap list is skipped without a documented reason.

## Constraints

- **Disk floor for fan-out worktrees**: a `chore/worklog-seed-<repo>` worktree per repo requires roughly 156× the size of one worktree; current disk is full. If per-repo worktree fan-out is blocked, seed via the canonical repo directory and document the deviation in the worklog entry.
- No `git reset --hard`; preserve any pre-existing work.
- One entry per repo, not per worktree.
