# asset-engine — Asset Pipeline Boundary

**Status**: `LIVE` / `DECLARE_BOUNDARY_OWNER` (2026-07-20)  
**Source**: `github.com/KooshaPari/asset-engine`  
**Extracted from**: `KooshaPari/phenoDesign/engine/`  
**Spine peer**: `KooshaPari/phenoDesign` (creativity / design / UX spine)

## Description

asset-engine is the **canonical boundary owner** for the Phenotype multi-tool asset creation pipeline. It produces branded UI graphics, icons, heroes, 3D renders, and cinematics at scale.

## Tool legs

| Leg | Purpose | Entry |
|-----|---------|-------|
| Blender | 3D icons, heroes | `blender/*.py` |
| ImageMagick | Raster ops, favicons | `imagemagick/*.sh` |
| FFmpeg | Video transcode | `ffmpeg/*.sh` |
| Unreal | Cinematics (stub) | `unreal/` |
| Adobe | CC automation (gated) | `adobe/` |
| Orchestrator | Manifest dispatch | `orchestrator/driver.py` |

## In scope

- Headless render scripts and orchestrator
- Brand token injection at render time (`orchestrator/tokens.json`)
- Sample outputs and manifest schema

## Out of scope

| Slice | Owner |
|-------|-------|
| Design tokens SSOT | `phenoDesign` |
| UX patterns / component library | `phenoDesign` |
| Docs site theme | `phenoDesign` |

## Migration

Seeded from `phenoDesign/engine/` on 2026-07-20. See `MIGRATION.md` in the asset-engine repo for consumer repointing guidance.
