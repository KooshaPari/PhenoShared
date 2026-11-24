# pheno-types (deprecated stub)

**This package has moved.** Canonical types live in the
**[<REDACTED>/phenotype-types](https://github.com/KooshaPari/phenotype-types)** repository.

HexaKit retains this directory only as a transitional pointer during the
`python/pheno-*` disposition. Do not add or extend types here.

## Install from canonical repo

```bash
pip install git+https://github.com/KooshaPari/phenotype-types.git
```

Or add to your project dependencies (package name remains `pheno-types`, import `pheno_types`):

```toml
dependencies = [
  "pheno-types @ git+https://github.com/KooshaPari/phenotype-types.git",
]
```

## Stack note

HexaKit's Python layer targets **Python 3.14+ with uv** as the edge binding surface.
Long-term canonical schemas for core types are expected to land in **Rust/Zig** in
`phenotype-types`; the Python package is the interim typed binding layer.

## Migration

See [MIGRATED.md](./MIGRATED.md) and [../docs/history/phenoTypes-relocation.md](../docs/history/phenoTypes-relocation.md).
