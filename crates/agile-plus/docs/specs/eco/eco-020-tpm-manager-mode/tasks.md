# Tasks — TPM Manager Mode (eco-020)

## WP-01 — Author spec artifact set
- Write `spec.md` with frontmatter, Problem, Target Users, FRs (FR-1..FR-7), ACs (AC-1..AC-6), Constraints.
- Write `plan.md` with Objective, Scope, Implementation Steps.
- Write this `tasks.md` and `meta.json`.
- **Done when:** all four files exist under `kitty-specs/eco-020-tpm-manager-mode/` and pass `agileplus validate-encoding --all --fix`.

## WP-02 — Bootstrap tick log
- Create `worklogs/PHENO_LAB_TICK.md` with header section and an entry schema reference.
- Write tick #1 entry (ISO timestamp, subagent count = 10, baseline re-read confirmed, sweep topics = TBD).
- **Done when:** file exists, is append-only, and tick #1 entry validates against the schema in `spec.md` FR-3.

## WP-03 — Cron re-arm contract
- Document the cron expression that fires `/goal` every 5 minutes.
- Document the re-arm command and idempotency rule.
- Add a "Cron Re-Arm Contract" section to `plan.md` (or a sibling doc under `kitty-specs/eco-020-tpm-manager-mode/`).
- **Done when:** re-arm command is documented and idempotency is provable from the doc alone.

## WP-04 — 10-tick acceptance run
- Execute a 10-tick dry run; populate tick #1..#10 in `worklogs/PHENO_LAB_TICK.md`.
- Verify AC-1 (≥10 subagents every tick), AC-2 (one dated entry per tick), AC-3 (cron re-armed), AC-4 (baseline re-read first), AC-5 (subagent death + re-dispatch recorded), AC-6 (append-only).
- **Done when:** all six ACs check pass on the dry run; results recorded in a final tick entry or a sibling verification doc.
