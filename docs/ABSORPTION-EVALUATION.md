# Absorption Evaluation — where the deleted repositories live now

**Evaluated:** 2026-11-09 07:14 UTC
**Method:** every claim below was checked against the GitHub API or a fresh clone at that time.
**Scope:** the repositories this programme absorbed, deleted, or found to be non-existent.

---

## 1. The headline

**PhenoShared is now the home of 8,683 files from five absorbed sources.** Together with
`HeliosLab/.archive/benchora/` and one restored repository, every repository this programme removed now
has its content in a versioned, GitHub-hosted place.

Nothing depends on a bundle, a local clone, or a single machine any more. That was not true when this
programme started.

---

## 2. Where each repository went

| Repository | Status on GitHub | Where its content lives | Files |
|---|---|---|---:|
| `PhenoTooling` | **restored** — private, created 2026-11-09T01:18Z, `main` @ `b9ec4220` | its own repo, **with full history and all four original branches**; also absorbed into `docs/absorbed-from-PhenoTooling/` | 30 681 |
| `zz-zz-agentcheck-PhenoTooling` | deleted by this programme, through `bin/repo-delete-gate.sh` | `docs/absorbed-from-PhenoTooling/` | 8 257 |
| `Benchora` | gone | `HeliosLab/.archive/benchora/` | 141 paths |
| `PhenoGoKit` | gone | `docs/absorbed-from-PhenoGoKit/` | 241 |
| `PhenoObservability` | gone | `docs/absorbed-from-PhenoObservability/` | 141 |
| `PhenoCompose` | gone | `docs/absorbed-from-PhenoCompose/` + 16 live crates in `crates/pheno-compose-*` | 42 |
| `zz-merge-unk-Eventra` | gone | `Eventra-archive-20261106` — 50 refs under `refs/preserved/*`, 332 commits | 130 at HEAD |
| `zz-zz-agentcheck-*` (5 others) | still archived, intact | themselves — archived is durable | — |

### PhenoShared absorbed footprint

```
docs/absorbed-from-PhenoTooling             8 257 files   70 MB
docs/absorbed-from-PhenoGoKit                 241 files   1.5 MB
docs/absorbed-from-PhenoObservability         141 files   1.1 MB
docs/absorbed-from-PhenoCompose                42 files   216 KB
docs/absorbed-from-zz-zz-agentcheck-...         1 file    4 KB
                                            ---------
                                            8 683 files  ~73 MB
```

---

## 3. Corrections to what this programme believed

Three claims in the session record were wrong at the time they were written. They are corrected here
rather than left to mislead a later reader.

1. **"PhenoTooling is deleted; the bundle is the only copy."** False by the time it was written. The
   repository was **restored privately at 2026-11-09T01:18Z** — about an hour before the bundle loss was
   noticed — with all four original branches at their original commits, including the local-only
   `absorb-phenoUtils` (`3c993fea`). The [section 11] warning was written without re-checking whether
   the repo had come back. **Re-check existence before declaring something the last copy.**

2. **"The backup bundle cannot restore the repository."** Half true. `git bundle unbundle` extracts all
   37 826 objects and every tree is readable (30 681 files). What is missing is a **pre-boundary ancestry
   object**, which breaks commit *traversal* — so clone and push fail while the content is intact.

3. **`KooshaPari/PhenoTooling-preserved` is redundant.** Created at 06:54Z as a content-only root-commit
   snapshot (30 681 blobs). The restored `PhenoTooling` has the **same 30 681 blobs** plus real history.
   The preserved repo is kept as a second copy and should not be treated as the primary.

---

## 4. What this means for the absorption rule

The programme's rule was: never delete a repository unless (a) a manifest exists, (b) it is archived and
unprotected, and (c) its content is provably present somewhere durable. That rule held and produced the
right outcome — 8 683 files absorbed, one repository deleted, zero content lost.

What it did **not** cover, and should:

- **Re-check the source repository still exists before declaring a backup the last copy.** A single
  `GET /repos/...` would have prevented the false alarm in correction 1.
- **Distinguish content from history when judging a backup.** "Cannot clone" is not "cannot recover";
  `git bundle unbundle` plus manual refs recovers trees from a bundle that fails a clone.
- **Test the backup by cloning it, fetching every ref.** A plain clone silently takes only the default
  branch — it took 135 commits where the bundle held 332.

---

## 5. Verification commands

```bash
# absorbed footprint
git -C PhenoShared ls-tree -r --name-only origin/main -- docs/absorbed-from-* | wc -l   # 8683
git -C HeliosLab  ls-tree -r --name-only origin/main -- .archive/benchora   | wc -l     # 141

# the restored repo carries the original branches
git ls-remote --heads https://github.com/KooshaPari/PhenoTooling.git                     # 4 branches at original SHAs

# Eventra history is preserved on GitHub
git ls-remote https://github.com/KooshaPari/Eventra-archive-20261106.git 'refs/preserved/*' | wc -l   # 50

# the two PhenoTooling trees are identical in content
gh api /repos/KooshaPari/PhenoTooling/git/trees/main?recursive=1          --jq '[.tree[]|select(.type=="blob")]|length'  # 30681
gh api /repos/KooshaPari/PhenoTooling-preserved/git/trees/main?recursive=1 --jq '[.tree[]|select(.type=="blob")]|length'  # 30681
```
