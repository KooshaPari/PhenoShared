# Wrapup Branch Triage

Generated: 2026-11-12
Refs examined: 19 (`origin/wrapup/*-20261108`, `origin/integration/*`)
Baseline: `origin/main` at tree `7ff6f98b2a65bbcb924f5b6e0a96273fd1df50d1`

## Why this document exists

The `wrapup/*-20261108` and `integration/*` refs accumulated during the
absorption programme. Some are snapshots whose content already landed; others
carry work that never did. Treating them uniformly -- deleting them all, or
merging them all -- is wrong in both directions. This document records a
per-branch disposition with the command that produced it, so the eventual
deletion is evidence-based.

## Method

Three checks per branch, in order of increasing cost.

**1. Supersede test (branches sharing history with main).**

```bash
git merge-tree --write-tree origin/main origin/<branch>
```

If the resulting tree equals `origin/main^{tree}` the branch introduces no
change that main lacks: every hunk is already present. This is a tree-identity
test, not a similarity heuristic.

**2. History test.** `git merge-base origin/main origin/<branch>` empty means the
ref is a snapshot of a _different_ repository root, so there is nothing to merge
and the supersede test does not apply.

**3. Absorption test (snapshot refs only).** A snapshot's files land in main
under a directory, usually renamed. So the comparison is by package name, not by
path:

```bash
git ls-tree --name-only origin/<branch>:crates          # snapshot's crate dirs
git show origin/<branch>:crates/<dir>/Cargo.toml        # its package name
git grep -h '^name = ' origin/main -- 'crates/*/Cargo.toml' 'absorption/*/Cargo.toml'
```

A package name absent from that second list means **no crate in main declares it**.
That is the only claim made here; it is not proof that the code is absent, because
code can be folded into an existing crate without keeping its name.

## Dispositions

### Summary

| Disposition                             | Count |
| --------------------------------------- | ----- |
| Superseded (adds nothing)               | 1     |
| Landed from this branch                 | 1     |
| Conflicting, partially landed           | 5     |
| Snapshot, fully absorbed                | 6     |
| Snapshot, **carries unabsorbed crates** | 2     |
| Snapshot, unclassified                  | 4     |

### Superseded

| Branch                          | Evidence                                                |
| ------------------------------- | ------------------------------------------------------- |
| `integration/absorbed-20261109` | merge-tree tree `7ff6f98b2` == main tree. Adds nothing. |

### Landed from this branch

| Branch                          | Evidence                                                                                                                                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/deny-advisory-20261108` | merge-tree tree `c2ed879ee` != main tree: adds content. Cherry-picked `9a0c9a817`, which landed the scoped GitGuardian ignore list. The `deny.toml` half (`6282f39fe`) was already in main -- the cherry-pick reported "nothing to commit". |

### Conflicting, partially landed

These five share history with main and diverge enough to conflict. Content was
landed by cherry-pick where it was still meaningful.

| Branch                                          | Status                                                                                                                                                                                                                                                                                                                                |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/pheno-20261108`                         | Partially landed. `ea45bbd30` (clippy.toml parse) landed. `c872f1f9f` (fabric-capability lint) landed. `5b0845293` (acceptance traceability test) and `385241668` (lefthook targets) were superseded by newer main-side work. `02dc21953` (eidolon/logkit/pheno-compose corrections) conflicts in 10 files and is tracked separately. |
| `wrapup/d1-nontq-20261108`                      | Superseded in substance. The only difference against main is two whitespace/rustfmt lines in `absorption/PhenoMLX-temp/perf-core/metal-runtime/src/cache.rs`; the crates it promotes already exist in main.                                                                                                                           |
| `wrapup/zz-forensic-zz-pheno-20261108`          | Conflicting, not triaged commit-by-commit.                                                                                                                                                                                                                                                                                            |
| `wrapup/vitepress-relaunch-20261108`            | Conflicting, not triaged commit-by-commit.                                                                                                                                                                                                                                                                                            |
| `wrapup/recovered-trunk-action-repair-20261108` | Conflicting, not triaged commit-by-commit.                                                                                                                                                                                                                                                                                            |

### Snapshots of a different repository root

Twelve refs have no merge base with main. Their root path collides with main's root
(`src/lib.rs`, `.gitignore`, `README.md`, `.github/*`) purely because both are
repository roots. A path-based diff therefore reports tens of thousands of spurious
"deletions"; the only meaningful comparison is by package name.

Six are fully accounted for:

