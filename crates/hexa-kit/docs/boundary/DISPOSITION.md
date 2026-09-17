# HexaKit — Per-Module Boundary Disposition

**Status:** Draft assessment
**Date:** 2026-06-16
**Repo:** `<REDACTED>/HexaKit` (a.k.a. `phenotype-infrakit`)
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md) (cited inline as **[charter]**)

This document applies the **three dispositions** from the ecosystem boundary-shaping
charter — **DECOMPOSE**, **ABSORB**, **DYNAMIC-KEEP** — to every top-level module,
crate, package, and workspace currently shipped from the HexaKit repository.

> **Doctrine (per charter):** *A stub / empty / broken / unused / incomplete module is
> not a delete candidate by default. On-paper-good boundaries still deserve an owner.*
> No module here is recommended for deletion; every entry receives an owner.

---

## 1. Summary — recommended end-state for HexaKit

Per **[charter §Target topology]**, HexaKit is the **Scaffolding** layer: it owns
*project + file templates / generators* that bootstrap new repos onto the Phenotype
architectural patterns. It is **not** a lib holder.

Concretely, the recommended end-state for `<REDACTED>/HexaKit` is:

| Concern | Owner after disposition |
|---|---|
| Per-language project templates (`template-go`, `template-python`, `template-rust`, `template-typescript`, `templates/<lang>/`) | **HexaKit** (dynamic-keep) |
| Per-repo infra-generic source files (`.template.ci.yml`, `.template.editorconfig`, `.template.pre-commit.yaml`, `.githooks`, `.devcontainer`, `.mise.toml`, `Taskfile.yml`, `Brewfile`) | **HexaKit** (dynamic-keep) |
| Scaffolding generators (`scripts/ci/`, `scripts/doc-sync/`, `scripts/gh/`) | **HexaKit** (dynamic-keep) |
| Reference implementations of the hexagonal pattern (ports, xdd-lib) | **HexaKit** (absorb) — these *teach* the scaffold |
| Scaffolding docs (`docs/`, `ADRs`, `.vitepress`) | **HexaKit** (dynamic-keep) |
| All 53 cargo workspace members under `crates/`, `libs/`, `Metron/`, `Traceon/`, `agileplus/crates/`, `forgecode-fork/`, `libs/nexus` | **Relocate** to domain SDK repos (see table §3) |
| All 7 python packages under `python/pheno-*` and `python/phenosdk` | **Relocate** to per-language domain SDK repos (see table §4) |
| Standalone apps / platforms (apps/byteport, platforms/thegent, src/thegent, flowra) | **Decompose** into per-app/per-platform repos (see table §5) |
| Stale/migrated placeholders (Eventra) | **Absorb** to the repo that already received the migration |
| Empty placeholder dirs (apps/byteport skeleton, koosha-portfolio, repos, vendor, bifrost, harnesses, shelf-infra, worklogs, deferred-tests) | **Dynamic-keep** with rationale (not delete) |

**After relocation, HexaKit becomes:** a templates + scaffolding-gen repo with a
single cargo member (`[package] name = "hexakit"`, the scaffolding CLI itself),
plus the `template-*` directories, `templates/` library, and the generated
infra-generic config files. The 53-crate Rust workspace dissolves into
~10 domain SDK repos + the `phenoShared` dynamic-install monorepo.

**Fleet bootstrap:** new repos enter the ecosystem via **`hexakit init`**, specified
in [`docs/scaffolding/FLEET_INIT.md`](../scaffolding/FLEET_INIT.md). That command
stamps TestingKit hooks, <REDACTED>/.github workflow templates, and a
`BOUNDARY.md` from the domain role picker — scaffolding only, no domain crate copies.

---

## 2. Method

Inventory sources:

