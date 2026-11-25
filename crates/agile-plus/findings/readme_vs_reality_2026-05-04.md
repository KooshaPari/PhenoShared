# README vs Reality Audit 2026-05-04

## Drift Summary

| # | Repo | Claim | Reality | Severity |
|---|------|-------|---------|----------|
| 1 | AgilePlus | Rust workspace at `rust/` with hexagonal core, event sourcing, gRPC stubs | `rust/Cargo.toml` exists but **fails to build** -- empty `members = []`, broken `tonic` workspace dependency inheritance. 24 crates + 19 libs directories exist on disk but contain **zero `.rs` files**. Python layer directory empty (no `.py` files). Proto files and openapi.yaml exist. Landing app is Astro-based. | HIGH |
| 2 | AgilePlus-wtrees | Should be worktree staging area | Contains 16 branch-name directories (e.g. `cargo-deny-fix-tonic`, `journey-impl`, `quality-gate`). Includes full copy of AgilePlus with its own `Cargo.toml`, `apps/`, `proto/`, etc. Not a worktree directory -- it appears to be a container repo for feature branches. No README. | LOW |
| 3 | heliosApp | "ElectroBun-based UI", "stable", 4 apps, 5 packages, 33 CI workflows, full runtime+desktop+renderer+colab | All 4 apps exist with full TypeScript source (~470 `.ts` files). All 5 packages present. 33 CI workflows confirmed. Desktop tests: 21 unit test files. Runtime modules (protocol, sessions, pty, providers, audit, secrets, etc.) all exist with source files. **But: Zero references to "ElectroBun" in package.json** -- runtime uses Bun directly, desktop shell is custom TypeScript, not ElectroBun framework. LocalBus V1, state machines, audit log all present. | MEDIUM |
| 4 | helios-cli | "Multi-model coding agent CLI with Bazel + Rust + TypeScript", "OpenAI Codex fork" | Is a fork of OpenAI Codex CLI (`codex-rs/` has 1456 `.rs` files across ~70 sub-crates). Bazel BUILD files present. `codex-cli/` has `package.json` but **zero `.ts` files** -- TS CLI layer does not exist. `helios-rs/` has exactly **1 `.rs` file** (Cargo.toml workspace root placeholder). README duplicates build badge sections. Claims "Supported Models: OpenAI, Claude, Gemini, Cursor, GitHub Copilot" but actual CLI only implements upstream Codex. Go tooling slots claimed in AgilePlus README -- none here. | HIGH |
| 5 | agileplus-agents | 3 Rust crates: dispatch, review, gRPC service with proto definitions | All 3 crates exist. 24 `.rs` source files. Proto definitions (4 `.proto` files: core, agents, integrations, common). 4 test files in review crate. `build.rs` with tonic-build confirmed. `cargo check` passes. Structure matches README almost exactly. Minor: README says "3 primary crates" which is accurate. | LOW |
| 6 | BytePort | "Self-hosted IaC deployment + portfolio platform", claims Go 1.25 backend + SvelteKit 2 + Tauri 2 frontend | Backend: Go source files exist (2731 `.go` files). Frontend: SvelteKit source (5277 `.files`). Tauri referenced in scripts. README has **contradictory claims**: top section says Go/SvelteKit/Tauri (current), but massive outdated manifesto section still describes Rust/Loco.rs/NanoVMS stack. The old narrative occupies ~80% of the README. `./start dev` script exists. No Rust workspace with meaningful code -- `Cargo.toml` only has `src-tauri` member. Go tests: 3 test files in backend. | HIGH |
| 7 | thegent | "100+ Python modules", "28 Rust crates", "10+ language stack templates", "platform bootstrap", "agent orchestration" | Python: 1748 `.py` files in src, 989 modules in `src/thegent/`. Rust: 205 `.rs` files in crates, **32 Cargo.toml files** (not 28 -- 4 more than claimed). 20+ test files found. 10 template directories confirmed (bash, cpp, go, java, php, python, ruby, rust, typescript, zig). Apps include `byteport`, `landing`. However: `bun run build` fails (no build script in package.json). The README mentions "shim wrappers: clode/dex/roid/droid" -- actual shim implementation files exist under `crates/thegent-shims/`. Architecture diagram shows 12 Rust crates, 12 assets; actual is 32 crates. Minor version drift. | MEDIUM |
| 8 | HexaKit | "Rust workspace with 16+ specialized infrastructure libraries", "phenotype-infrakit" | `Cargo.toml` has `members = []` -- **zero crates are workspace members**. However, 33 crate directories exist on disk. Of those, ~30 have actual `.rs` source (648 `.rs` files total). Top crates by file count: `phenotype-port-traits` (11), `phenotype-policy-engine` (11), `phenotype-xdd-lib` (10). Also contains **sub-repos**: agileplus, agileplus-agents, agileplus-mcp, BytePort, helios-cli (copies/symlinks of those repos). README architecture diagram shows `repos/` shelf layout: apps/, tooling/, infra/, libs/, platforms/ -- **none of these directories exist** at shelf level. | HIGH |
| 9 | phenoShared | "16 crates" listed, event sourcing, cache, policy engine, adapters | `Cargo.toml` declares exactly **16 crate members** -- count matches README table (which lists 16). 148 `.rs` source files. Test files: 3 test files across different crates. Packages/types has TS source + tests. `cargo check` passes. Source structure aligns README architecture diagram (domain -> application -> ports -> infrastructure). README code examples are extensive and match crate names. Fidelity is high. | LOW |
| 10 | Tokn | "Enterprise-grade token management", "80% test coverage", "SQLite + PostgreSQL", "CLI: report, costs, optimize" | Workspace: 2 crates (`pareto-rs`, `tokenledger`). 35 `.rs` source files. CLI has commands: Monthly, Daily, Coverage, PricingCheck/Apply/Reconcile/Lint/Audit, Ingest, Bench, Orchestrate, Benchmarks -- exceeds README claim of just "report, costs, optimize". **However**: Cargo.toml has **zero database dependencies** (no sqlx, sqlite, postgres). Claims SQLite+PostgreSQL but no DB code exists. Test files: 3 (smoke, integration, additional). Benchmarks: 1 file. Coverage claim (>=80%) unverified and unlikely with only 3 test files / 35 source files. `analytics.rs` at repo root references nonexistent `phenotype_analytics` crate. `sentry_config.rs` at root with no corresponding Cargo dep. `cargo check` passes. | HIGH |

