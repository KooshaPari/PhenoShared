# PhenoShared — Git History Forensics (Lane A3)

Repo: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
Remote: `https://github.com/KooshaPari/PhenoShared.git` (origin), plus a local `no-mistakes` mirror
`/Users/kooshapari/.no-mistakes/repos/e13a7c834298.git`
Current branch at analysis time: `layer/governance-happy-path-claims` (HEAD `ad667428b`)
Generated: 2026-11-10T04:55Z · read-only analysis, no git mutation performed

---

## 1. First Commit

| Field | Value |
|---|---|
| SHA | `56319267bee68f6d15a737d4299dc92cf8918ad3` |
| Date | 2026-02-23 05:34:53 -0700 (2026-02-23T12:34:53Z) |
| Author | Koosha Paridehpour `<kooshapari@gmail.com>` |
| Subject | `fix(tokenledger): resolve compile errors after utils.rs module split` |

**Forensic note:** the first commit is *not* an "init" commit. The repository was created by importing
an existing working tree (ParetoRs + TokenLedgerRs already in flight) and committing the tip of it.
This is the classic **"snapshot-import" origin**: there is no `chore: init` commit, no `.gitignore`
init, and the root commit already contains a compiled Rust project mid-refactor (`utils.rs module
split`). History before 2026-02-23 is **not present in this repo** — the pre-import history of
ParetoRs / TokenLedgerRs / the monorepo ancestors lives elsewhere (or was never imported).

### Earliest six commits (chronological)

| # | SHA | Date | Author | Subject |
|---|---|---|---|---|
| 1 | `56319267b` | 2026-02-23 05:34:53 -0700 | Koosha Paridehpour | fix(tokenledger): resolve compile errors after utils.rs module split |
| 2 | `0539bf2c8` | 2026-02-23 06:46:55 -0700 | Koosha Paridehpour | fix(tokenledger): fix clippy errors, box large enum variant, split ingest.rs |
| 3 | `865e43372` | 2026-02-23 08:48:28 -0700 | Koosha Paridehpour | test: add comprehensive test suite with 46 tests achieving 100% coverage |
| 4 | `85b019b38` | 2026-02-23 09:46:22 -0700 | Koosha Paridehpour | chore: add gitignore and ignore build artifacts |
| 5 | `ea482a759` | 2026-02-23 12:43:13 -0700 | Koosha Paridehpour | chore: add docs |
| 6 | `a505725e8` | 2026-02-23 12:55:45 -0700 | Koosha Paridehpour | docs: update research |

The entire 2026-02 window is **a single day** (22 commits) — the import day.

---

## 2. Commits Per Month

| Month | Commits | Notes |
|---|---|---|
| 2026-02 | 22 | Import day only (2026-02-23). Single-author. |
| 2026-03 | 384 | **Workspace explosion.** Cargo decomposition, libification, ~50 crates born. |
| 2026-04 | 355 | Continued workspace hardening, journeys/core scaffolding. |
| 2026-05 | 156 | Lowest full month. KlipDot port. Consolidation lull. |
| 2026-06 | 347 | Rebound. phenoData absorption (5 crates), observability. |
| 2026-07 | 257 | gfx absorption, i18n, flags. |
| 2026-08 | **987** | **Peak month.** "frontier untracked-recovery snapshot (16 commits, 5421 files)" + PhenoObservability subtree. |
| 2026-09 | 345 | **Absorption wave:** 5 sprawl repos + herdr-{jcode,forgecode,helioslite}. |
| 2026-10 | 431 | AX-4x/AX-5x workspace-promotion batches, Mergify+Renovate CI unification. |
| 2026-11 (to 09th) | 297 | perf-core/hwledger promotion, PhenoCompose port, governance hardening. |
| **Total** | **3,581** | all refs, all branches |

Merge commits by month (for contrast with the table above, which counts all reachable commits):

