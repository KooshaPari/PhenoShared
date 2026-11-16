---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-013-<REDACTED>-oldest-first
spec_id: eco-013
state: PENDING
status: active
superseded_by: null
title: <REDACTED> Oldest-First
type: operational
---
# <REDACTED> Oldest-First

## Problem

Fleet remediation sweeps across the <REDACTED> GitHub organization currently have no documented ordering policy. Agents default to alphabetical, recency-first, or hand-picked targets, which systematically starves the oldest, least-touched repositories. Repos that have not been pushed to in the longest time accumulate latent issues, drift from the rest of the fleet, and never get remediated because agents keep reaching for the most recently active crates. Established by `worklogs/oldest-<REDACTED>-20260605.json`.

## Target Users

- Fleet remediation agents running multi-repo sweeps.
- Coordinator agents dispatching parallel subagents against <REDACTED>.
- Auditors verifying that remediation work is equitably distributed.

## Functional Requirements

- FR-1: Every fleet sweep MUST enumerate <REDACTED> repos via `gh repo list <REDACTED> --limit 200 --json name,pushedAt,isArchived`.
- FR-2: Sweeps MUST filter out `isArchived == true` repos before ranking.
- FR-3: Sweeps MUST sort the remaining set by `pushedAt` ascending (oldest first).
- FR-4: Sweeps MUST take the top N (N declared per sweep) from the sorted list as the remediation target set.
- FR-5: The top-N list with `name` and `pushedAt` timestamps MUST be embedded in the sweep worklog header.

## Acceptance Criteria

- AC-1: Given a sweep worklog, the top-N target list is present and shows ascending `pushedAt` timestamps.
- AC-2: Given a sweep, no archived repo appears in the top-N target list.
- AC-3: Given a sweep, the worklog records the exact `gh` command used, its output timestamp, and N.

## Constraints

- Single source of truth: `gh repo list <REDACTED> --limit 200` JSON output.
- Sort key: `pushedAt` ascending; ties broken by repo name ascending.
- Top N is fixed at sweep start; mid-sweep re-ranking is forbidden.