---

## Detailed Findings

### 1. AgilePlus

**README Claims:**
- Rust workspace at `rust/` with hexagonal architecture, event sourcing, gRPC stubs
- 24 crates + 19 libs (inferred from directory names)
- Python MCP server layer
- TypeScript/VitePress landing site
- Event sourcing, hash-chained evidence ledger
- Quick start: `cd rust && cargo build`

**Reality:**
- `rust/` directory exists with `Cargo.toml`, `clippy.toml`, `deny.toml`, `rustfmt.toml`
- `rust/Cargo.toml` has `members = []` -- workspace declares no members
- Caching `agileplus-proto` is referenced in buf gen config but doesn't exist in rust/
- `cargo check` **fails** when run via `rust/Cargo.toml` (broken tonic workspace dep)
- 24 crate directories under `crates/` and 19 under `libs/` exist but contain **no `.rs` files** at all -- only `Cargo.toml`, `README.md`, `CHANGELOG.md` files
- Python layer exists as `python/phenotype_traceability` directory but has **no `.py` files** inside
- `proto/` has 4 proto files (buf configuration)
- `openapi.yaml` has 5 scaffold endpoints
- `apps/landing` is Astro-based with dependencies installed
- `evidence_ledger.jsonl` has 5 lines (not empty)
- Proto files: `agileplus/v1/` (core, agents, integrations, common)

**Verdict:** HIGH drift. The repo is a scaffolding/skeleton. Directories and config files exist for everything, but actual implementation code is missing. README is written as if the code exists.

---

### 2. AgilePlus-wtrees

**README Claims:** N/A (no README)

**Reality:**
- Contains 16 top-level directories named after feature branches
- `agile-main/` subdirectory contains a near-complete AgilePlus clone with its own `Cargo.toml`, `apps/`, `proto/`, etc.
- No `README.md`, no `package.json`, no `Cargo.toml` at root
- Functions as a container/branch management directory, not actual git worktrees

**Verdict:** LOW drift (no claims made). Structural oddity: named "wtrees" but contains branch directories, not git worktrees.

---

### 3. heliosApp

**README Claims:**
- Status: stable, Version 2026.03A.0
- ElectroBun-based desktop shell
- LocalBus V1 with 26 methods, 40 topics
- 4 apps: runtime, desktop, renderer, colab-renderer
- 5 shared packages
- 33 CI workflows
- State machines: Lane(8), Session(6), PTY(6), Renderer(7), Recovery(6)
- Append-only SQLite audit log
- Test commands: `bun run test`, `test:integration`, `test:e2e`, `test:coverage`