| Branch                          | Evidence                                                                                                                                                                                                                                                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/apisync-20261108`       | `src/lib.rs` blob identical to `crates/apisync/src/lib.rs`.                                                                                                                                                                                                           |
| `wrapup/tokn-20261108`          | `src/lib.rs` blob identical to `crates/tokn/src/lib.rs`.                                                                                                                                                                                                              |
| `wrapup/datakit-20261108`       | `src/lib.rs` blob identical to `crates/datakit/src/lib.rs`.                                                                                                                                                                                                           |
| `wrapup/logify-20261108`        | `src/lib.rs` blob identical to **both** `crates/logify/src/lib.rs` and `crates/logkit/src/lib.rs`.                                                                                                                                                                    |
| `wrapup/phenoplugins-20261108`  | All 5 crate directories are absent under those names, but all 5 package names (`pheno-plugin-core`, `pheno-plugin-examples`, `pheno-plugin-git`, `pheno-plugin-sqlite`, `phenotype-vessel`) are declared by crates in main. Absorbed under different directory names. |
| `wrapup/phenojourneys-20261108` | All 3 crate directories exist in main.                                                                                                                                                                                                                                |

Two carry crates that **no crate in main declares**:

| Branch                               | Missing package names                                                                                                                                                                                                                                                                                                 |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/phenoobservability-20261108` | `helix-logging`, `metrickit`, `pheno-dragonfly`, `pheno-questdb`, `phenotype-llm`, `phenotype-mcp-server`, `phenotype-observably-logging`, `phenotype-observably-ports`, `phenotype-observably-sentinel`, `phenotype-observably-tracing`, `tracely-core`, `phenotype-sentinel` (dir `tracely-sentinel`), `tracingkit` |
| `wrapup/nanovms-20261108`            | `ffi_utils`, `nanovms-i18n`, `phenotype-port-adapter-shim`                                                                                                                                                                                                                                                            |

**These two must not be deleted as superseded.** The 16 packages above are the
only copy of that work in this repository. The open question is a product
question, not a git question: whether each package is still wanted. Until that is
answered, the refs are the preservation path.

Four are unclassified and need an owner decision:

| Branch                                 | Shape                                                                                                                                                                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/phenoforge-20261108`           | Documentation-only root snapshot: `ADR.md`, `PRD.md`, `SPEC.md`, `FUNCTIONAL_REQUIREMENTS.md`, `SOTA_RESEARCH.md`, `TEST_COVERAGE_MATRIX.md`, `docs/`. No `Cargo.toml`, no `crates/`.                         |
| `wrapup/phenokits-commons-20261108`    | Monorepo root snapshot declaring package `phenokits`. Main declares `hexakit`, `hexakit-cli`, and `hexagonal-rs`, but no crate declares `phenokits`. Probably absorbed under the `hexakit` name; unconfirmed. |
| `wrapup/local-ops-20261108`            | Scripts repository: `bin/`, `guards/`, `tests/`, `PROVENANCE.md`. Its `README.md` and `.gitignore` differ from main's, and it adds `tests/test_unproven_bin_guards.sh`, which main does not have.             |
| `wrapup/pheno-runtime-config-20261108` | Declares package `pheno-runtime-config`; main has `crates/pheno-runtime-config/Cargo.toml`. Directory present, 15 shared files modified, 1 file added. Worth a diff review before deletion.                   |

## Consequences

1. Deletion of the 6 fully-absorbed snapshot refs and `integration/absorbed-20261109`
   is safe and loses nothing.
2. Deletion of `phenoobservability` and `nanovms` would destroy 16 packages that
   exist nowhere else. They stay until a product decision is recorded.
3. The 4 unclassified refs need an owner; each is small enough to review individually.
4. The 3 untriaged conflicting refs (`zz-forensic-zz-pheno`, `vitepress-relaunch`,
   `recovered-trunk-action-repair`) need a commit-by-commit pass before any disposition.

## Reproduction

Every claim above is regenerated by:

```bash
git fetch origin
MAIN=$(git rev-parse origin/main^{tree})
refs=$(git branch -r --list 'origin/wrapup/*' 'origin/integration/*')
for b in $(echo "$refs" | sed 's/^ *//'); do
  mb=$(git merge-base origin/main "$b" 2>/dev/null)
  tree=$(git merge-tree --write-tree origin/main "$b" 2>/dev/null | head -1)
  [ -z "$mb" ] && echo "$b UNRELATED" || \
    { [ "$tree" = "$MAIN" ] && echo "$b SUPERSEDED" || echo "$b DIVERGES"; }
