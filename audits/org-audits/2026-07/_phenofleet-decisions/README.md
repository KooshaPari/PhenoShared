# `_phenofleet-decisions` — Absorbed Audit Archive

This directory is the absorption target for the `KooshaPari/_phenofleet-decisions`
GitHub repository, which was archived on 2026-07-15.

**Date merged:** 2026-08-08
**Source commit:** see `migration-2026-07-14.json`
**Merger:** forge-airlock (manual semantic integration)

## What this repo was

`_phenofleet-decisions` was the operational state-tracking repository used by
the **phenofleet** (a phenotyped fleet of subagents that ran the `airlock` and
`airlock-v2` ingestion pipelines during the 2026-07 cleanup wave). It held:

- **airlock-decisions** — 19 immutable decision records (`2026-07-14-*`,
  `2026-07-15-*`) logging which orphaned repos were absorbed into which
  canonical home, which were abandoned as duplicates, and which were removed
  from the airlock staging area entirely. These are the canonical absorption
  decisions for the 2026-07-14 → 2026-07-15 cleanup wave and were the basis
  for the wave 11 (Phenotype organization audit).
- **airlock-v2** — Implementation of the second-generation airlock pipeline
  (smoke test, auto-commit daemon, cleanup daemon, LaunchAgent plists, hooks
  for claude/codex/cursor). Operational artifacts preserved as a snapshot;
  the live airlock-v2 is now at `KooshaPari/phenotype-harness/airlock-v2/`.
- **unpushed-recovery-parkings** — 7 stashes/files recovered from local
  subagent working trees that were never pushed upstream during the cleanup
  wave. These contain work-in-progress that was resumed and landed in
  canonical repos.
- **worktree-archived / worktree-orphans / worktree-parkings** — Snapshot
  archives of git worktrees that were abandoned mid-flight during the wave
  (paths to the original repos in the file names).
- **skip-decisions / stash-recovery-parkings** — Rationale documents and
  stash recovery artifacts.
- **push-deferred/phenotype-infra-2026-07-15.bundle** — A git bundle of
  `phenotype-infra` that was too large to push via the GitHub web flow at
  the time; later pushed directly via `git push`.
- **scripts/audit-misplaced-repos.py** — Tooling that audited repos whose
  content did not match their declared language/topics. The current
  generation of this tool lives at `KooshaPari/phenotype-tooling/`.
- **migration-2026-07-14.json** — Full machine-readable migration map for
  the 2026-07-14 → 2026-07-15 cleanup wave.
- **2026-07-06-reactivation-decision.md** — Long-form rationale for
  re-activating the phenofleet subagent fleet on 2026-07-06 after a
  multi-week pause.

## Provenance

- **Created:** 2026-07-15 (auto-import by subagent-2 from local
  `~/CodeProjects/Phenotype/repos/_phenofleet-decisions/`)
- **Classification:** `DATA_ONLY` — no live code, only operational records
- **Original GitHub:** `KooshaPari/_phenofleet-decisions` (deleted 2026-08-08)
- **Local source:** `~/CodeProjects/Phenotype/repos/_phenofleet-decisions/`
  still exists and was the source of truth for this merge

## Why here

`phenotype-org-audits` is the canonical home for all historical organizational
audit records (ADR-030 absorption audit, dependency audits, security audits).
The `_phenofleet-decisions` repo was an operational log of a specific audit
wave — it belongs alongside the rest of the audit trail at
`audits/2026-07/`.

## Status

Absorbed. The 56 files in this directory preserve 100% of the source
content (excluding `.github/workflows/ci.yml`, which is preserved here as a
reference artifact, and `.gitignore`, preserved as `.gitignore.source`).
