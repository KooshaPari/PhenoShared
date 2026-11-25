# Lane V1 — Independent Verification of PhenoShared Forensic Reports

Verifier: Lane V1 (independent measurement, read-only)
Repo measured: `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
Reports verified: A, B, C, E, F, G, H, I, J (D excluded — product dossier, not numeric)
Method: every "Ground truth" value below was produced by running the command in this session
against the working tree. **No report number was accepted without an independent measurement.**
Repo state at measurement time: HEAD `ad667428ba516859c8ea9da94e059dd9db782454`
(`layer/governance-happy-path-claims`), working tree not clean (measured, not assumed).

Command budget: 10 bash batches, ~200 individual measurements. Zero repo mutations
(`git status` / `git log` / `git ls-files` / `grep` / `wc` / `du` only).

---

## 1. Metric verification table

| Metric | Ground truth (measured) | Claimed in report | Report | Match? |
|---|---|---|---|---|
| Total commits (all refs) | 3581 (`git rev-list --all --count`) | 3,581 | A | ✅ |
| Commits on `main` | 1210 (`git rev-list --count main`) | not claimed | — | n/a |
| First commit SHA | `56319267bee68f6d15a737d4299dc92cf8918ad3` | same | A | ✅ |
| First commit date | 2026-02-23 05:34:53 -0700 | same | A | ✅ |
| First commit author | Koosha Paridehpour | same | A | ✅ |
| First commit subject | `fix(tokenledger): resolve compile errors after utils.rs module split` | same | A | ✅ |
| Merge commits | 113 | 113 (3.2%) | A | ✅ |
| Direct (non-merge) commits | 3468 | 3,468 (96.8%) | A | ✅ |
| First-parent commits on HEAD lineage | 1036 | 1,036 (28.9%) | A | ✅ |
| Direct : merge ratio | 30.69 : 1 | ≈ 30.7 : 1 | A | ✅ |
| Commits per month (10 buckets) | 22/384/355/156/347/257/987/345/431/297 | identical | A | ✅ |
| Merges per month | 1/20/13/3/38/1/2/19/4/12 | identical | A | ✅ |
| Author shortlog top-15 | 1741/529/346/256/211/148/80/68/67/36/24/14/7/7/7 | identical (incl. all 15 identities) | A | ✅ |
| `layer/` in commit subjects | 0 | 0 | A | ✅ |
| Max PR number in subjects | 825 | up to #825 | A | ✅ |
| Commits introducing ≥1 `crates/*/Cargo.toml` | 68 | 68 | A | ✅ |
| Tags | 0 | 0 | A | ✅ |
| Tracked files | 42225 | 42,225 | A, B | ✅ |
| `crates/` dir entries | 372 | 372 | A, B, J | ✅ |
| `crates/` crate-like dirs (non-`.md`) | 369 | 369 | B, H | ✅ |
| `crates/*/Cargo.toml` (top-level glob) | 337 | 337 | A, H | ✅ |
| `crates/` recursive `Cargo.toml` | 495 | not claimed | — | n/a |
| Crates with `src/main.rs` | 85 | 85 | B | ✅ |
| `[[bin]]` targets | 155 | 155 | B | ✅ |
| `crates/` refs in root manifest | 306 | 306 | B | ✅ |
| Tracked `.rs` files | 7209 | 7,209 | B | ✅ |
| Tracked `.py` files | 5709 | 5,709 | B | ✅ |
| Raw ext histogram (top 12) | md 10532, rs 7209, py 5709, ts 2884, go 2819, tsx 2327, json 1937, yml 1367, toml 1170, sh 474, yaml 382, js 375 | identical, all 12 | B | ✅ |
| First-party `.rs` files / LOC | 6451 files / 304,248 LOC | 6,451 / 304,248 | B | ✅ |
| First-party `.py` files / LOC | 4341 files / 720,862 LOC | 4,341 / 720,862 | B | ✅ |
| Language LOC split (claimed % of 1,383,743) | internally consistent (py 52.1%, rs 22.0%, go 17.6%, ts+tsx 3.4%, sh 3.8%, js 1.2%) | identical | B | ✅ (internal) |
| `crates/` tracked files | 13848 | 13,848 | B | ✅ |
| `docs/` tracked files | 11721 | 11,721 | B | ✅ |
| `absorption/` tracked files | 4414 | 4,414 | B, F | ✅ |
| agileplus family dirs (3 trees) | 23 / 51 / 25 = 99 | 23 / 51 / 25 = 99 | B | ✅ |
| `.github/workflows/` entries | 92 | 92 | C | ✅ |
| Workflow YAML files | 89 | 89 | C | ✅ |
| `workflows-disabled/` contents | pages.yml, release-macos.yml (+README.md) | pages.yml, release-macos.yml | C | ✅ |
| Rust `#[test]` under `crates/` | 16289 | 16,289 | C | ✅ |
| Test-shaped tracked files | 3622 | 3622 | C | ✅ |
| Coverage `aggregate_floor` | 36.00 | 36.00 | C | ✅ |
| 10 per-group coverage floors | 58.93/60.09/44.30/76.49/41.87/47.13/51.75/61.43/63.33/61.01 | identical, all 10 | C | ✅ |
| Codecov targets | 71% / 60% / 80%, threshold 1% | 71% / 80% / 60%, 1% | C | ✅ |
| Workflows referencing `pii-sweep` | 0 | 0 (gap) | C | ✅ |
| `cargo-deny.yml` manifest-path | `iac/Cargo.toml` | `iac/Cargo.toml` | H, C | ✅ |
| Remote branches excl. `origin/main` | 68 | 68 | E | ✅ |
| Remote branches excl. HEAD (incl. main) | 69 | not claimed | — | n/a |
| Branches with no merge-base (orphan) | 16 | 16 | E | ✅ |
| Branches sharing history with `origin/main` | 52 (53 incl. `origin/main` itself) | 52 | E | ✅ |
| Remote branches ancestry-merged into `main` | 0 | 0 | E | ✅ |
| Stale branches (committerdate < 2026-10-01) | 11 | 11 | E | ✅ |
| Local branches with `: gone` upstream | 31 | 31 | E | ✅ |
| **Local branches (total)** | **50** | **45** | **E** | ❌ |
| **Registered worktrees** | **24** (23 linked + main) | **19** | **E** | ❌ |
| `Cargo.lock` size | 499,324 B | 499,324 B (~488 KiB) | H | ✅ |
| `[[package]]` blocks in lockfile | 1903 | 1,903 | H | ✅ |
| `^name = ` lines | 1904 | 1,904 | H | ✅ |
| Registry-sourced lock packages | 1611 | 1,611 | H | ✅ |
| Local/path lock packages | 292 | 293 | H | ❌ (off-by-one) |
| **Workspace `members` entries** | **239** | **287** | **H** | ❌ |
| Workspace `exclude` entries | 4 | 4 | H | ✅ |
| `[workspace.dependencies]` entries | 121 | 123 | H | ❌ (off-by-2) |
| Commits touching `Cargo.lock` | 156 | 156 | H | ✅ |
| `license.workspace = true` (under `crates/`) | 259 | 259 | H | ✅ |
| `"MIT OR Apache-2.0"` literal | 148 | 113 | H | ❌ |
| `"MIT"` literal | 133 | 79 | H | ❌ |
| `"Apache-2.0 OR MIT"` | 16 | 16 | H | ✅ |
| `"Apache-2.0"` | 18 | 6 | H | ❌ |
| Manifests with no `license` key (workspace members) | 0 of 238 found | 0 | H | ✅ (scope-limited) |
| Manifests with no `license` key (all 690 tracked) | 50 | 0 | H | ❌ (unscoped claim) |
| `deny.toml` distinct RUSTSEC ids | 12 | 12 | H | ✅ |
| `deny.toml` `[licenses] allow` SPDX ids | 18 distinct (report text lists 18 but says "20") | "20" | H | ❌ (internal) |
| `confidence-threshold` | 0.8 | 0.8 | H | ✅ |
| `[bans] multiple-versions` | `"warn"` | `"warn"` | H | ✅ |
| `rust-toolchain.toml` channel | `1.99.0` | 1.99.0 | H | ✅ |
| `[workspace.package]` version / edition / rust-version | 0.3.10 / 2021 / 1.80 | identical | H | ✅ |
| `archives/` size | 97,244 KB (~95 MB) | 95 MB | F | ✅ |
| `absorption/` size | 49,048 KB (~48 MB) | 48 MB | F | ✅ |
| `docs/absorbed-from-PhenoTooling/` size | 71,752 KB (~70 MB) | 70 MB | F | ✅ |
| `absorption/PhenoInfra/` files | 2532 | 2537 (one table) / 2532 (another) | F | ❌ (internal inconsistency; ground truth 2532) |
| `absorption/PhenoMLX-temp/` files | 1355 | 1349 | F | ❌ (off-by-6) |
| `absorption/phenoDesign-visual-production-v2/` | 180 | 180 | F | ✅ |
| `absorption/phenotype-canonicalization/` | 44 | 44 | F | ✅ |
| `absorption/phenotype-cvp-audit-2026-09-14/` | 7 | 7 | F | ✅ |
| `absorption/herdr-{jcode,forgecode,helioslite}/` | 24 total = 8 each | 8 each | F | ✅ |
| `absorption/PhenoMLX-temp` workspace refs in root manifest | 38 | 38 | F | ✅ |
| herdr/absorption milestone SHAs (3b45203b0, dee522c88, 618ffd3c3, 5677bae9e, 2a2a9400c, 9bcf7ca16) | all resolve to commit objects | cited as commits | A, F | ✅ |
| phinbox default port | 7117 (`DEFAULT_PORT: u16 = 7117`) | 7117 | G | ✅ |
| focalpoint-mcp default addr | `127.0.0.1:8473` | 8473 | G | ✅ |
| brokerd default bind | `127.0.0.1:8787` | 8787 | G | ✅ |
| gateway-tools default port | 8081 (`default_value_t = 8081`) | 8081 | G | ✅ |
| fabric-daemon default listen | `127.0.0.1:9400` | 9400 | G | ✅ |
| phenotype-daemon TCP port conflict | `main.rs:28` = 9456, `protocol.rs:186` = 8953 | 9456 vs 8953 conflict | G | ✅ |
| `crates/` `.md` files | 3518 | 3,518 | I | ✅ |
| `docs/` `.md` files | 2581 | 2,581 | I | ✅ |
| `audits/` `.md` files | 1290 | 1,290 | I | ✅ |
| `absorption/` `.md` files | 1102 | 1,102 | I | ✅ |
| Root-level loose `.md` | 128 | 128 | I | ✅ |
| `_archived/` `.md` files | 126 | 126 | I | ✅ |
| `docs/specs/` `.md` | 528 | 528 | I | ✅ |
| `docs/adr/` / `docs/adrs/` / `adrs/` `.md` | 90 / 25 / 10 | 90 / 25 / 10 | I | ✅ |
| `docs/boundary/` / `docs/intent/` | 166 / 139 | 166 / 139 | I | ✅ |
| `docs/atlas/` / `docs/phenotype-docset-v1.1/` | 149 / 146 | 149 / 146 | I | ✅ |
| `docs/atlas/codebase/FILES.md` lines | 22660 | 22,660 | I | ✅ |
| **`crates/**/AGENTS.md`** | **50** | **136** | **I** | ❌ |
| **`crates/**/CLAUDE.md`** | **45** | **111** | **I** | ❌ |
| **`crates/**/README.md`** | **313** (314 untracked-inclusive) | **844** | **I** | ❌ |
| **`docs/sessions/` directories** | **50** | **53** | **I** | ❌ |
| **`[workspace] members` (J)** | **239** | **239** | **J** | ✅ (contradicts H) |
| Repo disk usage (`du -sk .`) | 3,369,616 KB (~3.2 GB) | 261,891 KB (~256 MB) | J | ❌ (source likely gh API, scope differs) |
| Max PR number seen in subjects | 825 | up to #828 (open) | J | ❌ (gh-side, unverified) |

