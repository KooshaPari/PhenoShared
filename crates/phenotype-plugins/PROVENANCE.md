# Provenance: PhenoPlugins

## Source

- **Repository**: `KooshaPari/zz-merge-unk-PhenoPlugins`
- **URL**: https://github.com/KooshaPari/zz-merge-unk-PhenoPlugins
- **License**: MIT OR Apache-2.0
- **Absorbed**: 2026-09-15

## Migration Details

The PhenoPlugins crate workspace was absorbed into `phenotype-tooling` as
`crates/phenotype-plugins/`. The original source repository is preserved
at the URL above for historical reference.

### Crates Migrated

| Crate | Description |
|-------|-------------|
| `pheno-plugin-core` | Core traits and types for the Phenotype plugin SDK |
| `pheno-plugin-git` | Git integration plugin |
| `pheno-plugin-sqlite` | SQLite integration plugin |
| `pheno-plugin-vessel` (pkg: `phenotype-vessel`) | Container utilities |
| `pheno-plugin-examples` | Reference plugin implementations |

### Notes

- Internal path dependencies between sibling crates remain unchanged.
- `rusqlite` version aligned to 0.32 to match existing `phenotype-tooling-observability`.
- The `pheno-plugin-vessel/fuzz` sub-crate is not a workspace member (built via `cargo fuzz`).
- `.pre-commit-config.yaml` symlinks to `../shelf-infra/hooks` in the source repo are not copied.
