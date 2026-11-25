---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-017-disk-recovery-gate
spec_id: eco-017
state: PENDING
status: active
superseded_by: null
title: Disk Recovery Gate
type: operational
---
# Disk Recovery Gate

## Problem

A dispatched subagent was aborted on 100% disk usage during a cargo build-fix cycle, wasting compute and leaving a half-finished target tree. The fleet lacks a uniform pre-flight disk check, so multi-GB writes (cargo builds, worktree creation, artifact downloads) silently fail or truncate mid-operation. We need a gate that catches low-disk conditions *before* agents commit to write-heavy work.

## Target Users

- Dispatched subagents (Opus/Codex/Copilot workers)
- Fleet orchestrators launching multi-GB cargo or worktree operations
- Operators triaging aborted runs in worklogs

## Functional Requirements

- **FR-1** — Any agent initiating a worktree creation, `cargo build/test/clippy`, or write of ≥1 GiB must first run `df -h /System/Volumes/Data` and parse the `Avail` column.
- **FR-2** — If available space is **< 20 GiB**, the agent MUST abort the operation, log the failure with current `Avail` value, and emit a structured `DISK_GATE_FAIL` event to the worklog.
- **FR-3** — If available space is **< 10 GiB**, the agent MUST additionally run `target-pruner` (or equivalent documented in `FocalPoint/tooling/target-pruner`) before re-checking, and only proceed if disk recovers to ≥ 20 GiB after pruning.
- **FR-4** — The gate check must be a single command/binary callable from any agent harness (`disk-gate --min-gib 20 /System/Volumes/Data`).
- **FR-5** — Worklog entries for aborted runs MUST include: timestamp, triggering command, `Avail` value, abort reason.

## Acceptance Criteria

- No dispatched subagent silently fails due to disk exhaustion on a write-heavy operation.
- Any operation gated by this spec exits non-zero with a clear `DISK_GATE_FAIL` message when Avail < 20 GiB.
- Worklog records are queryable for disk-gate aborts and show full diagnostic context.
- Gate is idempotent: re-running after disk recovery proceeds normally.

## Constraints

- Disk is currently full — implementation work deferred until recovery.
- Gate must work on macOS APFS (`/System/Volumes/Data`); Linux path support is a non-goal for v1.
- No new shell scripts per the scripting hierarchy — implement in Rust under `FocalPoint/tooling/disk-gate`.
- Threshold (20 GiB) and path are configurable, not hard-coded, but ship with v1 defaults above.
