# No-Idle Parallelism Policy

- **Status:** Accepted
- **Date:** 2026-06-16
- **ADR:** `docs/adr/0010-no-idle-parallelism-policy.md`
- **Owner:** Koosha Pari (solo-dev)
- **Source issue:** #77

## Purpose

The Phenotype org runs a large concurrent agent swarm across the 7-node hybrid
compute mesh (ADR 0001). Idle swarm capacity on free-tier nodes is wasted
capacity, but "idle" is not a property the repo can currently observe: there is
no tick definition, no in-flight task definition, no threshold, and no
structured worklog to audit. This policy closes that gap so an audit can return
a non-null signal and so a violation is a falsifiable claim, not a feeling.

## Definitions

| Term | Definition |
|------|------------|
| **Tick** | A single committed entry in a session worklog (`worklogs/SESSION_<id>.md`) produced by one `/loop` iteration. |
| **In-flight task** | A task counted in a tick's `active_count` field. See "What Counts as In-Flight" below. |
| **Queueable work** | Work that is *available* to the swarm right now. See "What Counts as Queueable Work" below. |
| **Idle violation** | A tick where `active_count < IDLE_THRESHOLD` **and** `queued_tasks[]` is non-empty. |
| **Audit week** | An ISO week (e.g. `2026-W24`). Ticks are bucketed by `tick_ts` into weeks. |
| **IDLE_THRESHOLD** | The integer below which a tick is considered under-filled. Default: **5**. Changes require a new ADR. |

## IDLE_THRESHOLD

Default: **5**.

Rationale (see ADR 0010 § Alternatives for the full discussion):

- Below 2 is trivially "everything stopped" and not interesting to audit.
- A solo-dev week spends a non-trivial fraction of ticks in the 2–4 range
  during *human-driven* blocks (ADR writing, PR review). Those are not idle
  violations because `queued_tasks[]` is empty.
- 5 is high enough to surface real under-utilization on the home-Mac heavy
  runner (ADR 0003) which can host 10+ cargo sub-jobs in parallel, and low
  enough to be reachable on free-tier days.

## What Counts as In-Flight

A task counts toward `active_count` if **any** of the following is true at
the moment of the tick:

1. The agent has spawned a subagent for it and not yet joined.
2. A CI job has been dispatched on the agent's behalf (e.g. via Woodpecker)
   and has not yet reported a terminal status. The agent should make a
   best-effort count via the Woodpecker API; if the API is unreachable, the
   agent omits CI jobs from the count and records `ci_unreachable: true` in
   the tick's `notes` field.
3. An open PR exists where the agent is the author and the PR is not yet
   marked ready-to-merge / not yet merged.

The agent must not double-count a task that satisfies multiple bullets.

## What Counts as Queueable Work

A task is queueable if **any** of the following is true:

1. An open issue exists in the org that is labeled `agent-runnable` or is
   unlabeled, and the agent is not already working on it.
2. The agent has a recorded `/loop` follow-up that is not yet in `active_count`.
3. The agent's current worktree has a tracked TODO that matches a tracked
   spec or ADR.

Closed issues, PRs the agent does not own, and work the agent has explicitly
deferred with a reason recorded in the worklog are **not** queueable.

## Worklog Schema

This is the contract the audit script consumes. A worklog file is
`worklogs/SESSION_<session-id>.md` where `<session-id>` is a stable opaque
identifier (e.g. a UUID, or `YYYY-Www` for a weekly rollup).

### File layout

```md
# Session Worklog — <session-id>

- **Agent:** <agent-id>
- **Loop started:** <ISO-8601 timestamp>
- **ADR reference:** docs/adr/0010-no-idle-parallelism-policy.md
- **IDLE_THRESHOLD:** 5

## Ticks

| tick_ts | active_count | queued_tasks | idle_violation | notes |
|---------|--------------|--------------|----------------|-------|
| 2026-06-16T10:00:00Z | 6 | [] | false |  |
| 2026-06-16T10:05:00Z | 3 | [issue-42, pr-77-followup] | true | ci_unreachable: true |
```

### Field rules

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `tick_ts` | ISO-8601 UTC timestamp | yes | One row per `/loop` iteration. |
| `active_count` | non-negative integer | yes | Counted per the "What Counts as In-Flight" rules. |
| `queued_tasks` | list of strings | yes | Use `[]` when empty, never omit. Each entry is a stable reference (`issue-N`, `pr-N`, `adr-NNNN`, or a free-form id). |
| `idle_violation` | boolean | yes | Computed: `active_count < IDLE_THRESHOLD && queued_tasks.length > 0`. The agent writes the computed value; the audit script re-checks. |
| `notes` | string | no | Free-form. Reserved keys: `ci_unreachable: true`, `human_block: true` (excluded from idle count), `deferred: <reason>`. |

### Weekly rollup (optional)

For audit-friendly aggregation, a file
`worklogs/SESSION_<iso-week>.md` (e.g. `worklogs/SESSION_2026-W24.md`) may
mirror the same schema with one row per tick across all session files in
that week. The audit script prefers the rollup when present.

## Audit Routine

Given a target ISO week `W`, an audit run:

1. Globs `worklogs/SESSION_*.md`. If none, emit a null result (this is the
   failure mode issue #77 reported).
2. Parses the **Ticks** table per the schema above. Rows with malformed
   `tick_ts`, non-integer `active_count`, or missing `queued_tasks` are
   flagged `parse_error: true` and excluded from the ratio computation but
   counted in a separate `parse_errors` field of the report.
3. Buckets rows into `W` by `tick_ts`.
4. Computes:
   - `total_ticks`
   - `idle_violation_ticks`
   - `idle_ratio = idle_violation_ticks / total_ticks` (0 when
     `total_ticks == 0`)
   - list of `(tick_ts, session_id, active_count, queued_tasks)` for every
     idle violation
   - `parse_errors` count
5. Emits the report as Markdown (matching the format used in issue #77's
   "Findings" section) plus a machine-readable JSON sidecar
   `worklogs/audit_<iso-week>.json` for CI consumption.

The audit routine is **read-only**; it never modifies worklog files.

## Out of Scope (Deferred)

- A GitHub Actions workflow that runs the audit on a weekly cron and posts
  results to a tracking issue. (Per agent directives in
  `~/.claude/rules/`, modifying `.github/workflows/` is out of scope for
  this fix. Tracked as a follow-up issue.)
- A Rust crate hosting the audit binary. (ADR 0010 defers this to a
  dedicated `phenotype-audit` repo.)
- Cross-repo aggregation. The policy is per-repo for now.

## Related

- ADR 0010 — No-Idle Parallelism Policy
- ADR 0001 — Hybrid compute mesh
- ADR 0003 — Home desktop as heavy runner
- ADR 0009 — hw-mesh-agent-bus (Phase 2)
- `docs/governance/journey-traceability-standard.md`
- `worklogs/README.md`
- Issue #77