| Month | Merges |
|---|---|
| 2026-02 | 1 |
| 2026-03 | 20 |
| 2026-04 | 13 |
| 2026-05 | 3 |
| 2026-06 | 38 |
| 2026-07 | 1 |
| 2026-08 | 2 |
| 2026-09 | 19 |
| 2026-10 | 4 |
| 2026-11 | 12 |

---

## 3. Authors

`git shortlog -sne --all` (top 15 of 3,581):

| Commits | Author |
|---|---|
| 1741 | KooshaPari `<42529354+KooshaPari@users.noreply.github.com>` |
| 529 | Koosha Paridehpour `<42529354+KooshaPari@users.noreply.github.com>` |
| 346 | dependabot[bot] `<49699333+dependabot[bot]@users.noreply.github.com>` |
| 256 | KooshaPari `<kooshapari@gmail.com>` |
| 211 | **jcode `<jcode@jcode.dev>`** |
| 148 | KooshaPari `<koosha@example.com>` |
| 80 | **Recovery Script `<recovery@phenotype.local>`** |
| 68 | KooshaPari `<claude@anthropic.com>` |
| 67 | KooshaPari `<forge@phenotype.dev>` |
| 36 | KooshaPari `<forge@kooshapari.local>` |
| 24 | Phenotype Agent `<agent@phenotype.ai>` |
| 14 | mergify[bot] `<37929162+mergify[bot]@users.noreply.github.com>` |
| 7 | Forge Bot `<forge@kooshapari.dev>` |
| 7 | KooshaPari `<agent@phenotype.local>` |
| 7 | pheno Decomposition `<decompose@phenotype.local>` |

**Key forensic observations:**

- **Identity fragmentation.** The same human appears under **6+ distinct identities**
  (`KooshaPari`/`Koosha Paridehpour` × 5 emails: `42529354+KooshaPari@users.noreply.github.com`
  (1741 + 529), `kooshapari@gmail.com` (256), `koosha@example.com` (148), `claude@anthropic.com` (68),
  `forge@phenotype.dev` (67)). Commit-count-per-author is therefore **not** a measure of human
  contribution — it is a measure of which email the tool happened to be configured with.
- **`koosha@example.com` (148 commits) is a placeholder identity** — an invalid RFC example domain.
  Any per-author governance metric computed on this repo will be skewed by it.
- **Agent identities are real, load-bearing authors**: `jcode@jcode.dev` (211), `forge@phenotype.dev`
  (67) + `forge@kooshapari.local` (36) + `Forge Bot` (7), `agent@phenotype.ai` (24),
  `agent@phenotype.local` (7), `decompose@phenotype.local` (7).
  **Automation-authored commits total ≈ 359 (10.0% of history).**
- **`Recovery Script <recovery@phenotype.local>` (80 commits)** — a machine identity that writes
  recovery/preservation commits (e.g. `44aa1d95a chore(recovery): preserve orphaned worktree
  trunk-action-repair`). Distinct from human authorship; these are forensic-preservation artifacts.
- **Bots**: dependabot 346 (9.7%) + mergify 14 = 360 commits (10.1%).
- Combined automation (bots + agents + recovery): **≈ 719 commits = 20.1% of all history.**
- **Human-attributed** (Koosha identities only): ≈ 2,862 = 79.9%.

---

## 4. Tags

**`git tag -l` → 9 tags, none of which is a product release tag.** They are 5 worktree-archive markers (`archive/orphan-worktree-agileplus-*-2026-07-15`, `archive/worktree-merged-2026-07-14-*`), 3 `promptscrape-v0.1.{0,1,2}`, and 1 `v0.2.0`.

Forensic consequences:

