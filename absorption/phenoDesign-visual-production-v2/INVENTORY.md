# Delivered inventory

Prepared September 15, 2026. This ZIP contains 179 files including this inventory and its SHA-256 manifest.

## Scope

- **45 skill files**: 26 newly authored workflows, 18 original workflows retained from v1, and one unchanged licensed upstream Anthropic frontend-design skill.
- **71 annotated resource entries**, with reference-only/partial/inspected distinctions; links do not imply installed or runtime-qualified tools.
- **84 original v1 files**, byte-compared against the original supplied ZIP with no changes.
- A private phenoDesign integration-primitives package, guarded Remotion source replacements, dry-run-first installer, native Illustrator/Photoshop/After Effects recipes, Rive route, local media checks, an interactive SVG fixture and real synthetic encoded media.
- Repository-aware audit, ownership recommendations, E2E contract and 11-task integration backlog. No new independent product registry or authority.

## Actual results

| Check | Actual result |
|---|---|
| JavaScript regression tests | 59 passed |
| Python regression tests | 20 passed |
| Chromium component checks via loaded HTML fixture | 17 passed |
| Syntax/transpile checks | 13 source files passed; not full typecheck |
| Synthetic media | H.264/AAC, 320x180, 30 fps, 2 seconds; full decode and metadata checks passed |
| Original v1 preservation | 84 files matched original ZIP bytes |

Full limits are in `evidence/VALIDATION.md`. Native Adobe, Blender, Rive, complete Remotion rendering, the real PhenoDesign integration/build and deployed/native consumer E2E remain unexecuted. No remote changes, application binaries, credentials or font binaries are included.

## Integrity

Run `python scripts/verify_manifest.py`. It verifies listed bytes against `MANIFEST.sha256`; it does not authenticate their producer or establish application behavior. Referenced web resources are not bundled wholesale.