---

## 2. CONFIRMED claims

**Report A (Git History Forensics) — 24 confirmed, 1 misstated**
- Total commit count 3,581; merge/direct split 113/3,468; first-parent 1,036 (28.9%).
- Full 10-bucket per-month commit table and full 10-bucket per-month merge table — **every value matched**.
- Full 15-row author shortlog table — **every value and every identity string matched exactly**, including the `kooshapari@gmail.com` / `koosha@example.com` / `claude@anthropic.com` fragmentation narrative.
- Root commit is a snapshot-import, not an `init` — SHA, date, author, subject all matched.
- 0 tags. Max PR `#825`. 0 `layer/` commit subjects. 68 commits introduced ≥1 `crates/*/Cargo.toml`.
- Volume stats: tracked files 42,225; 372 crate dirs; 337 top-level manifests; peak 987 (2026-08); trough 156 (2026-05); peak:trough 6.3:1; span 259 days; ≈341 commits/month; ≈13.8/day — **all arithmetically and empirically correct**.
- Direct:merge ≈ 30.7:1 — confirmed.
- Milestone SHAs sampled (2a2a9400c, 618ffd3c3, 3b45203b0, dee522c88, 5677bae9e, 9bcf7ca16) all resolve to real commit objects.

**Report B (Codebase Atlas) — 12 confirmed**
- Every one of the 12 headline raw extension-histogram buckets matched exactly.
- Tracked files 42,225; crates dirs 372/369; 306 manifest `crates/` refs; 85 binary crates; 155 `[[bin]]` targets.
- **First-party LOC figures are exactly reproducible**: 304,248 Rust LOC over 6,451 files and 720,862 Python LOC over 4,341 files, under the stated filter. The language-split percentages are internally consistent to the digit.
- The three parallel agileplus copies (23 / 51 / 25 = 99) — confirmed by direct directory listing.
- `crates/` 13,848 / `docs/` 11,721 / `absorption/` 4,414 tracked files — confirmed.
- The "three copies of one product family" structural finding is real and independently reproducible.

