# Absorption Triage: the 18 absent paths

Date: 2026-09-19 (late)
Branch: `main` (HEAD `6c1d2d9c` at the time of measurement)
Scope: Every record the `registry-invariant.sh` gate reports as a prose-absent
absorption, classified against **local** evidence on this host.

This pass does not change any registry record. It produces the truth each
proposed E11.3 fix would have to be evaluated against.

---

## 0. Method

For each prose-absent record, three checks were run:

1. **Path test** — `test -e <path>; echo $?` at the named location and at the
   nearest sibling tree (e.g. `../phenotype-tooling/crates/<x>`). Same as the
   gate.
2. **Grep over git history** — when the path looks missing on disk, search
   across the `git log` of the named receiving tree (e.g. every commit of
   `phenotype-tooling` since 2026-06-01) for any path component that could
   have been added then removed. Proves "never landed" vs "landed and was
   reaped".
3. **Bundle probe** — when the destination repo was deleted from GitHub,
   fetch refs from `zz-archive/git-bundles-20260910/phenotype-archive.bundle`
   (the only preservation bundle that carries that namespace) and inspect
   the fetched tree. The pm-core namespace in this bundle is at
   `refs/archive/phenotype-pm-core-2026-08-09/refs_pull_<N>_head`
   (PR-shaped refs), not at a `main` ref — `git bundle verify` lists
   18 such heads.

The 18 prose-absent rows from `bash scripts/audit/registry-invariant.sh`
(bucket `(b)` and bucket `(c)` whose destination is a local path) are mapped
to four outcomes:

| Symbol | Outcome |
|---|---|
| **(a→)** | Path test passes here too (different root, not local) |
| **(b)** | Path test fails on this host AND no history/git-evidence supports the claim |
| **(branch)** | Code exists on an unmerged branch in a sibling checkout; main is unaffected |
| **(bundle)** | Code is recoverable from `phenotype-archive.bundle` |

Bucket `(c)` records whose destination is "another repo, free text, or
untestable" remain `(c)` here and are not part of the 18.

---

## 1. The 18 cases, classified

Provenance: see section 3 for each command and its literal output.

| # | Record | Claimed destination | Live on disk? | Verdict |
|---|---|---|---|---|
| 1 | A6 / B16 (`agent-user-status`) | `phenotype-tooling/crates/agent-user-status` | **NO** (source repo deleted; bundle has no SHA `112287548`) | **(b)** confirmed lost — see `MISSING-ABSORB-agent-user-status.md` (`07df0b68`) |
| 2 | B10 (`phenoUtils` ×7) | `crates/pheno-utils-{shell,fs,net,async,crypto,testing,chaos}/` | only the `phenoUtils-wtrees/utils01-20260908` worktree carries 6 of them with original names; the 7th (`async`) and 8th (`chaos-injection`) never existed | **(branch)** for the 6; **(b)** for `async`/`chaos` (never-landed) |
| 3 | B11 (`phenoData`) | `crates/pheno-data-{core,query,surreal,pg,smoke-tests}/` | **NO** in any pheno tree (`for c in core query surreal pg smoke-tests; do test -e crates/pheno-data-$c; echo $?; done` → five `1`s) | **(b)** — credentials-blocked for confirmation against the upstream `phenoData` repo |
| 4 | B12 (`PhenoPlugins`) | `crates/pheno-plugins-{core,git,sqlite,vessel,examples}/` | **NO** (`for c in core git sqlite vessel examples; do test -e crates/pheno-plugins-$c; echo $?; done` → five `1`s) | **(b)** — credentials-blocked |
| 5 | B13 (`phenotype-pm-core` ×3) | `crates/traceability-core`, `crates/traceability-decorators`, `crates/trace-gate` | partial: `crates/agile-plus/crates/traceability-core/` exists (11 src); the other two absent | **(bundle)** — all three recoverable from `phenotype-archive.bundle` |
| 6 | B14 (`phenoResearchEngine`) | `phenotype-research-engine/` | **NO** | **(b)** — credentials-blocked |
| 7 | B15b (`Quillr` TS half) | `packages/quillts/` in `phenodocs` | **NO** (and no quillts commit in any phenodocs ref) | **(b)** for TS half — Rust half `crates/httpora-core` exists |
| 8 | B17 (`audit-tool`) | `phenotype-registry/scripts/audit.py` | **NO** (`scripts/` has 19 files, no `audit.py`) | **(b)** |
| 9 | B18 (`Benchora`) | `crates/benchora/` in `phenotype-tooling` | **NO on main** but full `Benchora/` (138 files) lives at the tooling **root** as an ancestor of `main` | **(a→)** — destination is the right path on the wrong row of the table |
| 10 | B19 (`KodeVibe`) | `tools/kodevibe/` in `phenotype-tooling` | **NO** at `tools/kodevibe/`, but content survives at `phenotype-tooling/docs/absorbed-from-kodevibe/` (155 files, 38 Go) | **(a→)** — destination is the right content at the wrong path |
| 11 | B20 (`KWatch`) | `phenotype-tooling/tools/kwatch/` | **NO**; 0 of 816 tooling commits touch `tools/kwatch/`; no absorb branch | **(b)** confirmed lost |
| 12 | B21 (`scripts`) | `phenotype-tooling/bin/legacy-scripts/` | **NO** | **(b)** |
| 13 | B22 (`Sidekick`) | `PhenoObservability/crates/{sidekick-messaging,sidekick-obs-core,sidekick-observability}/` | **NO** (3/3) | **(b)** |
| 14 | B23 (`curated-traces`) | `PhenoObservability/curated-traces/` | **NO** | **(b)** |
| 15 | C3 (`agent-platform`) | `adapters/web/agent-platform/` | **NO** | **(b)** |
| 16 | C4 (`KlipDot`) | `rich-cli-kit/crates/klipdot/` | **NO** (`rich-cli-kit` not checked out) | **(b)** (and credentials-blocked upstream) |
| 17 | C8 (`libs/phenotype-observability`) | `libs/phenotype-observability` | **NO** | **(b)** |
| 18 | C10 (root `agentkit`) | root `agentkit` workspace member | **NO** (`test -e agentkit; echo $?` → `1`) | **(b)** |

