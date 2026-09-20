# Forward WBS — PhenoShared

**Written:** 2026-09-19
**Basis:** measured only. Every number here was produced by a command whose
output is cited; anything unverified is labelled. Supersedes the "next steps"
prose in `LONG-TERM-WBS.md`, which remains the epic-level contract.

Task granularity follows the 10-minute rule: leaf tasks are ~10 minutes.

---

## 0. Verified state of the world (inputs to the plan)

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
| E1.1 | Decide fmt policy: CI→nightly **or** trim `rustfmt.toml` to the 19 stable-settable options | 10m | — | **your call** (or accept my recommendation) |
| E1.2 | Implement the decision in `rustfmt.toml` / workflow | 10m | E1.1 | |
| E1.3.1 | Reformat `crates/phinbox` (69 files) alone, message-scoped | 10m | E1.2 | |
| E1.3.2 | Reformat the other 219 files, separate commit | 10m | E1.3.1 | |
| E1.3.3 | Confirm `cargo fmt --check` exits 0 under the chosen toolchain | 10m | E1.3.2 | |
| E1.4 | Measure `cargo clippy --workspace --locked -- -D warnings` | 10m | E2.1 | |
| E1.5.x | Fix/allow the clippy findings it exposes (scoped allows only, see E4) | 10m each | E1.4 | unknown N |
| E1.6 | `make check` green end to end | 10m | E1.3.3, E1.5.x | |
| E1.7 | Generalise `crates/phinbox/scripts/check-targets.sh` → `scripts/check-cross-targets.sh` | 10m | — | |
| E1.8 | One Linux-only CI job running E1.6 + E1.7; delete/gate the redundant ones | 10m | E1.6, E1.7 | |

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
| E2.5 | Encode `--locked` (or `--offline`) everywhere so measuring never mutates lockfiles (see E12) | 10m | — |

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
| E10.7 | Wire the invariant into CI as a gate | 10m | queued |

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
- **pm-core ×3 move (d) → recoverable from the archive bundle.** Fetched
  `refs/archive/phenotype-pm-core-2026-08-09/*` from
  `zz-archive/git-bundles-20260910/phenotype-archive.bundle` into a scratch
  repo: it holds all three claimed crates — `traceability-core` (13 src files,
  **fuller than pheno's 11**: `execution_graph.rs`, `progress.rs` missing
  here), `traceability-decorators` (5 src files), `trace-gate` (binary + 3
  test fixtures + `trace-gate.yml` workflow).
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
| `traceability-core` | `crates/traceability-core` | `crates/agile-plus/crates/traceability-core` (**different lineage**, see absorption audit) | do **not** alias two different lineages → keep flagged / `PENDING` until provenance is confirmed |

Honest expected drop on the **violation count**: at most **1** from a pure
path-correction (`policystack`), because the other three case decisions change
*disposition*, not a claim path — and disposition changes only affect
`projects/*.json` `status=absorbed` rows, while the docs-derived claim lines
stay violations until the claim itself is edited. So E11.3 does **not** "shrink
18 to ~14 by itself"; that number only lands after the E10.2 status corrections
and the docs-claim edits are done together and the invariant is re-run.

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

---

## 10. Honest unknowns

- Whether the workspace **links** (E2.1) — unproven.
- Whether the 18 are 18: the scanner misses prose path lists, so **≥23**.
- How many of the 440 non-loading manifests are dead vs merely unregistered.
- Whether every "absent" destination is genuinely absent — E11 exists to settle it.
- Whether any recovered code is the **canonical** copy; existence ≠ fidelity.
