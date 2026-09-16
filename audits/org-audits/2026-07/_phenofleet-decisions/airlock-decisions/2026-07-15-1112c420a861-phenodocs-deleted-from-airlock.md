# phenodocs (1112c420a861) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/1112c420a861.git` (bare mirror, 1.5MB)
- `~/.airlock/worktrees/1112c420a861/` (worktree, any size)

## Why

Push to upstream completed successfully; airlock mirror is redundant with canonical clone and GitHub recovery branch.

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `1112c420a861_phenodocs.git.tar.zst` (1.5MB, sha256: `479fe37d765fa883e9b2dd3146be5f22a91df3abaf1d29e49fb2a1102ba1d073`)
- `1112c420a861_phenodocs.tree.tar.zst` (0.3MB, sha256: `0504554dcb7b6a2ba7ca38408628284a6f681fe28e388b9bb955b96c19796207`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/1112c420a861_phenodocs.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-1112c420a861-phenodocs-deleted-from-airlock.md`
