# PROVENANCE.md — phenotype-canonicalization Absorption

## Source Repository

- **Repository**: `KooshaPari/phenotype-canonicalization`
- **URL**: https://github.com/KooshaPari/phenotype-canonicalization
- **Commit**: `570e2c73aff565620a2c518a37d258981a31ca9e`
- **Commit message**: `docs: finish SOURCE-INDEX split (589 -> 348 lines, under 500 limit)`
- **Commit date**: 2026-09-17
- **Absorbed**: 2026-09-27

## What Was Absorbed

An agent-authored documentation/audit project covering canonicalization patterns:
`audit/`, `research/`, `examples/`, `migration/`, `schemas/`, `tests/`, `tools/`,
`verification/`, plus decision trees, a pattern matrix, coverage data, and
multi-part reports (`REPORT.md`, `REVIEW-REPORT.md`, `DOCS_REVIEW.md`,
`AUDIT-RUNBOOK.md`, `AGENT-HANDOFF.md`, `SOURCE-INDEX*.md`).

## Why Absorbed

Consolidate repo sprawl. Source repo is small (44 files, 468 KB source), is
purely documentation/tooling (no build), and was authored by agent work that
belongs with the rest of the Phenotype governance corpus.

## Notes

- Plain copy (no `.git`), matching the `absorption/*` pattern.
- Build/dependency dirs excluded (`.git`, `node_modules`, `__pycache__`).
- No overlapping copy of this corpus existed in PhenoShared at absorption time
  (`docs/ABSORPTION_INDEX.md` had no prior entry).

## Source Repo Status

- GitHub repo remains **unarchived** pending operator confirmation.
