---
Live worktree governance now embedded in: 
completed_at: 2026-03-29T00:00:00Z
created: 2026-03-29T00:00:00Z
created_at: 2026-03-29T00:00:00Z
last_audit: 2026-04-25
plan_rationale: All work packages complete; no forward implementation remaining.
plan_status: NOT_REQUIRED
retired_at: 2026-05-05T00:00:00Z
retirement_note: |
retirement_reason: COMPLETED_OPS
slug: eco-001-worktree-remediation
spec_id: AgilePlus-eco-001
state: RETIRED
status: retired
superseded_by: |
title: Worktree Remediation
type: operational
---
# Specification: Worktree Remediation
**Slug**: worktree-remediation | **Date**: 2026-03-29 | **State**: completed

## Problem Statement
Archived legacy worktrees - completed 2026-03-28/29

## Target Users
Ecosystem governance and developer productivity

## Functional Requirements
- [x] Archive 9 legacy *-wtrees directories to archive/legacy-wtrees/2026-03-28/
- [x] Implement worktree_governance_inventory.py with conformance checks
- [x] Implement worktree_legacy_remediation_report.py with legacy detection
- [x] Implement worktree_governance.sh shell wrapper
- [x] Clean up orphaned phenotype-gauge-wtrees directory
- [x] Stash WIP changes in thegent-wtrees/rebase-fix-cache-test-pyright

## Non-Functional Requirements
- Governance tests: 10/10 passing
- Shell script: executable with check/prune/migrate commands

## Constraints & Dependencies
- Git worktree management
- Python 3.10+

## Acceptance Criteria
- [x] All legacy worktrees archived
- [x] Governance scripts functional
- [x] Tests passing