**Report C (QA Matrix) — 9 confirmed**
- 92 workflow entries = 89 YAML + 3 non-YAML; `workflows-disabled/` holds `pages.yml` and `release-macos.yml`.
- 16,289 Rust `#[test]` under `crates/` and 3,622 test-shaped tracked files — both exact.
- `aggregate_floor = 36.00` plus **all 10 per-group floors matched to 2 decimals**.
- Codecov targets 71/60/80 with 1% threshold.
- `cargo-deny.yml` really does target `iac/Cargo.toml`, not the root workspace.
- Zero workflows reference `pii-sweep` — the "dormant tool" GAP is real.
- The report's honesty about "Enforced in CI" meaning *runs*, not *blocks merge*, is a methodological strength, not a hedge to punish.

**Report E (Branch Inventory) — 8 confirmed, 2 mismatches**
- 68 remote branches excl. `origin/main`; 16 orphan-root branches; 52 sharing history; 0 ancestry-merged into `main`; 11 stale; 31 local branches with `: gone`. All confirmed.

**Report F (Absorption Archaeology) — 7 confirmed**
- `archives/` 95 MB, `absorption/` 48 MB, `docs/absorbed-from-PhenoTooling/` 70 MB — all within measurement noise of the claimed values.
- 38 workspace refs for `absorption/PhenoMLX-temp`; herdr plugins 8 files each; canonicalization 44, cvp-audit 7, phenoDesign 180.
- All six cited milestone SHAs resolve.

