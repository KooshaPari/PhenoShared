# phenoTypes archive absorption

This note documents the migration of the archived
[<REDACTED>/phenoTypes](https://github.com/KooshaPari/phenoTypes) repository into HexaKit.

## Absorption

| Field | Value |
|-------|-------|
| Source repo | `<REDACTED>/phenoTypes` (archived) |
| Target | `HexaKit/python/pheno-types` |
| Package name | `pheno-types` (import: `pheno_types`) |
| Migration date | 2026-06-16 |

## Ported modules

| Archive module | Target module | Status |
|----------------|---------------|--------|
| `phenotype_types/skill.py` | `pheno_types/skill.py` | Ported |
| `phenotype_types/task.py` | `pheno_types/task.py` | Ported |
| `phenotype_types/schemas.py` | `pheno_types/schemas.py` | Ported |
| `phenotype_types/research.py` | `pheno_types/research.py` | Ported |
| `phenotype_types/phenotype_types.py` | `pheno_types/legacy.py` | Ported (renamed) |
| `phenotype_types/__init__.py` | `pheno_types/__init__.py` | Ported (adapted) |

## Ported tests

All archive tests under `phenoTypes/tests/` were ported to `pheno-types/tests/` with
imports updated from `phenotype_types` to `pheno_types`.

## Already present in HexaKit (not duplicated)

| Archive concept | HexaKit location | Notes |
|-----------------|------------------|-------|
| Atom validation types | `pheno-atoms` | Separate concern; not part of phenoTypes |
| Config/errors/logging | `pheno-core` | Foundation utilities; no overlap |
| Agent orchestration `TaskDefinition` | `pheno-mcp` | MCP agent task model; distinct from phenoTypes `Task` |

## Package choice

A new `pheno-types` package was created rather than folding into `pheno-atoms` or
`pheno-core` because the archived types (task lifecycle, skill manifests, research
reports, JSON schema export) form a cohesive domain module with their own test suite
and traceability to FR-TYPES-001 through FR-TYPES-008.