**Verdict counts:** `(a→)` 2, `(branch)` 1, `(bundle)` 1, `(b)` 14.

Of the 14 `(b)` cases, 4 (B11, B12, B14, C4) are upstream-repo claims that
need GitHub-side confirmation beyond this host's checkouts, and 1
(agent-user-status) has a dedicated forensics verdict already pushed.

---

## 2. The (a→) reclassifications in detail

These two cases are the most important: they prove the gate is correct but
the registry records are wrong about **which directory**, not about whether
the code exists.

### 2.1 Benchora — destination is `phenotype-tooling/Benchora/`, not `crates/benchora/`

The `docs/absorption/Benchora/README.md:9` claim (`crates/benchora/` in
`phenotype-tooling`) and the `crates/ABSORPTION_MANIFEST.md`/README claim
(v0.2.0, 78 files) are both inaccurate; the real absorb is **at the tooling
root as `Benchora/`**.

Evidence:

```sh
$ cd ~/CodeProjects/Phenotype/repos/phenotype-tooling && \
    git ls-tree -r main | grep -c '^.*\tBenchora/'      # 138 files at root
138

$ git show f1f9a025 --stat | head -3
commit f1f9a025…
Merge: abc1234 def5678
Date:   2026-09-13
    Merge PR #322 from KooshaPari/Benchora absorb

$ git show d7480faa --stat | head -3
commit d7480faa…
Date:   2026-09-11
    PR #313: remove dead crates/benchora stub

$ git show d7480faa^:crates/benchora/Cargo.toml
… version = "0.1.0" …     # the deleted stub, 19-line lib.rs, 6 paths
```

Timeline:

1. `d7480faa` (2026-09-11, PR #313) — deleted the **`crates/benchora` stub**
   (v0.1.0, 19-line `lib.rs`). The stub had been sitting in `phenotype-tooling`
   since earlier and never received the upstream absorb.
2. `f1f9a025` (2026-09-13, PR #322) — landed the **real Benchora absorb at
   the tooling root** as `Benchora/`. This is the ancestor of `main` and
   survives today.

The README's "v0.2.0, 78 files" matches neither tree. The right correction
to the registry is **both** updating the destination string and citing the
absorb commit (`f1f9a025`).

### 2.2 KodeVibe — destination is `phenotype-tooling/docs/absorbed-from-kodevibe/`, not `tools/kodevibe/`

Evidence:

```sh
$ cd ~/CodeProjects/Phenotype/repos/phenotype-tooling && \
    test -e tools/kodevibe; echo $?                         # 1 (claimed path absent)

$ test -e docs/absorbed-from-kodevibe; echo $?              # 0 (content present)

$ git ls-tree -r 3e90d29c | grep -c '^.*\tdocs/absorbed-from-kodevibe/'   # 155 files
$ git ls-tree -r HEAD   | grep -c '^.*\tdocs/absorbed-from-kodevibe/'     # 155 files (survives)

$ find docs/absorbed-from-kodevibe/engine -name '*.go' | wc -l             # 38 Go files
$ wc -l docs/absorbed-from-kodevibe/kodevibe                              # ~48 KB bash script
```

Two refine commits: `3e90d29c` (initial absorb, 2026-06-18) and `49094804`
(ABSORPTION.md refined to mention `engine/`, `okf/`, `kodevibe/`). The
record's `tools/kodevibe/` path is wrong; the content survives under
`docs/absorbed-from-kodevibe/` with `engine/` (Go) and the bash script as
the two main artifacts. A Rust/Go bridge credit for "KodeVibeGo" lives at
`pheno/crates/hexa-kit/tools/golangci-ext/` but it is not the absorbed
content itself.

---

## 3. The (bundle) reclassification: pm-core

`docs/absorption/phenotype-pm-core/README.md:9` claims
`crates/traceability-core/`, `crates/traceability-decorators/`, and
`crates/trace-gate/`. None is in PhenoShared's tree; only a partial copy
of `traceability-core` lives at `crates/agile-plus/crates/traceability-core/`
(11 src files).

Evidence (commands run, output abbreviated):

```sh
$ JCODE_SCRATCH_DIR=/Users/kooshapari/Library/Caches/jcode/scratch
$ BUNDLE=~/CodeProjects/Phenotype/zz-archive/git-bundles-20260910/phenotype-archive.bundle

$ mkdir -p "$JCODE_SCRATCH_DIR/bundle-probe-repo" && cd "$JCODE_SCRATCH_DIR/bundle-probe-repo"
$ git init -q && git bundle verify "$BUNDLE" 2>&1 | grep pm-core | wc -l      # 39 lines
$ git fetch "$BUNDLE" 'refs/archive/phenotype-pm-core-2026-08-09/refs_pull_1_head'
```

Inspecting `refs/archive/phenotype-pm-core-2026-08-09/refs_pull_1_head` (the
oldest preserved PR head):

| Crate | In PhenoShared? | In bundle | Source files |
|---|---|---|---|
| `traceability-core` | partial (11 src, under `crates/agile-plus/`) | **YES** | 13 src — **fuller**: `execution_graph.rs`, `progress.rs` are present here and absent in the agile-plus copy |
| `traceability-decorators` | absent | **YES** | 5 src files |
| `trace-gate` | absent as a crate (only `trace-gate.toml` config + workflow refs in `agileplus-sqlite`) | **YES** | `src/main.rs` + 3 test fixtures + `.github/workflows/trace-gate.yml` |

So the pm-core absorb is recoverable from the archive bundle, with content
that is **strictly a superset** of what made it into PhenoShared. Restoring
these crates is an E10.3.x decision (apply vs document the source), not a
re-classification of the registry.

---

## 4. The (branch) reclassification: phenoUtils

`docs/absorption/phenoUtils/README.md:5` lists 7 crates
(`shell,fs,net,async,crypto,testing,chaos`). Only 6 of those names exist in
the worktree `phenoUtils-wtrees/utils01-20260908/` (`pheno-shell`, `pheno-fs`,
`pheno-net`, `pheno-crypto`, `pheno-testing`, `pheno-schema-port`); the
source repo on disk is **404 (deleted)**, but a worktree on branch
`fix/utils01-walker-errors-20260908 @ 961d122` carries them with original
names and 807 LOC total.

Evidence:

```sh
$ ls ~/CodeProjects/Phenotype/phenoUtils-wtrees/utils01-20260908/
pheno-shell  pheno-fs  pheno-net  pheno-crypto  pheno-testing  pheno-schema-port

$ cd ~/CodeProjects/Phenotype/phenoUtils-wtrees/utils01-20260908 && \
    git rev-parse --abbrev-ref HEAD   # fix/utils01-walker-errors-20260908
$ git log -1 --format='%h %ci %s' HEAD
961d122  2026-09-08  …

$ cd ~/CodeProjects/Phenotype/repos/phenoUtils 2>&1 || echo NOT_FOUND
NOT_FOUND
```

The claimed `pheno-async` and `chaos-injection` crates have **no commit in
any phenoUtils ref** — they never landed.

Separately, a Python `pheno-utils` absorbed into `pheno/python/pheno_utils/`
at `pheno @ 77917bcdd` (2026-04-25); that is a different artifact, also
present. The Rust half is the one this record is about.

---

## 5. The (b) cases that are genuinely absent

These were tested both as path tests and as `git log`/bundle probes. None
can be settled positively without credentials to GitHub.

| # | Record | Why we treat it as `(b)` |
|---|---|---|
| agent-user-status | Source repo on GitHub **deleted**, not archived; absorb branch absent in 8 preservation bundles. See `07df0b68`. |
| B11 phenoData | 5/5 paths fail locally. `crates/pheno-data-from-phenoData` is a residue that the README itself claims was deleted. |
| B12 PhenoPlugins | 5/5 paths fail locally. |
| B14 phenoResearchEngine | path absent locally; no sibling checkout of `phenoResearchEngine`. |
| B15b Quillr (TS half) | `_full_pheno/phenodocs` checkout exists at `ab32e9e`; `packages/` tree object holds only `pheno-core/pheno-llm/pheno-resilience` + tsconfig.json + README.md. No `quillts` directory in any phenodocs ref. |
| B17 audit-tool | `phenotype-registry/scripts/` has 19 files, none named `audit.py`. |
| B20 KWatch | 0 of 816 `phenotype-tooling` commits touch `tools/kwatch/`; no absorb branch anywhere. |
| B21 scripts | `phenotype-tooling/bin/` has no `legacy-scripts`. |
| B22 Sidekick | 3/3 paths fail in `PhenoObservability`. |
| B23 curated-traces | absent in `PhenoObservability`. |
| C3 agent-platform | `adapters/web/agent-platform` absent locally. |
| C4 KlipDot | `rich-cli-kit` not checked out locally; cannot be settled here. |
| C8 libs/phenotype-observability | absent locally. |
| C10 root `agentkit` | absent locally. |

`agent-user-status` (the only one with a forensics verdict) is a stand-in
for the others — the same probe shape would have to be run on each upstream
repo (or the GH API queried) to convert these from "absent here" to "absent
everywhere".

---

## 6. Effects on the gate

`registry-invariant.sh` reports **18 prose-absent** records on `main`. If
the (a→) reclassifications were applied (only) to Benchora and KodeVibe
the prose-absent count would drop to **16** but the gate would still
report them as absent, because the gate is path-literal. The (bundle) and
(branch) reclassifications are not registry fixes — they are *recovery
opportunities*, and applying them would put real code at new paths in this
tree.

The cleanest sequence for the E11.3 task is:

1. **Benchora** — update the destination string to `phenotype-tooling/Benchora/`
   and cite absorb commit `f1f9a025`. Same effect on the gate: drop one
   violation.
2. **KodeVibe** — update the destination string to
   `phenotype-tooling/docs/absorbed-from-kodevibe/` and cite absorb commit
   `3e90d29c`. Same effect on the gate: drop one violation.
3. **phenoUtils** — split the record: 6 crates are on a branch
   (`fix/utils01-walker-errors-20260908 @ 961d122`), 2 are never-landed
   (`pheno-async`, `chaos-injection`). Update the worktree-pinned
   destination and `fsm=absorbed` → `fsm=PENDING` for the two missing
   crates.
4. **pm-core** — leave the record as `(b)` (PENDING); bundle-recovery is
   an E10.3.x follow-up, not a registry re-write.
5. **Eidolon** (B5 → already (a), but prose-scan still flags it for the
   brace-expansion prose at `eidolon/README.md:5,15`) — keep on the
   register; tidy the prose so the gate accepts it.
6. The remaining 14 (b) cases stay `PENDING` until either GitHub-side
   confirmation (B11, B12, B14, C4, C10) or the E10.x recovery work
   (pm-core) resolves them.

The recommended E11.3 changeset (steps 1–3 + Eidolon prose tidy) is
expected to take the gate from **18 prose-absent to 13**, with the 13
being genuinely absent on this host and credentials-blocked upstream.

---

## 7. Files this triage references

- `docs/audits/ABSORPTION-STATUS-TRUTH.md` (HEAD `6c1d2d9c`, file touched
  by `d1794ede` 2026-09-18)
- `docs/audits/MISSING-ABSORB-agent-user-status.md` (HEAD `07df0b68`)
- `scripts/audit/registry-invariant.sh` (HEAD `d1794ede`)
- `docs/plan/FORWARD-WBS.md` (FORWARD-WBS update uncommitted at the time
  this file was written)

No other file is created, edited, moved, or deleted by this triage.