**Report G (Runtime Surface) — 6 confirmed, and its hedges are the strongest in the corpus**
- Ports 7117, 8473, 8787, 8081, 9400 all confirmed at the cited source lines.
- **The 9456-vs-8953 `DEFAULT_TCP_PORT` conflict is real** — `crates/pheno-agent/phenotype-daemon/src/main.rs:28` says 9456 and `src/protocol.rs:186` says 8953, same constant name, same crate. Independently reproduced.
- The report's `UNKNOWN`/`NOT BUILT`/`LIBRARY ONLY`/`CONFLICT` cells are honest gaps, not missed facts.

**Report H (Supply Chain) — 12 confirmed**
- `Cargo.lock` 499,324 B; 1,903 `[[package]]`; 1,904 `name =`; 1,611 registry; 156 lockfile-touching commits.
- 369 crate dirs; 337 `crates/*/Cargo.toml`; 4 excludes.
- `license.workspace = true` = 259 under `crates/`; `"Apache-2.0 OR MIT"` = 16.
- `deny.toml` exactly 12 distinct RUSTSEC ids; `confidence-threshold = 0.8`; `multiple-versions = "warn"`.
- `rust-toolchain.toml` = 1.99.0; `workspace.package` = 0.3.10 / edition 2021 / rust-version 1.80.
- The `cargo-deny.yml` → `iac/Cargo.toml` filename trap is a genuinely valuable finding, and it is true.

