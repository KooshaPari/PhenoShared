# phenoData active-source revalidation (2026-08-07)

This is an evidence-only correction to the historical absorption packet. It
does not archive, delete, rename, or change the registry disposition.

## Live refs

| Surface | Ref | SHA | Observed fact |
|---|---|---|---|
| Source repository | `KooshaPari/phenoData:main` | `caf426c20d612bf7101f17e39ae63e1ab12dd110` | Protected, public, `archived=false`; pushed 2026-08-02 |
| Source archival branch | `archive/phenoData/main` | `896faa5860ba1e5f44e3374c470497f41d28348f` | 53 commits behind source `main`; provenance branch only |
| Apps mirror | `phenotype-apps` `apps/phenoData` | `5a0672024b798f852b6a36eaa83820c424d0b5aa` | Exact source crate-tree mirror at the absorption snapshot |
| Pheno candidate | `pheno` `crates/pheno-data-from-phenoData` | `be5da947c3fc747746b11f6f3010f9f15a7b21cb` | Stale failed-transfer residue; not the five renamed target crates described by the packet |

The GitHub API reports `KooshaPari/phenoData` as **not archived**, with open
maintenance PRs #17 and #19. Therefore the historical packet's statement that
the source was archived is no longer current evidence.

## Target verification

The five source crate manifests, sources, and tests (`core`, `pheno-query`,
`surreal-bridge`, `pg-bridge`, and `smoke-tests`) have identical Git blob SHAs
between `KooshaPari/phenoData:main` and `phenotype-apps/apps/phenoData` at
`5a0672024b798f852b6a36eaa83820c424d0b5aa` (16/16 checked files). This supports
`phenotype-apps/apps/phenoData` as the exact absorbed snapshot.

The `pheno` checkout currently exposes only the historical
`crates/pheno-data-from-phenoData` subtree; it does not expose the renamed
`pheno-data-core`, `pheno-data-query`, `pheno-data-surreal`, `pheno-data-pg`,
and `pheno-data-smoke-tests` tree claimed by the original packet. That surface
must not be treated as a completed transfer without a fresh target ref and
build evidence.

## Required disposition decision

Until the registry sponsor reviews ownership, the safe state is:

```text
source: active and preserved (KooshaPari/phenoData:main)
exact mirror: phenotype-apps/apps/phenoData (snapshot 5a06720)
pheno target: unresolved/stale candidate; no completion claim
registry: preserve historical absorption record; hold disposition transition
```

No source branch or repository should be archived or deleted based on the
historical packet alone. A future disposition PR must include an exact target
SHA, API/tree drift matrix, consumer evidence, and a successful bounded build.
