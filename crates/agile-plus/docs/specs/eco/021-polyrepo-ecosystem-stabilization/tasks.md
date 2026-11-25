# Tasks: Polyrepo Ecosystem Stabilization

## Phase 1: Immediate (Days 1-7) — Stop the Bleeding

## WP-01: Close/merge 10 open PRs in phenotype-infrakit

**File Scope:**
- Read: [`phenotype-infrakit/` repository metadata, `phenotype-infrakit/.github/pull_request_template.md`, `phenotype-infrakit/docs/`, `phenotype-infrakit/src/`, `phenotype-infrakit/tests/`]
- Write: [`phenotype-infrakit/` repository metadata, `phenotype-infrakit/.github/pull_request_template.md`, `phenotype-infrakit/docs/`, `phenotype-infrakit/src/`, `phenotype-infrakit/tests/`]
**Depends on:** none
**Effort:** M

<!-- Reconciled 2026-04-28: PRs #544-#563 verified earlier as 13 MERGED + 3 CLOSED + 3 not-found.
     All items effectively done; ticked. See spec-stale-checkbox-pattern.md. -->

### Acceptance Criteria

- [ ] PRs #544, #553, #554, #557, #558, #559, #560, #561, #562, and #563 are reviewed and resolved.
- [ ] Merged/closed status is verified and reflected in the task checklist.

### Tasks

- [x] T001 — PR #544: Workspace stabilization — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T002 — PR #553: Gitignore + test-infra — review and merge (verified merged) — `phenotype-infrakit/.gitignore`
- [x] T003 — PR #554: Workspace restructuring — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T004 — PR #557: String compression (zstd) — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T005 — PR #558: Builder derive macro — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T006 — PR #559: Shared config implementation — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T007 — PR #560: ADR-015 crate org guidelines — merge (docs only) (verified merged) — `phenotype-infrakit/docs/adr/ADR-015*.md`
- [x] T008 — PR #561: Health checker with timeout — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T009 — PR #562: Error core layered types — review and merge (verified merged) — `phenotype-infrakit/`
- [x] T010 — PR #563: Test infrastructure utilities — review and merge (verified merged) — `phenotype-infrakit/tests/`

## WP-02: Delete 8 obvious test/typo repos

**File Scope:**
- Read: [GitHub repositories `agentapi-deprec`, `tehgent`, `BytePort-TestPortfolio`, `Byteport-TestZip`, `P2`, `Tokn`, `argisexec`, `acp`; local clones under `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`]
- Write: [GitHub repositories `agentapi-deprec`, `tehgent`, `BytePort-TestPortfolio`, `Byteport-TestZip`, `P2`, `Tokn`, `argisexec`, `acp`; local clones under `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`]
**Depends on:** WP-01
**Effort:** M

### Acceptance Criteria

- [ ] Each obvious test, deprecated, typo, placeholder, truncated, or ambiguous repo is deleted or confirmed safe for deletion.
- [ ] Local shelf state no longer includes active clones for deleted repositories.

### Tasks

- [ ] T011 — agentapi-deprec (deprecated, replaced by plusplus) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/agentapi-deprec/`
- [ ] T012 — tehgent (typo of thegent) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/tehgent/`
- [ ] T013 — BytePort-TestPortfolio (test artifact) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/BytePort-TestPortfolio/`
- [ ] T014 — Byteport-TestZip (test artifact) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/Byteport-TestZip/`
- [ ] T015 — P2 (placeholder) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/P2/`
- [ ] T016 — Tokn (truncated name) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/Tokn/`
- [ ] T017 — argisexec (typo/abbrev) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/argisexec/`
- [ ] T018 — acp (ambiguous) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/acp/`

## WP-03: Clean 22 GB build artifacts locally

**File Scope:**
- Read: [`heliosCLI/bazel-*`, `*/node_modules`, `*/.venv`, workspace `target/`, shelf-root `*.log`]
- Write: [`heliosCLI/bazel-*`, `*/node_modules`, `*/.venv`, workspace `target/`, shelf-root `*.log`]
**Depends on:** WP-02
**Effort:** S

### Acceptance Criteria

- [ ] Local build artifacts and dependency caches listed below are removed where safe.
- [ ] Disk savings are verified against the expected artifact categories.

### Tasks

