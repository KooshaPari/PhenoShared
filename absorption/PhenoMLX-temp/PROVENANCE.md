# PROVENANCE.md — PhenoMLX-temp Absorption

## Source Repository

- **Repository**: `KooshaPari/PhenoMLX-temp`
- **URL**: https://github.com/KooshaPari/PhenoMLX-temp
- **Commit**: `70529a879715a8078e26eb564f8fc312e1923f57`
- **Commit message**: `docs: fix remote URL in handoff`
- **Commit date**: 2026-09-16
- **Absorbed**: 2026-09-27

## What Was Absorbed

A **temp snapshot** of the PhenoMLX / phenotype-omlx project (1356 files,
10 MB source): `apps/`, `cli/`, `gui/`, `config/`, `docs/`, `evals/`,
`hfscope/`, `kitty-specs/`, `ARCHITECTURE.md`, `ADR.md`, `COMPARISON.md`,
`FUNCTIONAL_REQUIREMENTS.md`, etc.

## Why Absorbed

Consolidate repo sprawl. This repo is explicitly a *temp* copy:

- `phenotype-omlx` and `PhenoMLX` resolve to the **same live repo**
  (`KooshaPari/PhenoMLX`, a fork of `jundot/omlx`), pushed 2026-09-27 —
  active and distinct from this snapshot.
- The source repo carried ~646 MB of committed `.cargo-target/` build
  artifacts and a 194 MB `.git`; only the 10 MB of real source is absorbed.

## Notes

- Plain copy (no `.git`), matching the `absorption/*` pattern.
- **Excluded**: `.cargo-target/` (build artifacts), `.git`, `node_modules`,
  `__pycache__`.
- If unique work from this snapshot is needed later, the live
  `KooshaPari/PhenoMLX` repo is the canonical source.

## Source Repo Status

- GitHub repo remains **unarchived** pending operator confirmation.