**Reality:**
- All 4 apps present with TypeScript source: `apps/runtime/src/` has 18 subdirectories matching README
- Desktop: `apps/desktop/src/` has all claimed modules (tabs/, panels/, settings/, stores/, etc.)
- Packages: all 5 exist (`runtime-core`, `ids`, `errors`, `logger`, `types`)
- 33 `.github/workflows/` files confirmed
- Test files found: 21 desktop unit tests, 10+ script tests
- `bun run build` **succeeds**
- **ElectroBun not found** anywhere in package.json or source -- runtime is pure Bun TypeScript, desktop shell is custom
- Runtime modules match README exactly: protocol, sessions, pty, providers, recovery, audit, secrets, policy, registry, config, diagnostics, integrations, workspace
- Tab surfaces match: terminal, agent, session, chat, project (all as `.ts` files)
- `colab-renderer/` exists with `package.json` and `SolidJS`-referencing code

**Verdict:** MEDIUM drift. Core claims (architecture, modules, apps, tests, build) are accurate. The "ElectroBun" claim is incorrect. README version number (2026.03A.0) may be aspirational.

---

### 4. helios-cli

**README Claims:**
- Multi-model coding agent CLI framework
- Bazel + Rust + TypeScript
- Helios-specific extensions in `helios-rs/`
- Supported models: OpenAI Codex, Claude, Gemini, Cursor, GitHub Copilot
- Quick start: `bazel build //...`, `bazel test //...`
- Security sandboxing with Docker/orbstack/podman

**Reality:**
- This is a fork of **OpenAI Codex CLI** (upstream `openai/codex`)
- `codex-rs/` has 1456 `.rs` files -- this is the upstream Rust Codex codebase
- Bazel BUILD files present at root and in subdirectories
- `codex-cli/` directory has `package.json` but **0 TypeScript files**
- `helios-rs/` has `Cargo.toml` (workspace root) but only **1 `.rs` file** in the entire directory
- `sdk/` has: `python/`, `python-runtime/`, `typescript/` directories (likely upstream SDKs)
- `BUILD.bazel` and `MODULE.bazel` exist
- `bazel build //...` likely would succeed for codex-rs portion
- "Helios-specific extensions" are essentially non-existent
- README has **duplicate badge sections** (build/release/license/phenotype repeated twice)
- Multi-model support claimed but upstream Codex only supports OpenAI
- `helios-rs/cli/BUILD.bazel` exists but the crate has virtually no code
- The `codex-rs/` Cargo.toml shows it has ~70 sub-crates all from upstream

**Verdict:** HIGH drift. README describes a "multi-model framework" but the repo is 99% upstream OpenAI Codex fork with minimal Helios-specific code. The TypeScript CLI layer is absent. The "Helios extensions" are a near-empty shell.

---

### 5. agileplus-agents

**README Claims:**
- 3 crates: dispatch, review, gRPC service
- Dispatch: spawns/coordinates Claude Code/Codex subprocesses
- Review: polls GitHub/Coderabbit
- Service: gRPC server with AgentDispatchService
- `unsafe_code = "forbid"` workspace lint
- Proto: `agents.proto`
- Build: `cargo build --workspace --release`

**Reality:**
- All 3 crates confirmed: `agileplus-agent-dispatch`, `agileplus-agent-review`, `agileplus-agent-service`
- 24 `.rs` total source files across crates
- Proto: 4 `.proto` files (core, agents, integrations, common) -- more than README implies
- Test files: `coderabbit_tests.rs`, `ci_status_tests.rs`, `fallback_tests.rs`, `integration.rs`
- `agileplus-agent-dispatch/src/` has: adapter, claude_code, codex, dispatch, lib, ports, pr_loop, types
- `agileplus-agent-review/src/` has: ci_status, coderabbit, fallback, lib
- `agileplus-agent-service/src/` has: main, service
- `build.rs` uses `tonic-build`
- `unsafe_code = "forbid"` confirmed in Cargo.toml lints
- `cargo check` passes

**Verdict:** LOW drift. README is highly accurate. All claimed crates, features, proto, and tests exist as described. Minor undercount on proto files (4 vs 1 mentioned).

---

### 6. BytePort

**README Claims:**
- Self-hosted IaC deployment + portfolio platform
- Go 1.25 backend (Gin + GORM + SQLite, PASETO auth)
- SvelteKit 2 + Svelte 5 + Tailwind 4 + Tauri 2 frontend
- LLM-generated showcase metadata
- `./start dev` / `./start prod`
- Manifest format: `odin.nvms`
- MicroVM runtime: Spin / nvms