1. **No PhenoShared release is addressable by tag.** The single semver-looking tag (`v0.2.0`) is not tied to a release workflow, and the 8 others are housekeeping markers, so any `crates.io` publish, container image, or consumer dependency pin cannot reference a PhenoShared release tag; everything must pin a branch or a raw SHA.
2. **Semver history is unrecoverable from refs.** The only surviving version signals are inside
   `Cargo.toml` files and commit subjects (e.g. `fix(pheno-tracing): restore 0.4.0-pre.0 per compat
   pre-release policy`, `ca9b9cc32`).
3. Note the commit `093cd6ae0` (2026-03-29) — *"fix(ci): prevent -unknown suffix tags; add
   duplication audit doc (#46)"*. Release tags **were** being produced at some point (CI was rejecting
   `-unknown` suffixed tags), but none survive in any reachable ref. This is consistent with a
   tag-push failure, tag deletion, or release tags never having been pushed to origin.
4. `release-plz` / `goreleaser` commits exist (e.g. `75cdb13c9 fix(ci): resolve release-plz failure`,
   `2003c3bc9 fix(ci): fix goreleaser v2 schema`, `1934076b5 fix(ci): use correct repo name for
   release uploads`) yet the release output is **unaddressable by ref**. The release pipeline was
   repeatedly repaired during Sept–Nov 2026 without ever converging on a tagged release.

---

## 5. Merge vs Direct Commits

| Metric | Count | Share |
|---|---|---|
| Merge commits (`--merges`) | 113 | 3.2% |
| Direct commits (`--no-merges`) | 3,468 | 96.8% |
| Total reachable | 3,581 | 100% |
| First-parent commits on `HEAD` lineage | 1,036 | 28.9% |

**Ratio: 3,468 direct : 113 merge ≈ 30.7 : 1 (96.8% direct).**

Forensic interpretation:

