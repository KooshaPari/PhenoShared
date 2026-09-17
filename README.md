# PhenoShared

Shared infrastructure workspace for the [Phenotype](https://github.com/KooshaPari) ecosystem. Houses three shared resources consumed across the org: **shared Rust crates**, **shared GitHub Actions workflows**, and **shared documentation** (including the Global Handbook).

[![CI](https://github.com/KooshaPari/PhenoShared/actions/workflows/ci.yml/badge.svg)](https://github.com/KooshaPari/PhenoShared/actions)
[![License: MIT OR Apache-2.0](https://img.shields.io/badge/License-MIT%2FApache--2.0-blue.svg)](LICENSE)

---

## What It Is

PhenoShared is **not** a single-purpose repo. It serves three cross-org functions co-located in one workspace:

| Function | Location | Scope |
|----------|----------|-------|
| **Shared crates** | `crates/` | 365+ Rust crates (workspace v0.3.10, edition 2021) |
| **Reusable workflows** | `.github/workflows/` | 83 CI/CD workflow files |
| **Shared actions** | `.github/actions/` | 6 composite actions |
| **Shared docs** | `docs/` + `handbook/` | Global Handbook, dossiers, ADRs, architecture |

The workspace consolidates infrastructure, tooling, agent frameworks, connectors, compute-mesh IaC, and ecosystem governance that previously lived across 10+ standalone repos (PhenoDesign, PhenoFabric, PhenoInfra, PhenoLab, PhenoGfx, PhenoRegistry, PhenoMLX, PhenoAI, PhenoProc, PhenoAgent, and others).

---

## Crate Inventory (365+)

| Category | Prefix | Count | Origin |
|----------|--------|-------|--------|
| Agent/persona ecosystem | `pheno-*` | 40 | PhenoAI, PhenoAgent |
| Phenotype infrastructure | `phenotype-*` | 75 | PhenoInfra, PhenoRegistry |
| Focus productivity suite | `focus-*` | 43 | PhenoLab, PhenoProc |
| AgilePlus planning | `agileplus-*` | 23 | PhenoProc |
| Fabric routing & transport | `fabric-*` | 20 | PhenoFabric |
| Substrate agent runtime | `substrate-*` | 9 | PhenoLab |
| Connector integrations | `connector-*` | 9 | PhenoProc |
| Eye tracker | `eyetracker-*` | 8 | PhenoLab |
| Engine adapters | `engine-*` | 7 | PhenoLab, PhenoAI |
| Cloud dispatch | `cloud-*` | 4 | PhenoInfra |
| Driver interfaces | `driver-*` | 4 | Substrate |
| Eidolon cross-platform | `eidolon-*` | 4 | PhenoLab |
| Store backends | `store-*` | 2 | Substrate |
| Other (standalone crates) | *(various)* | ~111 | Absorbed repos |

### Workspace members (selected)

Core substrate, engine, fabric, and infra crates are registered in `Cargo.toml`:

```
crates/substrate-{core,app,trace,schedule,dag,skills,memory}
crates/engine-{spec,forge,conformance,codex,claude,a2a,agentapi}
crates/driver-{cli,http,argv,mcp}
crates/store-{file,sqlite}
crates/fabric-{capability,capture,daemon,graph,routing,terminal,...}
crates/phenotype-{mcp,router,infrakit,gfx,registry,...}
```

---

## Reusable Workflows (83)

All workflows live in `.github/workflows/`. Key categories:

| Category | Workflows | Description |
|----------|-----------|-------------|
| **CI** | `ci.yml`, `coverage.yml`, `e2e.yml` | Main CI pipeline, coverage, E2E tests |
| **Security** | `codeql.yml`, `security-scan.yml`, `trufflehog.yml`, `secret-guard.yml` | SAST, secrets, dependency scanning |
| **Rust** | `cargo-deny.yml`, `cargo-machete.yml`, `cargo-semver-checks.yml` | Cargo audit, unused-deps, semver |
| **Release** | `release.yml`, `release-binary.yml`, `release-crates.yml`, `release-npm.yml`, `publish.yml`, `sbom.yml` | Multi-platform release pipeline |
| **Docs** | `docs.yml`, `docs-check.yml`, `docs-lint.yml`, `docs-validation.yml`, `doc-links.yml` | Documentation validation |
| **Quality** | `quality-gate.yml`, `policy-gate.yml`, `traceability-gate.yml` | Cross-repo quality gates |
| **Infrastructure** | `terraform-plan.yml`, `tf-ci.yml`, `iac-rust.yml` | IaC planning & validation |
| **Governance** | `governance.yml`, `audit.yml`, `quarterly-audit.yml`, `no-idle-audit.yml` | Org governance automation |

**Usage**: See [`.github/README.md`](.github/README.md) for workflow-reference syntax.

---

## Shared Actions (6)

| Action | Location | Description |
|--------|----------|-------------|
| build-rust-binary | `.github/actions/build-rust-binary/` | Cross-platform Rust binary build |
| run-benchmarks | `.github/actions/run-benchmarks/` | Benchmark runner |
| run-tests | `.github/actions/run-tests/` | Test runner with matrix support |
| security-checks | `.github/actions/security-checks/` | Aggregate security scanning |
| setup-env | `.github/actions/setup-env/` | Multi-tool environment setup |

---

## Shared Documentation

### Global Handbook (authoritative)

[`docs/GLOBAL_HANDBOOK.md`](docs/GLOBAL_HANDBOOK.md)

**Pinned revision: 2026-09-16** — superseeds all prior loose policy documents. This is the single canonical reference for agent behavior, quality gates, portfolio management, ecosystem evolution, delivery packaging, and creative production across all Phenotype repositories.

### Additional documentation

| Location | Content |
|----------|---------|
| `docs/dossiers/` | 2 product dossiers (quality-gate certified) |
| `docs/adr/` + `docs/adrs/` | 115 Architecture Decision Records |
| `docs/architecture/` | System architecture documentation |
| `docs/governance/` | Governance policies |
| `handbook/` | Ecosystem handbook (specs, patterns, anti-patterns, ADRs) |

---

## Consuming Shared Crates

Add a dependency using a git reference:

```toml
[dependencies]
phenotype-mcp = { git = "https://github.com/KooshaPari/PhenoShared", package = "phenotype-mcp" }
```

Or for a local workspace development clone:

```toml
[dependencies]
phenotype-mcp = { path = "../PhenoShared/crates/phenotype-mcp" }
```

> **Note**: The `[workspace.package]` metadata in `Cargo.toml` still carries a `phenotype-dev` origin repository URL in `repository`. This is a carry-forward from pre-consolidation and will be updated in a future pass. The correct source is `github.com/KooshaPari/PhenoShared`.

---

## Consuming Repositories

The crates and workflows in this repo are consumed by:

- [pheno](https://github.com/KooshaPari/pheno) — Phenotype Infrastructure Kit (Rust)
- [phenotooling](https://github.com/KooshaPari/phenotooling) — Org internal tooling
- [PhenoMLX](https://github.com/KooshaPari/PhenoMLX) — MLX-based AI runtime
- [HeliosLab](https://github.com/KooshaPari/HeliosLab) — Compiler & runtime lab
- Other KooshaPari org repos using `PhenoShared/.github/workflows/` or `PhenoShared/crates/*`

---

## License

MIT OR Apache-2.0