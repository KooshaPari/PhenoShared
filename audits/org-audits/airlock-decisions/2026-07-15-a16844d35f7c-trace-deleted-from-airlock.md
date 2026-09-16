# trace (a16844d35f7c) — DELETED FROM ~/.airlock/

**Date**: 2026-07-15
**Type**: orphan

## What was deleted

- `~/.airlock/repos/a16844d35f7c.git` (bare mirror, 668.3MB)
- `~/.airlock/worktrees/a16844d35f7c/` (worktree, any size)

## Why

REST API: 19 refs on Tracera

## Recovery

Tarballs preserved at `_phenofleet-decisions/airlock-phase-b-archived/`:

- `a16844d35f7c_trace.git.tar.zst` (668.3MB, sha256: `d1f1aad663a58a57c14bd00357d1f285ce92481eecd7d706abc2e23a00a7ec9d`)
- `a16844d35f7c_trace.tree.tar.zst` (474.4MB, sha256: `b32e5577f2316338038e7035e78081691d48447b9fbd4cd1c093ae5ca7f785df`)

Restore:
```bash
cd /Users/kooshapari/.airlock/repos
tar --zstd -xf /Users/kooshapari/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-phase-b-archived/a16844d35f7c_trace.git.tar.zst
```

## GitHub-side recovery branches

See `.airlock-phase-c2-push-audit-2026-07-15.json` for orphan pushes; `.airlock-phase-b1-push-audit-2026-07-15.json` for redundant pushes.

## Cross-ref

Decision file: `_phenofleet-decisions/airlock-decisions/2026-07-15-a16844d35f7c-trace-deleted-from-airlock.md`
