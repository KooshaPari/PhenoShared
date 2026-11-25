---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
plan_status: REQUIRED
slug: eco-034-functional-requirements-canonical
spec_id: eco-034
state: PENDING
status: active
superseded_by: null
title: Functional Requirements Canonical
type: operational
---
## Problem
FRs are scattered across kitty-specs, READMEs, and ad-hoc docs. The eco-024 trace matrix references a canonical `FUNCTIONAL_REQUIREMENTS.md`, but no single source of truth exists.

## Target Users
AgilePlus maintainers, agent implementers, reviewers, and governance auditors.

## Functional Requirements
Create `AgilePlus/FUNCTIONAL_REQUIREMENTS.md` with one row per FR: `id`, `title`, `owner`, `spec_slug`, `spec_anchor`, `status` (`proposed`, `accepted`, `mature`, `regressed`), `test_path`, `journey_stub`, `trace_path`.

## Acceptance Criteria
- Every FR in any active spec appears in the registry.
- New FRs are PR'd against `AgilePlus/FUNCTIONAL_REQUIREMENTS.md`.

## Constraints
Depends on eco-018 spec-first. Depends on eco-024 traceability.