**Reality:**
- Backend: Go source files present (2731 `.go` files in `backend/`)
- Frontend: SvelteKit source (5277 `.svelte` files)
- `./start` script exists with dev/prod modes using tmux
- 3 Go test files in backend
- `frontend/web/package.json` confirms SvelteKit, Storybook, Tauri commands
- `odin.nvms` manifest example exists in backend/nvms/
- `Cargo.toml` only has `src-tauri` member (no meaningful Rust)
- **README content is ~80% outdated Loco.rs/Rust/NanoVMS manifesto** -- describes a completely different architecture (Rust backend, Loco.rs, Diesel ORM, JWT auth, NanoVMS microvm tech)
- Current Go backend sections were added as "correction" but old content still dominates
- `backend/nvms/` likely the MicroVM orchestration
- No actual Rust source in repository proper (only Tauri)

**Verdict:** HIGH drift. The README is in severe contradiction with itself -- the top section describes the Go/SvelteKit reality but the majority of the document describes the old Rust/Loco.rs architecture. `go.mod` says Go 1.22 (not 1.25 as claimed).

---

### 7. thegent

**README Claims:**
- Platform bootstrap tool + AI agent orchestration + dotfiles manager
- Python CLI (989 modules) with Rust extensions (32 crates)
- 28 Rust crates (actual count: 32)
- 10+ language stack templates
- Agent orchestration, multi-provider routing, MCP support
- Workstream sync: GitHub Projects + Linear
- Two thegents: Python CLI (this repo) + Rust dispatch (separate repo)

**Reality:**
- Python: 989 `.py` files in `src/thegent/` -- claim of "100+ modules" is met
- Rust: 32 `Cargo.toml` files in crates (4 more than claimed 28)
- Rust source: 205 `.rs` files
- Templates: 10 language directories confirmed (bash, cpp, go, java, php, python, ruby, rust, typescript, zig)
- Test files: 20+ test files found in `tests/` and `tools/`
- Crates include: thegent-parser, thegent-discovery, thegent-git, thegent-cache, thegent-crypto, thegent-fs, thegent-hooks, thegent-tui, thegent-metrics, thegent-memory, etc.
- `conftest.py`, `src/scripts/` with build/generator scripts present
- `cli/commands/` with Python CLI command definitions
- `bun run build` fails (no "build" script in package.json) but `typecheck`, `lint`, `format`, `test` exist
- Dotfiles: shell, git, claude configs under `dotfiles/`
- `apps/byteport` and `apps/landing` present -- byteport app reference (likely cross-link)
- Architecture diagram in README: some crate names match (thegent-parser, discovery, git, cache, crypto, fs, hooks, tui, metrics, memory), diagram shows 12; actual is 32

**Verdict:** MEDIUM drift. Core claims are directionally correct. Crate count is off by 4. Build script missing. The Python CLI is real and large. The Rust layer is small but functional. Provider routing and MCP claims are supported by source module names.

---

### 8. HexaKit

**README Claims:**
- "Phenotype Infrastructure Kit" -- Rust workspace with 16+ specialized libraries
- Organized into shelf: apps/, tooling/, infra/, libs/, platforms/
- Hexagonal architecture, error handling, caching, health checks, policy, contracts
- Quick start: `find . -maxdepth 1 -mindepth 1 -type d | sort`
- "Shelf" organizational model

**Reality:**
- `Cargo.toml` declares `members = []` -- workspace has zero members
- 33 crate directories exist under `crates/`
- ~30 of 33 crates have actual Rust source (648 `.rs` files total)
- Top crates: phenotype-port-traits, phenotype-policy-engine, phenotype-xdd-lib, phenotype-event-sourcing
- **Sub-repos exist**: copies/symlinks of `agileplus`, `agileplus-agents`, `agileplus-mcp`, `BytePort`, `helios-cli`
- `apps/`, `Authvault/`, `bare-cua/`, `bifrost/`, `Cursora/`, `Datamold/`, `Dino/`, `Docuverse/`, `Duple/`, etc. 40+ top-level directories
- **No `apps/`, `tooling/`, `infra/`, `libs/`, `platforms/` directory structure exists** -- these are supposed to categorize projects but don't exist
- `docs/`, `crates/`, `config/` confirmed at root level
- Many directories appear to be independent project clones placed at root level without categorization
- `cargo check` passes (vacuously -- no members to check)
- README says "not all projects are yet in these categories -- the reorganization is ongoing"

**Verdict:** HIGH drift. The workspace config is empty despite 33 crate directories with actual code. The organizational structure described in the README (categorized shelves) does not exist. The repo functions as a flat container for many unrelated projects rather than an organized infrastructure kit.

