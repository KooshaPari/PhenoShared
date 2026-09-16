# PhenoDesign — CREATIVITY / DESIGN / UX Spine

**Status**: LIVE spine member (2026-07-20)  
**GitHub**: `KooshaPari/phenoDesign`  
**Registry row**: `projects/phenoDesign.json`, disposition-index `repo-phenoDesign`

## Spine role

| Field | Value |
|-------|-------|
| **Role** | `CREATIVITY_DESIGN_UX` |
| **Tier** | Tier 2: Operational (creativity stack) |
| **Owns** | Design tokens, UX patterns, art direction, `@phenotype/design` |
| **Peer** | `asset-engine` — asset render pipeline (extracted from `engine/`) |

## Structure

```
phenoDesign/
├── tokens / package root     # @phenotype/design
├── docs/                     # UX + style guide
├── engine/                   # compatibility pointer → KooshaPari/asset-engine
└── .github/                  # CI for design package
```

## Why a spine member, not absorbed

- Dedicated release train for design tokens consumed across the fleet
- Own VitePress theme and W3C DTCG token pipeline
- Creativity/UX boundary distinct from docs hosting (`phenodocs`) and graphics SDK (`phenotype-gfx`)
- Asset pipeline split to `asset-engine` keeps render tooling independently versioned

## Absorption reversal

2026-07-17 absorption into `phenodocs/packages/design/` is **reversed** (2026-07-20). phenoDesign is canonical; phenodocs may consume tokens downstream.

## Cross-references

- `docs/spine/SPINE-DEFINITION.md` — spine table
- `docs/boundary/PhenoDesign.md` — boundary declaration
- `docs/boundary/asset-engine.md` — pipeline peer
- `BOUNDARY_OWNERS.md` — creativity stack matrix
