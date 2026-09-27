# Absorption Record — phenoResearchEngine

## Transfer Record

| Field | Value |
|-------|-------|
| Source repo | `<REDACTED>/phenoResearchEngine` |
| Target repo | `<REDACTED>/pheno` |
| Where it lives (intended) | **PENDING — not absorbed into PhenoShared**. Originally intended for `phenotype-research-engine/` in `<REDACTED>/pheno`. Per FORWARD-WBS §5 / Notes below: `phenoResearchEngine` was DEPRECATED with migration to `packages/phenotype-research/` planned; neither path materialized. `find . -maxdepth 5 -type d -name "phenotype-research-engine"` returns zero hits across the tree. Closest live content: `crates/fabric-research-ledger/` (Rust, different name and lineage — `fabric-` prefix not `phenotype-`); `research/` at root (baselines + rlvr_af experiment fixtures, also unrelated). The stale `crates/hexa-kit/PHENOTYPE_INDEX.md:43` row still references `phenotype-research-engine` as if it existed; the row is also stale and not load-bearing. |
| Absorbed date | 2026-07-17 |
| Absorbed by | forge agent (batch absorption) |
| Verification | File count match: 140 files (175 items incl. dirs) |

## What was absorbed

Python research/investigation service: 6 source modules, 7 crawlers, MCP tools,
5 test files, docs, ports (TypeScript), configs, workflows.

## Notes

- phenoResearchEngine was already in DEPRECATED state with migration to
  `packages/phenotype-research/` planned.
- Target directory `phenotype-research-engine/` existed empty in the `pheno` monorepo.