---

### 9. phenoShared

**README Claims:**
- 16 Rust crates with hexagonal/clean architecture layers
- Domain: value objects, entities, aggregates
- Application: CQRS, commands, queries, DTOs
- Ports: inbound/outbound contracts
- Infrastructure: event sourcing, cache, policy, state machine, adapters
- Each crate documented in table with link

**Reality:**
- Exactly 16 crate members in Cargo.toml -- matches README table count
- All 16 crate directories exist with `Cargo.toml` files
- 148 `.rs` source files total across all crates
- 3 test files found: `integration_tests.rs` (nanovms-client), `unit.rs` (port-interfaces), `unit/mod.rs` (state-machine)
- README code examples use exact crate names from Cargo.toml
- Architecture diagram in README matches directory structure
- `crates/ffi_utils/` is an unlisted utility (not in README table)
- TS packages exist: `packages/types/` and `packages/ids/` with TypeScript source and tests -- not mentioned in README
- `contracts/errors/` directory exists
- `cargo check` passes
- `docs/` directory exists with VitePress playwright config

**Verdict:** LOW drift. README is highly accurate. All 16 crates documented, architecture matches, code examples align. Minor: `ffi_utils`, `phenotype-nanovms-client` are not in the README table. TS packages not mentioned.

---

### 10. Tokn

**README Claims:**
- Enterprise-grade token management and pricing governance
- 2 crates: tokenledger + ParetoRs
- 80% test coverage (cargo-tarpaulin)
- SQLite + PostgreSQL storage support
- CLI: report, costs, optimize commands
- Zero high/critical security findings
- Workflows: quality-gate, security-guard, policy-gate (3 CI workflows)
- Integrates with thegent and agentapi

**Reality:**
- 2 crates confirmed: `pareto-rs` (6 `.rs` files) and `tokenledger` (11 `.rs` files)
- 35 total `.rs` source files across workspace
- Test files: 3 found (`smoke_test.rs`, `integration_test.rs`, `tests_fr_additional.rs`)
- Benchmarks: 1 file (`benches/perf.rs`)
- CLI commands: Monthly, Daily, Coverage, PricingCheck/Apply/Reconcile/Lint/Audit, Ingest, Bench, Orchestrate, Benchmarks -- more than README claims
- **No database dependencies**: Cargo.toml has no sqlx, sqlite, postgres, or diesel -- README claim of SQLite+PostgreSQL is false
- `analytics.rs` at repo root references `phenotype_analytics` crate that doesn't exist in dependencies
- `sentry_config.rs` at repo root -- not part of any crate
- `.github/workflows/` has: quality-gate.yml, security-guard.yml, policy-gate.yml -- 3 workflows confirmed
- `cargo check` passes (root-level files compile as standalone)
- Coverage claim is unverified; 3 test files for 35 source files suggests coverage well below 80%
- `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` mentioned as required env vars

**Verdict:** HIGH drift. The core CLI structure is real and functional. But the database/storage claims are fabricated (no DB deps or code). The test coverage claim is likely overly optimistic. Root-level `.rs` files reference non-existent external crates. CI workflows exist as claimed.

---

## Summary Statistics

| Severity | Count | Repos |
|----------|-------|-------|
| HIGH | 5 | AgilePlus, helios-cli, BytePort, HexaKit, Tokn |
| MEDIUM | 2 | heliosApp, thegent |
| LOW | 3 | AgilePlus-wtrees, agileplus-agents, phenoShared |

**Key Cross-Cutting Findings:**
1. **Buildability**: 8/10 repos pass their nominal build check. AgilePlus fails (broken workspace). thegent fails (no "build" script in package.json).
2. **Empty scaffolding pattern**: AgilePlus and HexaKit both have directory structures and config files but missing actual Rust source (AgilePlus) or missing workspace member declarations (HexaKit).
3. **Duplicate/phantom dependencies**: Tokn references `phenotype_analytics` crate that doesn't exist. AgilePlus rust workspace can't resolve `tonic` from workspace deps.
4. **README staleness**: BytePort README is ~80% outdated architecture. helios-cli README duplicates sections and claims multi-model support not present in code.
5. **Claim inflation**: Tokn claims 80% coverage and DB support with no evidence. thegent undercounts its own crate count. heliosApp claims ElectroBun framework that isn't present.
6. **Accurate repos**: agileplus-agents and phenoShared have the highest README fidelity. Both are small, focused workspaces that match their documentation closely.
