# DataKit final deletion package

Date: 2026-06-20
Source repo: `KooshaPari/DataKit`
Decision: `DELETE`

## Evidence summary

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|---|---|---|---|---|---|---|---|---|---|
| `pheno-caching` | `DataKit/python/pheno-caching` nested repo | Python package | implemented; local worktree deleted but HEAD intact | `phenotype-python-sdk` | `phenotype-python-sdk#34` merged, package `packages/pheno-caching` with `ORIGIN.md` | `DONE` | Folded from nested repo HEAD | low | none |
| `pheno-database` | `DataKit/python/pheno-database` nested repo | Python package | implemented; local worktree deleted but HEAD intact | `phenotype-python-sdk` | `phenotype-python-sdk#34` merged, package `packages/pheno-database` with `ORIGIN.md` | `DONE` | Folded from nested repo HEAD | low | none |
| `pheno-events` | `DataKit/python/pheno-events` nested repo | Python package | implemented; local worktree deleted but HEAD intact | `phenotype-python-sdk` | `phenotype-python-sdk#34` merged, package `packages/pheno-events` with `ORIGIN.md` | `DONE` | Folded from nested repo HEAD | low | none |
| `pheno-storage` | `DataKit/python/pheno-storage` nested repo | Python package | implemented; local worktree deleted but HEAD intact | `phenotype-python-sdk` | `phenotype-python-sdk#34` merged, package `packages/pheno-storage` with `ORIGIN.md` | `DONE` | Folded from nested repo HEAD | low | none |
| `db_kit` | `DataKit/python/db_kit` | Python package/scaffold | local package dir | `phenotype-python-sdk` | `phenotype-python-sdk#34` merged, package `packages/db-kit` with `ORIGIN.md` | `DONE` | Folded into SDK | low | none |
| `eventra` dependency delta | `DataKit/rust/eventra/Cargo.toml` changed `thiserror` 1.0 to 2.0 | Rust dependency delta | local dirty nested repo | `Eventra` | `Eventra#33` merged, archive `archive/DataKit-eventra-2026-06-20` | `DONE` | Delta preserved in Eventra | low | none |
| root intent prompt ordering | `docs/intent/DataKit.md` reordered bound prompt row | docs metadata | local dirty | registry deletion package | this document records the non-semantic reorder | `NO_MERIT` | row ordering has no unique source value after package absorption | low | none |
| LFS audit files | `.gitattributes`, `LFS_AUDIT.md` untracked in local clone | governance/ops artifact | local untracked | registry deletion package | this document records presence; no runtime package content | `NO_MERIT` | generic repo-local audit stubs not needed after source deletion | low | none |

## Final recommendation

The matrix supports deleting `KooshaPari/DataKit`. All package content was folded into `phenotype-python-sdk`, and the only Rust delta was preserved in `Eventra`.
