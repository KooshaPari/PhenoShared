---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05
plan_status: NOT_STARTED
slug: eco-009-deploy-markers
spec_id: eco-009
state: PENDING
status: active
superseded_by: null
title: Deploy Markers
type: operational
---
# Deploy Markers

## Problem

The ecosystem health scan reports a deploy surface gap: **60 of 61 repos** lack a `docs/deployment.md` deploy marker. The health scan cannot confirm the deploy surface for these repos, leaving deployment readiness unverified across nearly the entire Phenotype fleet. Only the reference repository has a deploy marker; the remaining 60 are unverifiable by automated tooling.

## Target Users

- **Repository stewards** who own individual repos and need a canonical place to document deploy mechanics.
- **Ecosystem operators** running the health scan and reporting deploy readiness.
- **On-call responders** who need a single, predictable location to find how a repo is deployed.

## Functional Requirements

1. **FR-DM-01 — Marker File**: Every active repository in the Phenotype fleet MUST contain a `docs/deployment.md` file at the repository root.
2. **FR-DM-02 — Required Sections**: Each marker MUST include, at minimum: deploy surface, build command, deploy command, rollback command, and on-call contact.
3. **FR-DM-03 — Health Scan Gate**: The ecosystem health scan MUST treat the presence and required-sections completeness of `docs/deployment.md` as a precondition for confirming a repo's deploy surface.
4. **FR-DM-04 — Standard Template**: A canonical `docs/deployment.md` template MUST live at the spec root and be reused across all 60 repos to avoid drift.
5. **FR-DM-05 — Exclusions**: Repos excluded from the deploy-surface count MUST carry a justified exclusion note in their `docs/deployment.md` (or a sibling `docs/deployment.NA.md`) referencing the reason.

## Acceptance Criteria

1. **AC-DM-01**: `docs/deployment.md` exists in at least 61 of 61 active repos, OR the health scan returns only repos with justified exclusions — yielding a deploy surface coverage of 61/61 (effectively 117/117 including both `repos/` and the `Kitty/` reference set).
2. **AC-DM-02**: Every present `docs/deployment.md` passes the required-sections validator.
3. **AC-DM-03**: The health scan's deploy-surface metric reports 100% confirmed coverage.
4. **AC-DM-04**: A worklog entry (`worklogs/deploy-marker-scaffold-20260605.json`) records the per-repo status, timestamp, and author of the marker addition.

## Constraints

- Disk-full posture: **no git commits, no worktree creation** during scaffold. Files are written in place and committed only after a future disk-recovery window.
- Fan-out work must be tracked in the worklog so progress is resumable across sessions.
- Template content must be minimal but complete; no project-specific prose until a repo's owner fills it in.
- UTF-8 only; validated by `agileplus validate-encoding --all --fix`.
