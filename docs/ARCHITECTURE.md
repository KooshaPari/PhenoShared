# PhenoShared architecture index

This is the entry point for the **shared infrastructure container repository**, not a claim that all absorbed projects have one deployed runtime or one complete architecture.

## Architecture orientation

The [root README](../README.md) describes the shared crate inventory, root and nested Rust workspaces, reusable Actions workflows, project manifests, and the `substrate` dispatch spine. The root [Cargo workspace](../Cargo.toml) is a machine-readable source for members and dependency boundaries, not proof every nested crate builds as part of the root workspace.

- **Substrate:** `crates/substrate-core` defines domain/port contracts; application services and engine adapters are separate layers. See [README](../README.md#the-substrate-spine) and the `arch-test` crate for the enforced dependency direction.
- **Reusable workflows and actions:** see [workflows](../.github/workflows/) and [composite actions](../.github/actions/). A workflow file's presence is not proof its jobs are currently green.
- **Nested workspaces and absorbed projects:** see [root inventory](../README.md#beyond-the-root-workspace) and [absorption index](ABSORPTION_INDEX.md). Preserve distinct provenance and acceptance state for each component.
- **Project registry:** `projects/` contains manifests; legacy `KEEP`/queued states must not be mistaken for completed migration.
- **Product-specific documents:** retain project-local design and ADRs. In particular, the root [ARCHITECTURE.md](../ARCHITECTURE.md) documents a **phenotype-omlx** component history, not the entire current PhenoShared fleet; `docs/architecture.md` documents Pine and is likewise not a global contract.

## ResearchLedger migration exception

As of October 13, 2026, the recovered Emergent Garden Wave 5 corpus is staged in [PhenoShared PR #429](https://github.com/KooshaPari/PhenoShared/pull/429) under `docs/researchledger/historical-wave5/` and the application import remains unmerged in [PhenoApps #166](https://github.com/KooshaPari/PhenoApps/pull/166). The later September 9 research source is **not recovered**. Neither a historical corpus snapshot nor a `fabric-research-ledger` crate proves the full ResearchLedger product is integrated.

This file satisfies the repository's required architecture-document index without silently reclassifying historical/proposed components as implemented. Current CI and owner-review results govern acceptance.