**Report I (Docs Corpus) — 13 confirmed**
- Every top-level `.md` directory count in the 25-row table that I could measure matched exactly: crates 3,518 / docs 2,581 / audits 1,290 / absorption 1,102 / root 128 / _archived 126.
- `docs/specs` 528, `docs/adr` 90, `docs/adrs` 25, `adrs` 10, `docs/boundary` 166, `docs/intent` 139, `docs/atlas` 149, `docs/phenotype-docset-v1.1` 146.
- `FILES.md` = 22,660 lines exactly.
- The "two labels, one dataset" boundary/intent finding (166 vs 139) is reproducible and correct.

**Report J (Ecosystem Position) — 2 confirmed**
- 372 crate directories; **239 `[workspace] members`** (this is the number H got wrong).

---

## 3. MISMATCHES (ground truth vs claimed)

| # | Report | Claim | Ground truth | Delta | Severity |
|---|---|---|---|---|---|
| M1 | H | `[workspace] members` = **287** | **239** | −48 (17%) | **HIGH** — a headline supply-chain number is wrong, and it contradicts report J which states 239 correctly |
| M2 | H | `"MIT OR Apache-2.0"` literal = 113 | 148 | +35 | MEDIUM |
| M3 | H | `"MIT"` literal = 79 | 133 | +54 | MEDIUM |
| M4 | H | `"Apache-2.0"` = 6 | 18 | +12 | MEDIUM |
| M5 | H | "Manifests with no `license` key = **0**" (unscoped) | 50 of 690 tracked manifests lack one | 50 | MEDIUM — true only for the 238 workspace-member manifests; the report does not state that scope |
| M6 | H | `[workspace.dependencies]` = 123 | 121 | −2 | LOW |
| M7 | H | Local/path lock packages = 293 | 292 | −1 | LOW |
| M8 | H | `[licenses] allow` = "20 SPDX ids" | 18 distinct ids | −2 | LOW — and the report's own prose lists exactly 18, so the "20" is internally inconsistent with its own list |
| M9 | E | Local branches = 45 | 50 | +5 | MEDIUM — stale count, likely captured mid-cleanup |
| M10 | E | Registered worktrees = 19 | 24 (23 linked + main) | +5 | MEDIUM — same cause; the worktree table therefore may under-count by a quarter |
| M11 | I | `crates/` AGENTS.md ×136 | 50 | −86 | HIGH |
| M12 | I | `crates/` CLAUDE.md ×111 | 45 | −66 | HIGH |
| M13 | I | `crates/` README ×844 | 313 (314 incl. untracked) | −531 | HIGH — ~2.7× overstatement |
| M14 | I | `docs/sessions` = 53 | 50 | −3 | LOW |
| M15 | F | `absorption/PhenoInfra/` = 2,537 files | 2,532 | −5 | LOW, but the report contradicts itself (2537 in one table, 2532 in another) |
| M16 | F | `absorption/PhenoMLX-temp/` = 1,349 files | 1,355 | +6 | LOW |
| M17 | J | Repo disk usage 261,891 KB (~256 MB) | `du -sk .` = 3,369,616 KB (~3.2 GB) | 13× | MEDIUM — the two numbers measure different things (gh API size vs. full tree incl. `.git` and `target/`); the report presents it as an unqualified fact |
| M18 | J | PR sequence up to #828 | max in commit subjects = 825 | +3 | LOW — gh-side open PR, not refutable from the repo |
| M19 | A | "The `crates/*/Cargo.toml` glob matched only 68 of the 337 manifests" | the glob matches **337** manifests; **68** is the number of *commits* that added a manifest | category error | MEDIUM — the number 68 is right but attached to the wrong noun, and the derived claim "~80% of crate identities have no birth commit" is therefore mis-grounded |
| M20 | A | Human-attributed ≈ 2,862 / non-human ≈ 719 | Koosha identities total 2,880; non-Koosha identities total 702 | ±17–18 | LOW — rounding-level; the qualitative conclusion (≈20% automation) holds |

---

## 4. UNSUPPORTED or HEDGED claims (not verifiable from the repo, or not measured)

