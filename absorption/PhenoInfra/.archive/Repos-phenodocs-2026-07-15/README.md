# `Repos-phenodocs-2026-07-15` — Absorbed Uncommitted Snapshot

This directory preserves the contents of
`KooshaPari/zz-archive-Repos-phenodocs-uncommitted-2026-07-15` (archived
2026-07-15), which was a snapshot of uncommitted and unpushed work in
`/Users/kooshapari/Repos/phenodocs/` taken on 2026-07-15.

**Date merged:** 2026-08-08
**Source commit:** `KooshaPari/zz-archive-Repos-phenodocs-uncommitted-2026-07-15@main`
**Merger:** forge-airlock (manual semantic integration)

## What this archive was

A working-tree + 41-ahead-branch snapshot of the **secondary** phenodocs
working tree at `/Users/kooshapari/Repos/phenodocs/` (note: `Repos/`, not
`CodeProjects/Phenotype/repos/`). At the time of capture:

- **Branch:** `main` with **41 commits ahead** of `KooshaPari/phenodocs origin/main`,
  110 commits behind
- **3 modified files:** `agents.lock`, `agents.toml`, `scripts/check_docs_links.py`
- **28 untracked files** under `docs/sessions/2026-02-26-cliproxy-*` (4 sessions × 7 docs each)
- **5 untracked support files:** `scripts/__init__.py`, `tests/__init__.py`,
  `tests/test_check_docs_links.py`, etc.

## What was merged into live phenodocs

### 24 unique dirty docs (already in live paths)

The 24 docs (01-06 across 4 sessions) were **MISSING** from live phenodocs
(which only had the `00_SESSION_OVERVIEW.md` per session). They have been
copied directly into `docs/sessions/2026-02-26-cliproxy-*/`:

- `docs/sessions/2026-02-26-cliproxy-thegent-agentapi-reconcile/{01-06}*.md`
- `docs/sessions/2026-02-26-cliproxy-thegent-agentapi-cleanup-pass/{01-06}*.md`
- `docs/sessions/2026-02-26-cliproxy-thegent-agentapi-reconcile-v2/{01-06}*.md`
- `docs/sessions/2026-02-26-cliproxy-thegent-agentapi-reconcile-v3/{01-06}*.md`

### 2 patches + 2 tarballs (preserved as archive materials)

- `patches/0001-feat-add-L7-001-intent-boundary-snapshot-docs.patch`
  (commit `25832f00...`, 2026-06-18 — adds `docs/boundary/phenodocs.md` +
  `docs/intent/phenodocs.md`)
- `patches/0002-chore-templates-absorb-pheno-cargo-template-as-templ.patch`
  (commit `727f16da...`, 2026-06-20 — absorbs `pheno-cargo-template` into
  `templates/rust-crate/`, 28 unique files + 37 excluded as
  INTENTIONALLY_DEPRECATED)
- `Repos-phenodocs-41-ahead-patches.tar.gz` (437 KB — full 40-patch bundle
  covering 40 of the 41 ahead commits)
- `dirty-files-2026-07-15.tar.gz` (43 KB — the modified + untracked files)

### 6 dirty files (preserved as diff artifacts, NOT replacing live)

These files had **divergent content** between archive and live (live is
newer). The archive version is preserved here for diff/audit:

- `agents.lock` — archive has additional `agileplus-shard-lock-dag` entries
- `agents.toml` — archive has additional `[[skills]]` for
  `agileplus-shard-lock-dag`
- `scripts/check_docs_links.py` — divergent
- `scripts/__init__.py`, `tests/__init__.py`, `tests/test_check_docs_links.py` — divergent

**Decision:** the live versions were kept as-is (they reflect post-2026-07-15
evolution). The archive versions are preserved here for reference. If a
merge is needed, the diff between `dirty-files-as-of-2026-07-15/<file>`
and `../../<file>` will show exactly what would change.

## Status

Absorbed. 24 docs merged into live `docs/sessions/`. The 2 patches and
2 tarballs are preserved as archive materials. The 6 dirty file versions
are preserved as diff artifacts.
