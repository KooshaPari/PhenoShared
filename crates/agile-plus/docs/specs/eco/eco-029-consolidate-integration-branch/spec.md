---
created: 2026-06-15T00:00:00Z
created_at: 2026-06-15T00:00:00Z
slug: eco-029-consolidate-integration-branch
spec_id: eco-029
state: ACTIVE
status: active
title: Consolidate Integration Branch
type: operational
---
# eco-029: Consolidate Integration Branch

## Goal
Merge all open feature/fix branches onto `integration/consolidate` for a single review PR to main.

## Acceptance Criteria
- All open branches merged (or documented as conflicted/skipped)
- CI green on integration/consolidate
- Anti-wipe gate passes (no mass deletions)
