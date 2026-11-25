# pheno-mcp (deprecated stub)

**This package has moved.**

| Surface | Canonical owner |
|---------|-----------------|
| Python MCP library | **[PhenoMCP](https://github.com/KooshaPari/PhenoMCP)** |
| Rust MCP runtime | **[substrate](https://github.com/KooshaPari/substrate)** (`crates/phenotype-mcp`) |

HexaKit retains this directory only as a transitional pointer during Wave F
`python/pheno-*` disposition. Do not add or extend MCP tooling here.

## Install from canonical repos

```bash
# Python library (preferred)
pip install git+https://github.com/KooshaPari/PhenoMCP.git

# Or via phenotype-python-sdk mcp-kit submodule path
pip install git+https://github.com/KooshaPari/phenotype-python-sdk.git#subdirectory=packages/mcp-kit/python/pheno-mcp
```

Rust consumers should depend on `phenotype-mcp` from the substrate workspace, not HexaKit.

## Migration

See [MIGRATED.md](./MIGRATED.md) and registry `py-pheno-mcp` in phenotype-registry disposition-index.