- Root `dir /B` and `dir /AD /B` of `E:\bc\HexaKit` (post `git clone --depth 1`).
- `Cargo.toml` `[workspace] members` — authoritative list of 53 cargo crates.
- `BOUNDARY.md` (HexaKit's own boundary lock, status ACTIVE) — declares HexaKit
  is *not* a lib collection holder and that the listed domains are
  "domain SDKs — install separately".
- `python/*/pyproject.toml` — 7 python packages.
- README inspection of `Eventra/`, `Traceon/`, `Metron/`, `libs/nexus/`,
  `forgecode-fork/`, `apps/byteport/`, `platforms/thegent/`, `flowra/`.
- `Cargo.toml` inspection of representative crates to confirm domain mapping.

`crates/focalpoint` is **excluded from the workspace** (867 MB vendor dir;
"pending manual absorption" per `[workspace] exclude`) and is **not present
locally** after shallow clone. It is listed below for completeness.

---

## 3. Cargo workspace members (53) — disposition table

Dispositions map to the **[charter]** target topology:

- **Domain SDK repos (existing or new):** McpKit, AuthKit→Authvault, ResilienceKit,
  TestingKit, PhenoObservability, phenotype-gfx, plus new domain repos where no
  umbrella exists (e.g. phenotype-events, phenotype-policy, phenotype-state-machine,
  phenotype-compliance, phenotype-cost, phenotype-analytics).
- **Dynamic-install monorepo:** `phenoShared` — for crates too small to justify
  their own repo's governance.
- **Scaffolding-gen / HexaKit (absorb):** pattern-defining crates that *teach*
  the scaffold (ports, xdd-lib).

| # | Module (path) | What it is | Disposition | Target repo | Rationale |
|---|---|---|---|---|---|
| 1 | `crates/phenotype-analytics` | Analytics domain crate | **DECOMPOSE** | new `phenotype-analytics` repo | Single-domain, no existing SDK owns analytics. Charter: large/unfocused → split. |
| 2 | `crates/cipher` (a.k.a. `phenotype-cipher`) | Symmetric cipher / encryption crate | **ABSORB** | `Authvault` (AuthKit) | Charter §Decomposition map: "secret → AuthKit". Cipher is a secret-adjacent primitive. |
| 3 | `crates/phenotype-async-traits` | Async trait helpers | **DYNAMIC-KEEP** | `phenoShared` | Tiny infra (async-trait re-exports); no standalone-repo governance justified. |
| 4 | `crates/phenotype-bdd` | BDD test harness | **ABSORB** | `TestingKit` | BDD is testing; charter lists TestingKit as a domain SDK. |
| 5 | `crates/phenotype-cache-adapter` | Cache adapter abstraction | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting infra adapter; too small to own a repo. |
| 6 | `crates/phenotype-casbin-wrapper` | Optional Casbin backend for policy-engine | **ABSORB** | new `phenotype-policy` repo (with #37) | Backend-feature flag of policy-engine; relocates with its consumer. |
| 7 | `crates/phenotype-compliance-scanner` | Compliance scanner | **DECOMPOSE** | new `phenotype-compliance` repo | Single coherent domain, not covered by any existing SDK. |
| 8 | `libs/phenotype-config-core` | Config core types | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting; charter: "tiny infra crates" → dynamic-keep. |
| 9 | `crates/phenotype-config-loader` | Config loader | **DYNAMIC-KEEP** | `phenoShared` | Same family as config-core; both relocate together. |
| 10 | `crates/phenotype-contract` | Contract test trait (singular) | **ABSORB** | `TestingKit` | Charter: TestingKit is the testing SDK. |
| 11 | `crates/phenotype-contracts` | Contract value types | **ABSORB** | `TestingKit` | Sibling of #10; relocate together. |
| 12 | `crates/phenotype-contract-tests` | Contract test runner | **ABSORB** | `TestingKit` | Sibling of #10/#11; relocate together. |
| 13 | `crates/phenotype-core` | Core kernel types | **DYNAMIC-KEEP** | `phenoShared` | "core" is too generic to own a repo; charter: too-small-bits → phenoShared. |
| 14 | `crates/phenotype-cost-core` | Cost tracking core | **DECOMPOSE** | new `phenotype-cost` repo | Single-domain; not covered by an existing SDK. |
| 15 | `crates/phenotype-crypto` | Crypto utilities (hashing, AEAD, KDF, HMAC, ed25519) | **ABSORB** | `Authvault` (AuthKit) | Charter: "secret → AuthKit". Sibling of #2 cipher. |
| 16 | `crates/phenotype-error-core` | Error core types | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting infra; charter: tiny → phenoShared. |
| 17 | `crates/phenotype-error-macros` | Error proc-macros | **DYNAMIC-KEEP** | `phenoShared` | Sibling of #16; relocate with error-core. |
| 18 | `crates/phenotype-errors` | Error facade | **DYNAMIC-KEEP** | `phenoShared` | Sibling of #16/#17. |
| 19 | `crates/phenotype-event-bus` | Event bus abstractions | **DECOMPOSE** | new `phenotype-events` repo | Domain event primitives; "Eventra" README already declares migration to PhenoEvents. |
| 20 | `crates/phenotype-event-sourcing` | Event sourcing | **DECOMPOSE** | new `phenotype-events` repo | Sibling of #19; both belong in the events SDK. |
| 21 | `crates/phenotype-git-core` | Git utilities | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting CLI/dev tool; no standalone-repo governance justified. |
| 22 | `crates/phenotype-health` | Health-check primitives | **ABSORB** | `PhenoObservability` | Health checks are observability-adjacent (same family as metrics/logging/tracing). **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 23 | `crates/phenotype-http-client-core` | HTTP client core | **ABSORB** | `ResilienceKit` | Charter §Decomposition map explicit: "http-client-core → ResilienceKit". |
| 24 | `crates/phenotype-infrastructure` | Infra umbrella crate | **DYNAMIC-KEEP** | `phenoShared` | Umbrella of cross-cutting infra; charter: too-small-bits → phenoShared. |
| 25 | `crates/phenotype-iter` | Iterator utilities | **DYNAMIC-KEEP** | `phenoShared` | Tiny; no standalone-repo governance justified. |
| 26 | `crates/phenotype-logging` | Logging facade | **ABSORB** | `PhenoObservability` | Charter target: observability owns logging. **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 27 | `crates/phenotype-macros` | Proc-macros (general) | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting proc-macro crate; too small. |
| 28 | `crates/phenotype-mcp` | MCP primitives | **ABSORB** | `McpKit` (or `PhenoMCP`) | Charter target: McpKit owns MCP domain. |
| 29 | `crates/phenotype-policy-engine` | Policy engine | **DECOMPOSE** | new `phenotype-policy` repo | Single coherent domain; absorbs casbin-wrapper (#6). |
| 30 | `crates/phenotype-port-traits` | Hexagonal port trait defs | **ABSORB** | `HexaKit` (scaffolding-gen) | HexaKit's BOUNDARY.md declares hexagonal ports are *the* pattern HexaKit scaffolds. Reference impl belongs with the scaffold. |
| 31 | `crates/phenotype-ports-canonical` | Canonical port implementations | **ABSORB** | `HexaKit` (scaffolding-gen) | Sibling of #30; relocate together as the canonical reference. |
| 32 | `crates/phenotype-process` | Process spawning utilities | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting runtime helper; too small. |
| 33 | `crates/phenotype-project-registry` | Project registry types | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting; too small. |
| 34 | `crates/phenotype-security-aggregator` | Security aggregation | **ABSORB** | `Authvault` (AuthKit) | Security is auth's neighbor domain; charter: secret/security → AuthKit. |
| 35 | `crates/phenotype-sentry-config` | Sentry config helper | **ABSORB** | `PhenoObservability` | Sentry is an observability backend; belongs with the observability SDK. **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 36 | `crates/phenotype-shared-config` | Shared config types | **DYNAMIC-KEEP** | `phenoShared` | Cross-cutting config; too small. |
| 37 | `crates/phenotype-state-machine` | State machine primitives | **DECOMPOSE** | new `phenotype-state-machine` repo | Single coherent domain primitive. |
| 38 | `crates/phenotype-string` | String utilities | **DYNAMIC-KEEP** | `phenoShared` | Tiny; too small. |
| 39 | `crates/phenotype-telemetry` | Telemetry facade | **ABSORB** | `PhenoObservability` | Charter target: observability owns telemetry (logging/tracing/metrics/health). **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 40 | `crates/phenotype-test-infra` | Test infra utilities | **ABSORB** | `TestingKit` | Charter target: TestingKit. |
| 41 | `crates/phenotype-test-fixtures` | Test fixtures | **ABSORB** | `TestingKit` | Sibling of #40; relocate with test-infra. |
| 42 | `crates/phenotype-time` | Time utilities | **DYNAMIC-KEEP** | `phenoShared` | Tiny; too small. |
| 43 | `crates/phenotype-validation` | Validation primitives | **DYNAMIC-KEEP** | `phenoShared` | Tiny cross-cutting; too small. |
| 44 | `crates/phenotype-xdd-lib` | XDD methodology library | **ABSORB** | `HexaKit` (scaffolding-gen) | XDD is a governance/DX concept; scaffolding owns DX patterns. |
| 45 | `crates/settly` | Settings management (validation, versioning, migration, postgres, redis) | **DECOMPOSE** | new `phenotype-settings` repo | Substantial single-domain crate (postgres + redis deps); not config-core. |
| 46 | `crates/stashly` | Universal caching (TTL, multi-tier, singleflight) | **DECOMPOSE** | new `phenotype-cache` repo (or **ABSORB** → `ResilienceKit`) | Charter mentions rate-limit; cache is adjacent. Promoting to dedicated repo is cleaner given crate size; second choice: ResilienceKit. |
| 47 | `crates/focalpoint` | Excluded from workspace (867 MB vendor; "pending manual absorption" per `[workspace] exclude`) | **DECOMPOSE** | new `phenotype-focalpoint` repo | Not present in shallow clone; workspace self-documents pending relocation. |
| 48 | `Metron/` (workspace member) | Metrics collection (Prometheus, StatsD, JSON exporters) | **ABSORB** | `PhenoObservability` | README: "Metron is the observability backbone for all Phenotype services". **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 49 | `Traceon/` (workspace member) | Distributed tracing (OpenTelemetry, OTLP, Jaeger, Zipkin) | **ABSORB** | `PhenoObservability` | Charter + HexaKit BOUNDARY.md: "Telemetry → PhenoObservability / Tracely". **Wave A (2026-06-17):** `MIGRATED.md` stub added (runbook step 6); source retained pending repoint. |
| 50 | `forgecode-fork/` (workspace member) | Fork of `forgecode` code generator (Phenotype-specific transforms) | **ABSORB** | `HexaKit` (scaffolding-gen) | It's a code generator; scaffolding is the natural home (or stay as a separate fork repo if upstream sync matters). |
| 51 | `libs/nexus` (workspace member) | Service registry + discovery | **DECOMPOSE** | new `nexus` repo (README already points at `<REDACTED>/nexus`) | The crate's own README documents it as a standalone repo. |
| 52–56 | `agileplus/crates/agileplus-benchmarks`, `agileplus-domain`, `agileplus-events`, `agileplus-graph`, `agileplus-sqlite`, `agileplus-triage` | AgilePlus platform sub-crates | **DECOMPOSE** | `agileplus` repo (its own platform) | The `agileplus/` umbrella is already a separate platform concern; sub-crates stay together as one platform repo. |
| 57 | `agileplus-mcp/` (top-level standalone) | AgilePlus MCP server | **DECOMPOSE** | `agileplus` repo (or its own `agileplus-mcp` repo) | Standalone AgilePlus component; relocate with the AgilePlus platform. |

> **Counts:** 53 declared workspace members in `Cargo.toml` (`exclude = ["crates/focalpoint"]`) + 4 inlined standalone dirs (`Metron`, `Traceon`, `forgecode-fork`, `libs/nexus` covered above) = 57 cargo entries. Plus the 6 `agileplus/crates/*` (#52–56) and `agileplus-mcp/` (#57) for the AgilePlus platform.

---

## 4. Python packages under `python/` (7) — disposition table

`BOUNDARY.md` declares these "transitional" and being relocated to domain SDK repos,
matching the **[charter]** PhenoKits decomposition pattern (Python toolkit
collection → per-domain Python SDKs).

| # | Package | Disposition | Target repo | Rationale |
|---|---|---|---|---|
| 1 | `python/pheno-core` | **DECOMPOSE** | `phenotype-python-sdk` (umbrella) | Shared base; charter: "fold shared base into phenotype-python-sdk". |
| 2 | `python/pheno-mcp` | **DECOMPOSE** | `phenotype-python-sdk-mcp` | MCP domain SDK; mirrors Rust `phenotype-mcp` → McpKit. |
| 3 | `python/pheno-llm` | **DECOMPOSE** | `phenotype-python-sdk-llm` | LLM domain SDK. |
| 4 | `python/pheno-types` | **DECOMPOSE** | `phenotype-python-sdk-types` | Types domain SDK (or merge into umbrella). |
| 5 | `python/pheno-agents` | **DECOMPOSE** | `phenotype-python-sdk-agents` | Agents domain SDK. |
| 6 | `python/pheno-atoms` | **DECOMPOSE** | `phenotype-python-sdk-atoms` | Atoms domain SDK. |
| 7 | `python/phenosdk` | **DECOMPOSE** | `phenotype-python-sdk` (umbrella meta) | Meta-package; relocate with the umbrella it represents. |

---

## 5. Top-level apps, platforms, shelves, and historicals — disposition table

These are not cargo workspace members but top-level directories that hold
either real code, planning artifacts, or stale placeholders.

| # | Module (path) | What it is | Disposition | Target repo | Rationale |
|---|---|---|---|---|---|
| 1 | `apps/byteport` | Backend app (has `backend/` + FUNCTIONAL_REQUIREMENTS/PLAN/PRD) | **DECOMPOSE** | new `byteport` repo | App, not a lib. App repos are valid per charter. |
| 2 | `platforms/thegent/` (contains `planning/`) | Thegent platform planning artifacts | **DECOMPOSE** | new `thegent` repo (or merge with `src/thegent` → single `thegent` repo) | Platform; relocate all planning to the platform repo. |
| 3 | `src/thegent/planning` | Thegent planning mirror | **DECOMPOSE** | `thegent` repo (merge with #2) | Duplicate of platforms/thegent/planning; consolidate. |
| 4 | `flowra/` (ADR, CHARTER, PLAN, PRD, SPEC — no code) | Flowra project planning artifacts | **DECOMPOSE** | new `flowra` repo | Project, not a lib. |
| 5 | `Eventra/` (README-only stub) | Eventra crate already migrated to PhenoEvents/pheno-events (per `Eventra/README.md`) | **ABSORB** | `PhenoEvents` (migration already complete) | README self-declares the absorption; residual stub remains for history. Cleanup tracked separately. |
| 6 | `agileplus/` (umbrella: agileplus/, agileplus-agents/, agileplus-mcp/, crates/, docs/, harnesses/, pheno-cli/, prompts/, proto/, python/, references/, rust/, templates/, tests/, thegent-shm/) | AgilePlus platform umbrella | **DECOMPOSE** | `agileplus` repo | Distinct platform; relocate entire umbrella. |
| 7 | `agileplus-agents/` (top-level dir with `crates/`) | AgilePlus agents sub-project | **DECOMPOSE** | `agileplus` repo (with #6) | Sub-component of AgilePlus platform. |
| 8 | `koosha-portfolio/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` (scaffolding-gen) | Empty; if a portfolio scaffold is wanted it belongs in `templates/`. Keep dir for now per doctrine (no delete-on-sight). |
| 9 | `repos/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved for future scaffolded-repo manifest. |
| 10 | `vendor/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved. |
| 11 | `bifrost/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved. |
| 12 | `harnesses/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved (test harness templates). |
| 13 | `shelf-infra/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved (shelf-level infra templates). |
| 14 | `worklogs/` | Empty placeholder | **DYNAMIC-KEEP** | `HexaKit` | Empty; reserved. |
| 15 | `deferred-tests/bdd` | Deferred BDD test corpus | **ABSORB** | `HexaKit` (scaffolding-gen) | Test templates belong with the scaffold. |
| 16 | `prompts/`, `prompts/subcommands` | Prompt templates + subcommand prompts | **DYNAMIC-KEEP** | `HexaKit` (scaffolding-gen) | Part of scaffold generators (AI-DD metaproject). |
| 17 | `dotfiles/` (`governance/`, `hooks/`) | Dotfile + governance templates | **DYNAMIC-KEEP** | `HexaKit` (scaffolding-gen) | Per-repo dotfile templates belong with the scaffold. |
| 18 | `rust/` (only `.editorconfig` etc.) | Standalone rust template skeleton | **DYNAMIC-KEEP** | `HexaKit` | This is one of the `template-rust` siblings; merge into `template-rust/` or keep as alternate layout. |
| 19 | `proto/`, `proto/agileplus` | Protobuf + buf config | **ABSORB** | `agileplus` repo (the agileplus sub-proto) | Belongs with the AgilePlus platform. |
| 20 | `packages/pheno-core` (TS) | TS SDK core | **DECOMPOSE** | new `phenotype-ts-sdk` repo (or `phenoSDK` umbrella) | TS SDK package; relocate to TS domain SDK repo. |
| 21 | `packages/pheno-llm` (TS) | TS LLM SDK | **DECOMPOSE** | new `phenotype-ts-sdk-llm` (or `phenoSDK/llm`) | LLM TS SDK. |
| 22 | `packages/pheno-resilience` (TS) | TS resilience SDK | **DECOMPOSE** | new `phenotype-ts-sdk-resilience` (or `phenoSDK/resilience`) | Resilience TS SDK. |
| 23 | `kitty-specs/` (40+ spec dirs) | Spec-kitty specs history | **DYNAMIC-KEEP** | `HexaKit` (scaffolding-gen) | Specs are scaffolding metadata; keep with the scaffold. |
| 24 | `template-go/` | Go project template | **DYNAMIC-KEEP** | `HexaKit` | Per charter: HexaKit owns project templates. |
| 25 | `template-python/` | Python project template | **DYNAMIC-KEEP** | `HexaKit` | Per charter: HexaKit owns project templates. |
| 26 | `template-rust/` | Rust project template | **DYNAMIC-KEEP** | `HexaKit` | Per charter: HexaKit owns project templates. |
| 27 | `template-typescript/` | TS project template | **DYNAMIC-KEEP** | `HexaKit` | Per charter: HexaKit owns project templates. |
| 28 | `templates/` (go, hexagon, kotlin, linters, mojo, pages, partials, python, quality, rust, static, swift, typescript, zig) | Scaffolding templates library | **DYNAMIC-KEEP** | `HexaKit` | This *is* the scaffolding library HexaKit owns. |
| 29 | `.template.ci.yml`, `.template.editorconfig`, `.template.pre-commit.yaml` | Generated per-repo config sources | **DYNAMIC-KEEP** | `HexaKit` | Scaffolding source files; per-repo copies are generated. |
| 30 | `.githooks/`, `.github/`, `.devcontainer/`, `.mise.toml`, `Taskfile.yml`, `Brewfile`, `.editorconfig`, `.pre-commit-config.yaml`, `.gitattributes`, `.gitignore`, `.gitmodules` | Per-repo infra-generic config | **DYNAMIC-KEEP** | `HexaKit` (scaffolding source) | Charter: "infra-generic things present in *every* repo → hoist into a scaffolding / source-import generator". |
| 31 | `scripts/ci/`, `scripts/doc-sync/`, `scripts/gh/` | Scaffolding generators / CI scripts | **DYNAMIC-KEEP** | `HexaKit` | Scaffolding generator scripts. |
| 32 | `docs/` (.vitepress, adr, architecture, audit, audits, changes, checklists, concepts, decomposition, developers, doc-system, examples, fa, fa-Latn, governance, guide, guides, journeys, operations, pilot, process, reference, reports, research, roadmap, sdk, sessions, specs, tests, traceability, vendor, workflow, worklogs, zh-CN, zh-TW) | HexaKit scaffolding documentation | **DYNAMIC-KEEP** | `HexaKit` | Scaffolding docs. |
| 33 | Root governance files: `AGENTS.md`, `GOVERNANCE.md`, `CLAUDE.md`, `CODEOWNERS`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `FUNDING.yml`, `STATUS.md`, `CHANGELOG.md`, `VERSION`, `worklog.md`, `WORKTREES.md`, `LICENSE`, `README.md`, `BOUNDARY.md`, `SPEC.md`, `SOTA.md`, `COMPARISON.md`, `AGENTS.md`, `agents.toml`, `AGENTS.toml`, `convo-*.md` | Shelf + governance + project meta | **DYNAMIC-KEEP** | `HexaKit` | All HexaKit-internal governance and meta-docs. |
| 34 | `ADR.md`, `ADR-001..003.md`, `ADR_REGISTRY.md` | Architecture Decision Records | **DYNAMIC-KEEP** | `HexaKit` | ADRs are scaffolding history; keep. |
| 35 | `capital.toml`, `catalog-info.yaml`, `codecov.yml`, `cliff.toml`, `clippy.toml`, `deny.toml`, `dprint.json`, `renovate.json5`, `review.toml`, `rust-toolchain.toml`, `rustfmt.toml`, `buf.yaml`, `buf.gen.yaml`, `gitleaks.toml`, `registry.yaml`, `_typos.toml`, `.cliff.toml`, `.coderabbit.yaml`, `.commit-template`, `.commitlintrc.yml`, `.npmrc`, `.sccache`, `.serena`, `.vitepress`, `.work-audit`, `.agileplus`, `.airlock`, `.archive`, `.cargo`, `.forge`, `.kittify`, `.mcp-testing.yaml`, `Taskfile.yml`, `Cargo.lock`, `Cargo.toml.bak`, `bun.lock`, `Brewfile`, `Dockerfile.rust`, `docker-compose.yml`, `docker-compose.plane.yml`, `XDD-METHODOLOGIES.md`, `SPECS_REGISTRY.md`, `USER_JOURNEYS.md`, `USER_JOURNEYS_REGISTRY.md`, `PROJECT_CLASSIFICATION.md`, `FR_TRACEABILITY.md`, `FUNCTIONAL_REQUIREMENTS.md`, `EXECUTION_BRIEFING.md`, `FINAL_VERIFICATION_CHECKLIST.md`, `SAST_TIER1_QUICK_START.md`, `SENTRY_*.md` (8 files), `SNYK_AUTOMATION_READY.md`, `TOKEN_ACQUISITION_CHECKLIST.md`, `STATUS.md`, `GOVERNANCE_FIX_PLAN.md`, `GOVERNANCE_SYNC_COMPLETED.md`, `DUPLICATION_AUDIT.md`, `CONSOLIDATION_AUDIT.md`, `CONSOLIDATION_SUMMARY.md`, `FIXTURE_CONSOLIDATION_*.md` (3 files), `CI_FAILURE_DIAGNOSTIC_REPORT.md`, `CI_REMEDIATION_PLAN.md`, `DEPENDENCY_PHASE2_*.md` (4 files), `DEPENDENCIES.md`, `DEPENDENCIES_STANDARD.md`, `SSOT_DESIGN_SUMMARY.md`, `START_HERE_PHASE1.md`, `RICH_MEDIA.md`, `SPEC.md`, `docs/boundary/DISPOSITION.md` (this file) | Misc scaffolding / governance / config / ops files | **DYNAMIC-KEEP** | `HexaKit` | Scaffolding-adjacent. Trim during relocation but keep base files. |

---

## 6. Disposition roll-up

| Disposition | Count | Destination |
|---|---|---|
| **DECOMPOSE** (new domain repo) | 14 + 7 + 4 = **25** | new domain SDK / app / platform repos |
| **ABSORB** (existing target repo) | 20 | McpKit, Authvault, ResilienceKit, TestingKit, PhenoObservability, HexaKit scaffolding-gen, AgilePlus, PhenoEvents |
| **DYNAMIC-KEEP** | rest (templates, scaffolding assets, governance, empty placeholders) | `HexaKit` after relocation completes |
| **DELETE** | **0** | (charter doctrine: no delete-on-sight) |

> "Empty placeholders" count toward DYNAMIC-KEEP rather than deletion. If during
> a later pass the org decides an empty placeholder has no charter-aligned
> destination, it can be moved to a `phenoShared/_archive` style slot — still not
> a hard delete.

---

## 7. Open questions for the assessment PR review

1. **`crates/stashly` (caching):** dedicated `phenotype-cache` repo, or absorb
   into `ResilienceKit`? Charter mentions rate-limit → ResilienceKit; cache is
   adjacent. Both work; pick one.
2. **`crates/focalpoint`:** 867 MB vendor, excluded from workspace, not present
   in shallow clone. Needs its own dedicated assessment PR (cannot be relocated
   via `git subtree` due to size).
3. **`forgecode-fork`:** keep as a separate fork repo (for upstream sync) or
   absorb into HexaKit scaffolding-gen? Both are defensible.
4. **`packages/*` (TS SDKs):** new per-domain TS repos, or single
   `phenotype-ts-sdk` umbrella monorepo (mirrors Python umbrella)?
5. **`platforms/thegent` + `src/thegent`:** consolidate into a single
   `thegent` repo, or keep them as separate platform and source trees?

---

## 8. Citation

- **Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md) — Ecosystem Boundary-Shaping Charter, status *Active*, date 2026-06-16. Three dispositions: DECOMPOSE / ABSORB / DYNAMIC-KEEP. Doctrine: *no delete-on-sight*. Target topology: HexaKit = scaffolding, domain SDKs = McpKit / AuthKit / ResilienceKit / TestingKit / PhenoObservability / phenotype-gfx, umbrella = phenoSDK, too-small monorepo = phenoShared.
- **HexaKit self-declaration:** `BOUNDARY.md` (status ACTIVE) — "HexaKit is **not** a lib collection holder." Domain SDKs listed as install-separately.
- **Fleet scaffold generator:** [`docs/scaffolding/FLEET_INIT.md`](../scaffolding/FLEET_INIT.md) — `hexakit init` design (hooks, CI templates, BOUNDARY.md, STACK_POLICY lang gate, phenoSDK manifest extras).
- **HexaKit Cargo workspace:** `Cargo.toml` lines 10–71 — 53 members.
- **Related:** `phenotype-registry/docs/rationalization/block-c-consolidation.md` (charter §Execution); org memory `feedback_repo_boundary_shaping`.
