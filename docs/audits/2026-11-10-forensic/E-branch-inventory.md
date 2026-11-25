# Lane E — Branch + Stranded-Work Inventory: PhenoShared

- **Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
- **Remote:** `origin` = `https://github.com/KooshaPari/PhenoShared.git` (plus local-only `no-mistakes` fetch remote)
- **Observed at:** 2026-11-10T04:35Z–04:39Z
- **Mode:** READ-ONLY. No fetch, checkout, prune, rebase, or branch deletion. No writes inside the repo.
- **Caveat on staleness:** `origin/main` was NOT re-fetched (forbidden by lane scope), so every ahead/behind figure is relative to the **locally cached** `origin/main` at `65f0a5334` ("fix(ci): diff the happy-path guard against the merge-base… (#825)", 2026-11-09). Live GitHub state may be newer.
- **Authority used:** ancestry (`merge-base --is-ancestor`), divergence (`rev-list --left-right`), **patch identity** (`git cherry`), and tree diff (`diff --name-only`). Patch identity is the only meaningful merge test here, because main is a squash/rebase-derived line.

---

## 1. Summary counts

| Metric | Value |
|---|---|
| Remote branches (excl. `origin/main`) | **68** |
| `origin/main` head | `65f0a5334`, 2026-11-09 |
| **Ancestry-MERGED into `origin/main`** | **0** (`main` only) |
| Patch-EQUIVALENT / fully landed (unique=0) | **1** (`KooshaPari-patch-1`) |
| Share history with `origin/main` (merge-base exists) | **52** |
| **No common ancestor (orphan-root)** | **16** |
| Unmerged with ≥1 genuinely unique patch | **67** |
| Ahead > 0 | **68 of 68** (every branch) |
| Behind > 0 | **68 of 68** |
| **Stale** (last commit older than 2026-10-01) | **11** |
| Local branches | **45** |
| Local branches with deleted upstream (`: gone`) | **31** |
| Local branches fully patch-equivalent in main (safe local delete) | **26 gone + 1 alias = 27** |
| Worktrees registered | **19** |

### The headline finding

