# Dag Name Collision Cleanup — 2026-09-01

## Problem

Two products with the name `pheno-dag` (or `phenodag`) existed in the ecosystem:

| | Rust DAG foundation | Go multi-agent DAG |
|---|---|---|
| Path | `phenotype-registry/crates/pheno-dag/` | `KooshaPari/phenodag` (was a separate GH repo) |
| Language | Rust | Go |
| Origin | Extracted from BytePort per its Cargo.toml | Multi-agent multi-project DAG (SQLite + flock, v3-180 preset, hybrid similarity, atomic claims, mangled-git scan) |
| Size | small (lib.rs + serialize.rs) | 282 KB, 13 queue files + spec |
| Status before this PR | Cargo workspace member | **DELETED 2026-09-01** (absorbed into Tracera spec 008 + AgilePlus mirror) |

The two products were completely unrelated but shared the same name, causing namespace confusion.

## Resolution

Renamed the Rust foundation `crates/pheno-dag` → `crates/phenotype-dag-core` (and its package name `pheno-dag` → `phenotype-dag-core`).

### Why the Rust name had to change

- The Go `KooshaPari/phenodag` was a publicly-visible product (homepage `phenodag.phenotype.space`, 1 open issue).
- Its GitHub repo was archived in the L7 sweep on 2026-08-14 and then **deleted** on 2026-09-01 after full absorption into Tracera.
- However, the Rust DAG foundation inside `phenotype-registry` was extracted from BytePort per its Cargo.toml, predates the Go product, and has nothing to do with multi-agent work.
- The Rust name being `pheno-dag` was a historical accident — it pre-dated the Go product.
- Renaming to `phenotype-dag-core` removes the namespace ambiguity and signals "this is the core DAG foundation for the phenotype stack" (which is the actual purpose).

## Changes

### File-level

- **Renamed**: `crates/pheno-dag/` → `crates/phenotype-dag-core/`
- **Renamed**: `ADR-dag-duplication.md` → `ADR-dag-collision-phenodag-phenodag-2026-09-01.md`
- **Updated**: `Cargo.toml` workspace member `crates/pheno-dag` → `crates/phenotype-dag-core`
- **Updated**: `crates/phenotype-dag-core/Cargo.toml`: `name = "pheno-dag"` → `name = "phenotype-dag-core"`
- **Updated**: `crates/phenotype-dag-core/src/lib.rs`: doc-comments updated to reference `phenotype_dag_core::`
- **Updated**: `crates/phenotype-dag-core/src/serialize.rs`: doctest imports `use pheno_dag::` → `use phenotype_dag_core::`
- **Updated**: `docs/adrs/ADR-ECO-023-sdk-consolidation.md`: prose updated

### Verification

- `cargo check --workspace` passes cleanly: `phenotype-dag-core v0.1.0` compiles.
- Verified across all KooshaPari repos via `search/code?q=pheno-dag+repo:KooshaPari/<repo>` API: **no external Cargo.toml depends on `pheno-dag`** outside of `phenotype-registry` itself.
- The only remaining historical references to `pheno-dag` are in `phenotype-omlx/docs/sessions/2026-07-18-metal-model-runtime/21_TURN_14_RESUME_NOTES.md` (historical session notes — left unchanged, do not rewrite history).

### Registry updates

- `registry/disposition-index.json` v1.6.83 → v1.6.84
  - 1 row updated: `path` field `crates/pheno-dag` → `crates/phenotype-dag-core` (with rename note)
  - 1 new tombstone row added: `rename-pheno-dag-to-phenotype-dag-core-20260901` (TOMBSTONE_RENAME fsm=renamed)
  - Total rows: 1,033 → 1,034

### Project JSON

- `projects/phenotype-dag-core-rename-2026-09-01.json` (new, tombstone record)

## Why this matters

The Go product (`KooshaPari/phenodag`) was absorbed into Tracera spec 008 via PRs #723, #725, #727 and AgilePlus via PR #895, then deleted from GH on 2026-09-01. Without this rename, downstream consumers would have a `phenotype-dag-core` (Rust) and a "phenodag" (Tracera spec 008 mirror) coexisting under confusing names. The rename establishes a clean namespace.

## Related work

- `audits/13-source-polyrepo-audit-2026-09-01.md` — the larger polyrepo cleanup that included phenodag absorption
- `audits/absorption-justifications/phenodag-2026-09-01.md` — the phenodag absorption justification
- `audits/absorption-justifications/phenodag-2026-09-01.md` — referenced by this rename as the absorption context

## Provenance

- PR: `phenotype-registry#543`
- Author: Forge (Audit)
- Date: 2026-09-01
