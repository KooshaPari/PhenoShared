# Plan — TPM Manager Mode (eco-020)

## Objective

Codify and operationalize the **openclaw-persistent SSWE/TPM manager-mode loop** for the Phenotype lab: a durable, cron-re-armed, 5-minute tick loop that keeps ≥10 background subagents alive, logs every tick, and dispatches sweeps to keep the lab DAG extending.

## Scope

**In scope**
- `kitty-specs/eco-020-tpm-manager-mode/` artifact set (spec, plan, tasks, meta).
- `worklogs/PHENO_LAB_TICK.md` schema and append contract.
- Operational rules: subagent floor, tick cadence, cron re-arm, baseline re-read, sweep dispatch, graceful-exit-only.
- Coordination with existing `worklogs/aggregate.sh` and `[autonomous_repo_lab_goal]` memory.

**Out of scope**
- New git operations, worktrees, or branches (disk-full constraint).
- Cross-project shared module extraction (handled by separate kitty-specs).
- CI/scheduled workflow changes (billing ceiling).

## Implementation Steps

1. **Spec authoring** — produce `spec.md` with FRs/ACs as written. *(DONE in this WP)*
2. **Tick log bootstrap** — create `worklogs/PHENO_LAB_TICK.md` with header + first tick entry (tick #1, ISO timestamp, subagent count = 10, baseline re-read confirmed).
3. **Cron registration** — define the cron expression that fires the `/goal` prompt every 5 minutes; document the re-arm command and idempotency rule.
4. **Sweep catalog** — enumerate the standing sweep topics dispatched per tick (cross-repo audits, worklog aggregation, RUSTSEC, kitty-spec gap detection, branch hygiene, worktree discipline).
5. **Failure-mode playbook** — document responses to: subagent death (re-dispatch same tick), cron re-arm duplicate (idempotent skip), disk-full (pause + notify), CI-billing failure (proceed locally).
6. **Acceptance run** — execute a 10-tick dry run; verify AC-1..AC-6 against `worklogs/PHENO_LAB_TICK.md`.
7. **Meta + tasks** — emit `meta.json` and `tasks.md` (WP-01..WP-04) and link this spec from `worklogs/README.md` index.
