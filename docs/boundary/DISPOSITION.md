# phenokits-commons — Per-Module Boundary Disposition

**Status:** Approved assessment  
**Date:** 2026-06-17  
**Repo:** `<REDACTED>/phenokits-commons`  
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md) (cited inline as **[charter]**)  
**Audit:** [`docs/audit/BLOCK-C-AUDIT.md`](../audit/BLOCK-C-AUDIT.md)  
**Registry:** [`phenotype-registry/BOUNDARY_OWNERS.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/BOUNDARY_OWNERS.md) §Scaffold

This document applies the **three dispositions** from the ecosystem boundary-shaping
charter — **DECOMPOSE**, **ABSORB**, **DYNAMIC-KEEP** — to every top-level module
in the phenokits-commons repository.

> **Doctrine (per charter):** *A stub / empty / broken / unused / incomplete module is
> not a delete candidate by default. On-paper-good boundaries still deserve an owner.*
> No module here is recommended for deletion; every entry receives an owner.

---

## 1. Summary — recommended end-state

Per **[charter §Target topology]** and **BOUNDARY_OWNERS** §Scaffold,
`phenokits-commons` is the **fleet commons** layer. It owns:

| Concern | Owner after disposition |
|---------|-------------------------|
| Per-repo CI/governance **templates** (`governance/phenoproc-templates/`) | **phenokits-commons** (dynamic-keep) |
| Per-language lint/format **configs** (`governance/phenoproc-configs/`) | **phenokits-commons** (dynamic-keep) |
| Parameterized CI/CD + tooling **configs** (`configs/`) | **phenokits-commons** (dynamic-keep) — copy-source |
| Per-repo **test scaffolds** (Playwright, docsite harness) | **phenokits-commons** (dynamic-keep) |
| Polyglot **reference** `phenotype-id` | **phenokits-commons** (dynamic-keep) |
| Hexagon **ADR/doc pattern kit** (`hexagon/`) | **phenokits-commons** (dynamic-keep) |
| Domain runtime libraries (auth, config, cli, middleware kits) | **Relocate** to language SDK monorepos |
| Project **generators** and `template-*` CLI | **HexaKit** (absorb) |
| Org-wide **reusable** GitHub workflows | **phenotype-org-governance** / `<REDACTED>/.github` |
| Spec lifecycle (`agileplus specify`) | **AgilePlus** (consumes templates from here) |

**After relocation, phenokits-commons becomes:** governance templates + parameterized
configs + test harness patterns + polyglot-id reference — **not** a language-bucket SDK.

**Fleet bootstrap:** new repos copy from [`governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md`](../../governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md)
or run `hexakit init` (HexaKit) which stamps `.template.*` sources. Both paths are
valid; phenokits-commons is the **governance-depth** source, HexaKit is the **scaffold-gen** source.

---

## 2. Method

Inventory sources:

- Git tree `main` post PR #3 (2026-06-17), 12-category taxonomy from `Cargo.toml` header.
- Absorption records: `docs/absorption/PHENOKITS_GAP_PORT.md`, `docs/absorption/PHENOPROC_GOVERNANCE_PORT.md`.
- Cross-repo compare: archived `<REDACTED>/PhenoKits`, `PhenoProc/crates/phenotype-governance/`.
- **[charter]** decomposition map and `BOUNDARY_OWNERS.md` scaffold table.

---

## 3. Top-level modules — disposition table

| # | Module (path) | What it is | Disposition | Target repo | Rationale |
|---|---------------|------------|-------------|-------------|-----------|
| 1 | `governance/phenoproc-templates/` | CI templates, Rust BDD/http/validation integration scaffolds, `AGENTS.md.template` | **DYNAMIC-KEEP** | phenokits-commons | BOUNDARY_OWNERS: fleet bootstrap source; ADR-005 |
| 2 | `governance/phenoproc-configs/` | Per-language lint/format/deny/buf configs | **DYNAMIC-KEEP** | phenokits-commons | Copy-on-bootstrap; ported from PhenoProc PR #3 |
| 3 | `governance/standards/` | Language coding standards (rust, python, ts, go) | **DYNAMIC-KEEP** | phenokits-commons | Scaffold-adjacent standards docs |
| 4 | `configs/cicd/github-actions/` | Parameterized workflow templates (28 workflows) | **DYNAMIC-KEEP** | phenokits-commons (copy-source) | Per-repo templates; canonical reusables live in `<REDACTED>/.github` |
| 5 | `configs/cicd/workflows/` | Shell e2e scaffold scripts | **DYNAMIC-KEEP** | phenokits-commons | HexaKit/doc-sync complements |
| 6 | `configs/tooling/` | Semgrep, codecov, mypy configs | **DYNAMIC-KEEP** | phenokits-commons | Parameterized tooling configs |
| 7 | `configs/infra/` | Dockerfile, infra README | **DYNAMIC-KEEP** | phenokits-commons | Infra parameter templates |
| 8 | `configs/app/phenotype-config/` | App config scaffold (Python) | **DYNAMIC-KEEP** | phenokits-commons | Bootstrap config pattern; SDK copy at `phenotype-python-sdk/packages/phenotype-config/` |
| 9 | `templates/webapp/` | Webapp scaffold + `.github/` CI + docsite tests | **DYNAMIC-KEEP** | phenokits-commons | Per-repo test/CI harness pattern (PR #3) |
| 10 | `templates/hexagonal/` | Hexagonal Python template + domain tests | **DYNAMIC-KEEP** | phenokits-commons | Reference hexagonal layout + test harness |
| 11 | `templates/clean-rust/`, `microservice-scaffold/`, `phenotype-api/` | Project scaffolds | **ABSORB** | HexaKit `templates/` | Charter: HexaKit owns project templates |
| 12 | `hexagon/` | Hexagon ADR kit (SPEC, CHARTER, templates/, CI) | **DYNAMIC-KEEP** | phenokits-commons | Teaches hexagonal pattern; overlaps HexaKit `templates/hexagon/` — keep as doc kit |
| 13 | `hexagon/.github/workflows/` | Hexagon CI + legacy-tooling-gate | **DYNAMIC-KEEP** | phenokits-commons | Template CI reference (PR #3) |
| 14 | `libs/python/phenotype-id/` | Polyglot ID reference (Python) | **DYNAMIC-KEEP** | phenokits-commons | Cross-language reference impl; not a domain SDK |
| 15 | `libs/python/README.md` | Redirect manifest for absorbed Python kits | **DYNAMIC-KEEP** | phenokits-commons | Documents ABSORB targets |
| 16 | `libs/go/phenotype-id/` | Polyglot ID reference (Go) | **DYNAMIC-KEEP** | phenokits-commons | Sibling of #14 |
| 17 | `libs/typescript/phenotype-id/` | Polyglot ID reference (TypeScript) | **DYNAMIC-KEEP** | phenokits-commons | Sibling of #14 |
| 18 | `libs/go/pheno-core-cgo`, `phenotype-go-auth`, `phenotype-go-cli`, `phenotype-go-config`, `phenotype-go-kit`, `phenotype-go-middleware` | Go domain kits | **DECOMPOSE** | `phenotype-go-sdk` | Language-bucket anti-pattern; domain libs belong in SDK monorepo |
| 19 | `libs/typescript/phenotype-core-ts`, `plugin-typescript` | TS domain kits | **DECOMPOSE** | `phenotype-ts-sdk` (or `phenoSDK`) | Same as #18 |
| 20 | `libs/rust/` (excluded workspace) | Rust lib stubs | **ABSORB** | `phenotype-rust-sdk` / `phenoShared` | Virtual workspace excludes; relocate on touch |
| 21 | `tests/` | Repo structure + config validation (PhenoKits port) | **DYNAMIC-KEEP** | phenokits-commons | Validates commons layout itself |
| 22 | `docs/tests/` | Docsite Playwright harness | **DYNAMIC-KEEP** | phenokits-commons | Per-repo docsite test pattern |
| 23 | `docs/absorption/` | PhenoKits / PhenoProc port records | **DYNAMIC-KEEP** | phenokits-commons | Absorption evidence for archive gate |
| 24 | `docs/governance/` | Sunset-maturity, Tracera recovery dispositions | **DYNAMIC-KEEP** | phenokits-commons | Historical governance audits |
| 25 | `docs/adr/`, `docs/reference/`, `docs/guides/` | Commons documentation | **DYNAMIC-KEEP** | phenokits-commons | Scaffold docs |
| 26 | `schemas/` | Config param JSON schemas | **DYNAMIC-KEEP** | phenokits-commons | Parameterization contracts |
| 27 | `scripts/` | Utility scripts | **DYNAMIC-KEEP** | phenokits-commons | Scaffold automation |
| 28 | `secrets/`, `security/`, `policies/`, `credentials/` | Pattern stubs (README + templates) | **DYNAMIC-KEEP** | phenokits-commons | Placeholders per 12-category taxonomy; content TBD |
| 29 | `observability/` | OTel/logging stub | **DYNAMIC-KEEP** | phenokits-commons → future **PhenoObservability** bootstrap | Cross-project audit #4 deferred |
| 30 | `kitty-specs/` | Spec-kitty history | **DYNAMIC-KEEP** | phenokits-commons | Spec metadata; AgilePlus owns active spec lifecycle |
| 31 | `worklogs/` | Session / drift disposition logs | **DYNAMIC-KEEP** | phenokits-commons | Quarantine + sunset evidence |
| 32 | `Tracera/` | Empty Tracera placeholder | **DYNAMIC-KEEP** | phenokits-commons (quarantine) | Row-level disposition in worklogs; no delete |
| 33 | `HexaKit/` (git submodule) | Pointer to HexaKit repo | **ABSORB** | HexaKit (remove submodule) | Consumers should depend on `<REDACTED>/HexaKit` directly |
| 34 | `src/lib.rs` | Empty virtual package stub | **DYNAMIC-KEEP** | phenokits-commons | Root `Cargo.toml` tooling integration only |
| 35 | Root governance (README, AGENTS.md, CODEOWNERS, Taskfile, etc.) | Repo meta | **DYNAMIC-KEEP** | phenokits-commons | Standard org governance files |

---

## 4. Absorption evidence (archived sources)

| Archived repo | Coverage | Status | Evidence |
|---------------|----------|--------|----------|
| `<REDACTED>/PhenoKits` | **100%** (excl. redirected `libs/python`) | **KEEP_ARCHIVED** | PR #3, `docs/absorption/PHENOKITS_GAP_PORT.md` |
| `PhenoProc/phenotype-governance/{templates,configs}` | **100%** | Ported | `docs/absorption/PHENOPROC_GOVERNANCE_PORT.md` |

Hard **DELETE** of archived repos is **not** recommended until consumer manifest scan
(Lane F) confirms zero unique inbound references.

---

## 5. Execution phases

| Phase | Scope | Acceptance |
|-------|-------|------------|
| **P0** (this PR) | Publish disposition + fleet defaults spec | Docs on `main` |
| **P1** | README scope trim; `libs/go` + `libs/typescript` relocation PRs | SDK repos own domain kits |
| **P2** | Remove `HexaKit/` submodule; add `BOUNDARY.md` lock file | Single canonical HexaKit dep |
| **P3** | Observability bootstrap crate (#4 cross-project audit) | PhenoObservability owns OTel templates |

---

## 6. Related documents

- [`docs/audit/BLOCK-C-AUDIT.md`](../audit/BLOCK-C-AUDIT.md)
- [`docs/audit/BLOCK-C-CONSOLIDATION-PLAN.md`](../audit/BLOCK-C-CONSOLIDATION-PLAN.md)
- [`governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md`](../../governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md)
- [`phenotype-registry/BOUNDARY_OWNERS.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/BOUNDARY_OWNERS.md)
- [`HexaKit/docs/boundary/DISPOSITION.md`](https://github.com/KooshaPari/HexaKit/blob/main/docs/boundary/DISPOSITION.md)
- [`phenotype-registry/docs/rationalization/block-c-consolidation.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/block-c-consolidation.md)