- The repo is **merge-commit-light / squash-merge dominated**. PR subjects carry `(#NNN)` suffixes
  (e.g. `(#330)`, `(#784)`), which is the signature of **GitHub squash-merge** — squash merges create
  a *single* direct commit on the base branch, not a merge commit. So the 113 merges are the minority
  of the true PR-integration events; the real PR count is far higher (PR numbers observed up to
  **#825**).
- The 1,036 first-parent commits vs 3,581 total confirms heavy branch divergence: **~72% of commits
  are not on the mainline first-parent path**, i.e. the bulk of history lived on feature branches and
  entered via squash (which drops the branch commits' first-parent linkage but retains them as
  reachable objects).
- Merges are **bursty and episodic** — 38 in June, 19 in September, 20 in March, but only 1–4 in
  July, August, October. This matches long feature-branch lifetimes (branch opened, months of work,
  one merge at the end) rather than a continuous trunk.
- A `layer/`-prefixed branch naming convention is present in the branch list
  (`layer/governance-happy-path-claims`, `layer/a11y-gate-repair`,
  `layer/coverage-floor-sharecli-surface`, `layer/home-path-tail`, `layer/jsts-coverage-ratchet`,
  `layer/xdd-markdown-lint`) but **0 commit subjects** contain `layer/` — the convention is
  branch-name-only, never encoded in commit messages.

---

## 6. Inferred Eras

| # | Era | Boundary | Duration | Volume | Character |
|---|---|---|---|---|---|
| **E0** | **Snapshot import (pre-history absent)** | 2026-02-23 → 2026-02-23 | < 1 day | 22 | Working tree of an in-flight Rust project imported as git history. Root commit is already a mid-refactor fix. `.gitignore` arrives one commit late (commit #4), confirming the import was not a clean `git init`. |
| **E1** | **Hexagonal architecture + Cargo workspace foundation** | 2026-03-17 → 2026-03-31 | ~15 days | ~406 (Mar total 384 + tail of Feb) | `9bcf7ca16` (4 shared crates: event-sourcing, cache-adapter, policy-engine, state-machine) → `b9243d1c9`/`de112c884` (hexagonal contracts + adapter crates: application, domain, http-adapter, postgres-adapter, redis-adapter) → `2a2a9400c` ("Decompose into Cargo workspace: ParetoRs + TokenLedgerRs") → the 2026-03-29 **libification wave** (errors, telemetry, test-infra, retry, validation, agileplus-api-types, port-traits, config-core, crypto, error-core, iter, string, time, git-core, health, logging, macros, mcp) → `5677bae9e` "chore: consolidation (#439)" which mass-adds **27 `agileplus-*` crates** in a single commit. Era ends with `9a8e60f60` (RUSTSEC-2026-0002 lru upgrade) and `ac3c60d94` (ADR-002 Event Sourcing). |
| **E2** | **Steady-state workspace hardening** | 2026-04-01 → 2026-05-31 | ~2 months | 511 | Lowest-churn era. `phenotype-journey-core` (2026-04-20), `phenotype-casbin-wrapper` (2026-04-26), `klipdot-capture` (2026-05-31, "port KlipDot daemon into phenotype-journeys"). |
| **E3** | **Data-plane + observability expansion** | 2026-06-01 → 2026-07-31 | ~2 months | 604 | `pheno-data-from-phenoData` (5 crates: pg-bridge, pheno-query, smoke-tests, surreal-bridge — 2026-06-08); `phenotype-journeys-observability` + `phenotype-observability` (OTLP wiring, 2026-06-20/21); `phenotype-flags` (2026-07-02); `i18n` (2026-07-05); `phenotype-gfx` + `phenotype-voxel` (2026-07-17). First era with a clear **product-surface** (not just library-surface) direction. |
| **E4** | **Bulk import / recovery snapshot** | 2026-08-01 → 2026-08-31 | ~1 month | **987** | Peak. `618ffd3c3` "preserve(pheno): frontier untracked-recovery snapshot (16 commits, 5421 files) (#272)" — a single commit importing 5,421 files including the whole `agile-plus/PhenoObservability/crates/` subtree (helix-logging, pheno-dragonfly, pheno-questdb, phenotype-llm, phenotype-mcp-server, observably-*, tracely-core, tracely-sentinel). **History ceases to be a reliable proxy for effort in this month.** |
| **E5** | **Absorption wave (sprawl-repo consolidation)** | 2026-09-01 → 2026-09-30 | ~1 month | 345 | `3b45203b0` "absorption: absorb 5 sprawl repos with provenance and governance" — creates the `absorption/` tree (PhenoInfra and siblings, each with `.airlock/`, `.github/CODEOWNERS`, devcontainer, .env.example, tar.gz archives of dirty-file snapshots). Same day: `dee522c88` "absorb(herdr): fold herdr-{jcode,forgecode,helioslite} plugins into PhenoShared" with `PROVENANCE.md` per plugin. Era also carries release-pipeline repair (`release-plz`, `goreleaser`, `81bdc4f24` local release script) — but **no tags** (§4). |
| **E6** | **AX batch promotion + CI unification** | 2026-10-01 → 2026-10-31 | ~1 month | 431 | Mechanised promotion batches in `feat(workspace): add <crate> (E2.4 wave 3 batch AX-NN)` form — AX-42 through AX-58 observed, plus `05288e463` "batch AX-52 — unblock agileplus-* and focus-* via [workspace]-table removal". CI consolidation: `629b0b934` "route merges through Mergify queue, Renovate single merge path (#453)". Trunk action pinning (`ac32cc7b2`, `e3e3056d1`, `a4be46585`, `be3b7fc2f`) shows a **revert-and-repin loop**. |
| **E7** | **Governance hardening / happy-path claim removal** | 2026-11-01 → 2026-11-09 | 9 days | 297 | `6fd2835e5` "port the 41 unabsorbed PhenoCompose files (#758)"; `6e5fa283a` "durable homes for the go-sdk (240) and observability (140) files (#761)"; `7a9f14c28` "promote non-TQ perf-core and hwledger crates (#797)"; `a82de058c` "evaluate the absorption landscape as it actually stands (#781)"; `1e48fa7e3` "stop 28 scripts depending on one machine's absolute home path (#823)"; `ad667428b` "stop the guard reading shell syntax as a success claim". Era = **auditing the absorb-and-claim machinery itself.** |

**Era-boundary markers are the strongest signals in the history:** `2a2a9400c` (E1), `618ffd3c3`
(E4), `3b45203b0`/`dee522c88` (E5), `05288e463` (E6), `a82de058c` (E7).

---

## 7. Milestone Commits

| Date | SHA | Subject | Significance |
|---|---|---|---|
| 2026-02-23 | `56319267bee68f6d15a737d4299dc92cf8918ad3` | fix(tokenledger): resolve compile errors after utils.rs module split | **Repository origin (snapshot import, not init).** |
| 2026-03-17 | `9bcf7ca1649d59c085bcdfa0177d7377fe238944` | Add 4 shared crates: event-sourcing, cache-adapter, policy-engine, state-machine | First Rust crates in the tree. |
| 2026-03-25 | `1673df2c489daefbc3a104f79b9d687427ef00a5` | Merge ci/add-workflow into main (#14) | Earliest numbered PR; CI enters the repo. |
| 2026-03-25 | `b9243d1c9` / `de112c884` | hexagonal architecture contracts / adapter crates (#26, #39) | Hexagonal architecture codified. |
| 2026-03-28 | `2a2a9400c8f29873a795d9c085b333a75ae291b9` | **Decompose into Cargo workspace: ParetoRs + TokenLedgerRs (#171)** | The single most consequential structural commit. Creates `crates/pareto-rs` and `crates/tokenledger`. |
| 2026-03-29 | `ecc455bf7` … `01ade6ffe` | libification wave: shared-libs Phase 1 → remaining libification crates (#88 → #182) | ~18 crates born in one day. |
| 2026-03-30 | `5677bae9e` | chore: consolidation (#439) | Mass-adds 27 `agileplus-*` crates. |
| 2026-03-30 | `ac3c60d94` | docs(adr): ADR-002 Event Sourcing Strategy for Audit-Heavy Domains (#333) | Architecture decision record. |
| 2026-04-20 | `f26ee669a` | feat: initial phenotype-journeys package | Product-surface crate born. |
| 2026-05-31 | `458cbb5a5` | feat: port KlipDot daemon into phenotype-journeys | First external daemon port. |
| 2026-06-08 | `175afc87b` | chore: merge phenoData into pheno as crates/pheno-data-from-phenoData/ | External repo merge; 5 crates. |
| 2026-06-20/21 | `ce31e9d78` / `bee95e1c8` | wire pheno-tracing OTLP observability (#113, #245) | Observability substrate. |
| 2026-07-17 | `9047e9dc3` | feat(crates): absorb phenotype-gfx (graphics kernel) into crates/phenotype-gfx | First "absorb" commit using the absorb/crate convention that later scales. |
| 2026-08-08 | `618ffd3c3f70b66f75bc39c00fc9ecad955e5b2e` | **preserve(pheno): frontier untracked-recovery snapshot (16 commits, 5421 files) (#272)** | Largest single-commit import; **16 upstream commits flattened into one** — history loss point. |
| 2026-09-27 | `3b45203b0bc30b15c9e107b177d3567c7a358ae3` | **absorption: absorb 5 sprawl repos with provenance and governance** | Establishes the `absorption/<repo>/` + `PROVENANCE.md` pattern. |
| 2026-09-27 | `dee522c881e2940d8bb1a4461ff7a12f6f5b1103` | absorb(herdr): fold herdr-{jcode,forgecode,helioslite} plugins into PhenoShared | Three harness plugins absorbed in one commit, each with PROVENANCE.md. |
| 2026-09-27 → 09-29 | `ca9b9cc32` | fix(pheno-tracing): restore 0.4.0-pre.0 per compat pre-release policy | "compat pre-release policy" — a named compatibility policy in force. |
| 2026-10-10 | `05288e463` | chore(workspace): batch AX-52 — unblock agileplus-* and focus-* via [workspace]-table removal | Mechanised batch; AX-series begins. |
| 2026-10-17 | `629b0b934` | chore(ci): route merges through Mergify queue, Renovate single merge path (#453) | Single merge path established. |
| 2026-11-07 | `6fd2835e5` | feat(absorb): port the 41 unabsorbed PhenoCompose files (#758) | PhenoCompose absorption. |
| 2026-11-07 | `6e5fa283ad243fe96e72add3beb2d7989fd60a95` | feat(absorb): durable homes for the go-sdk (240) and observability (140) files (#761) | 380 files rehomed. |
| 2026-11-08 | `a82de058c` | docs(absorb): evaluate the absorption landscape as it actually stands (#781) | Explicit self-audit of the absorption program. |
| 2026-11-09 | `7a9f14c2831406a03678238dc7a4979b86cffea5` | feat(workspace): promote non-TQ perf-core and hwledger crates (#797) | Latest structural promotion. |
| 2026-11-09 | `1e48fa7e3` | fix(campaign): stop 28 scripts depending on one machine's absolute home path (#823) | Portability hardening. |
| 2026-11-09 | `ad667428b` | fix(governance): stop the guard reading shell syntax as a success claim | **HEAD.** Governance-claim falsification fix. |

---

## 8. Crate Birth Order

Current inventory: **372 entries under `crates/`, of which 337 are `Cargo.toml` manifests**
(68 distinct commits introduced at least one `crates/*/Cargo.toml`; the remaining manifests came in
via bulk import/subtree moves where the path did not match the `crates/*/Cargo.toml` glob, e.g.
nested `crates/agile-plus/PhenoObservability/crates/*`).

| Order | Date | SHA | Crate(s) born |
|---|---|---|---|
| 1 | 2026-03-17 | `9bcf7ca16` | `phenotype-cache-adapter`, `phenotype-event-sourcing`, `phenotype-policy-engine`, `phenotype-state-machine` |
| 2 | 2026-03-25 | `1673df2c4` | *(nested duplicate `phenotype-event-sourcing/phenotype-event-sourcing/` — path artifact of the merge)* |
| 3 | 2026-03-25 | `6f2d6879a` | `phenotype-port-interfaces` |
| 4 | 2026-03-25 | `b9243d1c9` | `phenotype-contracts` |
| 5 | 2026-03-25 | `de112c884` | `phenotype-application`, `phenotype-domain`, `phenotype-http-adapter`, `phenotype-postgres-adapter`, `phenotype-redis-adapter` |
| 6 | 2026-03-25 | `dcc2d7c09` | `ffi_utils` |
| 7 | 2026-03-28 | `2a2a9400c` | `pareto-rs`, `tokenledger` |
| 8 | 2026-03-29 | `093cd6ae0` | *(nested dupes: cache-adapter, contracts, policy-engine, state-machine)* |
| 9 | 2026-03-29 | `ecc455bf7` | `phenotype-errors`, `phenotype-telemetry`, `phenotype-test-infra` |
| 10 | 2026-03-29 | `3e6a8a951` | `phenotype-retry` |
| 11 | 2026-03-29 | `e5da22a49` | `phenotype-validation` |
| 12 | 2026-03-29 | `ed2969654` | `agileplus-api-types`, `phenotype-port-traits` |
| 13 | 2026-03-29 | `378c0e66d` | `agileplus-domain` |
| 14 | 2026-03-29 | `c47ddc158` | `phenotype-crypto`, `phenotype-error-core`, `phenotype-iter`, `phenotype-string`, `phenotype-time` |
| 15 | 2026-03-29 | `01ade6ffe` | `phenotype-git-core`, `phenotype-health`, `phenotype-logging`, `phenotype-macros`, `phenotype-mcp` |
| 16 | 2026-03-29 | `4694e3df1` | `phenotype-http-client-core` |
| 17 | 2026-03-30 | `72b30772f` | `phenotype-config-core` |
| 18 | 2026-03-30 | `4b6d374a1` | `agileplus-error-core`, `agileplus-health`, `phenotype-cost-core` |
| 19 | 2026-03-30 | `920451211` | `phenotype-config-loader` |
| 20 | 2026-03-30 | `68116ed53` | `phenotype-process` |
| 21 | 2026-03-30 | `ac3c60d94` | *(dupes: agileplus-api-types, agileplus-error-core)* |
| 22 | 2026-03-30 | `b73418901` | `phenotype-ports-canonical` |
| 23 | 2026-03-30 | `9a8e60f60` | `phenotype-async-traits` |
| 24 | 2026-03-30 | `5be2be2f3` | `phenotype-error-macros` |
| 25 | 2026-03-30 | `9d9b2130c` | `phenotype-contract` |
| 26 | 2026-03-30 | `dd1dbe005` | *(dupe: phenotype-iter)* |
| 27 | 2026-03-30 | `5677bae9e` | **27 crates at once**: `agileplus-api`, `agileplus-benchmarks`, `agileplus-cache`, `agileplus-cli`, `agileplus-contract-tests`, `agileplus-dashboard`, `agileplus-domain`, `agileplus-events`, `agileplus-git`, `agileplus-github`, `agileplus-graph`, `agileplus-grpc`, `agileplus-import`, `agileplus-integration-tests`, `agileplus-nats`, `agileplus-p2p`, `agileplus-plane`, `agileplus-sqlite`, `agileplus-subcmds`, `agileplus-sync`, `agileplus-telemetry`, `agileplus-triage` (+6 more in the same commit) |
| 28 | 2026-03-30 | `0c721c2e7` | `bifrost-routing`, `phenotype-shared-config` |
| 29 | 2026-04-20 | `f26ee669a` | `phenotype-journey-core` |
| 30 | 2026-04-26 | `d0808a5bc` | `phenotype-casbin-wrapper` |
| 31 | 2026-05-31 | `458cbb5a5` | `klipdot-capture` |
| 32 | 2026-06-08 | `175afc87b` | `pheno-data-from-phenoData`, `pheno-data-from-phenoData/pg-bridge`, `.../pheno-query`, `.../smoke-tests`, `.../surreal-bridge` |
| 33 | 2026-06-20 | `ce31e9d78` | `phenotype-journeys-observability` |
| 34 | 2026-06-21 | `bee95e1c8` | `phenotype-observability` |
| 35 | 2026-07-02 | `8add7f7cc` | `phenotype-flags` |
| 36 | 2026-07-05 | `02b376705` | `i18n` |
| 37 | 2026-07-17 | `9047e9dc3` | `phenotype-gfx`, `phenotype-gfx/crates/phenotype-voxel` |
| 38 | 2026-08-08 | `618ffd3c3` | `agile-plus`, `agile-plus/PhenoObservability` + 11 nested crates: `helix-logging`, `pheno-dragonfly`, `pheno-questdb`, `phenotype-llm`, `phenotype-mcp-server`, `phenotype-observably-logging`, `phenotype-observably-macros`, `phenotype-observably-sentinel`, `phenotype-observably-tracing`, `tracely-core`, `tracely-sentinel` |
| 39+ | 2026-08 → 2026-11 | (bulk) | Remainder (~260+ manifests) arrive via subtree/bulk imports: `absorption/*` trees, `phenotype-perf-core`/`hwledger` promotions (`7a9f14c28`, 2026-11-09), focus-* crates (AX-46..AX-50, 2026-10-10), `sharecli`/`pheno-compose-*`/`spawn-core-sys` members (`2624b4353`, AX-58). |

**Birth-order findings:**

- **Nested-duplicate manifests** (`crates/X/X/Cargo.toml`) appear at rows 2, 8, 21, 26 — a
  workspace-flattening bug that re-created four crates at a doubled path. Fixed later by the
  "remove [workspace]-table" / `[workspace]`-table-removal campaign (`05288e463` AX-52).
- **Crate naming is not uniform**: `phenotype-*` (majority), `agileplus-*`, `agile-plus` (hyphen vs
  no-hyphen for the same product family), `ffi_utils` (snake_case), `klipdot-capture`,
  `i18n` (bare), `pheno-data-from-phenoData` (camelCase in path). **Five distinct naming conventions**
  coexist in one workspace.
- **The bulk of crates were never individually authored** — they arrived with subtree imports. The
  `crates/*/Cargo.toml` glob matched only 68 of the 337 manifests, so **~80% of crate identities have
  no birth commit in this repo's history.**

---

## 9. Volume Stats

| Metric | Value |
|---|---|
| Total commits (all refs) | 3,581 at the time of this measurement; re-measure gives 3,641 (2026-11-10T07:38Z). The count drifts with branch pushes. |
| Total commits (first-parent lineage) | 1,036 (28.9%) |
| Direct (non-merge) commits | 3,468 (96.8%) |
| Merge commits | 113 (3.2%) |
| Direct : merge ratio | ≈ 30.7 : 1 |
| Tracked files at HEAD | 42,225 |
| Crate directories under `crates/` | 372 |
| `Cargo.toml` manifests under `crates/` | 337 |
| Distinct commits that introduced ≥1 crate manifest | 68 |
| Tags | 9 (5 worktree-archive markers, 3 `promptscrape-v0.1.x`, 1 `v0.2.0`; zero release tags) |
| Distinct commit authors (identities) | 15+ shown; same human under 6+ identities |
| Bot-authored commits | 360 (dependabot 346 + mergify 14) — 10.1% |
| Agent-authored commits | ~359 (jcode 211, forge 110, phenotype agents 31, decompose 7) — 10.0% |
| Recovery-script authored | 80 (2.2%) |
| **Total non-human-authored** | **≈ 719 — 20.1%** |
| Human-attributed (Koosha identities) | ≈ 2,862 — 79.9% |
| Avg commits/month (Feb 23 – Nov 9, 10.5 months) | ≈ 341 |
| Peak month | 2026-08 — 987 commits |
| Trough month | 2026-05 — 156 commits |
| Peak : trough ratio | 6.3 : 1 |
| Observed PR numbers | up to #825 |
| History span | 2026-02-23 → 2026-11-09 (259 days) |
| Avg commits/day over span | ≈ 13.8/day |

### Volume caveats (read before using these numbers)

1. **Commit count is not work volume.** `618ffd3c3` alone contributed **5,421 files** in a single
   commit, while 68 of the 3,581 commits contributed the majority of the 42,225 tracked files. The
   2026-08 peak (987) is dominated by **bulk-import commits**, not authoring velocity.
2. **History was flattened at least three times** — `618ffd3c3` ("16 commits" collapsed into one),
   `3b45203b0` (5 repos' history collapsed into a single `absorption/` tree with provenance files
   rather than real history), and `5677bae9e` (27 crates in one commit). The upstream commit graph of
   the absorbed repos is **not** in this repository.
3. **No tags + 3.2% merges = no verifiable release history.** Release intent is visible in commit
   subjects only.
4. **Author identity is fragmented 6 ways**, so any "top contributor" metric on this repo is
   measuring email configuration, not human effort.
5. The `no-mistakes` local remote (`/Users/kooshapari/.no-mistakes/repos/e13a7c834298.git`) means
   `git rev-list --all` may include commits present only in that mirror, not on `origin`.
6. All numbers were measured with read-only `git log`/`git show` commands; **no refs, branches, or
   the working tree were modified.**
