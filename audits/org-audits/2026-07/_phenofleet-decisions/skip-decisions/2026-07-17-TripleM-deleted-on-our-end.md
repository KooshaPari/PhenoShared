# TripleM — deleted on our end (user override, no tarball, no push)

**Date**: 2026-07-17
**Path**: `~/CodeProjects/archive/TripleM`
**Size**: 201M
**Pre-delete state**:
- HEAD: `main` at `e9d8768` ("Production Draft")
- Remotes: `origin` = `git@github.com:Dmouse92/TripleM.git` (fork parent); `upstream` = `git@github.com:KooshaPari/TripleM.git` (misconfigured alias — `KooshaPari/TripleM` does not exist as a KooshaPari native repo)
- Dirty files: 910 (uncommitted working-tree changes)
- Last 3 commits: `e9d8768` "Production Draft", `e7f11f6` "Production Draft", `26a4fc9` "Production Draft"

**User directive (2026-07-17)**: *"skip\delete triplem on our end"*

**Why no push**: The repo is a fork of `Dmouse92/TripleM`. The "upstream" remote was misconfigured to point at a non-existent `KooshaPari/TripleM`. The user explicitly chose deletion over tarballing or pushing anywhere.

**Why no tarball**: Per user override — explicit "rather than tarball properly create wip or other branches + PR \push all noted items od have remotes." TripleM has no remote the user wants work pushed to.

**Recoverability**: If the work is needed later, the original source is at `Dmouse92/TripleM` on GitHub — fork can be re-cloned from there. Local working-tree state is gone (910 uncommitted files lost per user override).

**Reversibility**: None for local state. Source fork still on Dmouse92/TripleM.

**Audit trail**: This file (in `_phenofleet-decisions/skip-decisions/`); logged in `.recovery-actions-2026-07-17.ndjson`.
