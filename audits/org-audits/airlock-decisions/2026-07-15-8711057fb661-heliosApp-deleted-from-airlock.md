# heliosApp (8711057fb661) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/8711057fb661.git` (bare mirror, 33.4MB)
- `~/.airlock/worktrees/8711057fb661/` (worktree, any size)

## Why

Push to upstream completed successfully; airlock mirror is redundant with canonical clone and GitHub recovery branch.

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `8711057fb661_heliosApp.git.tar.zst` (33.4MB, sha256: `d5c26a4aebd638abb4666855e5f1626e9573bd3e3211d5dac3793167bb9f09c4`)
- `8711057fb661_heliosApp.tree.tar.zst` (2.1MB, sha256: `d2383755ac6d9bf0fc26cd2e012a428a0f577f901313275955a27fec0d323a1e`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/8711057fb661_heliosApp.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-8711057fb661-heliosApp-deleted-from-airlock.md`
