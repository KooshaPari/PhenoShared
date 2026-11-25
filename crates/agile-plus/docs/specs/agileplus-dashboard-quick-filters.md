# AgilePlus Dashboard Quick Filters

## Summary

Add a small dashboard polish increment: quick filter chips for the live backlog view so a project manager can jump directly to blocked, review, or active stories without manually scanning the full board.

## Current Capability

AgilePlus already ships a live dashboard backed by SQLite data, including the epics backlog and a filtered story list. The product also has read-only CLI list commands for projects, epics, and stories, plus syncing and triage flows that map external work into local domain entities. That means the data is present, but the day-to-day PM workflow still depends on visually hunting through the board to isolate the most urgent items.

Traceability:
- FR-AGP-014: Web dashboard for project/backlog visualization
- FR-AGP-016: CLI read/list subcommands
- FR-AGP-017: Triage automation for synced items

## Proposed Increment

Add persistent, single-click dashboard filters for:

- `Blocked`
- `In Review`
- `Active`
- `All`

The default view remains unchanged. The new controls only narrow the existing live story list and keep the current Kanban/card layout intact.

## Why This Matters

This is a high-value usability improvement for a narrow PM MVP because it reduces the time required to answer the most common question on a live board: "what needs attention right now?" It also complements the shipped triage automation by making the outcome of triage immediately visible.

## Scope

In scope:

- Add a small filter control above the live story list.
- Filter stories client-side using the already-fetched dashboard payload.
- Preserve the existing default state when no filter is selected.
- Keep the change reversible and isolated to the dashboard surface.

Out of scope:

- New persistence model for saved views.
- New backend query endpoints.
- Bulk actions or editing flows.
- Cross-project analytics.

## Acceptance Notes

- PMs can switch between the filter chips without page reload.
- The filtered count is visible so the board stays scannable.
- The default "All" state renders the same content as today.
- No new secrets, env vars, or background jobs are required.

## Risk / Cost

Low implementation risk and low performance impact. The filter operates on already-loaded data, so it should not increase backend load. The only expected cost is a small amount of client-side state and rendering logic.