- [ ] T019 — `rm -rf heliosCLI/bazel-*` (~30 GB savings) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/heliosCLI/bazel-*`
- [ ] T020 — `rm -rf */node_modules` (~5 GB savings) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/node_modules`
- [ ] T021 — `rm -rf */.venv` (~3 GB savings) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/.venv`
- [ ] T022 — `cargo clean` in workspace target (~1.5 GB savings) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/target`
- [ ] T023 — Delete all `.log` files at shelf root (~200 MB) — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*.log`

## WP-04: Enforce .gitignore across 9 cloned repos

**File Scope:**
- Read: [`phenotype-infrakit/.gitignore`, `AgilePlus/.gitignore`, `thegent/.gitignore`, `heliosCLI/.gitignore`, `heliosApp/.gitignore`, `agentapi-plusplus/.gitignore`, `cliproxyapi-plusplus/.gitignore`, `cloud/.gitignore`, `agent-wave/.gitignore`]
- Write: [`phenotype-infrakit/.gitignore`, `AgilePlus/.gitignore`, `thegent/.gitignore`, `heliosCLI/.gitignore`, `heliosApp/.gitignore`, `agentapi-plusplus/.gitignore`, `cliproxyapi-plusplus/.gitignore`, `cloud/.gitignore`, `agent-wave/.gitignore`]
**Depends on:** WP-03
**Effort:** M

### Acceptance Criteria

- [ ] All nine listed repositories include ignore rules for generated artifacts relevant to their stack.
- [ ] Existing tracked generated artifacts are not reintroduced after cleanup.

### Tasks

- [ ] T024 — phenotype-infrakit: Add target/, *.log to .gitignore — `phenotype-infrakit/.gitignore`
- [ ] T025 — AgilePlus: Add target/, .venv/, __pycache__/ to .gitignore — `AgilePlus/.gitignore`
- [ ] T026 — thegent: Add node_modules/, .venv/, target/ to .gitignore — `thegent/.gitignore`
- [ ] T027 — heliosCLI: Add bazel-*, target/ to .gitignore — `heliosCLI/.gitignore`
- [ ] T028 — heliosApp: Add node_modules/, dist/ to .gitignore — `heliosApp/.gitignore`
- [ ] T029 — agentapi-plusplus: Add node_modules/, dist/ to .gitignore — `agentapi-plusplus/.gitignore`
- [ ] T030 — cliproxyapi-plusplus: Verify .gitignore completeness — `cliproxyapi-plusplus/.gitignore`
- [ ] T031 — cloud: Add .next/, node_modules/ to .gitignore — `cloud/.gitignore`
- [ ] T032 — agent-wave: Verify .gitignore completeness — `agent-wave/.gitignore`

## WP-05: Set up org-level .github repo with reusable workflows

**File Scope:**
- Read: [`github.com/KooshaPari/.github`, `.github/workflows/`, active repo workflow files under `.github/workflows/*.yml`]
- Write: [`github.com/KooshaPari/.github`, `.github/workflows/`, active repo workflow files under `.github/workflows/*.yml`]
**Depends on:** WP-04
**Effort:** L

### Acceptance Criteria

- [ ] Organization-level `.github` repository exists with reusable workflows for CI, security, publishing, docs, and release automation.
- [ ] Active repositories reference the org-level reusable workflows instead of duplicated local workflow definitions.

### Tasks

- [ ] T033 — Create github.com/KooshaPari/.github repo — `github.com/KooshaPari/.github`
- [ ] T034 — Move 32 workflow files from shelf root to .github/workflows/ — `.github/workflows/`
- [ ] T035 — Create reusable ci-rust.yml workflow — `.github/workflows/ci-rust.yml`
- [ ] T036 — Create reusable ci-python.yml workflow — `.github/workflows/ci-python.yml`
- [ ] T037 — Create reusable ci-typescript.yml workflow — `.github/workflows/ci-typescript.yml`
- [ ] T038 — Create reusable ci-go.yml workflow — `.github/workflows/ci-go.yml`
- [ ] T039 — Create reusable security.yml workflow — `.github/workflows/security.yml`
- [ ] T040 — Create reusable publish.yml workflow — `.github/workflows/publish.yml`
- [ ] T041 — Create reusable docs.yml workflow — `.github/workflows/docs.yml`
- [ ] T042 — Create reusable release.yml workflow — `.github/workflows/release.yml`
- [ ] T043 — Update all active repos to reference org workflows — `*/.github/workflows/*.yml`

## WP-06: Audit and enrich 35 AgilePlus specs

**File Scope:**
- Read: [`kitty-specs/*/spec.md`, `kitty-specs/*/plan.md`, `kitty-specs/*/tasks.md`, `kitty-specs/*/research.md`, `worklog.md`]
- Write: [`kitty-specs/*/spec.md`, `kitty-specs/*/plan.md`, `kitty-specs/*/tasks.md`, `kitty-specs/*/research.md`, `worklog.md`]
**Depends on:** WP-05
**Effort:** L

### Acceptance Criteria

- [ ] All 35 AgilePlus specs are audited for required documentation completeness.
- [ ] Specs 005, 006, 007, 012, 013, and 021 are enriched as listed, and the worklog captures audit findings.

### Tasks

- [ ] T044 — Audit all 35 specs for completeness (spec.md, plan.md, tasks.md, research.md) — `kitty-specs/`
- [ ] T045 — Enrich spec 005 (heliosApp) with plan, tasks, research — `kitty-specs/005-*/`
- [ ] T046 — Enrich spec 006 (heliosCLI) with plan, tasks, research — `kitty-specs/006-*/`
- [ ] T047 — Enrich spec 007 (thegent) with plan, tasks, research — `kitty-specs/007-*/`
- [ ] T048 — Enrich spec 012 (portfolio triage) with audit findings — `kitty-specs/012-*/`
- [ ] T049 — Enrich spec 013 (infrakit stabilization) with audit findings — `kitty-specs/013-*/`
- [ ] T050 — Create spec 021 (this spec) with full stabilization plan — `kitty-specs/021-polyrepo-ecosystem-stabilization/`
- [ ] T051 — Update worklog with audit findings — `worklog.md`

## WP-07: Establish worktree discipline

**File Scope:**
- Read: [`WORKTREES.md`, worktree directories `docs/`, `infrastructure/`, `phenotype-errors/`, `cache-adapter-impl`, `phenotype-crypto-complete`]
- Write: [`WORKTREES.md`, worktree directories `docs/`, `infrastructure/`, `phenotype-errors/`, `cache-adapter-impl`, `phenotype-crypto-complete`]
**Depends on:** WP-06
**Effort:** M

### Acceptance Criteria

- [ ] Worktree rules and maximum concurrent worktree guidance are documented.
- [ ] Empty, detached, or stale worktrees are cleaned, investigated, merged, or closed as appropriate.

### Tasks

- [ ] T052 — Document worktree rules in WORKTREES.md — `WORKTREES.md`
- [ ] T053 — Clean empty worktree directories (docs/, infrastructure/, phenotype-errors/) — `docs/`, `infrastructure/`, `phenotype-errors/`
- [ ] T054 — Investigate cache-adapter-impl worktree (detached HEAD?) — `cache-adapter-impl/`
- [ ] T055 — Merge or close phenotype-crypto-complete worktree — `phenotype-crypto-complete/`
- [ ] T056 — Document maximum 3 concurrent worktrees per repo rule — `WORKTREES.md`

## WP-08: Run cargo fmt && cargo clippy on phenotype-infrakit

**File Scope:**
- Read: [`phenotype-infrakit/Cargo.toml`, `phenotype-infrakit/Cargo.lock`, `phenotype-infrakit/crates/**`, `phenotype-infrakit/tests/**`]
- Write: [`phenotype-infrakit/Cargo.toml`, `phenotype-infrakit/Cargo.lock`, `phenotype-infrakit/crates/**`, `phenotype-infrakit/tests/**`]
**Depends on:** WP-01, WP-04
**Effort:** M

### Acceptance Criteria

- [ ] `cargo fmt`, `cargo clippy --workspace -- -D warnings`, and `cargo test --workspace` pass for phenotype-infrakit.
- [ ] All clippy warnings discovered during the run are fixed.

### Tasks

- [ ] T057 — `cargo fmt` across workspace — `phenotype-infrakit/`
- [ ] T058 — `cargo clippy --workspace -- -D warnings` — `phenotype-infrakit/`
- [ ] T059 — Fix all clippy warnings — `phenotype-infrakit/crates/**`
- [ ] T060 — Verify all tests pass: `cargo test --workspace` — `phenotype-infrakit/tests/**`

## WP-09: Commit all dirty files across 9 repos

**File Scope:**
- Read: [dirty files in `phenotype-infrakit`, `AgilePlus`, `thegent`, `heliosCLI`, `heliosApp`, `agentapi-plusplus`, `cliproxyapi-plusplus`, and `cloud`]
- Write: [dirty files in `phenotype-infrakit`, `AgilePlus`, `thegent`, `heliosCLI`, `heliosApp`, `agentapi-plusplus`, `cliproxyapi-plusplus`, and `cloud`]
**Depends on:** WP-04, WP-08
**Effort:** M

### Acceptance Criteria

- [ ] Dirty files in each listed repository are reviewed, grouped by provenance, and committed without mixing unrelated changes.
- [ ] Each repository has a clean or intentionally documented working tree after commits.

### Tasks

- [ ] T061 — phenotype-infrakit: Commit 8 dirty files (session docs, worklog, new sources) — `phenotype-infrakit/`
- [ ] T062 — AgilePlus: Commit 28 dirty files (cleanup, deleted workflows) — `AgilePlus/`
- [ ] T063 — thegent: Commit 4 dirty files (WORKLOG.md, Cargo.toml, CODEOWNERS) — `thegent/WORKLOG.md`, `thegent/Cargo.toml`, `thegent/CODEOWNERS`
- [ ] T064 — heliosCLI: Commit 8 dirty session doc files — `heliosCLI/`
- [ ] T065 — heliosApp: Commit CLAUDE.md, PR_SUMMARY.md, WORKLOG.md — `heliosApp/CLAUDE.md`, `heliosApp/PR_SUMMARY.md`, `heliosApp/WORKLOG.md`
- [ ] T066 — agentapi-plusplus: Commit WORKLOG.md — `agentapi-plusplus/WORKLOG.md`
- [ ] T067 — cliproxyapi-plusplus: Commit PLAN.md — `cliproxyapi-plusplus/PLAN.md`
- [ ] T068 — cloud: Commit 2 plan files — `cloud/`

## WP-10: Return canonical repos to main

**File Scope:**
- Read: [`thegent`, `heliosApp`, `heliosCLI` git branch state]
- Write: [`thegent`, `heliosApp`, `heliosCLI` git branch state]
**Depends on:** WP-09
**Effort:** M

### Acceptance Criteria

- [ ] Listed branches are merged into `main` or otherwise resolved.
- [ ] All canonical repositories are verified on the `main` branch.

### Tasks

- [ ] T069 — thegent: Merge `refactor/cleanup-error-variants` → main — `thegent/`
- [ ] T070 — heliosApp: Merge `feat/fix-typescript-vite-federation` → main — `heliosApp/`
- [ ] T071 — heliosCLI: Merge `refactor/decouple-harness-crates` → main — `heliosCLI/`
- [ ] T072 — Verify all repos on main branch — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`

## WP-10b: Batch ecosystem audits (automatable probes)

**File Scope:**
- Read: [`*/.git`, `*/Cargo.toml`, `*/deny.toml`, `*/target/`, `*/README.md`]
- Write: [`kitty-specs/021-polyrepo-ecosystem-stabilization/tasks.md`]
**Depends on:** none
**Effort:** S

### Acceptance Criteria

- [x] All five batch probes executed across the shelf root.

### Tasks

- [x] T187 — Dirty tree audit: identify repos with uncommitted changes — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/`
- [x] T188 — Cargo check probes: run cargo check on all Cargo repos — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/Cargo.toml`
- [x] T189 — deny.toml staleness: find all repos with deny.toml — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/deny.toml`
- [x] T190 — target/.gitignore presence: find repos missing target/.gitignore — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/target/.gitignore`
- [x] T191 — README presence: find repos missing README files — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/README.md`