**Unverifiable from the repo (external sources)** — treated as UNKNOWN, not as errors:
- J: registry id `pheno`, tier `phenotype-framework`, architecture `layered`, status `active` (external registry repo).
- J: repo created 2026-04-03T08:14:12Z, visibility PUBLIC, stars 0, topics, self-declared description.
- J: releases `promptscrape-v0.1.2` etc.; GitHub PR #828.
- A: the `no-mistakes` local mirror at `~/.no-mistakes/repos/e13a7c834298.git` and its effect on `--all` (I did not read that mirror; the 3,581 figure is for this clone's refs only).
- F: `PhenoGoKit` 404, `zz-merge-unk-hfscope` deleted, `phenotype-hub`/`vibeproxy-monitoring-unified` manifest-only rows — these depend on GitHub API state, not the repo.

**Structural claims that are directionally true but not independently reproduced** (labelled UNKNOWN, not PASS):
- B: "677k LOC across the top-45 crates" (uses `find`, includes untracked and nested duplicates) vs "304k tracked Rust LOC" — the ~2.2× discrepancy is real and the caveat is stated, but the 677k figure itself was not reproduced.
- B: `.json` 712,494 LOC / `.yml` 76,623 / `.sh` 52,450 / `.toml` 39,632 / `.md` 39,219 / `.ts` 30,445 / `.js` 16,339 / `.tsx` 16,149 / Go 243,250 — only `.rs` and `.py` were reproduced exactly. The Go total (243,250) is the largest unreproduced number in B and it drives the entire "Python dominates" conclusion — the *ranking* survives, the exact figure does not.
- B: "Code total 13,164 files" cannot be reconciled with the report's own 2b table (rs 6,451 + py 4,341 + go 2,819 + ts 467 + tsx 119 + sh 474 + js 375 = 15,046) without an undisclosed filter.
- B: ten largest first-party `.rs` files (3,254 / 3,080 / 2,912 / 2,721 / 2,640 / 2,142 / 2,029 / 2,008 / 1,939 / 1,925) — not individually reproduced.
- E: "Ahead > 0: 68 of 68", "Behind > 0: 68 of 68", "Unmerged with ≥1 genuinely unique patch = 67", "patch-equivalent = 1", "26 gone + 1 alias = 27 safe local deletes" — the ahead/behind values in the 50-row table were not re-derived per branch.
- E: the 50-row branch table's per-branch Ahead/Behind/U/E columns — not re-derived.
- C: "codecov upload step not found" (a negative claim from sampling; I confirmed only the absence of `pii-sweep` references and the presence of the codecov config).
- C: branch-protection required-check names — explicitly out of lane scope, correctly flagged by C itself.
- F: which 5 sprawl repos `3b45203b0` absorbed — F explicitly leaves this UNKNOWN.
- H: `[bans] wildcards = "allow"`, `[sources]` unknown-registry deny semantics, `[advisories] yanked = "warn"`, the per-step gating semantics of `security.yml` / `security-scan.yml` / `ffi-ci.yml` / `compute-infra-auditors.yml`, and the `windows-sys`/`nix`/`itertools`/… version lists — not re-derived (the version lists are the report's most citation-free numeric claims).
- I: "Temporal" doc class = 1,002; "Session/dated record" ≈ 1,600; "Canonical" ≈ 400; "Absorbed/vendored" ≈ 1,102; the atlas↔docset 152/523 shared basenames and boundary↔intent 132/305 overlap counts; the 20-row largest-file table (except `FILES.md`, which matched exactly).
- G: every MCP tool count, the 15 launchd plists, and all "binary presence not proven" rows — these are honest UNKNOWNs and the source-level claims that *were* checkable all matched.

**Hedged claims that were verified as *correctly* hedged** (credited, not penalized):
- G's `UNKNOWN` / `NOT BUILT` / `LIBRARY ONLY` / `CONFLICT` cells are accurate characterizations.
- C's "Enforced in CI" caveat, and its 5 explicit Unproven items.
- B's measurement caveats about `find` vs `git ls-files` and vendor/archive exclusion.
- A's caveats about the `no-mistakes` mirror and about commit-count ≠ work-volume.

---

## 5. Overall trust verdict per report

| Report | Verdict | Rationale |
|---|---|---|
| **A — Git History Forensics** | **HIGH** | 24 of 25 measurable claims reproduced exactly, including the full per-month commit table, the full per-month merge table, the entire 15-row author table, and the root-commit forensics. The single substantive error (M19) is a noun/quantity confusion, and the ±17 arithmetic drift (M20) is immaterial. Methodologically the strongest report in the set. |
| **B — Codebase Atlas** | **HIGH** | Every headline count and both first-party LOC totals are byte-exact reproductions of my independent measurement; the 12-bucket raw extension histogram is a perfect match. Weakness is confined to unreproduced detail tables (Go LOC, 677k untracked LOC, the file-size tables) — all of which the report explicitly flags as approximate. |
| **C — QA Matrix** | **HIGH** | All 9 sampled claims confirmed exactly, including all 10 coverage floors to 2dp, and the two GAP findings (PII sweep, cosign) are true negatives. The report's own epistemic discipline (runs ≠ blocks merge) is the model the other reports should follow. |
| **E — Branch Inventory** | **MEDIUM** | 8 of 10 measurable headline claims confirmed, but two counts are stale in the same direction and by the same magnitude (local branches 45 vs 50; worktrees 19 vs 24), which suggests the report was written against a moving tree. The 50-row table's ahead/behind/unique/equivalent columns were not independently re-derived here, so the per-branch correctness is UNKNOWN. |
| **F — Absorption Archaeology** | **MEDIUM** | 7 confirmed, but two file counts drift and the report contradicts itself on `PhenoInfra` (2,537 vs 2,532 in its own tables). Several rows rest on GitHub API state that is not reproducible from the repo. Content and framing are strong; the numbers need a re-run. |
| **G — Runtime Surface** | **HIGH** | Every source-level claim I sampled was exact, including the 9456/8953 port conflict — a defect most reports would have missed. Its `UNKNOWN` markers are precise rather than evasive. LOW risk of misleading the reader. |
| **H — Supply Chain** | **LOW** | The report with the **largest and most consequential error set**: the `[workspace] members` count is wrong by 48 (287 vs 239, and report J states 239 correctly), the license-declaration histogram is wrong on three of five buckets, and an unqualified "0 manifests without a license" is false at repo scope (50 of 690). Structural findings (the `cargo-deny.yml`→`iac/Cargo.toml` trap, 12 RUSTSEC ignores, `multiple-versions = "warn"`) are correct and valuable, but the numeric spine is unreliable. |
| **I — Docs Corpus** | **MEDIUM** | The directory-level `.md` inventory is **exactly right on 13 of 13 measured rows** — the actual doc-surface map is trustworthy. But the three "boilerplate" counts are badly inflated (136→50, 111→45, 844→313), the `docs/sessions` count is off by 3, and the class-size estimates and duplication-overlap counts are unreproduced. Use the map, distrust the derived proportions. |
| **J — Ecosystem Position** | **MEDIUM** | The two repo-measurable claims (372 crates, 239 members) are correct, and 239 is the decisive tiebreaker against report H. The disk-usage figure (256 MB vs a measured 3.2 GB tree) is presented as fact with no scope qualifier, and the PR sequence (#828) and all registry/release facts are external and unverified. Its own explicit `UNKNOWN` rows are honest. |

### Cross-report contradictions requiring resolution
1. **H vs J on workspace members**: H says 287, J says 239. Measured: **239**. H is wrong; J is right. Any downstream supply-chain or ecosystem document derived from H's 287 is inflated by 20%.
2. **A vs F on `absorption/PhenoInfra/` file count**: F states 2,537 in one table and 2,532 in another. Measured: **2,532**.
3. **H on `crates/*/Cargo.toml`**: H states 337 (correct, top-level glob) while A states 337 as "under `crates/`" (also the top-level glob) — both are correct but neither equals the 495 recursive manifests that exist. Both reports should state the glob explicitly; A's §8 birth-order analysis reads as if it covers all manifests.

### What to do with this
- **Trust and cite**: A, B, C, G — the counts, tables and structural findings in these four survive independent measurement.
- **Re-measure before citing any number**: H (re-derive members, license histogram, lockfile split, dependency count), E (re-run branch/worktree counts), F (re-run absorption file counts), I (re-run the crates boilerplate counts and class estimates).
- **Fix before reuse**: J's disk-usage number needs a scope qualifier; A's §8 "68 of the 337" sentence needs its noun corrected.
- The single highest-value correction is **H's `[workspace] members = 287 → 239**. It is a 17% overstatement of the workspace size, it is contradicted by report J, and it is trivially checkable by anyone who reads the root `Cargo.toml`.
