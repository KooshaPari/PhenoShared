# ADR-ECO-014: Decompose phenoShared — no generic consolidation repo

## Status
Amended (2026-11-11) — see §Amendment below

## Context
`phenoShared` absorbed cross-cutting crates during HexaKit P3 eviction as a **staging** home. It has no domain orientation — it is neither a role owner, nor a justified SDK/framework boundary. Fleet repoints that terminate on `phenoShared` recreate a junk-drawer monorepo under a different name.

## Decision

1. **phenoShared repo disposition: `DECOMPOSE` → delete** after crate relocation and consumer repoint gates pass.
2. **phenoShared is interim staging only** — git pins during P3 waves are tolerated; **not** a terminal `repoint_to` in chokepoints or fleet blockers.
3. **Consumers repoint to `DOMAIN_ROLES` owners** per crate/boundary slice, not to the phenoShared workspace umbrella.

## Crate routing (staging → terminal owner)

| phenoShared crate / slice | Role | Terminal owner |
|---------------------------|------|----------------|
| `settly`, `phenotype-config-loader` | `config` | **phenotype-config** |
| `stashly`, `phenotype-http-client-core`, retry/bulkhead adjacency | `resilience` | **phenotype-resilience** |
| `phenotype-health` (traits) | `observe` | **PhenoObservability** |
| `phenotype-errors` | types | **phenotype-types** |
| `phenotype-event-bus` | events | **Eventra** |
| `phenotype-contracts` | per-domain | **decompose** to role workspaces (not phenoShared) |
| `phenotype-async-traits`, `phenotype-macros` | genesis facades | **HexaKit** `templates/` or thin **phenotype-rust-sdk** re-exports only |
| `@phenotype/shared-utils` (npm) | docs edge | **phenodocs** (`@phenotype/docs`) |

## Anti-patterns (reject)

| Do not | Do instead |
|--------|------------|
| List `phenoShared` as canonical owner in ECOSYSTEM_MAP / BOUNDARY_OWNERS | Name the **role owner** for each capability |
| `repoint_to: ["phenoShared"]` in chokepoints | `repoint_to` lists **domain role repos**; optional `interim_staging: phenoShared` |
| Add new domain crates to phenoShared | Open or extend the **role workspace** (config, observe, resilience, …) |
| Treat phenoShared as “shared-lib” SSOT | Use **domain-oriented** lib/SDK/framework boundaries only |

## Consequences

- `registry/chokepoints.json` `pheno_fleet_blockers` use domain repoint lists.
- `disposition-index.json` gains repo-level `phenoShared` row `DECOMPOSE`; crate rows note `interim: phenoShared` where applicable.
- HexaKit wave 14+ parity work **routes crates to role owners**, not new phenoShared pins as end state.
- DELETE gate for phenoShared runs after pheno archive gate and per-crate consumer scan.


## Amendment (2026-11-11)

ADR-ECO-014 originally directed `phenoShared` to **DECOMPOSE → delete** after crate relocation.
That direction is amended: the repo is reclassified as the **container** for bulky and
non-publishable material, with a curated subset published as independently consumable crates.
Decomposition into domain-role repos is no longer the terminal goal; classification and
consumability are.

The seam contract (5 rules: standalone packaging, layer discipline, no bulk-leaking features,
declared stability, catalog completeness) replaces the relocation programme. The container
thesis is retained; the "no generic consolidation repo" rule is relaxed to allow consolidation
when a seam contract is enforced.

## Related

- [DOMAIN_ROLES.md](../../DOMAIN_ROLES.md)
- [ADR-ECO-006](./ADR-ECO-006.md) — no monorepo junk drawer
- [boundary-shaping.md](../rationalization/boundary-shaping.md)
