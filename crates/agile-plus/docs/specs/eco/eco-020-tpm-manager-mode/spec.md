---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-020-tpm-manager-mode
spec_id: eco-020
state: PENDING
status: active
superseded_by: null
title: TPM Manager Mode
type: operational
---
# TPM Manager Mode (openclaw-persistent)

## Problem

The OpenClaw / Phenotype lab requires a **Technical Program Manager (TPM) manager-mode loop** that keeps a persistent swarm of background agents alive across ticks. Today there is no canonical document describing:

- the minimum subagent count and lifecycle (≥10 active background agents),
- the 5-minute tick cadence and how each tick is logged,
- cron re-arming of the `/goal` prompt after every tick,
- baseline re-reading of worklog/repo state at the start of each tick,
- sweep-dispatch rules for new work detected during the tick.

Without this spec, the loop degrades into ad-hoc prompting, ticks are missed, subagents die, and latent lab issues go un-surfaced. The R&D-lab mandate (extend the DAG, keep sweeping) cannot be honored without a durable, documented loop.

## Target Users

- **Parent coordinator agent (Opus)** — owns the loop, synthesizes findings, never runs tools longer than a tick allows.
- **Dispatched subagents (Codex, cheap-llm)** — do repo work, return summaries, get re-spawned each tick.
- **Phenotype operator (Koosha)** — observes the loop via `worklogs/PHENO_LAB_TICK.md`; can pause/inspect without breaking it.

## Functional Requirements

- **FR-1 Subagent floor.** The session must maintain **≥10 active background subagents** at all times during a tick window. If any subagent terminates, the parent must re-dispatch within the same tick to restore the floor.
- **FR-2 5-minute tick cadence.** Each tick is exactly **5 minutes** of wall-clock. A tick boundary is the moment the cron job fires the `/goal` prompt.
- **FR-3 Tick log append.** On every tick, append a dated entry to `worklogs/PHENO_LAB_TICK.md` with: tick number, ISO timestamp, subagent count, sweep topics dispatched, worklog deltas observed, next-tick plan.
- **FR-4 Cron re-arm.** After every tick, re-arm the cron job that fires the `/goal` prompt so the next tick fires 5 minutes later. Re-arm is **idempotent** — a duplicate re-arm within the same tick must not produce overlapping prompts.
- **FR-5 Baseline re-read.** At the start of every tick, re-read the baseline state: `worklogs/README.md` index, `worklogs/PHENO_LAB_TICK.md` (last 5 entries), and the active `kitty-specs/` index. Baseline re-read must complete before any sweep dispatch.
- **FR-6 Sweep dispatch.** During the tick, dispatch sweep work to the ≥10 subagents (e.g., cross-repo audits, worklog aggregation, RUSTSEC scans, kitty-spec gap detection). Each dispatch is recorded in the tick log entry.
- **FR-7 Graceful exit only.** The loop terminates only on operator command or unrecoverable error. A subagent crash is **not** a termination signal — it triggers a re-dispatch per FR-1.

## Acceptance Criteria

- **AC-1** A 10-tick run produces **≥10 active subagents at every tick** (verified by tick log).
- **AC-2** `worklogs/PHENO_LAB_TICK.md` contains **one dated entry per tick** with all required fields (tick #, timestamp, subagent count, sweeps, deltas, next plan).
- **AC-3** After each tick, the cron job is re-armed; the next `/goal` prompt fires within 5m ± 30s.
- **AC-4** Baseline re-read is documented as the first action of every tick log entry.
- **AC-5** Killing a single subagent mid-tick triggers a re-dispatch within the same tick; the tick log records the death and replacement.
- **AC-6** Tick log file is append-only — no entries are deleted or rewritten in place.

## Constraints

- No git operations, no worktree creation (disk is full — verified 2026-06-05).
- All file writes are limited to `kitty-specs/eco-020-tpm-manager-mode/` and `worklogs/PHENO_LAB_TICK.md`.
- Loop must respect GitHub Actions billing ceiling — no CI-driven sweep dispatch; sweeps are local-only.
- Subagent dispatch must use the `dispatch` / `codex-agent` / `cheap-llm` skills per global CLAUDE.md.
- Tick log entries are markdown; one blank line between entries; ISO-8601 UTC timestamps.
- Parent coordinator never runs `git reset --hard`, `git restore`, or `git clean`.