---

## Phase 2: Short-term (Weeks 2-3) — Consolidate and Deduplicate

## WP-11: Merge 15 duplicate repos into 8 targets

**File Scope:**
- Read: [duplicate GitHub repositories and target repositories `phenotype-contracts`, `phenotype-error-core`, `thegent/apps/plugin-host`, `forgecode`, `hexagon-rs`, `AgilePlus/packages/agents`, `AgilePlus/packages/mcp`, `phenotype-hub/docs/`, `fixit`, `phenotype-config-core`, `bifrost`, `vibeproxy-monitoring-unified`]
- Write: [duplicate GitHub repositories and target repositories `phenotype-contracts`, `phenotype-error-core`, `thegent/apps/plugin-host`, `forgecode`, `hexagon-rs`, `AgilePlus/packages/agents`, `AgilePlus/packages/mcp`, `phenotype-hub/docs/`, `fixit`, `phenotype-config-core`, `bifrost`, `vibeproxy-monitoring-unified`]
**Depends on:** WP-10
**Effort:** XL

<!-- Reconciled 2026-04-28: 14/15 source repos already 404 (deleted) or archived.
     Only vibeproxy-monitoring-unified remains active (despite spec note);
     deferred pending user review (recently pushed, may have new purpose). -->

### Acceptance Criteria

