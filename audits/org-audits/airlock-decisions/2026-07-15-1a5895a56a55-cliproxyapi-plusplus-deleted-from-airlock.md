# cliproxyapi-plusplus (1a5895a56a55) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/1a5895a56a55.git` (bare mirror, 295.6MB)
- `~/.airlock/worktrees/1a5895a56a55/` (worktree, any size)

## Why

Push to upstream completed successfully; airlock mirror is redundant with canonical clone and GitHub recovery branch.

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `1a5895a56a55_cliproxyapi-plusplus.git.tar.zst` (295.6MB, sha256: `e079344c541bbbd25a922da4e1bf83fffbb335e6bc041e5d91b4d614d58cdec7`)
- `1a5895a56a55_cliproxyapi-plusplus.tree.tar.zst` (228.6MB, sha256: `0420e56e36b88a37a9cfaecb51e457e809213accdfca39f0081ed243afa36489`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/1a5895a56a55_cliproxyapi-plusplus.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-1a5895a56a55-cliproxyapi-plusplus-deleted-from-airlock.md`
