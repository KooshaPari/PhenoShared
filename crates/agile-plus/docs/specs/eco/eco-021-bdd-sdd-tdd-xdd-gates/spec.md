---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-021-bdd-sdd-tdd-xdd-gates
spec_id: eco-021
state: PENDING
status: active
superseded_by: null
title: BDD/SDD/TDD/XDD Gates
type: operational
---
## Problem
No single contract ties FR → spec → docs → test → lint → journey evidence.

## Target Users
Agents, maintainers, reviewers, repository stewards.

## Functional Requirements
- FR-01: Every FR has a test ID.
- FR-02: Every test cites a spec.
- FR-03: Every docs page references the FR/test IDs it satisfies.
- FR-04: BDD uses Given/When/Then narrative.
- FR-05: SDD makes the spec the source of truth.
- FR-06: TDD requires tests before code or in the same change.
- FR-07: XDD requires executable docs or runnable examples.
- FR-08: Journeys embed gif-stub placeholders linked to capture scripts.

## Acceptance Criteria
- AC-01: `make autograde` runs all gates and reports per-FR pass/fail.
- AC-02: Missing FR/test/spec/docs/journey links fail clearly.

## Constraints
Respect eco-017 disk gate, eco-018 spec-first, and eco-019 worktree-isolation.
