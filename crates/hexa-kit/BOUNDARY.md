# Boundary Lock: Project bootstrap & architectural scaffolding

**Status:** ACTIVE — HexaKit is **not** a lib collection holder.

## Owns
- New-project bootstrap (hexagonal layout, folder folding, file templates)
- Fleet architectural pattern enforcement (`.template.ci.yml`, `.template.editorconfig`, `.forge` recipes)
- Spec-kitty / AgilePlus scaffolding integration
- **Generators** that stamp per-repo config (not per-repo duplicated boilerplate repos)

## Does NOT own (domain SDKs — install separately)
- Runtime types → `phenotype-types`
- Auth → `AuthKit` / `phenotype-auth-ts`
- MCP → `PhenoMCP` / `McpKit`
- Telemetry → `PhenoObservability` / `Tracely`
- Testing utils → `TestingKit`
- Agent runtime → `thegent` (when stable)

## Transitional: `python/pheno-*` packages
Legacy interim packages under `python/` are **being relocated** to domain SDK repos.
Do not add new domain libraries here — use HexaKit templates to wire imports.

| Package | Status |
|---------|--------|
| `python/pheno-types` | **Migrated** — stub pointer to [phenotype-types](https://github.com/KooshaPari/phenotype-types) |
| Other `python/pheno-*` | Pending disposition (separate lanes) |

## Current recovery frontier

This workspace currently carries preserve-first recovery surfaces that should be
kept visible and organized, not deleted:

- `crates/hexa-kit/`
- `crates/agile-plus/`

These lanes are source-bearing consolidation work. Preserve the material, group
the recovery notes with the code, and avoid broad deletion or pruning.

## Future: phenoSDK hub (hypothetical)
Loose-coupled dynamic install surface for small domain modules that are not worth standalone repo governance — HexaKit scaffolds the import, SDK hub resolves versions.
