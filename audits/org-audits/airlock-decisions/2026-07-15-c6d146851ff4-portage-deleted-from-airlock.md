# portage (c6d146851ff4) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/c6d146851ff4.git` (bare mirror, 14.6MB)
- `~/.airlock/worktrees/c6d146851ff4/` (worktree, any size)

## Why

wt empty (0B)

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `c6d146851ff4_portage.git.tar.zst` (14.6MB, sha256: `d47e3df1ece6aa376ba7ca5ebe0f96bfd95cc774f7cbb99173de3c7ee86f1f7c`)
- `c6d146851ff4_portage.tree.tar.zst` (0.0MB, sha256: `5589195f32cab40a35e55e79c9149aa6c34f4830b3f0ac45cfba57f77aae1dcc`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/c6d146851ff4_portage.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-c6d146851ff4-portage-deleted-from-airlock.md`
