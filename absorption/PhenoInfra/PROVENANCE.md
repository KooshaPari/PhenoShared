# PROVENANCE.md — PhenoInfra Absorption

## Source Repository

- **Repository**: `KooshaPari/PhenoInfra`
- **URL**: https://github.com/KooshaPari/PhenoInfra
- **Commit**: `ecf486cab18b8e84213838d497a39ea3a94aca71`
- **Commit message**: `fix(security): redact Cloudflare API token from handoff doc`
- **Commit date**: 2026-09-16
- **Absorbed**: 2026-09-27

## What Was Absorbed

A full compute/infra consolidation monorepo (2537 files, 28 MB source):
`crates/`, `docs/`, `configs/`, `benches/`, `benchmarks/`, `.circleci/`,
`.github`-adjacent CI, `Cargo.toml`/`Cargo.lock`, `Dockerfile`,
`docker-compose.yml`, `deny.toml`, plus ADRs, validation notes
(`A-01`…`A-10`), and an `_archived/` subtree.

Repository description (as recorded on GitHub): *"Phenotype Compute/Infra
Consolidation Monorepo — shared crates, IaC, landing pages"*.

## Why Absorbed

Consolidate repo sprawl. The source repo was **already archived** on GitHub
prior to absorption — this completes the disposition by bringing its content
under the PhenoShared umbrella so the archived repo can eventually be retired.

## Relationship to Existing Code

PhenoShared already holds related material (`sites/phenoinfra-landing`,
`crates/phenotype-infrastructure`, `crates/phenotype-test-infra`). This
absorption is a **snapshot archive**, not a code merge — the source tree is
preserved as-is under this directory and is NOT wired into the Cargo workspace.
Deduplication against the live crates is a separate, deliberate follow-up.

## Notes

- Plain copy (no `.git`), matching the `absorption/*` pattern.
- `node_modules` / `__pycache__` / build caches excluded.
- **Not** added to `[workspace].members`.

## Source Repo Status

- GitHub repo is **already archived** (archived=true as of absorption).
