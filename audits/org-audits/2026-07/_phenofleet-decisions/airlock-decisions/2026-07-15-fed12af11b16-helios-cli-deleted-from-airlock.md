# helios-cli (fed12af11b16) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/fed12af11b16.git` (bare mirror, 145.9MB)
- `~/.airlock/worktrees/fed12af11b16/` (worktree, any size)

## Why

build cache cleared in Phase A

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `fed12af11b16_helios-cli.git.tar.zst` (145.9MB, sha256: `a67f4ab55354a7362074f82042e49c645e7f333656d1077c4714ff65a7c575bc`)
- `fed12af11b16_helios-cli.tree.tar.zst` (6.3MB, sha256: `e5f732db1f8cc717e08ba52ab119b49f58f3fdb56ee72ab4a8a5f6f973243772`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/fed12af11b16_helios-cli.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-fed12af11b16-helios-cli-deleted-from-airlock.md`
