# Plan: Commit / Branch Hygiene

## Objective
A fleet where every commit is conventionally named, every branch is freshly named, and no worktree is stale or dirty-ahead.

## Scope
- All Phenotype / <REDACTED> repos.
- Their worktrees.

## Implementation Steps
1. **Adopt Conventional Commits** — `commitlint` config in `AgilePlus/.commitlintrc.json`.
2. **Adopt branch naming** — `.github/branch-protection.yml` and a pre-push hook.
3. **Sweep** — `scripts/sweep-stale-worktrees.sh` runs weekly, emits JSON.
4. **CI gate** — refuse merges from branches with `commits-since-pushed < 1` and `uncommitted-changes > 0`.
5. **Refactor** — clean up the 130 stale and 14 merged candidates (after disk recovery).

## Verification
- A test commit with `WIP` is rejected.
- A test branch named `bugfix-x` is rejected.
- `sweep-stale-worktrees.sh` exits 0 after the cleanup pass.
