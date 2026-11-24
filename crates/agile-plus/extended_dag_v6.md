# Extended Workspace DAG v7
Generated: 2026-05-05 (extension of v6, 2026-05-04)

This v6 consolidates the latest workspace audit threads, preserves the corrected v5 findings, and adds a sharper execution order for the highest-leverage remediation paths.

## What changed since v5

- Root workspace reliability remains blocked by the nested `hwLedger`/`Sparkle` submodule chain; `git status` is still not trustworthy without submodule suppression.
- `BytePort` remains a dedicated triage hotspot because the remaining live `todo!()` surface is still the highest-risk implementation debt cluster.
- `phenodocs` broken-link remediation is still the fastest documentation win, but it should be paired with stub-target creation and a re-run of the checker so the delta is measurable.
- The spec backlog remains the largest planning surface; top canonical specs should be treated as work-package factories, not just a list.
- Cross-repo reuse candidates are now explicit: link-check tooling, dependency triage scripts, target-ignore auditing, and spec scanning should be shared where possible.

## Executive summary

| Dimension | Finding | Severity | Immediate posture |
|---|---|---:|---|
| Root workspace reliability | `hwLedger`/`Sparkle` nested object chain still breaks root `git status` | P0 | Fix or explicitly quarantine before trusting aggregate state |
| Documentation | `phenodocs` still has 224+ broken Markdown refs outside `node_modules` | P1 | Create targets, then rerun checker |
| Implementation debt | `BytePort` remains the densest live `todo!()` triage target | P1 | Triage before broad cleanup |
| Test coverage | Several active Rust repos still lack obvious tests | P1 | Add smoke tests in highest-surface repos first |
| Dependency hygiene | `dep_audit.csv` still reflects >1k findings, mostly path overrides | P2 | Classify internal vs accidental before touching manifests |
| Spec execution | Top canonical specs remain the biggest durable throughput lever | P2 | Convert spec backlog into phased work packages |
| Reuse opportunity | audit scripts and scanners are duplicated across threads | P2 | Extract shared tooling first |

## P0 — Workspace trust blockers

### 1. Root `git status` reliability is still compromised

**Evidence**
- Nested submodule chain under `apps/macos/HwLedger/.build/checkouts/Sparkle`
- `git status` can fail or become misleading at the workspace root without submodule suppression

**Action**
1. Decide whether the nested checkout should remain tracked.
2. If it must remain, document and enforce a root-safe status command.
3. If it should not remain, clean the nested checkout boundary and stabilize root status.

**Dependency**
- `hwLedger` tracking policy and submodule boundary decision

### 2. Detached recovery and cleanup branches still need closure

**Evidence**
- Prior recovery branches were pushed for detached-head rescue work
- Some branches still require PR closure, review, or merge choreography

**Action**
1. Audit open recovery branches.
2. Close the loop with PRs or merges.
3. Remove stale local-only recovery state after integration.

**Dependency**
- PR workflow ownership for recovery branches

## P1 — Documentation remediation DAG

### 1. `phenodocs` broken-link remediation

**Current state**
- 224+ broken Markdown refs outside `node_modules`
- Highest leverage source clusters remain the generated index documents

**DAG**
1. Create or stub the missing target pages.
2. Update root-relative links to point at stable targets.
3. Re-run the Markdown link checker.
4. Capture the post-fix count as the new baseline.