**Zero remote branches are ancestry-merged.** Every branch is "unmerged" by `git merge-base --is-ancestor`, including the ones whose work demonstrably landed (e.g. `#823`, `#825`, `#821` all appear in `origin/main`'s log). The repo merges by **squash**, so ancestry is a dead signal and `git cherry` is the real ledger. Consequences:

1. Any tool or agent that classifies "merged" by ancestry will report ~68 stranded branches forever. That is a false positive, not a backlog.
2. 16 branches have **no common ancestor at all** with main. They are orphan-root snapshots of *other repos' histories* imported into PhenoShared — not feature branches. Diffing them against main blows up to 42,000+ files because there is no shared base.
3. 31 of 45 local branches are provably landed work still occupying disk.

---

## 2. Full remote-branch table (68 branches)

Class legend:
- `ABSORB-SNAPSHOT` — orphan root, no merge-base with main; holds another repo's full history/tree (`wrapup/*`, `snapshot/*`, some `rescue/*`). Not a feature branch. Content question, not patch question.
- `ARCHIVE` — deliberate archive/import branch under `archives/`.
- `STALE` — last commit older than 2026-10-01.
- `STRANDED-ACTIVE` — real feature work off main, unique patches, recent activity. **This is the actual rescue backlog.**
- `LANDED` — all commits patch-equivalent in main; delete candidate.

`U` = unique patches (present in branch, absent by patch-id from main). `E` = patch-equivalent commits.

| # | Branch | Last commit | Ahead | Behind | Merge-base | U | E | Merged? | Class |
|---|---|---|---|---|---|---|---|---|---|
| 1 | origin/wrapup/apisync-20261108 | 2026-11-07 | 498 | 1213 | **none** | 442 | 49 | no | ABSORB-SNAPSHOT |
| 2 | origin/wrapup/nanovms-20261108 | 2026-11-07 | 378 | 1213 | **none** | 293 | 71 | no | ABSORB-SNAPSHOT |
| 3 | origin/wrapup/tokn-20261108 | 2026-11-07 | 307 | 1213 | **none** | 230 | 74 | no | ABSORB-SNAPSHOT |
| 4 | origin/wrapup/phenojourneys-20261108 | 2026-10-13 | 245 | 1213 | **none** | 179 | 60 | no | ABSORB-SNAPSHOT |
| 5 | origin/archives/recovered-worktrees-20261106 | 2026-11-05 | 151 | 108 | yes | 108 | 32 | no | ARCHIVE |
| 6 | origin/wrapup/phenoforge-20261108 | 2026-11-07 | 127 | 1213 | **none** | 58 | 61 | no | ABSORB-SNAPSHOT |
| 7 | origin/wrapup/datakit-20261108 | 2026-11-07 | 125 | 1213 | **none** | 73 | 46 | no | ABSORB-SNAPSHOT |
| 8 | origin/wrapup/phenokits-commons-20261108 | 2026-11-07 | 79 | 1213 | **none** | 19 | 60 | no | ABSORB-SNAPSHOT |
| 9 | origin/wrapup/logify-20261108 | 2026-11-07 | 79 | 1213 | **none** | 37 | 40 | no | ABSORB-SNAPSHOT |
| 10 | origin/docs/researchledger-recovery-20261012 | 2026-11-07 | 71 | 42 | yes | 70 | 0 | no | STRANDED-ACTIVE |
| 11 | origin/rescue/e-drive-2026-10-29/tags/v0.1.0 | 2026-03-29 | 40 | 1210 | yes | 28 | 4 | no | STALE |
| 12 | origin/pose-roulette/build | 2026-09-29 | 24 | 456 | yes | 24 | 0 | no | STALE |
| 13 | origin/tmp-pose-ci | 2026-09-30 | 22 | 456 | yes | 21 | 1 | no | STALE |
| 14 | origin/docs-audit-2026-10-17 | 2026-10-16 | 22 | 284 | yes | 22 | 0 | no | STRANDED-ACTIVE |
| 15 | origin/chore/archives-recovered-worktrees-20261106 | 2026-11-06 | 14 | 101 | yes | 14 | 0 | no | ARCHIVE |
| 16 | origin/wrapup/pheno-runtime-config-20261108 | 2026-11-07 | 11 | 1213 | **none** | 5 | 6 | no | ABSORB-SNAPSHOT |
| 17 | origin/feat/phinbox-full-intent-20261017 | 2026-11-07 | 10 | 42 | yes | 7 | 0 | no | STRANDED-ACTIVE |
| 18 | origin/feat/brokerd-write-api | 2026-11-09 | 9 | 31 | yes | 7 | 0 | no | STRANDED-ACTIVE |
| 19 | origin/fix/lazy-acquire | 2026-11-09 | 8 | 1 | yes | 7 | 0 | no | STRANDED-ACTIVE |
| 20 | origin/feat/pose-roulette-mobile | 2026-09-29 | 8 | 456 | yes | 8 | 0 | no | STALE |
| 21 | origin/KooshaPari-patch-2 | 2026-10-17 | 7 | 284 | yes | 7 | 0 | no | STRANDED-ACTIVE |
| 22 | origin/codex/opencode-keypool | 2026-11-07 | 7 | 42 | yes | 5 | 0 | no | STRANDED-ACTIVE |
| 23 | origin/ci/remeasure-baselines | 2026-11-09 | 7 | 2 | yes | 7 | 0 | no | STRANDED-ACTIVE |
| 24 | origin/wrapup/local-ops-20261108 | 2026-11-07 | 6 | 1213 | **none** | 6 | 0 | no | ABSORB-SNAPSHOT |
| 25 | origin/chore/workflow-actionlint-baseline-20261014 | 2026-10-14 | 6 | 288 | yes | 6 | 0 | no | STRANDED-ACTIVE |
| 26 | origin/wrapup/pheno-20261108 | 2026-11-08 | 5 | 140 | yes | 5 | 0 | no | STRANDED-ACTIVE |
| 27 | origin/chore/trunk-action-cache-compat-20261014 | 2026-10-14 | 5 | 288 | yes | 5 | 0 | no | STRANDED-ACTIVE |
| 28 | origin/fix/vitepress-redacted-escaping | 2026-11-07 | 4 | 65 | yes | 3 | 1 | no | STRANDED-ACTIVE |
| 29 | origin/fix/integration-kit-windows-python-20261012 | 2026-11-07 | 4 | 42 | yes | 3 | 0 | no | STRANDED-ACTIVE |
| 30 | origin/fix/coverage-job-timeouts | 2026-11-08 | 4 | 48 | yes | 4 | 0 | no | STRANDED-ACTIVE |
| 31 | origin/ci/reconcile-action-pins | 2026-10-13 | 4 | 289 | yes | 4 | 0 | no | STRANDED-ACTIVE |
| 32 | origin/feat/browser-profile-lease | 2026-11-04 | 3 | 459 | yes | 3 | 0 | no | STRANDED-ACTIVE |
| 33 | origin/wrapup/vitepress-relaunch-20261108 | 2026-11-08 | 2 | 52 | yes | 1 | 1 | no | STRANDED-ACTIVE |
| 34 | origin/wrapup/phenoobservability-20261108 | 2026-11-07 | 2 | 1213 | **none** | 2 | 0 | no | ABSORB-SNAPSHOT |
| 35 | origin/wrapup/deny-advisory-20261108 | 2026-11-08 | 2 | 52 | yes | 1 | 1 | no | STRANDED-ACTIVE |
| 36 | origin/snapshot/orphan/meta | 2026-11-05 | 2 | 1213 | **none** | 2 | 0 | no | ABSORB-SNAPSHOT |
| 37 | origin/instinct/kit-rerun-20261012 | 2026-10-12 | 2 | 289 | yes | 2 | 0 | no | STRANDED-ACTIVE |
| 38 | origin/fix/license-compliance-enforcement | 2026-11-07 | 2 | 42 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 39 | origin/fix/coverage-ratchet-floor | 2026-11-08 | 2 | 39 | yes | 2 | 0 | no | STRANDED-ACTIVE |
| 40 | origin/fix/cargo-taplo-native-member | 2026-11-09 | 2 | 4 | yes | 2 | 0 | no | STRANDED-ACTIVE |
| 41 | origin/feat/phinbox-discord-management-20261016 | 2026-11-07 | 2 | 42 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 42 | origin/chore/remove-dead-integration-crate | 2026-10-12 | 2 | 289 | yes | 2 | 0 | no | STRANDED-ACTIVE |
| 43 | origin/wrapup/zz-forensic-zz-pheno-20261108 | 2026-11-08 | 1 | 631 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 44 | origin/wrapup/recovered-trunk-action-repair-20261108 | 2026-11-07 | 1 | 40 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 45 | origin/wrapup/phenoplugins-20261108 | 2026-11-08 | 1 | 1213 | **none** | 1 | 0 | no | ABSORB-SNAPSHOT |
| 46 | origin/wrapup/d1-nontq-20261108 | 2026-11-08 | 1 | 284 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 47 | origin/verify/final | 2026-11-08 | 1 | 69 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 48 | origin/temp-docs-push | 2026-09-15 | 1 | 607 | yes | 1 | 0 | no | STALE |
| 49 | origin/snapshot/orphan/phenotype-hub | 2026-11-04 | 1 | 1213 | **none** | 1 | 0 | no | ABSORB-SNAPSHOT |
| 50 | origin/snapshot/orphan/cvp-fixture | 2026-11-04 | 1 | 1213 | **none** | 1 | 0 | no | ABSORB-SNAPSHOT |
| 51 | origin/snapshot/orphan/browser-infra | 2026-11-05 | 1 | 1213 | **none** | 1 | 0 | no | ABSORB-SNAPSHOT |
| 52 | origin/merge-pheno-data | 2026-09-15 | 1 | 613 | yes | 1 | 0 | no | STALE |
| 53 | origin/layer/governance-happy-path-claims | 2026-11-09 | 1 | 0 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 54 | origin/KooshaPari-patch-1 | 2026-10-17 | 1 | 284 | yes | 0 | 1 | no | **LANDED** |
| 55 | origin/integration/absorbed-20261109 | 2026-11-09 | 1 | 19 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 56 | origin/instinct/infra-resources-doc | 2026-10-07 | 1 | 443 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 57 | origin/governance/happy-path-claims | 2026-11-09 | 1 | 0 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 58 | origin/fix/trunk-action-immutable-pin-20261013 | 2026-10-13 | 1 | 288 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 59 | origin/fix/guard-claim-false-positive | 2026-11-09 | 1 | 1 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 60 | origin/fix/fmt-perf-core | 2026-11-09 | 1 | 1 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 61 | origin/fix/duplicate-cargo-toml-tables | 2026-10-15 | 1 | 573 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 62 | origin/fix/ci-vendor-phenotype-observably-macros | 2026-10-12 | 1 | 289 | yes | 1 | 0 | no | STRANDED-ACTIVE |
| 63 | origin/fix/build-dashboard-stub | 2026-09-15 | 1 | 613 | yes | 1 | 0 | no | STALE |
| 64 | origin/docs/chat-shaping-20260918-a0147e5 | 2026-09-18 | 1 | 521 | yes | 1 | 0 | no | STALE |
| 65 | origin/dependabot/uv/python/scipy-1.18.1 | 2026-09-17 | 1 | 546 | yes | 1 | 0 | no | STALE |
| 66 | origin/dependabot/npm_and_yarn/_archived/byteport/frontend/web/npm_and_yarn-7462689bbc | 2026-09-17 | 1 | 550 | yes | 1 | 0 | no | STALE |
| 67 | origin/dependabot/cargo/iac/landing-bootstrap/serde-1.0.229 | 2026-09-17 | 1 | 546 | yes | 1 | 0 | no | STALE |
| 68 | origin/chore/pin-action-refs | 2026-11-09 | 1 | 30 | yes | 1 | 0 | no | STRANDED-ACTIVE |

**Class totals:** ABSORB-SNAPSHOT 16 · ARCHIVE 2 · STALE 11 · STRANDED-ACTIVE 38 · LANDED 1 · MERGED 0.

---

## 3. Top 15 work worth rescuing

Ranked by unique patch count. **Split into two buckets, because they are different problems.**

### Bucket A — real feature branches off main (actual rescue candidates)

| # | Branch | U | Last commit | Behind | What it touches |
|---|---|---|---|---|---|
| 1 | origin/docs/researchledger-recovery-20261012 | 70 | 2026-11-07 | 42 | 64 files, +9,858. Read-only local Git object locator for missing Sept source; `tests/researchledger/test_historical_locator.py`, `test_recovery.py`, `test_workflow_secret_scope.py`. Still the only branch carrying the research-ledger recovery tooling. |
| 2 | origin/archives/recovered-worktrees-20261106 | 108 | 2026-11-05 | 108 | 5,448 files, +777,924. `archives/zz-rich-cli-kit-rb/`, `archives/*-rb` byte-exact recovered worktrees. Deliberate archive; big but landable. |
| 3 | origin/pose-roulette/build | 24 | 2026-09-29 | 456 | 18 files, +2,301. `apps/pose-roulette/` (Dart + `RecapRenderer.swift` 286 lines). Stale by age but content is real. |
| 4 | origin/docs-audit-2026-10-17 | 22 | 2026-10-16 | 284 | 18 files, +2,274. `docs/audits/2026-10-17/phenoshared-complement.md` + pose-roulette CI probe. |
| 5 | origin/tmp-pose-ci | 21 | 2026-09-30 | 456 | 18 files, +2,316. `.github/workflows/pose-roulette-build.yml`, `pose-roulette-ci-probe.yml`. |
| 6 | origin/feat/brokerd-write-api | 7 | **2026-11-09** | 31 | 8 files, +1,755/−113. `crates/substrate-browser-mcp/src/lib.rs`, new `tests/remote_write_api.rs` (327 lines). Mutation routes so the daemon is the single lease authority. **Active.** |
| 7 | origin/ci/remeasure-baselines | 7 | **2026-11-09** | 2 | 5 files, +1,350/−47. New `.github/scripts/coverage_membership.py` (376), `tests/test_coverage_membership.py` (345), `coverage.yml`. Only 2 behind. **Cheapest real merge.** |
| 8 | origin/fix/lazy-acquire | 7 | **2026-11-09** | 1 | 8 files, +654/−57. `substrate-browser-mcp/src/client.rs` (+198), new `tests/daemon_acquire.rs`. Only 1 behind. **Cheapest real merge.** |
| 9 | origin/feat/phinbox-full-intent-20261017 | 7 | 2026-11-07 | 42 | Phinbox native harness, plugin profiles, CLI guards, Swift transport. |
| 10 | origin/chore/workflow-actionlint-baseline-20261014 | 6 | 2026-10-14 | 288 | Actionlint baseline workflows. |
| 11 | origin/wrapup/pheno-20261108 | 5 | 2026-11-08 | 140 | 32 files, +561/−155. `crates/eidolon-sandbox`, `sharecli-ffi/src/lib.rs` (+97), `lefthook.yml`. |
| 12 | origin/chore/trunk-action-cache-compat-20261014 | 5 | 2026-10-14 | 288 | Trunk action cache compat. |
| 13 | origin/chore/pin-action-refs | 1 | 2026-11-09 | 30 | 43 files, +176/−174. Pins every workflow action to a commit SHA. Duplicates landed `#823` intent but patch-unique. |
| 14 | origin/fix/coverage-job-timeouts | 4 | 2026-11-08 | 48 | Coverage job timeouts (4 commits). |
| 15 | origin/ci/reconcile-action-pins | 4 | 2026-10-13 | 289 | Action pin reconciliation. |

High-value small branches also worth taking because they are 0–2 behind main:
`origin/layer/governance-happy-path-claims` (1/0), `origin/governance/happy-path-claims` (1/0, **duplicate of the above**, same commit subject), `origin/fix/guard-claim-false-positive` (1/1), `origin/fix/fmt-perf-core` (1/1), `origin/fix/cargo-taplo-native-member` (2/4), `origin/integration/absorbed-20261109` (1/19).

### Bucket B — orphan-root absorption snapshots (NOT feature branches)

These have **no common ancestor** with main. `ahead` counts are the size of a foreign history, not pending work. They cannot be merged, only (a) archived, (b) content-diffed selectively, or (c) deleted once the absorbed-repo question is settled.

| Branch | Foreign history size | Notable |
|---|---|---|
| origin/wrapup/apisync-20261108 | 498 commits | Apisync repo line, root 2026-03-25 |
| origin/wrapup/nanovms-20261108 | 378 | Nanovms line |
| origin/wrapup/tokn-20261108 | 307 | TokenLedger line, root 2026-02-23 |
| origin/wrapup/phenojourneys-20261108 | 245 | PhenoJourneys line |
| origin/wrapup/phenoforge-20261108 | 127 | 58 unique / 61 patch-equiv — partially overlaps main content |
| origin/wrapup/datakit-20261108 | 125 | DataKit line |
| origin/wrapup/phenokits-commons-20261108 | 79 | 19 unique / 60 equiv — mostly already in main |
| origin/wrapup/logify-20261108 | 79 | Logify line |
| origin/wrapup/pheno-runtime-config-20261108 | 11 | 5 unique / 6 equiv |
| origin/wrapup/local-ops-20261108 | 6 | Local ops |
| origin/wrapup/phenoobservability-20261108 | 2 | Frontmatter + 1 |
| origin/wrapup/phenoplugins-20261108 | 1 | Single "rescue stranded PhenoPlugins work" commit (2026-11-08) |
| origin/snapshot/orphan/meta | 2 | Sanitized architecture excerpt |
| origin/snapshot/orphan/phenotype-hub | 1 | |
| origin/snapshot/orphan/cvp-fixture | 1 | |
| origin/snapshot/orphan/browser-infra | 1 | |

---

## 4. Local-only / stranded local branches

### 4a. Local branches with **no** upstream at all (4)

| Branch | Ahead | Behind | Worktree |
|---|---|---|---|
| build/merged-tls | 0 | 20 | `~/CodeProjects/temp/build-merged` |
| chore/pin-action-refs-clean | 0 | 12 | `~/CodeProjects/temp/pins-clean` |
| fix/nonblocking-lease-lock | 0 | 31 | `.../PhenoShared-space/fix/nonblocking-lease-lock/wtree` |
| fix/guard-merge-base | 1 (patch-equiv=1) | 1 | `~/CodeProjects/temp/guard-base` |

`build/merged-tls`, `chore/pin-action-refs-clean`, `fix/nonblocking-lease-lock` are **0 ahead** — they hold no unique commits and are pure disk. `fix/guard-merge-base` is patch-equivalent in main (landed as `#825`).

### 4b. Local branches whose upstream is `origin/main` (not their own branch) — mis-tracked

| Branch | Ahead | Behind |
|---|---|---|
| main | 1 | 4 |
| feat/mcp-ca-pinning | 0 | 1 |
| feat/promote-nontq-perf-core-hwledger | 3 | 24 |

**`main` is 1 ahead / 4 behind `origin/main`** with a patch-unique commit `c682ec2d8` "fix(campaign): stop **63** scripts depending on one machine's absolute home path" — a broader variant of the landed `#823` ("**28** scripts"). This is the one genuinely stranded local commit on the trunk. `feat/promote-nontq-perf-core-hwledger` holds 3 patch-unique commits and tracks `origin/main` by mistake (so `git status` will never warn about it).

### 4c. Local branches with deleted upstream (`: gone`) — 31

Of these **26 are fully patch-equivalent in main** (unique=0) — landed via PR, upstream deleted, local copy is pure disk:
`fix/windows-job-object`, `fix/trunk-trailing-space`, `fix/trunk-trailing-space-2`, `fix/trunk-rust-runtime`, `fix/trunk-format-disabled-workflows`, `fix/trunk-config-valid`, `fix/trufflehog-scan-range`, `fix/scorecard-publish-permissions`, `fix/scorecard-codeql-pin`, `fix/release-attestation-step`, `fix/pages-deployer-duplication`, `fix/osv-scanner-cli`, `fix/lease-owner-identity`, `fix/guard-merge-base`, `fix/governance-claims-and-formatting`, `fix/e2e-unknown-type-assertion`, `fix/e2e-invalid-json-assertion`, `fix/docs-validation-paths`, `fix/docs-build-vue-resolution`, `fix/disabled-workflow-annotation`, `fix/dead-action-pins-2`, `fix/bounded-lease-lock`, `fix/actionlint-three-errors`, `docs/absorption-evaluation`, `ci/windows-job-object-test`, `ci/coverage-per-crate`.

**Not landed — unique work despite deleted upstream (5):**

| Branch | Ahead | Unique | Note |
|---|---|---|---|
| feature/pii-sweep-path-repair | 2 | 2 | upstream deleted, work not in main |
| fix/pii-sweep-broken-workflow-refs | 2 | 2 | upstream deleted, work not in main |
| fix/cargo-audit-4-vulns | 1 | 1 | upstream deleted; the "four cargo-audit vulnerabilities" fix is NOT in main |
| feat/launchd-service | 2 | 2 | TLS staging for the daemon; not in main |
| feat/brokerd-write-api-squashed | 1 | 1 | squashed twin of `feat/brokerd-write-api` |

`fix/cargo-audit-4-vulns` is the highest-risk of these: a security fix whose branch was deleted upstream but whose patch never reached main.

---

## 5. Worktree registry (19 entries)

| Path | Branch | Conforms to layout policy? |
|---|---|---|
| repos/PhenoShared | layer/governance-happy-path-claims | ✅ main checkout |
| PhenoShared-space/chore/wtree | chore/pin-action-refs | ✅ `<type>/wtree` |
| PhenoShared-space/feat/brokerd-write-api-squashed/wtree | feat/brokerd-write-api-squashed | ✅ slugged (2nd `feat`) |
| PhenoShared-space/feat/brokerd-write-api/wtree | feat/brokerd-write-api | ✅ slugged (2nd `feat`) |
| PhenoShared-space/feat/wtree | feat/launchd-service | ⚠️ unslugged `feat/wtree` |
| PhenoShared-space/fix/bounded-lease-lock/wtree | fix/bounded-lease-lock | ✅ |
| PhenoShared-space/fix/nonblocking-lease-lock/wtree | fix/nonblocking-lease-lock | ✅ |
| PhenoShared-space/fix/wtree | fix/windows-job-object | ⚠️ unslugged `fix/wtree` |
| temp/build-merged | build/merged-tls | ❌ **volatile `temp/`** |
| temp/ca-pinning | feat/mcp-ca-pinning | ❌ volatile |
| temp/coverage-restructure | ci/coverage-per-crate | ❌ volatile |
| temp/fmtcheck-main | fix/fmt-perf-core | ❌ volatile |
| temp/guard-base | fix/guard-merge-base | ❌ volatile |
| temp/lazy-acquire | fix/lazy-acquire | ❌ volatile |
| temp/lease-identity | fix/lease-owner-identity | ❌ volatile |
| temp/pii-base | **detached HEAD** @ 8760a379a | ❌ volatile + detached |
| temp/pins-clean | chore/pin-action-refs-clean | ❌ volatile |
| temp/remeasure | ci/remeasure-baselines | ❌ volatile |
| temp/windows-ci | ci/windows-job-object-test | ❌ volatile |

Note two `CodeProjects/temp/*` vs `CodeProjects/Phenotype/repos/PhenoShared-space/*` spellings both appear for the space root (`phenotype` lowercase vs `Phenotype`). macOS APFS is case-insensitive so both resolve, but a case-sensitive Linux node would see two different trees.

**Risk:** 9 worktrees live in `~/CodeProjects/temp`, which policy declares disposable and wipe-on-reboot. `temp/lazy-acquire` (8 ahead, active) and `temp/remeasure` (7 ahead) hold live work in a directory that may be deleted.

---

## 6. Hygiene verdict + concrete per-class actions

**Verdict: unhealthy by ancestry, but only ~40% of the apparent backlog is real.** The repo looks like it has 68 stranded branches; in reality there are 16 foreign-history snapshots (not branches), 1 fully landed branch, 11 stale ones (mostly pose-roulette / dependabot), and roughly 38 branches carrying genuine unmerged patches. The reporting defect is that squash merges make `merge-base --is-ancestor` useless, so nothing is ever recorded as merged.

Additional structural finding: **`origin/main` is 1,213 commits ahead of the common base of the entire `wrapup/*` family.** Main absorbed a large body of work in one step; the wrapup branches never rebased onto it, so they will each present as "498 ahead / 1213 behind" forever.

### Per-class actions

| Class | Count | Action |
|---|---|---|
| MERGED (ancestry) | 0 | Nothing. Do not use ancestry as the merge test in this repo; add a `git cherry`-based script to repo hygiene tooling. |
| LANDED (`KooshaPari-patch-1`) | 1 | Delete remote branch. Zero unique patches. |
| ABSORB-SNAPSHOT (`wrapup/*`, `snapshot/orphan/*`) | 16 | Do **not** attempt to merge. For each: confirm the absorbed repo's content already exists in `crates/` or `docs/absorbed-from-*` on main, record the verdict, then delete the branch. `wrapup/phenokits-commons` (19 unique / 60 equiv) and `wrapup/phenoforge` (58/61) are the only two where selective content diff is worth a pass. |
| ARCHIVE (`archives/*`, `chore/archives-*`) | 2 | Land or keep permanently. `archives/recovered-worktrees-20261106` is 5,448 files / +777,924 lines — if it is genuinely the recovery archive of record, it should live in a tagged release or external artifact store, not a branch behind main. |
| STALE (11) | 11 | `pose-roulette/build`, `tmp-pose-ci`, `feat/pose-roulette-mobile`, `docs-audit-2026-10-17` → pose-roulette work is 2026-09 / 10 and 456 behind; consolidate into one branch or delete. Dependabot ×3 (2026-09-17, 546 behind) are superseded — close. `temp-docs-push`, `merge-pheno-data`, `fix/build-dashboard-stub` (all 2026-09-15, 600+ behind) are one-commit experiments → delete. `rescue/e-drive-2026-10-29/tags/v0.1.0` (2026-03-29, 1,210 behind) → verify then delete. `docs/chat-shaping-…` (2026-09-18) → delete. |
| STRANDED-ACTIVE (38) | 38 | Triage in 3 tiers. **Tier 1 — merge now (≤4 behind):** `ci/remeasure-baselines` (2), `fix/lazy-acquire` (1), `fix/cargo-taplo-native-member` (4), `fix/guard-claim-false-positive` (1), `fix/fmt-perf-core` (1), `layer/governance-happy-path-claims` (0), `governance/happy-path-claims` (0, duplicate — delete one), `integration/absorbed-20261109` (19). **Tier 2 — rebase then merge:** `feat/brokerd-write-api`, `docs/researchledger-recovery-20261012`, `fix/coverage-ratchet-floor`, `chore/pin-action-refs`, `wrapup/pheno-20261108`, `verify/final`, `chore/remove-dead-integration-crate`. **Tier 3 — decide-keep-or-kill (behind >280):** the `chore/*-2026101x`, `ci/reconcile-action-pins`, `instinct/*`, `KooshaPari-patch-2`, `docs-audit-2026-10-17`, `fix/trunk-action-immutable-pin-20261013`, `fix/duplicate-cargo-toml-tables` (573 behind) — most describe CI state that main has already moved past. |
| Local `: gone` landed (26) | 26 | `git branch -d` (safe delete; `-D` is policy-blocked). Zero unique patches. |
| Local `: gone` unlanded (5) | 5 | Promote: `fix/cargo-audit-4-vulns`, `feature/pii-sweep-path-repair`, `fix/pii-sweep-broken-workflow-refs`, `feat/launchd-service`, `feat/brokerd-write-api-squashed`. Re-push and open PRs; do not delete. |
| Local alias `fix/trunk-config` | 1 | Points at `fix/disabled-workflow-annotation`; landed. Delete. |
| Local 0-ahead (3) | 3 | `build/merged-tls`, `chore/pin-action-refs-clean`, `fix/nonblocking-lease-lock` — delete plus their worktrees. |
| Local `main` ahead 1 | 1 | Reconcile `c682ec2d8` ("63 scripts") against landed `#823` ("28 scripts"); either rebase-and-push the broader variant or drop it. |
| Mis-tracked local branches | 2 | `feat/mcp-ca-pinning` (0 ahead) delete; `feat/promote-nontq-perf-core-hwledger` (3 unique) re-track and push. |
| Worktrees in `~/CodeProjects/temp` | 9 | Migrate the 2 live ones (`lazy-acquire`, `remeasure`) to `PhenoShared-space/<type>/<slug>/wtree` via `git worktree move`; leave the dead ones to `git worktree prune`. |
| Unslugged `feat/wtree`, `fix/wtree` | 2 | Rename to `<type>/<branch-slug>/wtree` per layout policy. |

### Do-not-do list (carried from policy)

- No `git push --force`, no `git reset --hard`, no `git branch -D`, no `git clean -fd`.
- Do not `git worktree` **move** a linked worktree with `mv` — use `git worktree move` then `git worktree prune`.
- Do not delete `wrapup/*` snapshots before their absorbed content is confirmed present on main; they are the only copies of some foreign histories.

---

*Evidence commands: `git branch -r --format=…`, `git rev-list --left-right --count`, `git merge-base --is-ancestor`, `git merge-base origin/main <b>`, `git cherry origin/main <b>`, `git diff --name-only`, `git branch -vv`, `git branch --format`, `git worktree list`, `git rev-list --max-parents=0`. All read-only. Report written outside the repo at `PhenoShared-space/analysis/2026-11-10-forensic/E-branch-inventory.md`.*