done
```

The absorption test for the snapshot refs is the `git grep -h '^name = '` package-name
list against each snapshot's `crates/*/Cargo.toml`.

---

## Addendum 2026-11-12: the three untriaged refs, triaged

Measured at blob level, not at commit level. That measurement revises one
conclusion above: **two crates absent from main were not counted**.

| Ref                                             | Commits unique to it     | Disposition                                                                                                                                                                                                 |
| ----------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wrapup/zz-forensic-zz-pheno-20261108`          | `9e1ca05fa`              | **Empty tree.** The commit deletes everything it inherited: 9,855 files, 1,764,092 deletions against parent `ab32e9ec6`. Nothing to absorb, nothing at risk; the ref records a deletion, not stranded work. |
| `wrapup/vitepress-relaunch-20261108`            | `52aaca90e`, `6695b8738` | **Not absorbed.** 369 paths exist that main does not have.                                                                                                                                                  |
| `wrapup/recovered-trunk-action-repair-20261108` | `44aa1d95a`              | **Not absorbed.** 386 paths exist that main does not have.                                                                                                                                                  |

### Where the two snapshots differ from main

| Area                                                                                       | vitepress | recovered-trunk | Reading                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------ | --------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `absorption/PhenoMLX-temp/perf-core/hwledger/`                                             | 295 paths | 295 paths       | **Pre-promotion copy.** The file set is identical to main's `crates/hwledger` (295 files each, zero branch-only paths, as `comm` reports). Content differs because main's promoted copy is the maintained one. No work at risk. |
| root snapshot files                                                                        | 55        | 58              | Main relocated them into `docs/absorbed-root-docs/`; of the 369 branch blobs, 249 are present in main at the relocated path. Older revisions.                                                                                   |
| `.github/workflows/`                                                                       | 3         | 6               | Older revisions of workflows main has since edited.                                                                                                                                                                             |
| `crates/phenotype-dag-core/`                                                               | 7         | 7               | **Absent from main.** See the correction below.                                                                                                                                                                                 |
| `crates/pheno-registry-python/`                                                            | 7         | 7               | **Absent from main.** See the correction below.                                                                                                                                                                                 |
| `tests/*.rs`, `tests/features`, `docs/adr`, `tools/integration-kit/`, `agents/phenoagent/` | 1         | 10              | Root-layout tests and ADRs from before the per-crate restructure; `tools/integration-kit/` and `agents/phenoagent/` are absent from main.                                                                                       |

### Correction: two more main-absent crates

`crates/phenotype-dag-core` (declares `name = "phenotype-dag-core"`;
description says it is a standalone crate extracted from BytePort, renamed from
`pheno-dag` on 2026-09-01) and `crates/pheno-registry-python` (declares
`name = "pheno-registry-python"`, a PyO3 SDK, `crate-type = ["cdylib"]`,
depending on `phenotype-registry` at `../..`) appear in **neither the tree nor
any manifest of `origin/main`**:

```
$ git ls-tree -r --name-only origin/main | grep -c 'crates/phenotype-dag-core/'
0
$ git ls-tree -r --name-only origin/main | grep -c 'crates/pheno-registry-python/'
0
$ git grep -l '^name = "phenotype-dag-core"' origin/main -- '**/Cargo.toml'
(no output)
```

Their module content is absent too: `dag.rs`, `scheduler.rs`, `topo.rs`,
`schema.rs`, `serialize.rs` and `lib.rs` all have blob hashes that occur nowhere
in main, and main's nearest crates (`crates/substrate-dag`,
`crates/dag-scheduler`) each hold a single `src/lib.rs`. Main nevertheless
_refers_ to both names: 25 paths mention `phenotype-dag-core` (audits plus
`cmd/dagrun` Go code) and 11 mention `pheno-registry-python` (including the
release workflow below).

Both are held redundantly, so one ref deletion cannot lose them:

| Crate                   | Refs holding it                                                                                                                        |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `phenotype-dag-core`    | `integration/absorbed-20261109`, `wrapup/{pheno,deny-advisory,vitepress-relaunch,d1-nontq,recovered-trunk-action-repair}-20261108` (6) |
| `pheno-registry-python` | `wrapup/{pheno,deny-advisory,vitepress-relaunch,d1-nontq,recovered-trunk-action-repair}-20261108` (5)                                  |

**They join `phenoobservability` and `nanovms` on the do-not-delete list**
until a product decision is recorded for each.

### A latent defect this exposed

Main's release workflow still builds the absent SDK:

```
$ git show origin/main:.github/workflows/publish-pypi.yml | sed -n '47p'
          args: --release --out dist -m crates/pheno-registry-python/Cargo.toml
```

The step only runs on `release: [published]` or `workflow_dispatch`, so nothing
is red today, but the next published release fails at wheel build because that
manifest does not exist in main. Two small remedies, neither applied here
because the choice is a product one:

1. **Restore** `crates/pheno-registry-python/` (7 files; its manifest carries an
   empty `[workspace]`, so the main workspace build is unaffected) from any ref
   in the table.
2. **Retire** the SDK: drop the workflow step and the SDK references main
   carries in `docs/atlas/codebase/`, `docs/dossiers/` and `docs/pilot/`.

### Regenerating these numbers

```bash
git ls-tree -r --name-only "origin/wrapup/<ref>" | sort > branch.txt
git ls-tree -r --name-only origin/main          | sort > main.txt
comm -23 branch.txt main.txt                     # paths main does not have
git ls-tree -r origin/main | awk '{print $3}' | sort -u > main-blobs.txt
# then test each branch blob for membership
git diff --stat ab32e9ec6 9e1ca05fa              # the empty-tree commit
for r in $(git branch -r --list 'origin/wrapup/*'); do
  git cat-file -e "$r:crates/phenotype-dag-core" 2>/dev/null && echo "$r"
done
```
