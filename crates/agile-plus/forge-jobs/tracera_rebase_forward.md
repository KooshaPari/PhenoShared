# Tracera — rebase stale branches forward onto integration/consolidate

You are a forge agent working in the Tracera repo at E:/Dev/Tracera.
READ-ONLY audit lane — do NOT run cargo/git merge/commit. Write findings to E:/Dev/Tracera/docs/audit/rebase_audit.md.

## Setup
```
cd E:/Dev/Tracera
git fetch origin
```

## Problem
All 4 "safe" branches have ~85 file DELETIONS vs integration/consolidate because they
forked BEFORE those 85 files were added to integration/consolidate.
Anti-wipe gate blocks all auto-merges.

## Task
For each branch below, run the diagnostic:
- forge/tracera-ci-fix
- forge/tracera-test-infra
- forge/tracera-lint-cleanup
- forge/tracera-debt-hotspots

```
for branch in forge/tracera-ci-fix forge/tracera-test-infra forge/tracera-lint-cleanup forge/tracera-debt-hotspots; do
  echo "=== $branch ==="
  git fetch origin $branch 2>/dev/null
  dels=$(git diff --name-status origin/integration/consolidate...origin/$branch | grep '^D' | wc -l)
  adds=$(git diff --name-status origin/integration/consolidate...origin/$branch | grep '^A' | wc -l)
  mods=$(git diff --name-status origin/integration/consolidate...origin/$branch | grep '^M' | wc -l)
  echo "Deletions: $dels, Additions: $adds, Modifications: $mods"
  echo "Unique changes on branch (A+M only):"
  git diff --name-status origin/integration/consolidate...origin/$branch | grep -v '^D' | head -20
done
```

Then check: what are the 85 deleted files? Are they files that exist on integration/consolidate 
but were never on these branches (i.e., the branches are just MISSING them, not actively deleting)?
```
git diff --name-status origin/integration/consolidate...origin/forge/tracera-ci-fix | grep '^D' | head -30
```

## Key question
Can we do: `git checkout origin/forge/tracera-ci-fix` then `git merge origin/integration/consolidate --no-squash`
and preserve the branch's unique changes without losing the 85 files?
Test rebase viability (DRY RUN only):
```
git checkout -b test-rebase-dry origin/forge/tracera-ci-fix
git merge origin/integration/consolidate --no-commit --no-ff 2>&1 | tail -20
git merge --abort
git checkout integration/consolidate
git branch -D test-rebase-dry
```

## Output
Write full findings to E:/Dev/Tracera/docs/audit/rebase_audit.md including:
1. Per-branch: deletion count, actual unique adds/mods
2. Whether the deletions are "branch doesn't have these files" (safe) vs "branch actively deleted them" (unsafe)
3. Rebase dry-run result: conflicts? clean merge?
4. Recommendation: auto-merge forward, manual rebase, or cherry-pick unique changes
