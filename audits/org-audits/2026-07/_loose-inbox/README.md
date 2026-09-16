# `_loose-inbox` — Absorbed Loose-Inbox Archive

This directory preserves the contents of `KooshaPari/zz-archive-_loose-inbox`
(archived 2026-07-15), which was a staging area for subagent outputs from
the 2026-07 cleanup wave that did not fit cleanly into any single
canonical repo at the time.

**Date merged:** 2026-08-08
**Source commit:** `KooshaPari/zz-archive-_loose-inbox@main`
**Merger:** forge-airlock (manual semantic integration)

## What this archive was

A "loose inbox" — files from 8 distinct subagent runs that landed in
`~/CodeProjects/Phenotype/repos/_loose-inbox/` during the 2026-07-14 wave
and were auto-imported to GitHub on 2026-07-15 as a single repo so they
could be tracked and reviewed together. None of these were ever turned
into canonical repos; they were intended as inputs/observations for
future audit work.

## Subdirectories (8 distinct artifacts, 121 files)

| Directory | Files | What it is |
|-----------|-------|------------|
| `bak-bmad-templates-2026-07-14/` | 83 | BMAD template snapshots (agent/workflow templates for bmad-builder, game-dev, etc.) — backup of a third-party template set |
| `contracts-metric-2026-07-14/` | 1 | `metric-contracts.json` — output of the contracts-metric subagent (contracts for metric emission) |
| `findings-helioscope-2026-06-21/` | 1 | `2026-06-21-L5-130-helioscope-retirement-cleanup.md` — finding doc from the L5-130 helioscope retirement |
| `pheno-compute-layer-2026-07-14/` | 20 | Pheno compute layer scratch (bin, config, providers, mcp, docs, scripts, skills) |
| `pheno-llm-level1-2026-07-14/` | 4 | Pheno LLM Level 1 scratch |
| `projects-control-plane-2026-07-14/` | 9 | Projects control plane scratch |
| `scripts-repo-duplicate-2026-07-14/` | 1 | `repo-duplicate-workflow.sh` — script for the repo-duplicate cleanup subagent |
| `worklogs-L5-130-2026-07-14/` | 1 | `L5-130-helioscope-cleanup-2026-06-21.json` — structured worklog for the L5-130 helioscope retirement |

## Note on the original symlink

The original `pheno-compute-layer-2026-07-14/skills/global` was a symlink
to `/Users/kooshapari/CodeProjects/Phenotype/skills`. It was preserved as
a metadata file at `pheno-compute-layer-2026-07-14/skills/global.md` because
absolute local paths don't transfer to GitHub.

## Status

Absorbed. All 121 source files preserved with original names. The `.gitignore`
from the source is preserved as `.gitignore.source` for reference.
