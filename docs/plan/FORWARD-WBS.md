# Forward WBS — PhenoShared

**Written:** 2026-09-19
**Basis:** measured only. Every number here was produced by a command whose
output is cited; anything unverified is labelled. Supersedes the "next steps"
prose in `LONG-TERM-WBS.md`, which remains the epic-level contract.

Task granularity follows the 10-minute rule: leaf tasks are ~10 minutes.

---

## 0. Verified state of the world (inputs to the plan)

> **2026-09-27 addendum (CI cold-runner campaign):** the port of the deleted
> `KooshaPari/nanovms` git dep into `crates/nvms-manifest` (821cc1cb) removed
> the last git dependency and unblocked three gates. Evidence landed today:
> `cargo-deny.yml`, `ci.yml` **green** on 762102b1 (run head_sha query);
> `deny.yml` both jobs green on dispatched run 36342489246 (go-audit fix
> ec1682d5: go 1.26 + govulncheck@v1.8.0). Linux-build blockers fixed with
> evidence per commit: glib-sys (1c838b69 GTK3 apt deps), cfg(linux) probe
> branch (9a06d2c2, cross-target `cargo check --target x86_64-unknown-linux-gnu`
> exit 0), fabric-tray `-lxdo` link (dc932ff0 libxdo-dev). iac advisory/license
> gate (762102b1) verified locally under cargo-deny 0.20.2: `advisories ok,
> bans ok, licenses ok, sources ok` (iac full `check`, exit 0).
>
> **fmt correction:** E1.3.2's "done" was overstated — validation had run
> without `--all`. Measured 2026-09-27: `cargo fmt --all --check` at HEAD
> = 152 files failing; at the E1.3.2 commit itself = 326 (same stable
> rustfmt 1.9.0-stable / rustc 1.97.1, `rustfmt.toml` unchanged since
> 09-24 — so it is formatting debt, not toolchain drift). Full
> `cargo fmt --all` reformat landed; check now exit 0. Note
> `cargo +nightly fmt --all --check` also fails (nightly-only options are
> active there); the pin (`rust-toolchain.toml` = stable) is the standard.
>
> **2026-09-29 addendum (clippy -D remediation + E1.6 green):** quality-gate
> went RED on f8a891c4 (cargo-check job = cold clippy `-D warnings`).
> Workspace-wide measure: **166 warning lines** = 41 autofixable files +
> 46 manual sites across ~25 files. Remediation landed as `2fc733e8`
> (54 files: `cargo clippy --workspace --all-targets --locked --
> -D warnings` exit 0; `cargo fmt --all --check` exit 0). First full-green
> `make check` (E1.6) 2026-09-29 20:29 UTC: fmt 0 + clippy 0 + test-unit
> **79 targets, 0 failed**, after closing 8 pre-existing unit-test failures
> CI never gated (ci.yml's cargo test step is advisory: `|| echo
> "::warning::test failures (advisory)"`): 6 in `98263c03` (two malformed
> fixture literals; `OMNIROUTE_BASE_URL` host-env leak whose panic poisoned
> the static ENV_LOCK and cascaded 3 more), 1 in `ca9b9cc3` (pheno-tracing
> restored to `0.4.0-pre.0` per compat pre-release policy — the 0.4.0 came
> in via absorb-Substrate 33673213), 1 in `2a8c7fef` (absolute wall-clock
> perf assert → load-robust paired-ratio gate; host load measured **348 →
> 802** from parallel sessions during the runs). Pushed through a merge
> with `d24b13ed` (Pose Roulette workflow); HEAD `2a8c7fef`.

| Fact | Value | Evidence |
|---|---|---|
| Workspace members | **79** | `cargo metadata --no-deps` |
| `Cargo.toml` on disk (excl. `target/`) | **594** | `find . -name Cargo.toml` |
| Non-member manifests | **515** | 594 − 79 |
| `cargo check --workspace` | **exit 0**, warm **and cold** | `WORKSPACE-BUILD.md` |
| Ordinary Rust linking | **works** (`cargo build -p phinbox` links) | measured by coordinator |
| Host `cc` linking | **broken** (exit 1) — SDK split-brain, `SDKROOT` fixes it | measured by coordinator |
| C/FFI surface at risk | **2** `cc` crates + **14** `*-sys` crates | measured |
| `cargo check --workspace --all-targets` | **exit 0**, 79/79 | same |
| Workspace crates that fail to compile | **0** | same |
| Non-member manifests that even load | **75 / 515** (440 fail pre-compile) | same |
| Non-member crates with real compile errors | **4** distinct (6 manifest entries) | same |
| Dominant non-member blocker | **manifest config, not code**: 292 × "believes it's in a workspace when it's not", 109 × `workspace = true` inheritance | same |
| Registry records | 178 files, **11** `status: absorbed` | measured |
| Absent local destinations (5 sources) | **18 paths / 12 records** | invariant, negative-controlled |
| Lower bound on that | **≥23** — 5 more invisible to the scanner | `phenoData/README.md:37-41` |
| Unverifiable destinations | **70** | invariant |
| fmt: stable wants | **288** files (nightly 456; 168 nightly-only) | `FMT-GATE.md` |
| `rustfmt.toml` nightly-only options | **19 of 29** | measured |
| eyetracker | **divergent fork**, not a duplicate | `EYETRACKER-DUPLICATE.md` |
| Lockfiles mutated by `cargo` runs | **4** paths observed | observed twice |

**The load-bearing caveat from E2:** `cargo check` does not link. `bear`
reported a genuine host linker defect, and I reproduced it (plain `cc` exits 1).
**But I narrowed its impact**: ordinary Rust linking is **unaffected** —
`cargo build --offline -p phinbox` links fine, and a cold-dir crate builds
without `SDKROOT`. The at-risk surface is narrow and countable: **2** crates
with a `cc` build-dependency and **14** crates depending on a `*-sys` crate.
So "the workspace builds" is **established for Rust**; what remains unproven is
only the FFI/C surface.

---

## 1. Critical path

```
E10.7 (wire invariant into CI) ─┐
E1.1 fmt decision ──────────────┼─> E1.6 make check green ─> E1.8 single CI job
E2.1 real link (cargo build) ───┘                              │
                                                               v
                                        merge reliability restored
                                                               │
                        E11 (path-mismatch class) ─────────────┘
                        E10.2 status corrections
```

E1 and E2.1 are the gate. Nothing merges reliably until E1.6 is green, and
E1.6 cannot be honest while `cargo check` is being substituted for a link.

---

## 2. E1 — Make every gate actually run (CRITICAL PATH)

| ID | Task | Est | Depends | Blocked by |
|---|---|---|---|---|
| E1.1 | Decide fmt policy: CI→nightly **or** trim `rustfmt.toml` to the 19 stable-settable options | 10m | — | **done 2026-10-01 — trim chosen** (MCQP, operator reply): the 18 nightly-only options removed from `rustfmt.toml`; stable rustfmt had been printing 18 `unstable features` warnings per run. Churn-free proof: `cargo fmt --all --check` exit 0 before AND after the trim. Evidence: d03c0ebf |
| E1.2 | Implement the decision in `rustfmt.toml` / workflow | 10m | E1.1 | **done 2026-10-01** — `rust-toolchain.toml` pinned `channel = "1.99.0"` and CI's `dtolnay/rust-toolchain@stable` → `@1.99.0` (the floating-vs-pinned drift that produced failed run 36626812921's 8 clippy errors). Bump procedure (change both files together, one commit, full make check) documented in the toolchain file. Evidence: d03c0ebf (pin), c92a24fe (CI side) |
| E1.3.1 | Reformat `crates/phinbox` (69 files) alone, message-scoped | 10m | E1.2 | |
| E1.3.2 | Reformat the other 219 files, separate commit | 10m | E1.3.1 | |
| E1.3.3 | Confirm `cargo fmt --check` exits 0 under the chosen toolchain | 10m | E1.3.2 | **done 2026-09-27 (2nd pass)** — 1st-pass claim retracted: `--all` was never clean. The E1.3.2 tree itself measures **326** diff files under the same toolchain (worktree test at 1f250aad); HEAD was at **152**. Full `cargo fmt --all` reformat landed 2026-09-27, `cargo fmt --all --check` exit 0 |
| E1.4 | Measure `cargo clippy --workspace --locked -- -D warnings` | 10m | E2.1 | **done; re-corrected 2026-09-29** — the 2026-09-27 "done" was freshness-limited to two sub-areas (traceability-core 277 `missing_docs` + `int_plus_one`; fabric-checker/graph; fixed 0f161d08, 7feb3c64). The full workspace measure ran 2026-09-29: **166 warning lines**, 41 autofixable files + 46 manual sites, all remediated in 2fc733e8 with `-D warnings` exit 0 |
| E1.5.x | Fix/allow the clippy findings it exposes (scoped allows only, see E4) | 10m each | E1.4 | **3 batches done**: 0f161d08 (traceability-core, 0 errors), 7feb3c64 (checker/graph, 0 errors, 2 scoped allows), 2fc733e8 (full workspace: 41 autofix + 46 manual incl. scoped allows in material_registry tests and settings.rs file-level `unused_unit` — proc-macro spans escape item-level attributes — plus `[lints.rust]` check-cfg declarations for pheno-otel `cfg(loom)` and policy-engine vestigial `feature(casbin-backend)`); `-D warnings` exit 0 |
| E1.6 | `make check` green end to end | 10m | E1.3.3, E1.5.x | **done 2026-09-29** — exit 0 (first full-green run): fmt 0, clippy -D 0, test-unit 79 targets/0 failed. Evidence: 2fc733e8 (lints), 98263c03 (test repairs), ca9b9cc3 (version policy), 2a8c7fef (load-robust perf gate). CI's cargo test step is advisory, so the 8 pre-existing failures had never gated. **Re-validated on pinned 1.99.0** (the CI toolchain): first attempt **2026-10-01** died at clippy — the 2026-09-29 green had been measured on stale 1.97.1 and could not compile Linux-cfg-gated code. Host gate round 1 = task **122535h9de** (2026-10-02, fmt+clippy green); test-target enumeration task **094961g685** found **8** additional lints (7× `clippy::assert_is_empty` + 1× `clippy::chunks_exact_to_as_chunks`; earlier count of 9 corrected to 8). Lint remediation commit **89f4df30** = **16 fixes total** (8 CI-visible + 8 test-target) across phinbox + phenotype-gfx. Round 2 = task **696747sq7k** (**1199s, 0 failures, 79 test suites green**) after fixes — fmt clean, clippy `--workspace --all-targets -- -D warnings` clean. Evidence: 89f4df30 |
| E1.7 | Generalise `crates/phinbox/scripts/check-targets.sh` → `scripts/check-cross-targets.sh` | 10m | — | **done 2026-10-01** — crate×target matrix script (DEFAULT_CRATES × {linux-gnu, pc-windows-gnu, apple-darwin}), `--locked` everywhere, loud SKIPs for uninstalled targets. Live run on 1.99.0 = validation task **273019w1lh** (2026-10-02, 26m30s, **exit 0**): **3 checked / 0 skipped** (x86_64-unknown-linux-gnu, x86_64-pc-windows-gnu, x86_64-apple-darwin). Old `crates/phinbox/scripts/check-targets.sh` removed (no callers). Evidence: 7d8ad7a6 |
| E1.8 | One Linux-only CI job running E1.6 + E1.7; delete/gate the redundant ones | 10m | E1.6, E1.7 | **done 2026-10-01** — `quality-gate.yml`/cargo-check now: pinned toolchain → `cargo build --workspace --locked` (E2.1) → `make check` (E1.6) → `scripts/check-cross-targets.sh` (E1.7) → cargo-nextest `ci` profile (belt-and-braces, workspace-wide); path filter expanded to Makefile/rustfmt/toolchain/script/self. Advisory `rust` job deleted from `ci.yml` (branch protection verified: **no required status checks**, only PR-review rules). YAML parsed via `yaml.safe_load`. Evidence: c92a24fe (deployed quality-gate as the single rust gate + pinned toolchain). **OBSERVED gate runs on this row, dated** (all 5 of the wave-4/5/6 cycle): 36926774889 on c92a24fe (`needless_return` in engine-forge Linux-cfg, fixed in 7546252b) — 37238178334 on f71aef9a (`make check` Broken-pipe flake in focalpoint raw-gaze test, fixed in f5dfd6c1) — 37707359194 on f5dfd6c1 (arch-test contract was reading stale `ci.yml`, fixed in ca53e5d5) — **37710242002 on ca53e5d5: PASS** (2026-10-08 00:55:05Z → 01:05:46Z, wall 10m41s, queue 0s; jobs: changes=success, cargo-check=success [incl. new `Upload cargo-nextest JUnit report` step uploading `target/nextest/ci/junit.xml` artifact `substrate-nextest-ci-junit` 47258 bytes expired=false], go-vet/go-lint/security=skipped by `dorny/paths-filter` rust path). **E1 GATE EVIDENCE: GREEN.** |
| E1.8-R | Linux CI replica (pre-push validation): rust:1.99.0 container mirroring the gate, 8 stages | — | E1.8 | **OBSERVED 2026-10-02 (171998tsbp) — REPLICA_FAILED stage=4 code=125 (infra, not code)**: colima VM died mid cargo build; **2026-10-02 (8542192coz) — REPLICA_FAILED stage=4 code=14 (missing libclang, real code)**: `error: failed to run custom build command for `v4l2-sys-mit v0.3.0``: bindgen-0.65.1 panicked "Unable to find libclang"; **2026-10-07 (replica3/4/5) — INFRA-FAIL on docker daemon, spurious EXIT=0 due to `RC=$?` after `docker|tee` pipe** (regression: tee's exit=0, not docker's; replicas 3-5 reported false-positive green); **2026-10-08 (replica6) — REPLICA_FAILED stage=4 code=14 (real code via fixed PIPESTATUS wrapper)**: container `stupefied_dewdney`, first error `error: failed to run custom build command for `v4l2-sys-mit v0.3.0`` (bindgen-0.65.1 "Unable to find libclang ... set LIBCLANG_PATH ... (invalid: [])"). Root cause: wrapper passes `LIBCLANG_PATH=/usr/lib/x86_64-linux-gnu` to an aarch64 container where the actual libclang lives at `/usr/lib/aarch64-linux-gnu/libclang.so.*` — apt installs it but the env var points at a path that does not exist inside the ARM64 rust:1.99.0 image. Replica6 stages 0-3 LEG_GREEN (toolchain rustc 1.99.0, sysdeps, Go, cross-target std); ~6min wall; load healthy. Stages 5-7 (make check / cross-targets / nextest) NOT YET EXERCISED on Linux — still UNKNOWN. **The CI gate is the authoritative E1 proof (run 37710242002 green); the replica is pre-push tool validation, and its libclang ARM64 path bug is a separate E1.9 tool-reliability item, not an E1.8 blocker.** |

**Toolchain trap to encode in E1.2:** the host's rustup **default is nightly**,
so any instruction to "run cargo fmt" must name the toolchain or the result is
not reproducible.

---

## 3. E2 — Prove the workspace actually builds and links

| ID | Task | Est | Depends |
|---|---|---|---|
| E2.1.1 | ~~Reproduce the linker defect~~ **DONE** — verified independently: plain `cc` on a 2-line C file exits **1**; `SDKROOT=<xcode sdk>` alone fixes it; Rust builds are unaffected | — | done |
| E2.6 | **Fix the host SDK split-brain.** Measured root cause (2026-09-19): `SDKROOT` is **not** set, and `xcrun --show-sdk-path` returns the CLT SDK **even when `DEVELOPER_DIR` is pointed at Xcode** — so this is the CLT install resolving ahead of the Xcode selection, not an env-var bug. The CLT `.tbd` (`MacOSX27.0.sdk/usr/lib/libSystem.B.tbd`) declares `arm64e.x1-macos`, which `ld-1221.4` (Xcode 26) cannot parse. Proven per-build workaround (no sudo): `export SDKROOT="$(xcode-select -p)/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"` — plain `cc` exits 0. Permanent fix is a system-level change (regenerate/remove the malformed CLT `.tbd`, or repair the CLT via `xcode-select --install`), which needs approval | 10m + approval | — |
| E2.7 | Verify the **14** `*-sys` and **2** `cc` crates build once the SDK is corrected | 10m | E2.6 |
| E2.2 | Fix or formally exclude the **4** non-member crates with real compile errors | 10m | — |
| E2.3 | Decide the **440** non-member manifests that never load (register / exclude / delete) | 10m | — |
| E2.4 | Root-cause the **292** "believes it's in a workspace when it's not" | 10m | — |
| E2.5 | **DONE (2026-10-08)** — audit complete. `--locked` added to every build/test/clippy/bench `cargo` invocation in CI workflows, repo scripts, and `grade.sh`; 14 files in 3 commits: `e8324250` (.github/workflows), `65ecac9a` (scripts/), `c5dfa0e1` (grade.sh). Justified skips recorded in E12.4. | done | — |

**Why E2.1 first:** it is the difference between "compiles" and "works". `check`
passing on a warm target dir is exactly the kind of green that hid four earlier
broken mechanisms in this repo.

---

## 4. E10 — The ledger must not overstate what was migrated

| ID | Task | Est | Status |
|---|---|---|---|
| E10.1 | Re-derive every count with the three-bucket rule (path+exists / path+absent / not-a-local-path) | 10m | **done** (2 methods reconciled: 12 records = 18 paths) |
| E10.2 | Correct the 1 provable false `absorbed` status (`agent-user-status`) | 10m | queued |
| E10.3 | Reclassify all 18 absent paths against the **local** sibling checkouts | 10m | **done** (2026-09-19, `docs/audits/ABSORPTION-TRIAGE-18.md`) |
| E10.3.1 | Path-mismatch cases: code present under a different root (e.g. `crates/policystack`, 1,711 files, claimed as `packages/policystack`) → ledger fix, not recovery | 10m | measured, not yet committed |
| E10.3.2 | Branch-only cases: present on unmerged branches (`Benchora` in 3 worktrees) → `PENDING` until branch+commit named | 10m | measured |
| E10.3.3 | Genuinely absent locally (`kodevibe`, `kwatch`, `pheno-plugins-*`) → credentials-blocked | 10m | blocked |
| E10.4 | Schema split: typed `absorbing_path` (repo-relative) vs `absorbing_repo` (slug) | 10m | recommended |
| E10.5 | `phenoData` decision — the ledger says the surviving `crates/pheno-data-from-phenoData/` was removed; it is still there with 14 files | 10m | **your call** |
| E10.6 | Extend the scanner to prose path lists (**≥5** more violations known) — deliberately deferred so the gate does not cry wolf | 10m | deferred on purpose |
| E10.7 | Wire the invariant into CI as a gate | 10m | **landed 2026-09-24** — hard `registry-invariant` job (self-test + gate) feeding the `ci / lint` aggregate |

### E10.5 decision package (phenoData) — one-word yes

Verified the record's shape: there is **no `projects/phenoData.json`** —
`phenoData` survives only as `docs/absorption/phenoData/README.md`. So E10.5 is
**not** a registry-status change; it is a README-claim correction.

- `README.md:32-33` asserts "Removed 5 stale `crates/pheno-data-from-phenoData/`
  artefacts" — **false**: that directory still exists with **14 files**.
- `README.md:17-21` claims the target is the external `pheno/crates/pheno-data-*`
  monorepo — **unverifiable from this tree** (external repo), the same as every
  other other-repo destination.

Two independent decisions, both one-word:
- **A (safe doc-truth fix, do now):** correct line 32-33 to state the artefacts
  were *intended* to be removed and *are still present*. Aligns the record to
  reality, deletes nothing. Say **"fix"** and I apply it.
- **B (destructive, separate):** whether to *actually delete*
  `crates/pheno-data-from-phenoData` (14 files). This is a real deletion and is
  **not** bundled with A. Say **"delete"** (with that specific dir) and I will,
  after a confirming check; otherwise it stays exactly as-is.

A "yes" to A does not imply B, and vice versa.

---

## 5. E11 — NEW: the path-mismatch class (MEASURED)

Discovered while verifying E10.3, then classified by a single-pass sweep over
every sibling checkout (159 directory hits). **The 18 "absent" destinations are
not 18 missing absorptions.** They split four ways:

### (a) PRESENT LOCALLY — ledger names the wrong path (4)

| Destination | Ledger says | Actual location |
|---|---|---|
| `policystack` | `packages/policystack` | **`crates/policystack`** — 1,711 files |
| `byteport` | `crates/byteport` | **`absorption/byteport`** — still in the *staging* directory |
| `melosviz` | `packages/melosviz` | `crates/argis-extensions/melosviz-wt/.../melosviz` |
| `traceability-core` | `crates/traceability-core` | `crates/agile-plus/crates/traceability-core` — **caution: a different lineage**, not the same crate |

These are **ledger edits, not recoveries**. They need no credentials and no
network.

### (b) BRANCH / SIBLING ONLY — unmerged or other checkouts (2)

`benchora` (4 sibling worktrees), `phenotype-research-engine` (14 sibling hits).
Correct status is `PENDING` until a branch and commit are named.

### (c) DOC PLACEHOLDER only — no code anywhere (1)

`agent-user-status` — the only trace in the entire tree is
`docs/absorption/agent-user-status/`. Consistent with the earlier finding that
the absorb never landed.

### (d) TRULY ABSENT locally (17)

`kodevibe`, `kwatch`, the five `pheno-plugins-*`, `quillts`, `graphclient`,
`pheno-utils`, `traceability-decorators`, `trace-gate`, the five
`pheno-data-*`, `klipdot`. Credentials-blocked for recovery.

| ID | Task | Est | Status |
|---|---|---|---|
| E11.1 | Locate each absent destination across sibling checkouts (single-pass sweep) | 10m | **done** — 159 hits |
| E11.2 | Split into mis-pathed / branch-only / placeholder / truly-absent | 10m | **done** — 4 / 2 / 1 / 17 |
| E11.3 | Correct the mis-pathed ledger records; re-run the invariant and record the drop | 10m | triaged (see measured updates below); sign-off needed |
| E11.4 | Add a "did you mean" hint: on VIOLATION, report a same-basename directory elsewhere in the tree | 10m | queued |

**Effect:** E11 converts **4** of the 18 violations from "missing code" to
"wrong path in the ledger", and **2** more to a branch-state question — so only
**~12** are genuinely absent locally.

### Measured updates (2026-09-19 late, `docs/audits/ABSORPTION-TRIAGE-18.md`)

Three rows above are superseded by direct evidence:

- **Benchora moves (b) → (a).** The real absorb `f1f9a025` (#322, 2026-09-13)
  landed the repo at the tooling **root** as `Benchora/` (138 files) and it is
  an ancestor of `main` — it **survives on main today**. What `d7480faa`
  (2026-09-11, PR #313) deleted was the `crates/benchora` **stub** (v0.1.0,
  19-line lib.rs), not the absorbed content. The record's "v0.2.0, 78 files"
  matches neither tree.
- **pm-core ×3 move (d) → RESOLVED 2026-09-20 via bundle.** Fetched
  `refs/archive/phenotype-pm-core-2026-08-09/heads/master` from
  `zz-archive/git-bundles-20260910/phenotype-archive.bundle` (HEAD
  `d3277c40`, 2026-08-01), extracted the 3 crates to canonical paths
  (`crates/traceability-core/`, `crates/traceability-decorators/`,
  `crates/trace-gate/`). `cargo check` passes; 101/102 tests pass
  (1 perf-gate flake under host load). The old partial at
  `crates/agile-plus/crates/traceability-core` is orphaned gitignored.
- **quillts negative strengthened.** The `phenodocs` checkout exists at
  `_full_pheno/phenodocs`; its `packages/` tree object holds only
  pheno-core/pheno-llm/pheno-resilience — **no quillts, and no quillts commit
  in any phenodocs ref**. The TS half survives only in the standalone `Quillr`
  checkout (`src/` = `@<REDACTED>/quillts`).

Also measured: KodeVibe content **exists** at
`phenotype-tooling/docs/absorbed-from-kodevibe/` (155 files at the absorb
commit and at HEAD, incl. 38 real Go files under `engine/` and the 48 KB
`kodevibe` bash script); KWatch has **0 of 816** tooling commits touching
`tools/kwatch/` (the 42-file claim went nowhere).

### Proposed E11.3 corrections (apply only with sign-off — they edit the source-of-truth registry)

The 4 "present locally" cases do **not** all get the same fix. Only one is a
clean path correction; the other three are disposition decisions, because the
invariant scans both `projects/*.json` **and** the `docs/absorption/*/README.md`
claims, so a fix must touch every claim site of a destination.

| Destination | Claimed | Actual | Fix & expected invariant effect |
|---|---|---|---|
| `policystack` | `packages/policystack` | `crates/policystack` (1,711 files) | **clean path edit at every claim site** → removes its VIOLATION |
| `byteport` | `crates/byteport` | `absorption/byteport` (still **staged**) | do **not** claim the staging path as final; set status `PENDING` + note "staged at absorption/byteport" |
| `melosviz` | `packages/melosviz` | `crates/argis-extensions/melosviz-wt/...` (unstable worktree path) | not a stable location → set `PENDING` |
| `traceability-core` | `crates/traceability-core` | `crates/traceability-core` (restored 2026-09-20 from bundle, 13 src) | **done** — supersedes old `crates/agile-plus/crates/traceability-core` partial (orphaned gitignored) |

Honest expected drop on the **violation count**: at most **1** from a pure
path-correction (`policystack`), because the other three case decisions change
*disposition*, not a claim path — and disposition changes only affect
`projects/*.json` `status=absorbed` rows, while the docs-derived claim lines
stay violations until the claim itself is edited. So E11.3 does **not** "shrink
18 to ~13 by itself" — and pm-core (traceability-{core,decorators}+trace-gate)
already moved 3 violations to resolution on 2026-09-20; that number only
lands after the E10.2 status corrections and the docs-claim edits are done
together and the invariant is re-run.

---

## 6. E12 — NEW: `cargo` mutates committed lockfiles

Observed twice, reproducibly: running `cargo metadata` / `cargo check` in this
repo **modifies committed `Cargo.lock` files** and creates new ones
(`crates/fabric-frame-transport/fuzz`, `crates/fabric-gui/src-tauri`,
`crates/forge_daemon`, `agileplus-agents`). One is binary-diffed by git.

| ID | Task | Est |
|---|---|---|
| E12.1 | Identify the minimal command that triggers it | 10m |
| E12.2 | Document the trap (any measurement must use `--locked`/`--offline`) | 10m |
| E12.3 | Restore the 4 paths and verify a clean tree after a full measurement run | 10m |
| E12.4 | **DONE (2026-10-08)** — E2.5 audit closed. 131 candidate files triaged: 14 hardened with `--locked` (`e8324250`, `65ecac9a`, `c5dfa0e1`); remaining invocations are already-locked (a) or intentional-no-lock (c). Skips: dead workflows (`perf-core/`, `libs/phenotype-auth`, `nanovms/` absent), lockfile-less standalone crates (`rust/`), external-repo builds (`phenotype-tooling`), and install/publish/audit/deny/fmt/metadata. Report: `~/.jcode/scratch/worker-reports/E2.5-locked-everywhere.md` | done |

---

## 7. E3/E8 — the three domains you asked about

| ID | Task | Est | Blocked by |
|---|---|---|---|
| E3.1 | `agent-user-status`: restore at `crates/agent-user-status/` + the promised `ABSORPTION.md` marker | 10m | **credentials** — no local copy exists (only 4 doc placeholders) |
| E3.2 | `sidekick-messaging` documents a dependency on `agent-imessage`, which exists nowhere | 10m | — |
| E8.1 | Eyetracker disposition: keep `crates/eyetracker-*`, remove `crates/eyetracker/`, after harvesting `license = "MIT"` ×7 and the one `mouse.rs` form | 10m | **your call** |
| E8.2 | Fix `crates/eyetracker-PROVENANCE.md:25` (claims criterion "workspace 0.8"; root declares 0.5) | 10m | — |
| E8.3 | Decide whether to promote `crates/eyetracker-*` into workspace `members` or `exclude` | 10m | **your call** |
| E8.4 | Presence gating in `phinbox`: it has none | 10m | — |

---

## 8. Blocked on you (in priority order)

1. **Unlock the login keychain** (answer the pending `SecurityAgent` prompt, or
   `security unlock-keychain`). One step unblocks: the `agent` CLI, `gh auth`,
   and every credential-dependent recovery.
2. **E1.1 fmt decision** — CI→nightly, or trim the 19 nightly-only options.
   Blocks the whole critical path.
3. **E8.1 / E8.3 eyetracker** — approve keep-`crates/eyetracker-*` and the
   members-vs-exclude choice.
4. **E10.5 `phenoData`** — the ledger's removal claim is false; confirm intent.

---

## 9. Progress at time of writing

```
[E1 gates run        ] ████████░░░░░░░░░░░░  40%  measured; decision pending
[E2 builds+links     ] ██████████░░░░░░░░░░  50%  check=exit 0; LINK UNPROVEN
[E10 ledger truth    ] ████████████░░░░░░░░  60%  18 violations, ≤23 known
[E11 path mismatches ] ██░░░░░░░░░░░░░░░░░░  10%  class found, sweep running
[E12 lockfile trap   ] ██░░░░░░░░░░░░░░░░░░  10%  observed twice
[E3/E8 three domains ] ██████░░░░░░░░░░░░░░  30%  all three need a decision
--------------------------------------------------------------
OVERALL              ] ██████░░░░░░░░░░░░░░  33%
```

**E1 re-measure 2026-09-29** (dated; the block above stays frozen at its
2026-09-19 observation): 6/10 E1 leaves done — E1.3.1, E1.3.2, E1.3.3,
E1.4, E1.5.x, E1.6 — = 60%. Remaining: E1.1/E1.2 (fmt policy decision,
sponsor-blocked), E1.7, E1.8.

```
[E1 gates run        ] ████████████████████ 100%  3 consecutive greens: 37710242002 (ca53e5d5, 10m41s wall, junit 47258B), 37711666376 (2030926d, docs-only), 37714365796 (84f1e914, docs-only) — all 2026-10-08 (then **5th consecutive green on 5bb818ff**, 2026-10-08, after the eyetracker flake fix `fix(eyetracker-inference): de-flake focalpoint socket publish tests`; 4b024344 wave showed a pre-existing flake H4 in `focalpoint::tests::test_publish_falls_back_to_raw_gaze` 0.25-1.4% rate, NOT a wave regression — see Quality Gate run 37743799606 cargo-check step 12 for the failed-then-fixed chain)
[E1 evidence (commits)] ████████████████████ 100%  9 E1 commits: 89f4df30, d03c0ebf, 7d8ad7a6, c92a24fe, 7546252b, f71aef9a, f5dfd6c1, ca53e5d5, 2030926d (+ 84f1e914 ledger-correction, itself gate-green) (+ 281f4a4f bar refresh)
[E1.8-R replica      ] ██████████░░░░░░░░░░  50%  PIPESTATUS wrapper bug fixed in replica6; **E1.9 libclang ARM64 fix landed** (octopus, ~/.jcode/scratch/ci-replica.sh dpkg-based detection + replica6-pipeline.sh hard-coded env removed, bash -n exit 0; awaiting next replica6 run with `load1 < 500` for the dpkg + stage 4 evidence leg)
[E1.9 libclang ARM64 ] ██████████░░░░░░░░░░  50%  fix landed 2026-10-08 (octopus worker, retry 2 on mimo-v2.6-flash); bash -n on both scripts exit 0; replica NOT re-run (colima load >500); full proof pending next replica6
[E1.10 PIPESTATUS     ] ████████████████████ 100%  audit CLOSED 2026-10-08. 306 `.sh` files in scope (255 with `pipefail`), 62 lines containing `$?`: **0 PIPELINE_DROP**, **0 ALREADY_PIPESTATUS** among `$?` sites (the only `${PIPESTATUS[0]}` user, `scripts/migrate_50_beads.sh:31`, contains no `$?` at all), 1 pipeline-adjacent but semantically correct (`crates/local-ops/tests/test_jcode_tool_safety.sh:35` — the last pipeline element *is* the hook under test), 61 NOT_AFTER_PIPE (redirection / command substitution only). The E2.5-flagged `scripts/test_cross_machine.sh` is clean (no `$?` after a pipe; `set -euo pipefail` line 13) — the E2.5 mention was about a missing lockfile, not RC handling. Real defects were elsewhere: **44c33538** `demos/bench-throughput-stress/scripts/stress.sh` (RC clobbered by `|| true` → `exit_code` always 0, *and* `pipefail` making the suite-list fallback dead code so the driver died at the probe), **39af864d** repo CI tee-masking (`.github/workflows/ratchet.yml`, `compute-infra-auditors.yml`), **5e5cfce4** crate CI tee-masking (`crates/hexa-kit/.github/actions/run-benchmarks/action.yml`, `crates/agile-plus/.github/workflows/infra.yml`, `crates/settly/.github/workflows/benchmarks.yml`). Report: `~/.jcode/scratch/worker-reports/E1.10-pipestatus-audit.md`
[E1.8-AA flake         ] ████████████████████ 100%  eyetracker-inference focalpoint test flake fixed 5bb818ff; 500-iter stress of prebuilt binary 0 failures; cargo-check step 12 of quality-gate back to success
[E2.1 real link        ] ████████████████████ 100%  quality-gate cargo-check step 12 (cargo nextest run --workspace --profile ci --locked) green on ca53e5d5, 2030926d, 84f1e914, 281f4a4f, 5bb818ff
[E2.2 4 non-member    ] ████████████████████ 100%  all 4 crates fixed 2026-10-08: 5a5f912a oci-lottery, 317aed39 oci-post-acquire, 2822ef5d argis-monitor opentelemetry 0.27 pin, bde31356 agileplus-agent-service build.rs; audited by 4b024344 (carries the WORKSPACE-BUILD §4.3 evidence table); 0 exclusions
[E2.5 --locked everywhere] ████████████████████ 100%  14 files hardened, 4 commits (e8324250 workflows, 65ecac9a scripts, c5dfa0e1 grade.sh, 3c935bb4 docs) — audit closed 2026-10-08
[E2.3 440 non-loading   ] ░░░░░░░░░░░░░░░░░░░░   0%  queued — mostly manifest config not code (E2.4)
[E2.4 292 belief-error  ] ░░░░░░░░░░░░░░░░░░░░   0%  queued
```

**E1 CLOSEOUT 2026-10-08 01:09Z (Pacific)** — quality gate **GREEN** on
ca53e5d5. All E1 rows (E1.1 / E1.2 / E1.3.1 / E1.3.2 / E1.3.3 / E1.4 / E1.5.x
/ E1.6 / E1.7 / E1.8) have evidence in the ledger and the gate is proving
it; the 7-todo mandate (clippy, toolchain, make check green, push+watch,
E1.7, E1.8, WBS evidence) is complete. E1.8-R (Linux pre-push replica) is
tool validation, not gate validation; its remaining gap is a separate
ARM64 libclang env fix in `ci-replica.sh` (E1.9). Operator ledger commits
in this cycle:

| SHA | Description | Gate impact |
|---|---|---|
| `89f4df30` | clippy remediation (16 fixes, 8 CI + 8 test-target) | unblocks E1.6 |
| `d03c0ebf` | toolchain pin 1.99.0 + 18 nightly rustfmt options removed | unblocks E1.1/E1.2 |
| `7d8ad7a6` | E1.7 cross-target script generalised | E1.7 done |
| `c92a24fe` | E1.8 single-gate restructure (quality-gate.yml, ci.yml = thin router) | E1.8 deployed |
| `7546252b` | engine-forge `needless_return` Linux-cfg fix (run 36926774889) | clears first E1.8 attempt |
| `f71aef9a` | E1.8-rev: workflow `cargo nextest run --profile ci` + repair CI-broken tests | unblocks nextest leg |
| `f5dfd6c1` | eyetracker-inference focalpoint raw-gaze test deterministic (Barrier sync) | clears run 37238178334 |
| `ca53e5d5` | arch-test contract points at quality-gate.yml + junit upload step | clears run 37707359194, lands **GREEN** on 37710242002 |
| `2030926d` | chore(wbs): E1 closeout — record green gate + 8-SHA evidence | itself gate-evidenced: run 37711666376 PASS on 2026-10-08 01:11:29Z (docs-only, no code touched) |
| `84f1e914` | chore(wbs): add 2030926d row to E1 evidence ledger table | itself gate-evidenced on 37714365796 (docs-only) |
| `281f4a4f` | chore(wbs): refresh E1 bars with 3 greens + 9-SHA ledger | itself gate-evidenced on 37715702087 (docs-only) |
| `34867274` | chore(wbs): start E2 phase — bars added for E2.2, E2.5, E1.9 | docs-only push |
| `5a5f912a` | fix(iac/oci-lottery): declare missing oci-helpers path dependency | E2.2 / 1 of 4 |
| `317aed39` | fix(iac/oci-post-acquire): declare missing oci-helpers path dependency | E2.2 / 2 of 4 |
| `e8324250` | chore(ci): enforce --locked on cargo build/test/bench in GitHub workflows | E2.5 / workflows cluster |
| `65ecac9a` | chore(scripts): enforce --locked on cargo build/test/clippy in repo scripts | E2.5 / scripts cluster |
| `c5dfa0e1` | chore(grade): enforce --locked on cargo build/test/clippy/doc/bench | E2.5 / grade.sh cluster |
| `3c935bb4` | docs(wbs): mark E2.5 --locked-everywhere audit complete | itself gate-evidenced (docs-only) |
| `2822ef5d` | fix(argis-monitor): pin opentelemetry_sdk to 0.27 line | E2.2 / 3 of 4 |
| `bde31356` | fix(agileplus-agent-service): build.rs compile_protos slices share one element type | E2.2 / 4 of 4 |
| `4b024344` | docs(audits): record E2.2 resolution of the 4 non-member compile-error crates (WORKSPACE-BUILD §4.3) | exposes pre-existing eyetracker flake (Q-Gate 37743799606 cargo-check step 12 FAIL H4) — **NOT a wave regression**; flake 0.25-1.4% per run |
| `5bb818ff` | fix(eyetracker-inference): de-flake focalpoint socket publish tests (BufReader::read_line + write_all) | E1.8-AA flake: Q-Gate 5bb818ff PASS (cargo-check step 12 back to success); 500-iter prebuilt-binary stress 0 failures |

**Operator routing ladder note (dated 2026-10-08):** the standing-default
worker model `opencode-go:mimo-v2.6-flash` (operator 2026-09-24) returned
`OpenAI-compatible stream error ... model: mimo-v2.6-flash` repeatedly for
boar (E2.2 #1), dolphin (E2.2 retry 1), hippo (E1.9 #1), zebra (E2.2
retry 3), and unicorn/scorpion (E2.5 #1, #2). **3 of 5 first-attempt
failures** on a fresh session — the model is unreliable on this host.
Per the operator-authorized fallback ladder (`~/.jcode/memories/global/harness-agents.md`,
2026-09-17 retention, 2026-09-24 advance), I advanced to
`opencode-go:deepseek-v4.1-flash` (tool-loop verified 2026-09-17) for
**octopus** (E1.9 — succeeded), **stallion** (E2.5 — succeeded), and
**hare** (E2.2 retry 4 — succeeded, 9 commits closed). **No silent
silent advancement** — every dispatch records the actual model that
served. Net result: 3 retries × 2 = 6 spawns on mimo-v2.6-flash
vs 3 successful dispatches on deepseek-v4.1-flash.
```

---

## 10. Honest unknowns

- Whether the workspace **links** (E2.1) — unproven.
- Whether the 18 are 18: the scanner misses prose path lists, so **≥23**.
- How many of the 440 non-loading manifests are dead vs merely unregistered.
- Whether every "absent" destination is genuinely absent — E11 exists to settle it.
- Whether any recovered code is the **canonical** copy; existence ≠ fidelity.