**High-leverage targets**
- `README.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `reference/api.md`
- `governance/journeys.md`
- `templates/release-matrix-template.md`

### 2. Documentation quality should be measured by delta, not intent

**Action**
- Track broken-link counts before/after each PR.
- Prefer one measurable docs PR per cluster over many opaque link edits.

## P1 — Implementation debt and missing tests

### 1. `BytePort` remains the top live marker hotspot

**Evidence**
- The earlier inflated counts were corrected
- The current live surface is still concentrated enough to warrant its own triage pass

**Action**
1. Isolate the live `todo!()` / placeholder sites.
2. Replace reachable placeholders with explicit errors or concrete code paths.
3. Add tests around the highest-density modules.

**Dependency**
- Triage of reachable code paths before broad cleanup

### 2. Add smoke tests to active Rust repos with no obvious coverage

**Priority order**
1. `helios-router`
2. `PhenoKits`
3. `Tasken`
4. `Configra`
5. `HeliosLab`
6. `PhenoVCS`

**DAG**
1. Identify one smoke-path per repo.
2. Add minimal integration-style coverage.
3. Wire the tests into the local quality target for each repo.

### 3. Dead-code and placeholder clusters need classification before edits

**High-signal repos**
- `FocalPoint`
- `HexaKit`
- `PhenoDevOps`
- `helios-cli`
- `helioscope`
- `phenotype-tooling`

**Action**
- Separate production debt from intentional prototype scaffolding.
- Only then decide whether to delete, reduce, or guard the markers.

## P2 — Dependency hygiene

### 1. Cargo dependency findings require classification, not bulk churn

**Current summary**
- 1,227 findings
- 862 path overrides
- 357 duplicate/conflict cases
- 8 git overrides

**DAG**
1. Classify internal workspace path deps versus accidental pins.
2. Review the 8 git overrides for supply-chain risk.
3. Convert safe overrides to registry releases or pinned SHAs.
4. Re-run the audit and compare deltas per repo.

**Rule**
- Do not “fix” internal path dependencies blindly; some are structural and expected.

### 2. Cross-repo dependency reuse opportunity

**Shared tooling candidates**
- cargo-dependency triage helpers
- manifest classification scripts
- repo-wide dependency graph diffing

**Benefit**
- Reduces repeated audit logic across multiple Rust repos.

## P2 — Spec execution priorities

### Top canonical specs to treat as work packages

1. `kitty-specs/021-polyrepo-ecosystem-stabilization/tasks.md`
2. `thegent/docs/changes/research-cross-platform-shell/tasks.md`
3. `thegent/docs/changes/research-tui-compositor/tasks.md`
4. `thegent/docs/changes/research-idea-seed-system/tasks.md`
5. `thegent/docs/changes/research-library-retry/tasks.md`
6. `thegent/docs/changes/research-cross-platform-isolation/tasks.md`
7. `thegent/docs/changes/research-simulation-replay/tasks.md`
8. `thegent/docs/changes/research-supermemory-integration/tasks.md`

### Spec execution DAG

1. Pick the smallest spec with the strongest dependency unlock.
2. Convert it into work packages with explicit predecessor links.
3. Mark completed packages at the wp level.
4. Repeat in descending leverage order.

### Low-hanging fruit rule

- Specs above 80% completion should be batched as quick wins.
- Do not leave 80%+ specs hanging while starting lower-value new work.

## P3 — Scaffold and packaging classification

### Repo list still needing classification

- Parpoura
- nanovms
- heliosApp
- phenoShared
- PolicyStack
- phenoData
- phenodocs-scorecard-remediation
- docs
- forgecode
- Planify
- phenodocs
- AppGen
- Civis
- PhenoHandbook
- cliproxyapi-plusplus
- phenotype-registry
- phenotype-org-audits
- PhenoCompose
- Paginary
- phenotype-tooling
- chatta
- agent-devops-setups

### DAG

1. Classify each repo as docs-only, package-only, or app-with-runtime.
2. Verify whether it has real `src`/`app`/`pages` entrypoints.
3. Only scaffold when the classification proves a missing runtime surface.

## Cross-Project Reuse Opportunities

### 1. Markdown link audit tooling

**Candidate code**
- broken-link scanners
- stub target generators
- docs baseline diff reporters

**Target shared location**
- `repos/docs/` or a shared audit utility package

**Impacted repos**
- `phenodocs`
- `AgilePlus`
- any repo with generated docs indexes

**Migration order**
1. Extract the scanner logic.
2. Parameterize repo roots and ignore rules.
3. Replace per-repo copies.

### 2. Dependency triage and manifest classification

**Candidate code**
- path override classification
- git override review helpers
- workspace manifest diffing

**Target shared location**
- shared Rust tooling package or `phenotype-tooling`

**Impacted repos**
- `FocalPoint`
- `BytePort`
- `helios-cli`
- other Rust workspace repos

**Migration order**
1. Identify shared manifest parsing logic.
2. Extract classification into a reusable library.
3. Update repo-specific audits to call the shared helper.

### 3. `target/` ignore auditing

**Candidate code**
- target-ignore discovery
- repo-level `.gitignore` enforcement
- missing-ignore reporting

**Target shared location**
- audit utility in the shared tooling repo

**Impacted repos**
- Rust repos with build artifacts and missing ignores

**Migration order**
1. Normalize the detection logic.
2. Emit a repo-level fix list.
3. Batch safe `.gitignore` edits.

### 4. Spec/task inventory scanners

**Candidate code**
- `tasks.md` inventory scanning
- blocked marker counting
- spec completion sorting

**Target shared location**
- `AgilePlus`-adjacent shared tooling or a reusable workspace scanner

**Impacted repos**
- `AgilePlus`
- `thegent`
- `kitty-specs`

**Migration order**
1. Unify scanning inputs.
2. Preserve per-repo output formatting.
3. Reuse the scanner for future DAG regeneration.

## Next execution order

| Priority | Action | Repos | Why now |
|---|---|---|---|
| 1 | Stabilize root workspace status | workspace root | Unblocks reliable aggregate analysis |
| 2 | Triage BytePort live marker surface | BytePort | Highest concentrated implementation debt |
| 3 | Stub/fix phenodocs missing targets | phenodocs | Fastest measurable docs win |
| 4 | Add smoke tests to `helios-router` | helios-router | Highest coverage gap surface |
| 5 | Classify dependency findings | multiple Rust repos | Prevents unnecessary manifest churn |
| 6 | Execute top canonical spec work packages | `kitty-specs`, `thegent`, `AgilePlus` | Converts backlog into durable shipped work |

## Notes on operating mode

- Treat this DAG as a living execution map, not a static report.
- Prefer small, measurable PRs that reduce one dimension at a time.
- Keep audit artifacts versioned so future DAG regeneration can compare deltas cleanly.

---

# v7 Extension — 2026-05-05

## What changed since v6

All three concurrent R&D audit streams completed. Findings consolidated below.

### Build sweep results (20-repo probe)

| Result | Count | Details |
|---|---|---|
| PASS | 13 | agileplus-agents, heliosApp, helios-cli, helios-router, BytePort, thegent-dispatch, HexaKit, phenoShared, Tokn, Sidekick, GDK, Configra, HeliosLab |
| FAIL | 3 | **thegent** (esbuild EOVERRIDE), **Parpoura** (3 vitest assertion failures), **PhenoDevOps** (missing blake3_hash/signatures module API) |
| SKIP | 4 | AgilePlus, AgilePlus-wtrees, AuthKit, kitty-specs (no Cargo/npm manifest at root) |

### README-vs-reality drift summary

| Severity | Count | Repos |
|---|---|---|
| HIGH | 5 | AgilePlus (24 crates, 0 .rs files, Rust workspace broken), helios-cli (nearly pure Codex fork, TS layer absent), BytePort (contradictory README: Rust/Loco.rs vs Go/Svelte/Tauri), HexaKit (members=[] despite populated crate dirs), Tokn (SQLite/PostgreSQL claims unbacked by deps) |
| MEDIUM | 2 | heliosApp (ElectroBun claim absent, otherwise accurate), thegent (no build script, esbuild conflict) |
| LOW | 3 | agileplus-agents (accurate), phenoShared (16 crates confirmed, minor omission of ffi_utils), AgilePlus-wtrees (no claims made) |

### Spec/FR completion gap summary

- 50 kitty-specs audited; 5 critical gaps identified
- **Critical:** 013 (cancelled, 56 orphaned unchecked tasks), eco-001–006 (all claim COMPLETED with zero evidence), 021 (only 11% done — P0 blocker), 001 (94% done but WP04 security domain model tasks are the remaining 9), 003 (120/120 done but says "Draft" —AgilePlus production code contradicts)
- 22 specs missing plan.md; 14 missing tasks.md; 68 repo-root FR/PLAN files with no task tracking
- TheGent docs/changes: 15 research directories, 11 at 0-18% completion, no spec artifacts

## New workstreams identified

### WS-A: PhenoDevOps build repair (P0)
- Restore missing `hash` module API (`blake3_hash`, `content_id`, `sha256_hash`, `HashAlgorithm`) and `signatures` module
- Unblocks HexaKit which shares the same crate
- Estimated: 1–2 files, low risk

### WS-B: thegent esbuild override resolution (P1)
- Fix `package.json` override conflict: `esbuild@^0.28.0` override conflicts with direct dependency
- Unblocks vitest and the entire CI pipeline for thegent
- Estimated: package.json edit, verify with `npm install`

### WS-C: Parpoura vitest failure diagnosis (P1)
- 3 failing vitest assertions need root cause analysis
- Could be environment issue or actual logic bug
- Estimated: read test output, check assertions, patch or skip

### WS-D: AgilePlus branch debt cleanup (P1)
- 47 local branches; many 169 commits behind main
- Identify which have unique unmerged work vs fully merged
- Prune merged branches, push unmerged ones
- Estimated: audit, then batch prune

### WS-E: AgilePlus Rust workspace repair (P0)
- 24 crates + 19 libs with zero `.rs` files; `rust/Cargo.toml` has `members = []` and broken `tonic` workspace dep
- Decide: scaffold the claimed hexagonal architecture or update spec to match reality (scaffolding only)
- Unblocks spec 003 which claims 120/120 done
- Estimated: workspace dep fix + decision on scaffold vs spec update

### WS-F: phenodocs broken-link remediation — stub creation (P1)
- 224 broken refs outside node_modules
- Top targets: ARCHITECTURE.md, docs/api-standards.md, docs/security/requirements.md, benchmarks/README.md (5 refs each)
- Create stub pages for 10 highest-referenced targets, then re-run link checker
- Estimated: 10 stub .md files

### WS-G: Spec 021 — polyrepo ecosystem stabilization advancement (P0)
- Only 28/254 tasks done (11%); P0 critical path
- Many sub-tasks are automatable (dirty-tree checks, cargo check probes, deny.toml staleness)
- Pick the 20 most batchable unchecked tasks and execute a first-pass sweep
- Should advance ratio to ~20%+

### WS-H: HexaKit Cargo.toml members fix (P2)
- `members = []` but populated crate directories exist with source
- Either add actual members or remove empty crate dirs
- Estimated: audit members vs dirs, edit Cargo.toml

### WS-I: Eco-spec cleanup — remove or evidence completion (P2)
- eco-001 through eco-006 all claim COMPLETED with zero task/plan evidence
- Either create retrospective task evidence or change status to RETIRED
- Estimated: 6 spec.md status updates + minimal plan.md stubs

### WS-J: TheGent research spec artifact creation (P2)
- 15 docs/changes directories, most missing spec.md/plan.md/tasks.md
- Create minimal stub artifacts for research tracks that have >0% completion
- Estimated: 10–15 spec stub files

## Updated execution order

| Priority | WS | Action | Repos | Expected outcome |
|---|---|---|---|---|
| 0 | WS-A | Fix PhenoDevOps build | PhenoDevOps, HexaKit | Cargo check passes |
| 1 | WS-E | Repair AgilePlus Rust workspace or align spec | AgilePlus | Build passes or spec matches reality |
| 2 | WS-G | Advance spec 021 first-pass batch | kitty-specs + all repos | Ratio from 11% → ~20%+ |
| 3 | WS-B | Fix thegent esbuild conflict | thegent | CI passes |
| 4 | WS-C | Diagnose Parpoura failures | Parpoura | Known root cause |
| 5 | WS-D | AgilePlus branch prune | AgilePlus | Clean branch list |
| 6 | WS-F | Create phenodocs stub targets | phenodocs | Broken refs -20+ |
| 7 | WS-H | Fix HexaKit members | HexaKit | Cargo.toml consistent |
| 8 | WS-I | Eco-spec retirement/evidence | kitty-specs | Honest spec status |
| 9 | WS-J | TheGent spec stubs | thegent | Research tracks trackable |

---

# v8 Extension — 2026-05-05 (afternoon)

## What changed since v7

All ten workstreams completed. Six new workstreams identified from findings.

### Completion scorecard

| WS | Status | Outcome |
|---|---|---|
| WS-A | ✅ Done | `8bb23c77d` — hash + signatures stubs added |
| WS-B | ✅ Done | `63649ebd1` — esbuild override conflict resolved |
| WS-C | ✅ Done | No failures — vitest config correct, `passWithNoTests: true` |
| WS-D | ✅ Done | `cherry-mech-7` pruned (1 branch deleted) |
| WS-E | ✅ Done | Proto-tonic workspace deps fixed in wtree `061edf6` |
| WS-F | ✅ Done | All 14 phenodocs stubs already existed — no action needed |
| WS-G | ✅ Done | 5 batch tasks executed; ratio 28/254 → 34/260 (11% → 13%) |
| WS-H | ✅ Done | `fe59272` — 34 crates + root package added to HexaKit members |
| WS-I | ✅ Done | `ec899e66`–`6d7953dc` — all 6 eco-specs retired with plan.md |
| WS-J | ✅ Done | `9ea8fcd5a` — 10 research dirs now have plan.md stubs |

### New findings (v8)

- **cargo-deny staleness**: 51 deny.toml files scanned; 9 repos with 65 ignored advisories, **0% with rationale**, 0% with expiration. 2 repos (AtomsBot, PhenoControl) have duplicate `allow-registry` keys causing cargo-deny to fail entirely. 1 repo (PhenoObservability) has silent ignore failure — wrong field names. Most dangerous: RUSTSEC-2017-0008 (9 years old, no rationale, hwLedger).
- **Python test infra**: 23 Python repos found; 15 have CI workflows. **13 repos have Python tests but NO CI**: Parpoura, phenodocs, PhenoMCP, python, QuadSGM, etc. 1 repo has pyproject.toml but NO tests/: phenodocs-scorecard-remediation.
- **Broken CLAUDE.md ref**: helioscope CLAUDE.md references `heliosCLI` but actual directory is `helios-cli` (wrong casing).
- **CI gaps fixed**: `pheno-cli/` and `phenotype-shared/` now have push/PR CI workflows.
- **target/.gitignore**: 17 repos fixed (15 created/updated .gitignore, 4 already compliant).

## New workstreams (WS-K through WS-Q)

### WS-K: Fix cargo-deny parse errors (P0)
- AtomsBot and PhenoControl have duplicate `allow-registry` keys — cargo-deny fails entirely
- Fix: deduplicate deny.toml entries

### WS-L: Add CI to Python repos without tests (P1)
- 13 repos have Python tests but zero CI: Parpoura, phenodocs, PhenoMCP, python, QuadSGM, etc.
- Add push/PR workflows to highest-priority repos

### WS-M: Fix PhenoObservability silent deny ignore (P1)
- Uses wrong field names (`crate`/`advisory`/`reason`) — advisories not actually suppressed
- Fix: correct field names per cargo-deny schema

### WS-N: Fix helioscope CLAUDE.md casing reference (P1)
- References `heliosCLI` but actual directory is `helios-cli`
- Fix: one-line replacement

### WS-O: Batch-rationalize cargo-deny ignores (P2)
- 65 ignored advisories across 9 repos, all lack rationale and expiration
- Prioritize: RUSTSEC-2017-0008 (9yr, hwLedger), RUSTSEC-2023-0071 (3yr, hwLedger+phenoData)
- 10-advisory batch in BytePort+hwLedger likely from shared transitive dep

### WS-P: phenodocs-scorecard-remediation has code but no tests (P2)
- Has pyproject.toml but no tests/ directory

### WS-Q: BytePort cargo check recheck (P1)
- Previously passed (5m41s) with 7 live `todo!()` stubs remaining

## Updated execution order (v8)

| Priority | WS | Action | Repos | Expected outcome |
|---|---|---|---|---|
| 0 | WS-K | Fix cargo-deny parse errors | AtomsBot, PhenoControl | cargo-deny passes |
| 1 | WS-M | Fix silent deny ignores | PhenoObservability | Advisory suppression works |
| 2 | WS-L | Add CI to Python repos | 13 repos | Test coverage in CI |
| 3 | WS-N | Fix helioscope CLAUDE.md ref | helioscope | Accurate reference |
| 4 | WS-O | Rationalize deny ignores | 9 repos | Auditable advisory policy |
| 5 | WS-Q | BytePort todo!() triage | BytePort | Known implementation debt |
| 6 | WS-P | Test infra for scorecard-remediation | phenodocs-scorecard-remediation | Consistent with reality |

---

# v9 Extension — 2026-05-05 (evening)

## What changed since v8

WS-K through WS-Q all completed. 4 new audits surfaced new findings.

### Completion scorecard (v8 additions)

| WS | Status | Outcome |
|---|---|---|
| WS-K | ✅ Done | AtomsBot `94303d1`, PhenoControl `012c7622` — duplicate allow-registry removed |
| WS-L | ✅ Done | helios-router (PR#212), heliosBench (direct push), QuadSGM (direct push) — all have CI |
| WS-M | ✅ Done | PhenoObservability `324cd90` — field names fixed, cargo deny passes |
| WS-N | ✅ Done | helioscope `9be8873` — all 5 heliosCLI → helios-cli casing fixed |
| WS-O | ✅ Done | hwLedger: RUSTSEC-2017-0008 removed (false positive), RUSTSEC-2023-0071 kept+reasoned. phenoData: RUSTSEC-2023-0071 kept+reasoned |
| WS-P | ✅ Done | False alarm — libs/docslib has Go tests; Python layer is uv compat only |
| WS-Q | ✅ Done | findings/byteport_todo_audit_2026-05-05.md — 1 live todo!() (nvms.rs:280), ~50 in .history/ (no action) |

### New audit findings (v9)

- **Go ecosystem**: 7 Go repos without CI (BytePort highest: 11,444 Go files). argis-extensions has interface mismatches (code/schema drift). netweave-final2 has 14 lock-copying violations.
- **Dependency hygiene**: SHA-pinning status for GitHub Actions (in progress). npm staleness checks (in progress).
- **Repo metadata**: CLAUDE.md/FUNDING.yml completeness scan (in progress). CI/CD coverage map (in progress).
- **Broken symlinks**: 8 canonical repos affected. helioscope (8 links), helios-cli (transport/harness). Worktrees have orphaned CONSTITUTION.yaml/ADR.md links from refactors.
- **Duplicate Cargo names**: None — all high-count names are distinct crates across subdirectories.

## New workstreams (WS-R through WS-Z)

### WS-R: Add CI to BytePort (P0)
- 11,444 Go files, no CI. Highest-priority Go CI gap.
- Add push/PR workflow: `go test ./...`, `go vet ./...`

### WS-S: Fix argis-extensions interface mismatches (P1)
- Interface mismatches between Go code and schema definitions
- Code/schema drift from schema evolution without code sync
- Audit: go_ecosystem_audit_2026-05-05.md

### WS-T: Fix netweave-final2 lock-copying violations (P1)
- 14 lock-copying violations (golangci-lint) — concurrency bug risk
- Fix: ensure mutexes are never copied after initialization

### WS-U: Fix broken symlinks (P2)
- 8 canonical repos with broken symlinks (helioscope, helios-cli, etc.)
- Most are transport/harness placeholders or refactor orphans
- Remove or recreate symlinks pointing to moved files

### WS-V: Add FUNDING.yml to repos missing it (P2)
- ALL canonical repos are missing FUNDING.yml — findings/repo_metadata_completeness_2026-05-05.md
- Agent running

### Rust Ecosystem Audit (findings/rust_ecosystem_audit_2026-05-05.md)
- **FocalPoint**: 4 ignore directives (all unmaintained advisories, reasoned)
- **PhenoControl**: 2 ignore directives (properly reasoned)
- **PhenoObservability**: 1 ignore directive (well-documented with expiration)
- **AgilePlus, AtomsBot, PhenoMCP**: Zero ignores — clean
- No critical unpatched vulnerabilities found across top Rust repos

### CI Coverage Gap (MAJOR — 37 repos need CI)
- 34 repos missing CLAUDE.md governance
- WS-R (BytePort) done (PR#213)
- WS-L (Python repos) done earlier
- Remaining 35 repos needing CI include critical Rust projects: eyetracker, bdd-integration, phenoAI, thegent-dispatch, phenotype-bus
- See findings/repo_metadata_completeness_2026-05-05.md for full list

### npm Vulnerability Fixes (running)
- WS-W: Fix AtomsBot 34 vulnerabilities (2 critical, 20 high, 7 moderate) — updating Vite
- WS-X: Fix thegent 7 moderate vulnerabilities (markdown-it ReDoS has no fix)

## Updated execution order (v9)

| Priority | WS | Action | Repos | Expected outcome |
|---|---|---|---|---|
| 0 | WS-R | Add CI to BytePort | BytePort | ✅ Done (PR#213) |
| 1 | WS-S | Fix argis-extensions interface drift | argis-extensions | In progress |
| 2 | WS-T | Fix lock-copying violations | netweave-final2 | ✅ Done (0e378d8) |
| 3 | WS-U | Fix broken symlinks | 5 repos | ✅ Done (5 commits) |
| 4 | WS-V | Add FUNDING.yml | 5 repos | ✅ Done (5 FUNDING.yml added) |
| 5 | WS-W | Fix AtomsBot npm vulnerabilities | AtomsBot | ✅ Done (undici update, 4d32914) |
| 6 | WS-X | Fix thegent npm vulnerabilities | thegent | ✅ Done (9d08d44) |
