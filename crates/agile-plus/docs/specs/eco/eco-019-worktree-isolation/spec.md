---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-019-worktree-isolation
spec_id: eco-019
state: PENDING
status: active
superseded_by: null
title: Worktree Isolation
type: operational
---
## Problem
Canonical `main` workspaces are being used for implementation, risking mixed provenance, accidental direct commits, and unsafe integration.

## Target Users
Agents, maintainers, repo stewards, and CI policy authors.

## Functional Requirements
- FR-01: Every code change MUST start from a fresh git worktree: `git worktree add .claude/worktrees/<scope>-<repo> -b <branch>`.
- FR-02: No code edits may occur directly on canonical `main` checkouts.
- FR-03: CI MUST reject direct-to-main pushes that bypass worktree isolation.

## Acceptance Criteria
- AC-01: No merge is accepted from a non-worktree branch.
- AC-02: Change evidence includes the worktree path and branch.

## Constraints
- Maintain the eco-017 20 GiB disk floor before creating worktrees.
