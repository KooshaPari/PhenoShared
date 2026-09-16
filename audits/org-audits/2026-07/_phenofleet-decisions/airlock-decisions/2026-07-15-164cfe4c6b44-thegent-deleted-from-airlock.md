# thegent (164cfe4c6b44) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: redundant

## What was deleted

- `~/.airlock/repos/164cfe4c6b44.git` (bare mirror, 1012.8MB)
- `~/.airlock/worktrees/164cfe4c6b44/` (worktree, any size)

## Why

Push to upstream completed successfully; airlock mirror is redundant with canonical clone and GitHub recovery branch.

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `164cfe4c6b44_thegent.git.tar.zst` (1012.8MB, sha256: `bcd568d316756576dbc59e92a5eb39925a0791ca7750348f45b6920bf22d20e4`)
- `164cfe4c6b44_thegent.tree.tar.zst` (134.1MB, sha256: `24aa8f9fb5f04c10748a51f0d4c5f8586c3109c49d0b70ac9465534be128a6f9`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/164cfe4c6b44_thegent.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-164cfe4c6b44-thegent-deleted-from-airlock.md`