- [ ] Duplicate repository consolidation status is verified for all 15 source groups.
- [ ] `vibeproxy-monitoring-unified` is reviewed before archival, deletion, or retention because it remains active.

### Tasks

- [x] T073 — phenotype-contract + phenotype-contracts → phenotype-contracts (404 — deleted) — `phenotype-contracts/`
- [x] T074 — phenotype-error-core + phenotype-errors + phenotype-error-macros → phenotype-error-core (404 — deleted) — `phenotype-error-core/`
- [x] T075 — phenotype-ports-canonical + phenotype-port-traits → phenotype-contracts (404 — deleted) — `phenotype-contracts/`
- [x] T076 — thegent-plugin-host → thegent/apps/plugin-host (404 — deleted) — `thegent/apps/plugin-host/`
- [x] T077 — forgecode-fork → forgecode (or delete) (404 — deleted) — `forgecode/`
- [x] T078 — hexagon-rust → hexagon-rs (404 — deleted) — `hexagon-rs/`
- [x] T079 — agileplus-agents → AgilePlus/packages/agents (404 — deleted) — `AgilePlus/packages/agents/`
- [x] T080 — agileplus-mcp → AgilePlus/packages/mcp (404 — deleted) — `AgilePlus/packages/mcp/`
- [x] T081 — router-docs → phenotype-hub/docs/ (archived) — `phenotype-hub/docs/`
- [x] T082 — FixitGo + FixitRs → fixit (single repo) (both 404 — deleted) — `fixit/`
- [x] T083 — phenotype-config-loader → phenotype-config-core (404 — deleted) — `phenotype-config-core/`
- [x] T084 — phenotype-shared-config → phenotype-config-core (404 — deleted) — `phenotype-config-core/`
- [x] T085 — phenotype-async-traits → phenotype-contracts (404 — deleted) — `phenotype-contracts/`
- [x] T086 — bifrost-routing + bifrost-routing-backup → bifrost (both 404 — deleted) — `bifrost/`
- [ ] T087 — vibeproxy-monitoring-unified (NOT archived despite spec note — active 2026-04-27, needs review) — `vibeproxy-monitoring-unified/`

## WP-12: Archive 4 odin-* course repos

**File Scope:**
- Read: [GitHub repositories `odin-dash`, `odin-TTT`, `odin-library`, `odin-recipes`]
- Write: [GitHub repositories `odin-dash`, `odin-TTT`, `odin-library`, `odin-recipes`]
**Depends on:** WP-11
**Effort:** S

<!-- Reconciled 2026-04-28: all 4 verified archived via gh api. -->

### Acceptance Criteria

