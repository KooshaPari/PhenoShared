# `zz-archive-phenotype-org-audits-archive2` — Preserved Snapshot

This directory preserves unique content from the `KooshaPari/zz-archive-phenotype-org-audits-archive2`
GitHub repository (archived 2026-07-15, after `KooshaPari/phenotype-org-audits`
was deleted 2026-07-14 and recreated 2026-07-17 following Sentry PAT rotation).

**Date merged:** 2026-08-08
**Source commit:** `KooshaPari/zz-archive-phenotype-org-audits-archive2@main`
**Merger:** forge-airlock (manual semantic integration)

## What this archive was

A pre-2026-07-14 snapshot of `phenotype-org-audits` (the original deleted
repo), restored 2026-07-17 from a local clone after Sentry PAT rotation
forced a fresh init of the live repo. The live repo was reseeded from
`pnpm`-manifests + ADR files and lost most of the original `.claude/`
working-tree state.

## What was preserved (and why)

The diff against the live `phenotype-org-audits` (post-2026-07-17) revealed
that ~95% of the archive content was already present in the live tree.
Only the following UNIQUE content was preserved here:

### 1. `.claude-worktrees-snapshot_audit-rebuild-v38/` (370 files)

A complete snapshot of the `audit-rebuild-v38` Claude worktree from the
original `phenotype-org-audits` repo — 370 files spanning the full
audit rebuild work-in-progress that was active in mid-2026:

- `audit-30-pillar/audit-30-pillar-L*.md` — the L0-L29 audit pillar catalog
- `audit-v38/catalog/{clusters.tsv, PILLARS-INDEX.md, SCORECARD-TEMPLATE.md, WORKER-SPEC.md}`
- `audit-v38/output/{SessionLedger, substrate}/` — audit session outputs
- `audits/2026-04-24/` — the April 24 absorption audit (Cargo.toml, INDEX.md, etc.)
- `audits/2026-06-18_ADR-03*` — the ADR-030 through ADR-042 wave
- `audits/{drift-detector, framework-lint, predict-dry, worklog-schema}/`
  — the pheno tooling audits (each is a full sub-project with `pyproject.toml`,
  `tests/`, `SPEC.md`, `MANIFEST.md`)
- `audits/services/` — scorecard, SBOM templates, BLOCK-C plans
- `catalog/RUBRIC-LINEAGE.md` — the audit lineage document
- `consolidation/` — config + observability consolidation plans
- `curation/forge/` — curation candidate tooling (`candidates.tsv`, `curate.py`)
- `findings/2026-06-17-L5-104-*` and `findings/2026-06-18-McpKit-branch-only/`
  — the L5 audit findings and the McpKit branch-only investigation
- `forge-runner-scripts/` — 35+ shell scripts for autoqueue, subagent orchestration
- `inventory/{AUTHORITATIVE_REPO_INVENTORY, deleted_traces, github_remote_inventory}.md`
- `metrics/`, `pillar-scores/` — scorecards
- `ops/heavy-runner-cron/` — cron infrastructure
- `plans/2026-06-17-v7-dag-stable.md`, `2026-06-29-ownership-program.md`
- `work-dag-2026-06-17-v7-extended.md`, `work-dag-2026-06-17-wrapup.md`
- `worklogs/{ARCHITECTURE, GOVERNANCE, RESEARCH}.md`

The `audit-rebuild-v38/` worktree is the most historically valuable artifact
in this archive — it represents the **only surviving copy of the work-in-progress
state** of the v38 audit rebuild, which was the basis for the ADR-030 → ADR-042
wave.

### 2. `audits-2026-04-24-aggregator-Cargo.lock/`

A single `Cargo.lock` from `audits/2026-04-24/aggregator/`. The live tree
has the `Cargo.toml` and `src/main.rs` but not the lockfile. This preserves
the exact dependency pinning for the audit aggregator tool.

### 3. `modified-files/` (6 files)

Files that exist in BOTH the archive and the live tree but with **divergent
content** (the live tree has newer versions, the archive has the
pre-2026-07-14 versions). Each is preserved here with a `.pre-2026-07-14`
suffix:

- `audit-v38/output/SessionLedger/{C03, C10, C11}.md.pre-2026-07-14`
- `curation/forge/candidates.tsv.pre-2026-07-14`
- `docs/remediation/misleading-green-ci.md.pre-2026-07-14`
- `plans/AUDIT_CURSOR.md.pre-2026-07-14`

These were the files actively being edited when the original repo was
deleted and represent the **last-known working state** before the deletion.

## Status

Absorbed. 372 files preserved under `audits/2026-07/zz-archive-archive2/`.
The remaining ~700 files in the source archive were duplicates of live
content (or `.github/workflows/` which is intentionally not merged — see
`audits/_phenofleet-decisions/.github/workflows/ci.yml` for the captured
`ci.yml` reference artifact).
