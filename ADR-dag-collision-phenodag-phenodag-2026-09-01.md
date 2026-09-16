# ADR: Name collision between Rust `pheno-dag` and Go `phenodag`

## Status

Accepted (2026-09-01)

## Context

Two unrelated DAG-bearing crates coexisted in the Phenotype ecosystem under
near-identical names, causing persistent confusion in registries, search,
and dependency graphs:

1. **`phenotype-registry/crates/pheno-dag/`** (Rust, package name `pheno-dag`)
   - DAG foundation for Phenotype compute/infra automation (epic F)
   - Extracted from BytePort's `byteport-dag` crate as a standalone copy
   - Used as a Rust library by other workspace members; provides generic DAG,
     topological sort (Kahn + DFS), parallel-bucket scheduler, enriched
     node/edge schema, YAML/JSON serialization

2. **`KooshaPari/phenodag`** (Go, public 282 KB) — *now deleted*
   - Multi-agent multi-project DAG with SQLite + flock, v3-180 preset,
     atomic claims, heartbeat, dedup, mangled-git scan
   - Phased migration complete: absorbed into Tracera spec 008 + 11 queue
     files (PRs #723/#725/#727) + AgilePlus mirror (PR #895)
   - Go source confirmed as thin redirector per D3 sponsor decision
     (2026-07-05)

The name collision (`pheno-dag` vs `phenodag`) had no functional overlap
but caused:

- Repeated confusion in registry disposition-index entries
- Ambiguous search hits across monorepos (rust vs go, library vs tool)
- Future risk of cargo deps resolving to wrong type under sloppy copy-paste

## Decision

Rename `phenotype-registry/crates/pheno-dag/` → `phenotype-registry/crates/phenotype-dag-core/`
(package name `pheno-dag` → `phenotype-dag-core`) on 2026-09-01, breaking
the collision before any downstream consumer picks up the bad name.

### Why rename rather than alias / dual-namespace?

- **Alias is fragile**: cargo's `package = "pheno-dag"` rename preserves
  internal crate name; downstream crates would still need their imports
  updated when they bump their pin.
- **Dual-namespace adds churn**: a `phenodag-foundation` alias would require
  every consumer to maintain two import paths for one library.
- **Collision is local to one workspace**: `pheno-dag` is only depended on
  inside `phenotype-registry`. No external repo references it. The blast
  radius of the rename is zero on remote.

### Why now?

- `phenodag` is now deleted (2026-09-01) so there is no parallel
  `phenotype-dag-core` to migrate from — only one crate is renamed.
- The 13-source polyrepo audit (2026-09-01) flagged this collision as
  P2 cleanup that should land in the same wave as the deletions.
- The package was at v0.1.0 (never released to crates.io), so semver
  guarantees don't apply.

## Consequences

### Required mechanical updates

- Workspace member path in `phenotype-registry/Cargo.toml`:
  `"crates/pheno-dag"` → `"crates/phenotype-dag-core"`
- Crate `package.name`: `"pheno-dag"` → `"phenotype-dag-core"`
- All `use pheno_dag::` references in doctest examples (e.g. `lib.rs`,
  `serialize.rs`) → `use phenotype_dag_core::`

### Documentation updates

- This ADR file renamed: `ADR-dag-duplication.md` →
  `ADR-dag-collision-phenodag-phenodag-2026-09-01.md`
- Old `ADR-dag-duplication.md` content (about byteport-dag duplication)
  archived separately; it describes a different concern (dedup vs
  BytePort, not collision with phenodag)
- Any docs referencing `pheno-dag` crate name updated (no external
  Cargo.toml deps found via `search/code` across all KooshaPari repos)

### Registry tracking

- `phenotype-registry/registry/disposition-index.json` adds a tombstone
  row `repo-pheno-dag-rename-tombstone-2026-09-01` noting the old name
  → new name mapping
- `phenotype-registry/projects/pheno-dag-rename-2026-09-01.json` records
  the rename metadata

### Historical session notes

`phenotype-omlx/docs/sessions/2026-07-18-metal-model-runtime/21_TURN_14_RESUME_NOTES.md`
and any other historical session notes mentioning `pheno-dag` are NOT
modified — they are point-in-time records and rewriting them would
falsify history.
