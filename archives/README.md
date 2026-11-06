# Recovered worktrees

Contents recovered from 12 repositories whose GitHub remotes were deleted (404).

## Why these are here

The sources were **shallow clones**. `.git/shallow` recorded a boundary commit whose
parent object no longer exists and never can, so `git bundle`, `git clone` and
`git push` all refused. `fast-export` drops the broken link, `fast-import` rebuilds a
valid history. 1,457 commits recovered.

They are stored on this branch rather than in their own repositories, deliberately.

## Verification

Each import was checked by **subtree-id comparison** against its source. A git
subtree id is content-addressed, so an equal id proves a byte-identical directory
rather than merely a plausible one.

**11 of 12 are identical.** Three silent data-loss bugs were found and fixed by that
check alone, each of which reported success:

| Defect | Files lost | Fix |
|---|---|---|
| `git add` honoured this repo's `.gitignore` | 51 across 8 repos | `git add -f` |
| `* text=auto eol=lf` normalised CRLF | 20 in Eventra alone | `archives/** -text -eol` |
| `git archive` honoured `export-ignore` | 35 in PhenoVCS | `checkout-index` |

Plus `$GIT_DIR/info/attributes`, because phenotype-landing's own nested
`.gitattributes` outranked the repo-level rule.

## The exception: PhenoProc

`PhenoProc` carries 12 gitlink entries (mode 160000). Submodule content was **never in
that repository** — only pointers. Ten have no `.gitmodules` entry at all;
`crates/byteport`'s recorded commit is not fetchable from its remote;
`worktree-manager` returns 404. See `PhenoProc-rb/SUBMODULES.md` for all 12 SHAs.

## `.github/` was excluded

Each archive ships `.github-EXCLUDED.txt` in place of its CI metadata. The original
workflows reference actions that no longer resolve, and this repository's
pin-integrity and lint scanners walk the entire tree. Nested workflows are inert for
execution, so nothing is lost functionally.

The full original trees, `.github/` included, are at
`CodeProjects/temp/recovery-clean-20261106/<name>-repo`.

## Restoring one

    git clone --branch chore/archives-recovered-worktrees-20261106 \
      https://github.com/KooshaPari/PhenoShared.git
    cp -R PhenoShared/archives/<name> /somewhere/<name>

To recover per-commit history, use the original recovered repo referenced above; these
archives are flat content snapshots, not history-preserving subtrees (a subtree merge
requires a clean worktree, and this repository cannot be checked out cleanly on a
case-insensitive filesystem because it contains case-colliding paths).
