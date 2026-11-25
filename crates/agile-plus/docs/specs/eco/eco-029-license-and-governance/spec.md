---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-029-license-and-governance
spec_id: eco-029
state: PENDING
status: active
superseded_by: null
title: License and Governance
type: operational
---
## Problem
The 9-clone audit (`worklogs/clone-fill-audit-20260605.json`) found 8/9 repos lack LICENSE, weakening reuse and governance clarity.

## Target Users
Repository stewards, maintainers, agents, and compliance reviewers.

## Functional Requirements
- FR-01: Every repo must include a LICENSE; MIT is preferred unless explicitly constrained.
- FR-02: Every repo must include `GOVERNANCE.md` referencing the Phenotype Org baseline.
- FR-03: Repos must include `CODEOWNERS` for ownership routing.

## Acceptance Criteria
- License coverage = 100%.
- Governance coverage = 100%.
- CODEOWNERS coverage >= 80%.

## Constraints
No broad rewrites; preserve repo-specific legal constraints; prefer minimal governance stubs linked to canonical baseline.
