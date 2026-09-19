# Git history integrity — PhenoShared

**Audited:** 692 commits, HEAD `a0147e56`, 29,057 tracked files, 54 branches,
6 tags, 30 merge commits, 1 root commit.

**Verdict: the tree was not replaced, history was not rewritten, and nothing
was force-pushed over.** The repo's problems are of a different kind: about
60% of its commits are squash-merged PRs (multi-commit work deliberately
collapsed), and four bulk operations were performed on the whole tree with
generic messages. One commit is outright mislabeled.

---

## 1. What was asked, and the answer

> "confirm that we didn't fuck the git tree and replace the repo, or do other
> fuckeries"

| Question | Answer | Evidence |
|---|---|---|
| Was history rewritten? | **No** | 1 root commit; no `.git/refs/original`; not a shallow clone; committer timestamps strictly monotonic along the parent chain (0 backwards steps); 0 revert commits |
| Was the repo replaced wholesale? | **No** | No commit deletes >500 files in one event; absorptions are additive commits that only add paths |
| Were branches force-pushed over history? | **No evidence** | Would require a server-side event log to prove absolutely; what is checkable locally (dangling commits, reflog discontinuities, backward committer times) shows nothing |
| Is the lineage single-rooted? | **Yes** | `git rev-list --max-parents=0` returns exactly 1 commit |
| Are redactions hiding history changes? | **No** | The PII sweeps are ordinary forward commits (`3b6d8798`, `eb6fd899`); they rewrote *content*, not history |

So the "we replaced the repo" worry is unfounded. What follows is what is
actually wrong.

---

## 2. Commits that do not follow a clean forward iterative progression

This is the requested list, grouped by kind. Counts are measured, not
estimated.

### 2.1 Squash-merged PRs — 415 of 692 commits (60%)

415 commits carry a `(#NNN)` suffix. Each is the collapsed result of a
multi-commit branch. This is the single largest deviation from incremental
history: the intermediate states were never recorded. It is a *policy* choice
(squash-merge), not corruption, and it is the reason `git log` reads as
coarse-grained. Nothing is recoverable now — the branch commits were not
preserved as refs.

### 2.2 Merge commits — 30

Ordinary `Merge remote-tracking branch 'origin/main'` commits. Linear-history
purists would call these noise; they are honest records of a diverged branch
and they are not a problem. Note that merge commits also dominate the
"largest diffs" list (e.g. `099784b7` reports 5,384 files changed — that is
the branch delta, not 5,384 edits).

### 2.3 Bulk whole-tree operations — 23 commits touching >200 files

The four that matter, all with generic messages that explain nothing:

| Commit | Date | Files | Message |
|---|---|---|---|
| `3b6d8798` | 2026-09-16 | 4,214 | `chore: PII sweep — redact names, emails, paths across all files` |
| `618ffd3c` | 2026-08-08 | 5,421 | `preserve(pheno): frontier untracked-recovery snapshot (16 commits, 5421 files) (#272)` |
| `eb6fd899` | 2026-09-16 | 1,691 | `chore: PII deep-clean pass 2 + GitHub URL restoration` |
| `5677bae9` | 2026-03-30 | 1,472 | `chore: consolidation (#439)` |

`618ffd3c` is notable: **16 commits were squashed into one** and its body is
four unrelated one-line bullets, so the actual work is unrecoverable from the
message.

### 2.4 The PII sweep, and the four commits spent repairing it

A repo-wide redaction pass on 2026-09-16 broke references, and it took four
follow-up commits to partially undo:

```
3b6d8798  chore: PII sweep — redact names, emails, paths across all files
5b903999  fix: restore GitHub URLs in Cargo.toml broken by PII sweep
ed4c0642  fix: restore GitHub URLs broken by PII sweep, unstack nested REDACTED patterns
eb6fd899  chore: PII deep-clean pass 2 + GitHub URL restoration
cc6b8e39  fix(npm): restore PII-sweep-corrupted scopes/github refs; npm audit fixes
```

Consequences still present: **2,541 tracked files contain the literal
`REDACTED`** (1,985 markdown). Most damaging is provenance: the absorption
ledger now reads `<REDACTED>/PhenoProc` where a real source path was, so the
lineage is partly unrecoverable from the docs. See
`docs/audits/PII-SWEEP-DAMAGE.md`.

### 2.5 One clearly mislabeled commit

`bc7c0ad7` (2026-06-13), subject:

