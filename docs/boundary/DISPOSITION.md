# pheno — Per-Module Boundary Disposition

**Status:** Assessment
**Date:** 2026-06-16
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/<REDACTED>/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md)
**Repo assessed:** [<REDACTED>/pheno](https://github.com/<REDACTED>/pheno) — Rust mega-monorepo + organizational "shelf"
**Charter's pre-classification of this repo:** *"170K LOC, 11 workspaces — Decompose by workspace into domain repos / existing *Kits; keep only too-small bits."*

> **Doctrine reminder (verbatim from charter):** A stub / empty / broken / unused / incomplete module is **not** a delete candidate by default. On-paper-good boundaries still deserve an owner. For each module/crate/folder pick ONE: **(1) DECOMPOSE**, **(2) ABSORB**, **(3) DYNAMIC-KEEP**. **No deletions** — every entry below gets an owner or stays in a dynamic-install monorepo.

---

## 1. Disposition Table

> **Legend:** D=DECOMPOSE · A=ABSORB · K=DYNAMIC-KEEP
> Columns: **Module** · **What it is** · **Disposition** · **Target repo** · **Rationale**

| # | Module | What it is | Disp. | Target repo | Rationale |
|---|--------|-----------|:-----:|-------------|-----------|
| 1 | `crates/` | Rust workspace, 60+ infra + agileplus + phenotype-* crates (the bulk of "pheno") | **D** | split per-crate → domain SDKs / phenoShared (see §2) | Charter: "pheno 170K LOC, 11 workspaces — Decompose by workspace." Largest signal in repo. |
| 2 | `python/` | Python packages (`pheno-agents`, `pheno-async`, `pheno-atoms`, `pheno-core`, `pheno-llm`, `pheno-mcp`, `phenosdk`, …) | **D** | split per-package → `phenotype-python-sdk` umbrella + per-domain Python SDKs | Charter: PhenoKits "decompose into domain Python SDKs; fold shared base into phenotype-python-sdk." |
| 3 | `rust/` | Rust apps sub-workspace (`src/`) | **D** | move apps out to their owning repos (Dino, Helix, …) | Apps belong with their platform, not in pheno. |
| 4 | `apps/` | Single sub-project `apps/byteport` (Go) | **D** | new repo `byteport` (or `phenotype-byteport`) | A standalone Go service should not live as a sub-dir of a Rust shelf. |
| 5 | `proto/` | Protobuf definitions for `agileplus/v1` | **A** | `agileplus-mcp` (or the new `agileplus` repo once extracted) | Proto is owned by the consuming service, not the shelf. |
| 6 | `platforms/thegent` | Thegent agent platform | **D** | new repo `thegent` (already named) | Thegent is a full platform product, not a library. |
| 7 | `platforms/thegent-pr882` | Thegent worktree clone for PR #882 | **K** | `thegent` (merge or drop the worktree) | Worktree clone, not a real project boundary. |
| 8 | `repos/phenotype-bootstrap` | Bootstrap tooling for new phenos | **A** | `phenotype-sentinel` (governance) or `HexaKit` (scaffolding) | Bootstrap is governance/scaffolding, not a domain repo. |
| 9 | `repos/phenotype-replication-engine` | Replication engine | **D** | new repo `phenotype-replication-engine` | Distinct domain, has its own readme/mission. |
| 10 | `templates/` | 9 language/framework scaffolding templates (`template-lang-*`, `template-domain-*`, `template-program-ops`) | **A** | `HexaKit` (scaffolding-gen) | Charter: "HexaKit = project + file templates / generators … NOT a lib holder." This is exactly that. |
| 11 | `template-domain-service-api`, `template-domain-webapp`, `template-go`, `template-lang-*`, `template-program-ops`, `template-python`, `template-rust`, `template-typescript` (root-level templates) | Duplicate/older template dirs at root | **A** | `HexaKit` (scaffolding) — merge w/ `templates/` | These appear to be the older root-level set vs. `templates/` newer set; consolidate. |
| 12 | `template-lang-elixir-hex`, `template-lang-kotlin`, `template-lang-mojo`, `template-lang-swift`, `template-lang-zig` | Extra language templates (no `template-lang-rust/go/python/ts` siblings at root) | **A** | `HexaKit` (scaffolding) | Charter: scaffolding templates belong in HexaKit. |
| 13 | `kitty-specs/` | 24 spec-kit specs (001..007 + eco-* + phenosdk-* + portfolio-*) | **A** | `phenotype-skills` or new `phenotype-specs` repo | Specs are governance content, not source. |
| 14 | `prompts/` + `prompts/subcommands/` | Agent prompts + sub-commands | **A** | `phenotype-skills` (skill defs) | Prompts/skills are one boundary. |
| 15 | `harnesses/` | Test harnesses (contains `FR-TRACE-BACKFILL-001.md`) | **A** | `HexaKit` (scaffolding) — generated, tailorable | Harnesses are infra-generic across repos. |
| 16 | `tests/` (root: `bdd/`, `contract/`, `contracts/`, `fixtures/`, `integration/`, `test_phench_runtime.py`) | Cross-project test scaffolding | **A** | `HexaKit` (scaffolding) | Infra-generic test scaffolding belongs in scaffolding-gen. |
| 17 | `scripts/` + `scripts/ci`, `scripts/doc-sync`, `scripts/gh` | Dev scripts incl. CI helpers, doc-sync, gh helpers | **A** | `HexaKit` (scaffolding) | Scripts duplicated across repos → scaffolded from a single source. |
| 18 | `docs/` (root governance index) | Cross-project governance docs (`adr/`, `governance/`, `roadmap/`, `agents/`, `journeys/`, …) | **A** | `phenotype-sentinel` (governance) | Governance is a domain, not a side-effect of pheno. |
| 19 | `docs/decomposition/` | Per-crate decomposition plans (SQLite adapter etc.) | **A** | move to the receiving crate's own repo once decomposed | Decomposition plans follow the code they describe. |
| 20 | `sbom/` | SBOM artifacts (`*.cdx.json` cyclonedx) | **A** | `phenotype-sentinel` (security aggregator) | SBOM is a security/output concern. |
| 21 | `dotfiles/` (`dotfiles/governance/`, `dotfiles/hooks/`) | Base `CLAUDE.md`, pre-commit base, linter templates | **A** | `HexaKit` (scaffolding) | Charter: "reverse: infra-generic things present in *every* repo … hoist into a scaffolding / source-import generator." |
| 22 | `vendor/` (`vendor/phenodocs`) | Vendored third-party docs | **A** | drop into the consuming repo or a `phenodocs` repo | Vendored deps belong with the consumer, not the shelf. |
| 23 | `src/` (`src/thegent`) | Stray thegent source mirror | **A** | `platforms/thegent` (which moves to its own repo) | Mirror of thegent, not a new boundary. |
| 24 | `specs/` | Per-spec kits (root level — confirmed empty) | **A** | `phenotype-skills` / merged into `kitty-specs` | Single source for specs. |
| 25 | `worklogs/` + `WORKTREES.md` + `worklog.md` | Session worklogs, worktree notes | **A** | `phenotype-sentinel` (governance memory) or a dedicated `phenotype-worklogs` repo | Worklogs are operational telemetry, not a domain. |
| 26 | `phenotype-agent-core` | Agent runtime core (Rust) | **D** | new repo `phenotype-agent-core` (or merged into `thegent` if identical) | Distinct domain — agent runtime. |
| 27 | `phenotype-task-engine` | Task execution engine (Rust) | **D** | new repo `phenotype-task-engine` | Distinct domain — task execution. |
| 28 | `phenotype-auth-ts` | TypeScript authentication | **D** | **`AuthKit`** (the charter's named "AuthKit" SDK) | Charter names `AuthKit` (and points it at `Authvault`); this is the TS face of it. |
| 29 | `phenotype-cipher` | Cryptographic operations (Rust) | **D** | new repo `phenotype-cipher` (or merge into `ResilienceKit`) | Cross-cutting crypto: stays a domain repo. |
| 30 | `phenotype-sentinel` | Security monitoring (Rust) | **D** | new repo `phenotype-sentinel` | Distinct domain — security monitoring. |
| 31 | `phenotype-dep-guard` | Dependency scanning (Rust) | **A** | `phenotype-sentinel` (security aggregator) | Dep-scanning is a security concern. |
| 32 | `phenotype-router-monitor` | HTTP router monitoring (Rust) | **A** | **`ResilienceKit`** (HTTP health/rate/observability domain) | Charter: ResilienceKit owns the resilience/observability/transport boundary. |
| 33 | `phenotype-forge` | Code generation + templating (Rust) | **A** | `HexaKit` (scaffolding-gen) | Forge *is* scaffolding generation. |
| 34 | `phenotype-cli-extensions` | CLI tooling extensions (Rust) | **D** | new repo `phenotype-cli-extensions` (or merged into `helios-cli`) | CLI is a domain. |
| 35 | `phenotype-patch` | Patch management (Rust) | **A** | `phenotype-sentinel` (governance tooling) | Patch mgmt is governance. |
| 36 | `phenotype-skills` | Agent skill defs (Markdown) | **D** | new repo `phenotype-skills` (or merged with `kitty-specs` owner) | Skills are a domain. |
| 37 | `phenotype-docs-engine` | Documentation generation (Rust) | **D** | new repo `phenotype-docs-engine` (or merge into `phenodocs`) | Distinct domain — docs gen. |
| 38 | `phenotype-research-engine` | Research data processing (Rust) | **D** | new repo `phenotype-research-engine` | Distinct domain — research. |
| 39 | `phenotype-xdd-lib` | xDD shared library (TS) | **A** | new/extract `phenotype-xdd` (already named in PHENOTYPE_INDEX) or new repo | xDD methodology is a single domain. |
| 40 | `phenotype-config-ts` | TypeScript configuration | **A** | new `phenotype-config-ts` repo (or `phenoShared`) | Cross-cutting config — DYNAMIC-KEEP if small. |
| 41 | `phenotype-types` | Shared type defs (TS) | **K** | **`phenoShared`** (too-small monorepo) | Charter: "phenoShared = home only for bits too small to own a repo." Type defs fit. |
| 42 | `phenotype-infrakit` | Shared Rust infrastructure crates | **D** | per-crate → domain SDKs; deprecate umbrella | Already a duplicate of `crates/` work; decompose. |
| 43 | `phenotype-vessel` | Container / runtime tools (Rust) | **D** | new repo `phenotype-vessel` | Distinct domain. |
| 44 | `phenotype-evaluation` | Code evaluation tools (Rust) | **D** | new repo `phenotype-evaluation` (or merge into `Evalora`) | Domain — code eval. |
| 45 | `phenotype-hub` | Web dashboard (Next.js) | **D** | new repo `phenotype-hub` | Standalone web app. |
| 46 | `phenotype-middleware-py` | Python middleware | **A** | `phenotype-python-sdk` umbrella (per-language SDK) | Charter: "phenotype-python-sdk / go-sdk … per-language SDK umbrellas." |
| 47 | `phenotype-governance` | Shared governance configs | **A** | `phenotype-sentinel` (governance owner) | Governance is one domain. |
| 48 | `phenotype-logging-zig` | Zig logging library (Archived) | **D** | new repo `phenotype-logging-zig` (or move to `PhenoObservability` if revived) | Already archived; keep its own repo for future revival. |
| 49 | `agileplus` | AgilePlus project mgmt system (root) | **D** | new repo `agileplus` (single canonical repo) | Already named; needs its own dedicated repo. |
| 50 | `agileplus-agents` | Agent defs for AgilePlus | **A** | `agileplus` (single canonical) | Sub-piece of agileplus. |
| 51 | `agileplus-mcp` | MCP server for AgilePlus | **A** | `agileplus` (single canonical) | Sub-piece of agileplus. |
| 52 | `agileplus-plugin-core` | AgilePlus plugin core | **A** | `agileplus` (single canonical) | Sub-piece of agileplus. |
| 53 | `agileplus-plugin-git` | AgilePlus git plugin | **A** | `agileplus` (single canonical) | Sub-piece of agileplus. |
| 54 | `agileplus-plugin-sqlite` | AgilePlus sqlite plugin | **A** | `agileplus` (single canonical) | Sub-piece of agileplus. |
| 55 | `crates/agileplus-*` (22 crates incl. `agileplus-api`, `-benchmarks`, `-cache`, `-cli`, `-contract-tests`, `-domain`, `-error-core`, `-events`, `-git`, `-github`, `-graph`, `-grpc`, `-import`, `-integration-tests`, `-nats`, `-p2p`, `-plane`, `-sqlite`, `-subcmds`, `-sync`, `-telemetry`, `-triage`, `-api-types`) | AgilePlus Rust crate family | **A** | `agileplus` repo (single canonical) | All 22 belong with the agileplus platform. |
| 56 | `Apisync` | API sync (Go?) | **D** | new repo `apisync` | Standalone app. |
| 57 | `bare-cua` | CUA (computer-use-agent) bare project | **D** | new repo `bare-cua` | Distinct domain — agent modality. |
| 58 | `bifrost` | Routing (likely a service) | **A** | **`McpKit`** (mcp/router overlap) or new repo `bifrost` | Bifrost = routing; charter has `McpKit` for mcp-domain. Likely new repo. |
| 59 | `bifrost-routing` (under `crates/`) | Bifrost routing crate | **A** | `bifrost` repo (after extraction) | Belongs with bifrost. |
| 60 | `BytePort` | Data transport platform | **D** | new repo `byteport` (also `apps/byteport` goes here) | Standalone platform. |
| 61 | `clikit` | CLI kit | **A** | `helios-cli` (the CLI surface) or new repo `clikit` | CLI boundary. |
| 62 | `cloud` | Cloud tooling | **A** | new repo `phenotype-cloud` or merge into `HexaKit` as infra | Cloud tooling is infra-generic, leans scaffolding. |
| 63 | `Cmdra` | Command runner | **A** | `helios-cli` / new repo `cmdra` | CLI sub-domain. |
| 64 | `Cursora` | Cursor-related tool | **D** | new repo `cursora` (or merge into `phenotype-cli-extensions`) | Distinct tool. |
| 65 | `Datamold` | Data transformation platform | **D** | new repo `datamold` | Standalone platform. |
| 66 | `Dino` | Dino (likely a DOTS/Unity bridge per `dinoforge` MCP) | **D** | new repo `dino` | Standalone domain (DOTS/Unity). |
| 67 | `Docuverse` | Documentation app | **D** | new repo `docuverse` (or merge into `phenodocs`) | Standalone app. |
| 68 | `Duple` | Data duplication | **D** | new repo `duple` | Standalone app. |
| 69 | `Evalora` | Evaluation framework | **D** | new repo `evalora` (or merge with `phenotype-evaluation`) | Domain — evaluation. |
| 70 | `Flagward` | Feature flags | **D** | new repo `flagward` | Standalone app. |
| 71 | `Flowra` | Workflow app | **D** | new repo `flowra` | Standalone app. |
| 72 | `forgecode-fork` | Fork of forgecode | **K** | `HexaKit` (scaffolding) — fork is scaffolding reference | Fork; reference for scaffolding. |
| 73 | `Guardis` | Security app | **A** | `phenotype-sentinel` (security owner) | Security is one domain. |
| 74 | `helios-cli` | Helios CLI | **D** | new repo `helios-cli` (canonical) | Standalone CLI. |
| 75 | `helix-logging` | Logging lib (helix) | **A** | **`PhenoObservability`** (the charter's observability SDK) | Charter names `PhenoObservability` — this is its rust face. |
| 76 | `helMo` | HelMo (unclear) | **D** | new repo `helmo` or merge into relevant domain | Distinct project. |
| 77 | `Hexacore` | Hexagonal core (kit) | **A** | `HexaKit` (scaffolding) + relocate any real libs to domain SDKs | Charter: "HexaKit = project + file templates / generators … NOT a lib holder." Hexacore's libs must move out. |
| 78 | `HexaGo` | Hexagonal Go | **A** | `HexaKit` (scaffolding) — same disposition as Hexacore but Go | Same as Hexacore. |
| 79 | `hexagon-python` | Hexagonal Python | **A** | `HexaKit` (scaffolding) | Same as Hexacore. |
| 80 | `hexagon-rs` | Hexagonal Rust | **A** | `HexaKit` (scaffolding) | Same as Hexacore. |
| 81 | `hexagon-ts` | Hexagonal TypeScript | **A** | `HexaKit` (scaffolding) | Same as Hexacore. |
| 82 | `HexaPy` | Hexagonal Python (alt) | **A** | `HexaKit` (scaffolding) — merge with `hexagon-python` | Duplicates `hexagon-python`. |
| 83 | `HexaType` | Hexagonal TypeScript (alt) | **A** | `HexaKit` (scaffolding) — merge with `hexagon-ts` | Duplicates `hexagon-ts`. |
| 84 | `Httpora` | HTTP toolkit app | **A** | **`ResilienceKit`** (HTTP/transport/resilience) | Charter's `ResilienceKit` is the home for HTTP/transport. |
| 85 | `KaskMan` | Cache manager app | **A** | **`ResilienceKit`** (caching is a resilience concern) | Caching = resilience. |
| 86 | `kits/` | Root `kits/` dir (empty / no sub-dirs) | **K** | drop after `phenotype-python-sdk` consumes its members | Empty shell; dissolve. |
| 87 | `kits/pheno-core`, `kits/pheno-llm`, `kits/pheno-resilience` (NOT in this clone — only `packages/` versions) | Earlier kit layout | **D** | `phenotype-python-sdk` umbrella (per-language SDK) | Replace with `packages/*` versions (which exist). |
| 88 | `KodeVibeGo` | Go dev tooling | **D** | new repo `kodevibe-go` | Standalone dev tool. |
| 89 | `Kogito` | Knowledge app | **D** | new repo `kogito` | Standalone app. |
| 90 | `koosha-portfolio` | Personal portfolio site | **D** | new repo `koosha-portfolio` (out of org scope) | Personal site; not a phenotype project. |
| 91 | `libs/` (root: `nexus`, `phenotype-config-core`, `pheno-core`, `pheno-llm`, `pheno-resilience` + `README.md`, `tsconfig.json`) | Root-level "libs" sub-tree (overlaps `packages/`) | **D** | merge with `packages/` and feed `phenotype-python-sdk` | Duplicates `packages/`; consolidate. |
| 92 | `libs/phenotype-config-core` | Duplicate of `crates/phenotype-config-core` | **A** | `crates/phenotype-config-core` (Rust owns it) | Cross-tree duplicate. |
| 93 | `libs/pheno-core` / `libs/pheno-llm` / `libs/pheno-resilience` | TS/Node mirror of Python pkgs | **D** | `phenotype-typescript-sdk` (or each into its own domain SDK: `PhenoCore`, `PhenoLLM`, `ResilienceKit`) | Per-language SDK umbrellas. |
| 94 | `nanovms` | nanovms-related work | **D** | new repo `phenotype-nanovms` (or merge into a serverless domain) | Distinct domain. |
| 95 | `omniroute-temp` | Omniroute scratch dir | **A** | `bifrost` (routing) or `phenotype-cli-extensions` | Scratch / temp; absorb into real home. |
| 96 | `org-github` | Org-GitHub scratch dir | **A** | `phenotype-sentinel` (governance) | Org-level governance scratch. |
| 97 | `packages/pheno-core`, `packages/pheno-llm`, `packages/pheno-resilience` | Python packages (npm/pip?) | **D** | `phenotype-python-sdk` umbrella (per-language SDK) | Per-language SDK umbrellas. |
| 98 | `pheno-cli` (`cmd/`, `docs/`, `hooks/`, `internal/`) | Pheno CLI | **A** | `helios-cli` (single canonical CLI) or new repo `pheno-cli` | CLI is a domain. |
| 99 | `pheno-agents` (under `python/`) | Python agent pkg | **A** | `phenotype-agent-core` (or `phenotype-python-sdk`) | Belongs with agent core. |
| 100 | `pheno-async`, `pheno-atoms`, `pheno-core`, `pheno-core-utils`, `pheno-errors`, `pheno-exceptions`, `pheno-llm`, `pheno-mcp`, `pheno_config`, `pheno_core`, `pheno_utils` (under `python/`) | Python base pkgs | **A** | `phenotype-python-sdk` (umbrella) | Per-language SDK umbrella. |
| 101 | `phenosdk` (under `python/`) | Pheno SDK (Python) | **A** | `phenotype-python-sdk` (umbrella) | Confirms the umbrella role. |
| 102 | `phenodocs` | Pheno docs (likely a repo) | **D** | new repo `phenodocs` (or merge with `phenotype-docs-engine`) | Docs is a domain. |
| 103 | `phenoSDK` (root) | Pheno SDK (umbrella) | **D** | `phenotype-python-sdk` + per-language SDKs (umbrella dispatcher) | Umbrella → per-language SDKs. |
| 104 | `Planify` | Planning app | **D** | new repo `planify` | Standalone app. |
| 105 | `Platforms` (vs `platforms`) | Capital-P duplicate directory | **A** | `platforms/` (lowercase) | Normalize casing. |
| 106 | `PolicyStack` | Policies app | **D** | new repo `policystack` | Standalone app. |
| 107 | `portage` | Package mgmt CLI | **D** | new repo `portage` (or merge with `helios-cli`) | Distinct CLI. |
| 108 | `Portalis` | Portal app | **D** | new repo `portalis` | Standalone app. |
| 109 | `Profila` | Profile mgmt | **D** | new repo `profila` | Standalone app. |
| 110 | `Queris` | Query system | **D** | new repo `queris` | Standalone app. |
| 111 | `Quillr` | Document processing | **D** | new repo `quillr` | Standalone app. |
| 112 | `Schemaforge` | Schema mgmt | **D** | new repo `schemaforge` | Standalone app. |
| 113 | `Seedloom` | Seeding tool | **D** | new repo `seedloom` | Standalone app. |
| 114 | `sharecli` | Share CLI | **A** | `phenotype-cli-extensions` (CLI sub-domain) | CLI sub-domain. |
| 115 | `shelf-infra` | Shelf infrastructure tooling | **A** | `phenotype-sentinel` (governance) | Shelf-internal infra. |
| 116 | `thegent-cache`, `thegent-mesh`, `thegent-metrics`, `thegent-plugin-host`, `thegent-sharecli`, `thegent-shm`, `thegent-subprocess` (root) | Thegent sub-components | **A** | `thegent` (single canonical) | Sub-pieces of thegent. |
| 117 | `Tokn` | Token mgmt app | **D** | new repo `tokn` (or merge into `AuthKit`) | Auth/token domain. |
| 118 | `Tossy` | Task orchestration | **D** | new repo `tossy` (or merge with `phenotype-task-engine`) | Distinct domain. |
| 119 | `tracely` | Tracing tool | **A** | **`PhenoObservability`** | Tracing is observability. |
| 120 | `Tracera` | Tracing app | **A** | **`PhenoObservability`** | Tracing is observability. |
| 121 | `vibeproxy` | Vibe proxy | **D** | new repo `vibeproxy` (or merge into `bifrost` routing) | Distinct proxy domain. |
| 122 | `vibeproxy-monitoring-unified` | Vibeproxy monitoring | **A** | `vibeproxy` after extraction, or **`PhenoObservability`** | Monitoring is observability. |
| 123 | `worktree-manager` | Worktree manager | **A** | `phenotype-sentinel` (governance tooling) | Governance/dev tooling. |
| 124 | `zen` | Zen (unclear) | **D** | new repo `zen` (or merge with `phenotype-research-engine`) | Distinct project. |
| 125 | `Zerokit` | Zero-config toolkit | **D** | new repo `zerokit` | Standalone toolkit. |
| 126 | `Cargo.toml`, `Cargo.toml.bak` | Workspace manifest + backup | **A** | dissolved once `crates/` decomposes | Workspace dissolves with decomposition. |
| 127 | `bun.lock` (root), `Brewfile`, `buf.gen.yaml`, `buf.yaml`, `cliff.toml`, `clippy.toml`, `codecov.yml`, `deny.toml`, `Dockerfile.rust`, `docker-compose*.yml`, `gitleaks.toml`, `justfile`, `lefthook.yml`, `process-compose.yml`, `renovate.json5`, `release-plz.toml`, `review.toml`, `rust-toolchain.toml`, `rustfmt.toml`, `Taskfile.yml`, `.template.*`, `Taskfile.yml`, `agents.toml`, `capital.toml`, `.commit-template`, `.cliff.toml`, `Brewfile`, `Taskfile.yml` | Top-level config / build / lint / dev-shell files | **A** | `HexaKit` (scaffolding) — these are the exact "infra-generic" patterns the charter says should be **generated, not hand-maintained per repo** | Charter: *"reverse: infra-generic things present in every repo → hoist into a scaffolding / source-import generator (unified maintenance + per-repo distributed config/tailoring), not N hand-maintained copies."* |
| 128 | `.adoption/`, `.airlock/`, `.agileplus/`, `.archive/`, `.cargo/`, `.coderabbit.yaml`, `.commitlintrc.yml`, `.devcontainer/`, `.editorconfig`, `.env.*.example`, `.forge/`, `.gitattributes`, `.githooks/`, `.github/`, `.gitignore`, `.gitmodules`, `.grade-reports/`, `.kittify/`, `.mcp-testing.yaml`, `.mise.toml`, `.npmrc`, `.pre-commit-config.yaml`, `.sccache/`, `.serena/`, `.vitepress/`, `.work-audit/` | Top-level dotfiles, configs, governance | **A** | `HexaKit` (scaffolding) — generated/tailorable per repo | Charter: infra-generic → scaffolding generator. |
| 129 | `AGENTS.md`, `CLAUDE.md`, `CODEOWNERS`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `STATUS.md`, `CHANGELOG.md`, `LICENSE`, `CITATION.cff`, `README.md` (shelf-level) | Shelf-level meta files | **A** | `HexaKit` (scaffolding) for templates + kept at shelf level until shelf dissolves | Standard meta files belong in scaffolding templates. |
| 130 | `ADR.md`, `ADR_REGISTRY.md`, `PRD.md`, `PLAN.md`, `PLAN_REGISTRY.md`, `COMPARISON.md`, `CONSOLIDATION_AUDIT.md`, `CONSOLIDATION_SUMMARY.md`, `DUPLICATION_AUDIT.md`, `EXECUTION_BRIEFING.md`, `PHENOTYPE_AUDIT_REPORT.md`, `PHENOTYPE_INDEX.md`, `PHENOTYPE_TEST_AUDIT.md`, `SPECS_REGISTRY.md`, `USER_JOURNEYS.md`, `USER_JOURNEYS_REGISTRY.md`, `WORKTREES.md`, `TOKEN_ACQUISITION_CHECKLIST.md`, `SENTRY_*` series, `SNYK_AUTOMATION_READY.md`, `CI_FAILURE_DIAGNOSTIC_REPORT.md`, `CI_REMEDIATION_PLAN.md`, `DEPENDENCY_PHASE2_*`, `EVIDENCE_LEDGER.jsonl`, `worklog.md`, `convo-*.md`, `START_HERE_PHASE1.md`, `GOVERNANCE*.md`, `GOVERNANCE_SYNC_COMPLETED.md`, `GOVERNANCE_FIX_PLAN.md`, `FR_TRACEABILITY.md`, `FUNCTIONAL_REQUIREMENTS.md`, `FINAL_VERIFICATION_CHECKLIST.md`, `FIXTURE_CONSOLIDATION_*`, `SSOT_DESIGN_SUMMARY.md`, `MULTI_AGENT_ORCHESTRATION_COMPARISON_2026.md`, `XDD-METHODOLOGIES.md`, `SAST_TIER1_QUICK_START.md`, `grade.sh`, `_typos.toml`, `evidence_ledger.jsonl` | Shelf-level reports / plans / governance / audit logs / worklogs | **A** | `phenotype-sentinel` (governance) or `phenotype-worklogs` | Operational + governance artifacts; not source. |

> **Note on `crates/` decomp:** The 60+ crates in `crates/` decompose along the same lines as the table above (e.g. `phenotype-cipher` → `phenotype-cipher` repo, `phenotype-error-core`/`-errors`/`-error-macros` → `phenoShared` if small, `phenotype-retry`/`-time`/`-string`/`-validation` → `ResilienceKit`, `phenotype-mcp` → `McpKit`, `phenotype-test-*` → `TestingKit`, `phenotype-telemetry` → `PhenoObservability`, etc.). See §2 for the per-crate outline.

---

## 2. Recommended End-State for pheno

### 2.1 Where each major workspace lands

| From `pheno` (today) | To (end-state) | Owner disposition |
|----------------------|----------------|-------------------|
| `crates/` (60+ Rust crates) | split per-crate → domain SDKs and `phenoShared` | **DECOMPOSE** by crate; see §2.2 |
| `python/` (Python packages) | `phenotype-python-sdk` umbrella + domain Python SDKs | **DECOMPOSE** (per pkg) |
| `rust/` (apps sub-workspace) | apps → their owning repos | **DECOMPOSE** |
| `apps/byteport` | new repo `byteport` (or `phenotype-byteport`) | **DECOMPOSE** |
| `proto/` | `agileplus-mcp` (consumer) | **ABSORB** |
| `platforms/thegent*` | new repo `thegent` (single canonical) | **DECOMPOSE** |
| `repos/phenotype-*` | each → its own domain repo | **DECOMPOSE** |
| `templates/` + `template-*` (root) | `HexaKit` (scaffolding) | **ABSORB** |
| `kitty-specs/`, `prompts/`, `skills`, `specs/` | `phenotype-skills` / `phenotype-specs` | **ABSORB** |
| `harnesses/`, `tests/`, `scripts/`, `dotfiles/`, root `*.toml/*.yml/*.lock` | `HexaKit` (scaffolding-gen) | **ABSORB** |
| `docs/`, `sbom/`, `worklogs/`, `WORKTREES.md`, `shelf-infra/`, `worktree-manager/`, governance/reports | `phenotype-sentinel` (governance) | **ABSORB** |
| Per-app dirs (`agileplus*`, `Apisync`, `bare-cua`, `bifrost`, `BytePort`, `clikit`, `cloud`, `Cmdra`, `Cursora`, `Datamold`, `Dino`, `Docuverse`, `Duple`, `Evalora`, `Flagward`, `Flowra`, `Guardis`, `helios-cli`, `helMo`, `Httpora`, `KaskMan`, `KodeVibeGo`, `Kogito`, `koosha-portfolio`, `nanovms`, `Planify`, `PolicyStack`, `portage`, `Portalis`, `Profila`, `Queris`, `Quillr`, `Schemaforge`, `Seedloom`, `Tokn`, `Tossy`, `vibeproxy*`, `zen`, `Zerokit`, …) | each → new dedicated repo | **DECOMPOSE** (one repo per project) |
| `Hexacore` / `HexaGo` / `hexagon-python` / `hexagon-rs` / `hexagon-ts` / `HexaPy` / `HexaType` / `phenotype-forge` | `HexaKit` (scaffolding) — any real lib code relocated to domain SDKs first | **ABSORB** + **DECOMPOSE** (libs out) |
| `helix-logging`, `tracely`, `Tracera`, `phenotype-router-monitor` | `PhenoObservability` (charter-named) / `ResilienceKit` | **ABSORB** |
| `phenotype-auth-ts`, `Tokn`, `Authvault-ref` (sibling repo) | `AuthKit` → `Authvault` (charter: "AuthKit→Authvault") | **ABSORB** |
| `phenotype-cipher`, `phenotype-sentinel`, `phenotype-dep-guard`, `Guardis`, `phenotype-patch` | `phenotype-sentinel` (security aggregator) | **ABSORB** |
| `Httpora`, `KaskMan`, `phenotype-router-monitor` | `ResilienceKit` | **ABSORB** |
| `phenotype-mcp` crate, `bifrost` | `McpKit` | **ABSORB** |
| `phenotype-test-*` (test-infra, test-fixtures, testing, bdd) | `TestingKit` | **ABSORB** |
| `kits/`, `packages/`, `libs/` (sub-trees), `pheno-cli`, `phenosdk`, `phenoSDK` | per-language SDK umbrellas (`phenotype-python-sdk`, `phenotype-typescript-sdk`, `phenotype-go-sdk`) | **DECOMPOSE** into per-language SDKs |
| `phenotype-types`, small cross-cutting type defs | `phenoShared` (dynamic-install monorepo) | **DYNAMIC-KEEP** |
| `agileplus` + `agileplus-*` + `crates/agileplus-*` (22 crates) | single canonical `agileplus` repo | **DECOMPOSE** (consolidate) |
| `phenotype-governance`, `phenotype-skills` (markdown) | `phenotype-sentinel` (governance) / `phenotype-skills` (skills) | **ABSORB** |
| `phenotype-forge` (Rust code-gen) | `HexaKit` (scaffolding-gen) | **ABSORB** |

### 2.2 `crates/` per-crate decomp outline (charter says "decompose by workspace")

| Crate | Disposition | Target |
|-------|:-----------:|--------|
| `phenotype-error-core` / `phenotype-error-macros` / `phenotype-errors` / `phenotype-async-traits` / `phenotype-iter` / `phenotype-string` / `phenotype-time` / `phenotype-validation` / `phenotype-macros` | **K** (DYNAMIC-KEEP) | `phenoShared` — too small to own a repo |
| `phenotype-telemetry` | **A** | `PhenoObservability` |
| `phenotype-logging` (and `helix-logging` root) | **A** | `PhenoObservability` |
| `phenotype-mcp` | **A** | `McpKit` |
| `phenotype-cipher` | **D** | new repo `phenotype-cipher` |
| `phenotype-retry` / `phenotype-state-machine` / `phenotype-policy-engine` / `phenotype-casbin-wrapper` / `phenotype-rate-limit` | **A** | `ResilienceKit` |
| `phenotype-health` | **A** | `ResilienceKit` (or `PhenoObservability`) |
| `phenotype-http-client-core` / `phenotype-contracts` / `phenotype-contract` / `phenotype-port-traits` / `phenotype-ports-canonical` | **A** | `ResilienceKit` (transport) / `phenoShared` (port-traits if tiny) |
| `phenotype-cache-adapter` | **A** | `ResilienceKit` |
| `phenotype-test-infra` / `phenotype-test-fixtures` / `phenotype-testing` / `phenotype-bdd` / `phenotype-mock` | **A** | `TestingKit` |
| `phenotype-event-bus` / `phenotype-event-sourcing` | **D** | new repo `phenotype-event-sourcing` |
| `phenotype-config-core` / `phenotype-config-loader` / `phenotype-shared-config` | **A** | `phenoShared` (small) or `phenotype-config-ts` mirror |
| `phenotype-cost-core` / `phenotype-infrastructure` | **D** | new repo `phenotype-infrastructure` |
| `phenotype-process` / `phenotype-git-core` | **D** | new repo `phenotype-process` / merge into `phenotype-git-core` standalone |
| `phenotype-security-aggregator` / `phenotype-compliance-scanner` | **A** | `phenotype-sentinel` |
| `phenotype-project-registry` | **D** | new repo `phenotype-project-registry` |
| `agileplus-nats` (and all other 22 `agileplus-*` crates) | **A** | `agileplus` (single canonical) |
| `bifrost-routing` | **A** | `bifrost` repo (after extraction) |
| `forgecode-core` | **A** | `HexaKit` (scaffolding) |
| `pheno-data-from-phenoData` | **K** | `phenoShared` (odd name; tiny) |

### 2.3 Net result for `pheno`

- **Goes away** as a mega-monorepo (charter: *"decompose by workspace"*).
- **Becomes** a small "shell-archive" repo whose only role is to point at the now-scattered repos, OR is fully deprecated once every project has a canonical repo and `HexaKit` carries the scaffolding.
- **No deletions occur** during the move — every project gets a destination repo, every crate gets a destination crate/repo, and the `pheno` shell is retained as a redirector until all README/CLAUDE links are migrated.

---

## 3. Target Topology Reference (from charter, verbatim)

> *"HexaKit = project + file **templates / generators** that bootstrap new repos onto our arch patterns. NOT a lib holder. Owns the infra-generic layer (tests/CI/governance) as generated, tailorable scaffolding."*
> Domain SDKs: **McpKit · AuthKit→Authvault · ResilienceKit · TestingKit · PhenoObservability · phenotype-gfx**
> Umbrella: `phenoSDK`-style meta (dynamic install/import of the domain SDKs)
> Too-small monorepo: **`phenoShared`** (dynamic install)

For `pheno` specifically the charter says:

> *"pheno | 170K LOC, 11 workspaces | Rust mega-monorepo | **Decompose** by workspace into domain repos / existing *Kits; keep only too-small bits."*

This document delivers that assessment.

---

## 4. Execution Order (per charter)

> *"Per repo: assessment job → per-module disposition table → history-preserving move PRs → archive emptied shells only after relocation."*

1. **Now (this PR):** per-module disposition table — ✅ this document.
2. **Next PRs:** one history-preserving move PR per receiving repo, in this order:
   1. `HexaKit` first (so generated scaffolding replaces the root `.toml`/`.yml`/`.lock` files).
   2. `phenoShared` (consume the too-small crates from `crates/`).
   3. Domain SDKs in charter order: `McpKit` → `AuthKit`/`Authvault` → `ResilienceKit` → `TestingKit` → `PhenoObservability` → `phenotype-gfx`.
   4. Standalone product repos (one per top-level app dir).
   5. `agileplus` consolidation (last, biggest blast radius).
3. **After all moves land:** archive the `pheno` shell repo (rename to `pheno-archive`) so old links still resolve to a redirect.

---

**End of disposition.** No deletions. Every module above has an owner.
