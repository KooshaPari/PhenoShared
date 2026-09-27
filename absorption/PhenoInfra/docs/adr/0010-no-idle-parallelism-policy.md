# ADR 0010 — No-Idle Parallelism Policy

- **Status:** Accepted
- **Date:** 2026-06-16
- **Deciders:** Koosha Pari (solo-dev), scaffold agent (issue #77)
- **Supersedes:** none
- **Related:** `docs/governance/no-idle-parallelism-policy.md`, `worklogs/README.md`, ADR 0009 (hw-mesh-agent-bus)

## Context

The Phenotype org runs a large concurrent agent swarm (up to ~50 subagents in
flight) across the 7-node hybrid compute mesh (ADR 0001). The risk surface
this introduces:

- **Idle compute = wasted free tier.** Free-tier nodes (OCI Ampere, GCP e2-micro)
  have small, fixed allocations; an agent swarm that falls below a healthy
  parallelism floor leaves cycles on the table that any other workload could
  have used.
- **Idle compute ≠ "nothing to do".** Most weeks the queue (open issues, in-flight
  PRs, deferred sub-tasks, /loop follow-ups) is non-empty. An under-filled swarm
  is almost always a *routing or instrumentation* problem, not a *work* problem.
- **No measurement today.** The 2026-06-15 audit (issue #77) found zero
  worklog entries and therefore zero observable ticks. Without a defined
  "tick", a defined "in-flight count", and a defined "queueable work" set, the
  claim "we are not idle" is unfalsifiable.
- **No policy today.** The referenced document
  `docs/governance/no-idle-parallelism-policy.md` does not exist, so the
  threshold (referenced as `< 5 in-flight tasks = idle`) is undefined and
  unauditable.

Constraints:

- **Solo-dev operational model.** Audit must be runnable by an agent without
  human judgment; rules must be mechanical.
- **Zero new spend.** No new services. The audit is a local script over
  committed worklog files in the repo.
- **Per CLAUDE.md: ADR before IaC.** Governance changes that agents will
  enforce belong in `docs/adr/` before they land in `docs/governance/`.

## Decision

Adopt a **no-idle parallelism policy** with the following components:

1. **Tick definition.** A *tick* is a single committed entry to a session
   worklog (`worklogs/SESSION_<id>.md`) produced by a `/loop` run. Ticks are
   the unit of measurement; an audit week is a set of ticks whose `tick_ts`
   falls inside the ISO week.

2. **In-flight task definition.** A task is *in-flight* if it appears in the
   `active_count` field of a tick entry. The agent counts:
   - subagents it has spawned and not yet joined,
   - CI jobs dispatched but not yet completed (best-effort, via Woodpecker API
     if reachable; otherwise omitted from count and flagged in `notes`),
   - open PRs the agent is the author of and has not marked ready-to-merge.

3. **Queueable work definition.** *Queueable work* is any of:
   - open issues with label `agent-runnable` (or unlabeled) in the org,
   - `/loop`-tracked follow-ups recorded in the session worklog's
     `queued_tasks[]` field,
   - TODOs in the agent's current worktree that match a tracked spec.

4. **Idle threshold.** A tick is an *idle violation* iff
   `active_count < IDLE_THRESHOLD` **and** `queued_tasks[]` is non-empty.
   `IDLE_THRESHOLD` defaults to **5** (matching the figure in issue #77);
   changes to the threshold require a new ADR.

5. **Worklog schema.** See `docs/governance/no-idle-parallelism-policy.md`
   § "Worklog Schema". The schema is the contract the audit script consumes.

6. **Audit routine.** An audit run is a deterministic pass over
   `worklogs/SESSION_*.md` (and the per-week rollup at
   `worklogs/SESSION_<iso-week>.md` if present) that emits:
   - `total_ticks`
   - `idle_violation_ticks`
   - `idle_ratio = idle_violation_ticks / total_ticks`
   - list of `(tick_ts, session_id, active_count, queued_tasks)` rows.

7. **Audit hosting.** The audit routine ships as a Rust binary in a future
   `phenotype-audit` crate (out of scope for this issue; ADR 0010 only commits
   the schema and policy). Wiring the audit into a scheduled CI workflow is
   explicitly deferred (see Consequences).

## Consequences

**Positive**

- Makes the "are we idle?" question falsifiable for the first time.
- Forces `/loop` sessions to emit structured evidence, which feeds the
  journey-traceability standard (`docs/governance/journey-traceability-standard.md`).
- Single threshold (5) is small enough to reason about; ADR-gated changes
  prevent silent policy drift.

**Negative**

- Schema enforcement is a *social* contract until a parser lints worklog
  entries in CI (deferred).
- `active_count` is best-effort; the CI-job component can be wrong if the
  Woodpecker API is unreachable. The schema's `notes` field is the escape
  hatch; auditors must surface notes that look like "ci_unreachable: true".
- Counting open PRs the agent authored requires the agent to record its own
  identity in the worklog, which is a soft contract.

**Neutral**

- Requires per-session worklog files; agents must remember to append on each
  /loop iteration.

**Deferred (out of scope for this ADR / issue)**

- GitHub Actions workflow that runs the audit on a weekly schedule and posts
  results to a tracking issue. (Out of scope per agent directives that
  forbid modifying `.github/workflows/`; deferred to a follow-up issue.)
- Cross-repo audit aggregation. The policy is per-repo for now.

## Alternatives considered

1. **No policy; rely on gut feel.** Rejected: this is what produced issue #77
   (audit returned zero data and no actionable signal).
2. **Lower threshold (e.g. 2 or 3).** Rejected: too sensitive; a solo-dev
   week genuinely has <5 subagents in flight during human-driven blocks
   (writing an ADR, reviewing a PR), and those are not idle violations.
3. **Higher threshold (e.g. 10).** Rejected: hides real under-utilization
   on the heavy runner (ADR 0003) which can comfortably host 10+ cargo
   sub-jobs in parallel.
4. **Tie policy to a specific agent framework API.** Rejected: locks the
   policy to one toolchain; the schema + worklog-file approach is
   framework-agnostic.
5. **Per-node threshold.** Considered: would let OCI Ampere (4 OCPU) carry
   a smaller threshold than the home Mac. Deferred: adds complexity to
   the audit script for marginal accuracy gain; revisit when the
   `phenotype-audit` crate lands.

## Related

- ADR 0001 — Hybrid compute mesh (the substrate this policy audits)
- ADR 0003 — Home desktop as heavy runner (the node most likely to be idle)
- ADR 0009 — hw-mesh-agent-bus (Phase 2; will eventually report in-flight
  counts directly, replacing the best-effort agent-side accounting)
- `docs/governance/journey-traceability-standard.md` (sibling standard for
  visible-flow evidence)
- `worklogs/README.md` (where session worklogs live)
- Issue #77 (the audit that surfaced the gap this ADR closes)