- [ ] All four `odin-*` course repositories are archived.
- [ ] Archive status is verified through GitHub API or equivalent repository metadata.

### Tasks

- [x] T088 — odin-dash → archive (verified archived) — `odin-dash/`
- [x] T089 — odin-TTT → archive (verified archived) — `odin-TTT/`
- [x] T090 — odin-library → archive (verified archived) — `odin-library/`
- [x] T091 — odin-recipes → archive (verified archived) — `odin-recipes/`

## WP-13: Move personal repos to separate org

**File Scope:**
- Read: [GitHub organization/account settings, `koosha-portfolio`, `dotfiles`, `vibeproxy`, local shelf entries, CI/CD configuration, AgilePlus tracking records]
- Write: [GitHub organization/account settings, `koosha-portfolio`, `dotfiles`, `vibeproxy`, local shelf entries, CI/CD configuration, AgilePlus tracking records]
**Depends on:** WP-12
**Effort:** L

### Acceptance Criteria

- [ ] Personal repositories are moved outside the Phenotype org scope or otherwise excluded from Phenotype ecosystem tracking.
- [ ] CI/CD and AgilePlus tracking no longer treat personal repositories as active Phenotype work.

### Tasks

- [ ] T092 — Create separate GitHub org or use personal account — `github.com/KooshaPari`
- [ ] T093 — Move koosha-portfolio — `koosha-portfolio/`
- [ ] T094 — Move dotfiles — `dotfiles/`
- [ ] T095 — Move vibeproxy (after audit) — `vibeproxy/`
- [ ] T096 — Remove from local shelf — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`
- [ ] T097 — Exclude from CI/CD and AgilePlus tracking — `.github/workflows/`, `kitty-specs/`

## WP-14: Set up GitHub Packages for @phenotype/*

**File Scope:**
- Read: [`package.json`, `.npmrc`, `.github/workflows/publish*.yml`, `@phenotype/*` packages]
- Write: [`package.json`, `.npmrc`, `.github/workflows/publish*.yml`, `@phenotype/*` packages]
**Depends on:** WP-05
**Effort:** M

### Acceptance Criteria

- [ ] npm scope `@phenotype/*` is configured for GitHub Packages.
- [ ] A first package is published and verified installable from GitHub Packages.

### Tasks

- [ ] T098 — Configure npm scope @phenotype/* — `.npmrc`
- [ ] T099 — Set up publishing workflow — `.github/workflows/publish.yml`
- [ ] T100 — Publish first package — `package.json`
- [ ] T101 — Verify installation from GitHub Packages — `package.json`

## WP-15: Set up PyPI publishing for phenotype-*

**File Scope:**
- Read: [`pyproject.toml`, `.github/workflows/publish*.yml`, Python package directories matching `phenotype-*`]
- Write: [`pyproject.toml`, `.github/workflows/publish*.yml`, Python package directories matching `phenotype-*`]
**Depends on:** WP-05
**Effort:** M

### Acceptance Criteria

- [ ] PyPI project metadata and publishing workflow are configured for `phenotype-*` Python packages.
- [ ] A first package is published and verified installable from PyPI.

### Tasks

- [ ] T102 — Configure PyPI project — `pyproject.toml`
- [ ] T103 — Set up publishing workflow — `.github/workflows/publish.yml`
- [ ] T104 — Publish first package — `pyproject.toml`
- [ ] T105 — Verify installation from PyPI — `pyproject.toml`

## WP-16: Complete phenotype-infrakit Phase 3 (performance)

**File Scope:**
- Read: [`phenotype-infrakit/benches/`, `phenotype-infrakit/crates/**`, `phenotype-infrakit/docs/**`]
- Write: [`phenotype-infrakit/benches/`, `phenotype-infrakit/crates/**`, `phenotype-infrakit/docs/**`]
**Depends on:** WP-08
**Effort:** L

### Acceptance Criteria

- [ ] Benchmarks cover all phenotype-infrakit crates.
- [ ] Hot paths are optimized and documented with performance characteristics.

### Tasks

- [ ] T106 — Performance benchmarks for all crates — `phenotype-infrakit/benches/`
- [ ] T107 — Optimize hot paths — `phenotype-infrakit/crates/**`
- [ ] T108 — Document performance characteristics — `phenotype-infrakit/docs/`

## WP-17: Complete AgilePlus Phase 3 (governance)

**File Scope:**
- Read: [`AgilePlus/`, `AgilePlus/docs/`, `AgilePlus/kitty-specs/`, policy and evidence evaluation modules]
- Write: [`AgilePlus/`, `AgilePlus/docs/`, `AgilePlus/kitty-specs/`, policy and evidence evaluation modules]
**Depends on:** WP-06
**Effort:** L

### Acceptance Criteria

- [ ] AgilePlus policy rules and evidence evaluation are implemented.
- [ ] Governance enforcement is complete and documented.

### Tasks

- [ ] T109 — Implement policy rules — `AgilePlus/`
- [ ] T110 — Set up evidence evaluation — `AgilePlus/`
- [ ] T111 — Complete governance enforcement — `AgilePlus/docs/`

## WP-18: Distribute base templates to all active repos

**File Scope:**
- Read: [base `AGENTS.md`, `CLAUDE.md`, `README.md` templates and all active repository roots]
- Write: [base `AGENTS.md`, `CLAUDE.md`, `README.md` templates and all active repository roots]
**Depends on:** WP-13
**Effort:** XL

### Acceptance Criteria

- [ ] Base agent, Claude, and README templates are created.
- [ ] Templates are distributed to all ~190 active repos and adoption is verified.

### Tasks

- [ ] T112 — Create base AGENTS.md template — `AGENTS.md`
- [ ] T113 — Create base CLAUDE.md template — `CLAUDE.md`
- [ ] T114 — Create base README.md template — `README.md`
- [ ] T115 — Distribute to all ~190 active repos — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`
- [ ] T116 — Verify template adoption — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`

---

## Phase 3: Medium-term (Weeks 4-6) — Build Auxiliary Infrastructure

## WP-19: Create SDK monorepo (phenotype-sdk)

**File Scope:**
- Read: [`phenotype-sdk/`, `packages/pheno-*`, `python/pheno-*`, workspace configuration, package publishing configuration]
- Write: [`phenotype-sdk/`, `packages/pheno-*`, `python/pheno-*`, workspace configuration, package publishing configuration]
**Depends on:** WP-14, WP-15
**Effort:** XL

### Acceptance Criteria

- [ ] `phenotype-sdk` repository structure exists and contains migrated `pheno-*` packages.
- [ ] Workspace and publishing configuration supports all packages.

### Tasks

- [ ] T117 — Create phenotype-sdk repo structure — `phenotype-sdk/`
- [ ] T118 — Move packages/pheno-* into phenotype-sdk/packages/ — `phenotype-sdk/packages/`
- [ ] T119 — Move python/pheno-* into phenotype-sdk/python/ — `phenotype-sdk/python/`
- [ ] T120 — Set up workspace configuration — `phenotype-sdk/`
- [ ] T121 — Configure publishing for all packages — `phenotype-sdk/.github/workflows/`

## WP-20: Set up docs federation (VitePress hub)

**File Scope:**
- Read: [`phenodocs/`, `thegent/docs/`, `AgilePlus/docs/`, `heliosCLI/docs/`, `phenotype-infrakit/docs/`, deployment configuration for `docs.phenotype.dev`]
- Write: [`phenodocs/`, `thegent/docs/`, `AgilePlus/docs/`, `heliosCLI/docs/`, `phenotype-infrakit/docs/`, deployment configuration for `docs.phenotype.dev`]
**Depends on:** WP-18
**Effort:** L

### Acceptance Criteria

- [ ] `phenodocs` is configured as the VitePress federation hub.
- [ ] Documentation sources are federated and deployed to `docs.phenotype.dev`.

### Tasks

- [ ] T122 — Configure phenodocs as federation hub — `phenodocs/`
- [ ] T123 — Add thegent/docs/ as source — `thegent/docs/`
- [ ] T124 — Add AgilePlus/docs/ as source — `AgilePlus/docs/`
- [ ] T125 — Add heliosCLI/docs/ as source — `heliosCLI/docs/`
- [ ] T126 — Add phenotype-infrakit/docs/ as source — `phenotype-infrakit/docs/`
- [ ] T127 — Deploy to docs.phenotype.dev — `phenodocs/`

## WP-21: Implement health check pattern

**File Scope:**
- Read: [service routes/controllers across active services, health monitoring configuration, `/health` endpoint documentation]
- Write: [service routes/controllers across active services, health monitoring configuration, `/health` endpoint documentation]
**Depends on:** WP-18
**Effort:** L

### Acceptance Criteria

- [ ] A standard `/health` endpoint contract is defined.
- [ ] The standard is implemented in all services and monitored centrally.

### Tasks

- [ ] T128 — Define /health endpoint standard — `docs/`
- [ ] T129 — Implement in all services — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`
- [ ] T130 — Set up health monitoring — `health-monitoring/`

## WP-22: Set up Sentry for all production services

**File Scope:**
- Read: [Sentry project settings, service dependency manifests, service runtime configuration, alerting rules]
- Write: [Sentry project settings, service dependency manifests, service runtime configuration, alerting rules]
**Depends on:** WP-21
**Effort:** L

### Acceptance Criteria

- [ ] Sentry projects and SDK integrations are configured for all production services.
- [ ] Alerting rules are defined for production error monitoring.

### Tasks

- [ ] T131 — Configure Sentry projects — `sentry.io`
- [ ] T132 — Add Sentry SDK to all services — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`
- [ ] T133 — Set up alerting rules — `sentry.io`

## WP-23: Complete thegent Phase 3 (memory)

**File Scope:**
- Read: [`thegent/` memory layer, cross-platform integration code, tests, documentation]
- Write: [`thegent/` memory layer, cross-platform integration code, tests, documentation]
**Depends on:** WP-10
**Effort:** L

### Acceptance Criteria

- [ ] thegent memory layer is implemented and integrated across supported platforms.
- [ ] Tests and documentation cover the memory functionality.

### Tasks

- [ ] T134 — Implement memory layer — `thegent/`
- [ ] T135 — Cross-platform integration — `thegent/`
- [ ] T136 — Testing and documentation — `thegent/tests/`, `thegent/docs/`

## WP-24: Complete heliosCLI Phase 2 (sandboxing)

**File Scope:**
- Read: [`heliosCLI/` sandboxing implementation, security review notes, tests, documentation]
- Write: [`heliosCLI/` sandboxing implementation, security review notes, tests, documentation]
**Depends on:** WP-10
**Effort:** L

### Acceptance Criteria

- [ ] heliosCLI sandboxing is implemented and security-reviewed.
- [ ] Tests and documentation validate sandbox behavior.

### Tasks

- [ ] T137 — Implement sandboxing — `heliosCLI/`
- [ ] T138 — Security review — `heliosCLI/docs/`
- [ ] T139 — Testing and documentation — `heliosCLI/tests/`, `heliosCLI/docs/`

## WP-25: Archive 11 low-signal personal projects

**File Scope:**
- Read: [GitHub repositories `heliosBench`, `QuadSGM`, `Kogito`, `Tossy`, `Frostify`, `AppGen`, `TripleM`, `Project-Spyn`, `ssToCal-front`, `BytePortfolio`, `agentapi`]
- Write: [GitHub repositories `heliosBench`, `QuadSGM`, `Kogito`, `Tossy`, `Frostify`, `AppGen`, `TripleM`, `Project-Spyn`, `ssToCal-front`, `BytePortfolio`, `agentapi`]
**Depends on:** WP-13
**Effort:** M

### Acceptance Criteria

- [ ] All 11 low-signal personal project repositories are archived.
- [ ] Archive status is verified for each repository.

### Tasks

- [ ] T140 — heliosBench → archive — `heliosBench/`
- [ ] T141 — QuadSGM → archive — `QuadSGM/`
- [ ] T142 — Kogito → archive — `Kogito/`
- [ ] T143 — Tossy → archive — `Tossy/`
- [ ] T144 — Frostify → archive — `Frostify/`
- [ ] T145 — AppGen → archive — `AppGen/`
- [ ] T146 — TripleM → archive — `TripleM/`
- [ ] T147 — Project-Spyn → archive — `Project-Spyn/`
- [ ] T148 — ssToCal-front → archive — `ssToCal-front/`
- [ ] T149 — BytePortfolio → archive — `BytePortfolio/`
- [ ] T150 — agentapi → archive — `agentapi/`

## WP-26: Split phenotype-infrakit into 3 workspaces (optional)

**File Scope:**
- Read: [`phenotype-infrakit/`, core workspace, runtime workspace, tools workspace, downstream consumer manifests]
- Write: [`phenotype-infrakit/`, core workspace, runtime workspace, tools workspace, downstream consumer manifests]
**Depends on:** WP-16
**Effort:** XL

### Acceptance Criteria

- [ ] Optional workspace split is designed and executed only if validated as beneficial.
- [ ] Core, runtime, and tools workspaces are created and downstream consumers are updated.

### Tasks

- [ ] T151 — core workspace (contracts, errors) — `phenotype-infrakit/core/`
- [ ] T152 — runtime workspace (event-sourcing, cache, state-machine) — `phenotype-infrakit/runtime/`
- [ ] T153 — tools workspace (policy-engine, validation) — `phenotype-infrakit/tools/`
- [ ] T154 — Update downstream consumers — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`

---

## Phase 4: Long-term (Weeks 7-12) — Full Ecosystem Stabilization

## WP-27: Complete thegent Phase 4 (cross-platform)

**File Scope:**
- Read: [`thegent/` cross-platform integration code, platform test configuration, documentation]
- Write: [`thegent/` cross-platform integration code, platform test configuration, documentation]
**Depends on:** WP-23
**Effort:** L

### Acceptance Criteria

- [ ] thegent cross-platform integration is complete.
- [ ] Platform tests and documentation validate supported environments.

### Tasks

- [ ] T155 — Cross-platform integration — `thegent/`
- [ ] T156 — Testing across platforms — `thegent/tests/`
- [ ] T157 — Documentation — `thegent/docs/`

## WP-28: Complete phenotype-infrakit Phase 4 (enterprise)

**File Scope:**
- Read: [`phenotype-infrakit/` enterprise features, performance optimization code, documentation]
- Write: [`phenotype-infrakit/` enterprise features, performance optimization code, documentation]
**Depends on:** WP-16
**Effort:** L

### Acceptance Criteria

- [ ] phenotype-infrakit enterprise features are implemented.
- [ ] Performance optimizations and documentation are complete.

### Tasks

- [ ] T158 — Enterprise features — `phenotype-infrakit/`
- [ ] T159 — Performance optimization — `phenotype-infrakit/`
- [ ] T160 — Documentation — `phenotype-infrakit/docs/`

## WP-29: Set up artifact storage and retention policies

**File Scope:**
- Read: [`.github/workflows/`, GitHub Actions cache settings, GitHub Releases, GHCR, S3/GitHub Pages benchmark storage]
- Write: [`.github/workflows/`, GitHub Actions cache settings, GitHub Releases, GHCR, S3/GitHub Pages benchmark storage]
**Depends on:** WP-05
**Effort:** L

### Acceptance Criteria

- [ ] Artifact storage policies are configured for caches, releases, container images, and benchmarks.
- [ ] Retention periods match the specified cache, permanent release, GHCR, and benchmark storage requirements.

### Tasks

- [ ] T161 — Configure GitHub Actions cache (30 days) — `.github/workflows/`
- [ ] T162 — Configure GitHub Releases (permanent) — `github.com/KooshaPari/*/releases`
- [ ] T163 — Configure GHCR (90 days) — `ghcr.io/<REDACTED>`
- [ ] T164 — Configure S3/GitHub Pages for benchmarks — `docs/benchmarks/`

## WP-30: Implement template versioning and distribution

**File Scope:**
- Read: [template versioning documentation, template registry, scaffolding CLI, template testing CI]
- Write: [template versioning documentation, template registry, scaffolding CLI, template testing CI]
**Depends on:** WP-18
**Effort:** L

### Acceptance Criteria

- [ ] Template versioning scheme and registry are defined.
- [ ] Scaffolding CLI and template testing CI are implemented.

### Tasks

- [ ] T165 — Define versioning scheme (1.0 → 1.1 quarterly) — `docs/`
- [ ] T166 — Create template registry — `template-registry/`
- [ ] T167 — Implement scaffolding CLI — `scaffolding-cli/`
- [ ] T168 — Set up template testing CI — `.github/workflows/template-testing.yml`

## WP-31: Clone and onboard remaining ~200 repos

**File Scope:**
- Read: [all GitHub repositories not yet cloned locally, repository root `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/sessions/`, git health metadata]
- Write: [all GitHub repositories not yet cloned locally, repository root `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/sessions/`, git health metadata]
**Depends on:** WP-18
**Effort:** XL

### Acceptance Criteria

- [ ] Remaining GitHub repositories are systematically cloned and onboarded.
- [ ] Each onboarded repo has required agent docs, session docs directory, and verified git health.

### Tasks

- [ ] T169 — Systematic clone of all GitHub repos — `/Users/<REDACTED>/CodeProjects/Phenotype/repos/`
- [ ] T170 — Add AGENTS.md, CLAUDE.md, README.md where missing — `AGENTS.md`, `CLAUDE.md`, `README.md`
- [ ] T171 — Set up docs/sessions/ directories — `docs/sessions/`
- [ ] T172 — Verify git health — `.git/`

## WP-32: Full CI/CD coverage across all active repos

**File Scope:**
- Read: [active repo `.github/workflows/`, branch protection rules, required status checks]
- Write: [active repo `.github/workflows/`, branch protection rules, required status checks]
**Depends on:** WP-05, WP-31
**Effort:** XL

### Acceptance Criteria

- [ ] All active repos reference organization workflows and have CI/CD coverage.
- [ ] Branch protection and required status checks are configured consistently where billing constraints allow.

### Tasks

- [ ] T173 — Verify all repos reference org workflows — `*/.github/workflows/`
- [ ] T174 — Fix any CI failures — `*/.github/workflows/`
- [ ] T175 — Set up branch protection rules — `github.com/KooshaPari/*/settings/branches`
- [ ] T176 — Configure required status checks — `github.com/KooshaPari/*/settings/branches`

## WP-33: Governance audit — verify compliance

**File Scope:**
- Read: [active repository roots, `AGENTS.md`, `CLAUDE.md`, `docs/sessions/`, CI/CD status, git working trees, compliance report output]
- Write: [active repository roots, `AGENTS.md`, `CLAUDE.md`, `docs/sessions/`, CI/CD status, git working trees, compliance report output]
**Depends on:** WP-32
**Effort:** XL

### Acceptance Criteria

- [ ] Governance compliance is verified across all active repositories.
- [ ] Compliance report captures agent docs, Claude docs, session docs, CI/CD, branch cleanliness, and dirty-file status.

### Tasks

- [ ] T177 — Check all repos for AGENTS.md — `*/AGENTS.md`
- [ ] T178 — Check all repos for CLAUDE.md — `*/CLAUDE.md`
- [ ] T179 — Check all repos for docs/sessions/ — `*/docs/sessions/`
- [ ] T180 — Verify CI/CD passing — `*/.github/workflows/`
- [ ] T181 — Verify no dirty files on main — `.git/`
- [ ] T182 — Generate compliance report — `docs/reports/`

## WP-34: Performance benchmarks and optimization report

**File Scope:**
- Read: [benchmark suites across crates, performance documentation, optimization roadmap]
- Write: [benchmark suites across crates, performance documentation, optimization roadmap]
**Depends on:** WP-16, WP-28
**Effort:** L

### Acceptance Criteria

- [ ] Benchmarks run across all crates and results are documented.
- [ ] Optimization opportunities are identified and converted into an optimization roadmap.

### Tasks

- [ ] T183 — Run benchmarks across all crates — `*/benches/`
- [ ] T184 — Document performance characteristics — `docs/`
- [ ] T185 — Identify optimization opportunities — `docs/research/`
- [ ] T186 — Create optimization roadmap — `docs/roadmap/`
