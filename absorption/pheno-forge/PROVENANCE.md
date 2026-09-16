# PROVENANCE.md -- PhenoForge Absorption

## Source Repository

- **Repository**: `KooshaPari/zz-merge-unk-PhenoForge`
- **URL**: `https://github.com/KooshaPari/zz-merge-unk-PhenoForge.git`
- **Commit**: `6c5a9f902650aae12d7a628a4e5f4d02e3c86043`
- **Commit message**: `tombstone: mark for deletion`
- **Commit date**: 2026-09-12
- **Absorbed**: 2026-09-15

## What Was Absorbed

PhenoForge was a Rust task runner project with:
- Parallel execution, dependency graph resolution, hot reload, and plugin system
- Comprehensive specs (SPEC.md, PRD.md, FUNCTIONAL_REQUIREMENTS.md)
- Architecture decision records (ADRs)
- Documentation site (VitePress)
- CI/CD workflows (GitHub Actions)
- Previously absorbed sub-project: SchemaForge (in `docs/absorbed/schemaforge/`)

## Relationship to Existing Code

- `crates/pheno-forge-scaffold` (already in phenotype-tooling) is a scaffold-only placeholder
  binary ported from PhenoForge on 2026-09-10. It preserves the historical command name
  (`phenotype-forge`) and documents the truthful scaffold state.
- This absorption captures the original specs, docs, and CI config from the source repo.

## Source Repo Status

The source repo was tombstoned for deletion on 2026-09-12. This absorption preserves
the complete project history and specifications.