```
Add unit tests for DurationExt::format_human in phenotype-time
```

It is a normal (non-merge) commit that touched **3,763 files, of which 3,757
were zero-byte additions** — a `git add -A` that swept up empty placeholder
files from `.agileplus/` scratch trees into permanent history. The message
describes a handful of test lines. This is the clearest example in the repo
of a commit whose message and tree have nothing to do with each other.

Mitigating: the empty files were mostly cleaned up in later commits — only
**13 zero-byte tracked files remain today** (`.trunk/` ×6,
`.archive/kitty-specs/**` ×6, `.vale/styles` ×1). The history entry stays.

### 2.6 Warnings suppressed rather than fixed

`d0fe3aa3` — `fix: suppress all code warnings in absorbed crates (44 -> 3
warnings)`. It did not fix 41 warnings; it added blanket
`#![allow(dead_code)]` and `#![allow(missing_docs)]` to module roots
(`crates/fabric-capture/src/main.rs`, `fabric-daemon`, `fabric-terminal`,
`fabric-terminal/tmux_capture.rs`, …). The underlying code was neither fixed
nor removed, so the gate reads green over retained dead code. Audited in
`docs/audits/PII-SWEEP-DAMAGE.md`.

### 2.7 Duplicated subjects — 19

The same subject appears more than once, which is the fingerprint of a change
being applied, lost, and re-applied:

```
5 × Merge remote-tracking branch 'origin/main'
3 × ci: add trunk.yaml
3 × ci: add renovate.json
3 × ci: add .trunk/trunk.yaml
3 × ci: add .pre-commit-config.yaml
```

Four different CI configuration files were each added three separate times.
That is branch churn (a branch was recreated rather than rebased), not data
loss — but it means "when was CI added?" has no single answer.

### 2.8 Author/committer skew — 9 commits

Nine commits have a committer timestamp more than an hour after the author
timestamp; all cluster on 2026-03-30 → 03-31, consistent with review latency
before a squash-merge rather than a rebase (a rebase would also break the
monotonic committer ordering, and it does not).

---

## 3. What is *not* a problem, despite looking like one

- **Merge commits with enormous diffs.** `099784b7` (5,384 files) and
  `3e3cd115` (2,441) are `Merge remote-tracking branch` commits. Their stat is
  the branch delta, not an edit.
- **`c8715972` / `62368071`** (757 / many files, 2026-09-17): archive path
  shortening for the Windows 260-char limit. Message matches the change.
- **The absorption commits.** Each is additive, well-titled, and scoped to
  its source project (`208b0523` PhenoAI, `33673213` Substrate, `f6ab4cdb`
  PhenoRegistry, `6c9b79ca` PhenoInfra, `a2437820` PhenoLab, `365a3572`
  PhenoFabric, `7a8ef302` PhenoMLX, `9afc0cd4` PhenoDesign, `25c8dde1`
  PhenoGfx, `248874cd` Pine, `df365465` PhenoContracts, `121f79f6` stashly,
  `76cb136b` Apisync, `9b9275f0` Configra, `c3f47016` substrate-family,
  `2fe6b59a` eyetracker). See `docs/absorption/ABSORPTION-LINEAGE.md`.

---

## 4. Repair guidance

**Do not rewrite history.** The 692-commit ledger is append-only and shared;
`git filter-repo` to drop `bc7c0ad7`'s empty files or to un-redact paths would
invalidate every clone and every SHA referenced in this document. Fix forward.

Cheap and safe, in order:

1. Delete the 13 remaining zero-byte files (they are noise; check each first).
2. Repair the redaction damage that is still resolvable: restore source paths
   in the absorption ledgers where the original is known from `git log`.
   Everything else in the 2,541 files needs classification first — see the
   sweep audit.
3. Replace the `#![allow(dead_code)]` blanket suppressions with either real
   deletion or a scoped `#[allow]` plus a comment saying why the code stays.
4. Add a `CONTRIBUTING`-level rule: bulk operations (sweeps, imports,
   formatting) must state their scope and their verification in the message.
   All four bulk commits above are unreadable a year later.
5. Consider stopping squash-merge for this repo if incremental history matters
   for auditability; otherwise record it as policy so the shape is expected.

**Unrecoverable:** the 16 commits collapsed into `618ffd3c`, the intermediate
states of 415 squashed PRs, and any provenance path the PII sweep redacted
without a recorded original.
