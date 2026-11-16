# Worktree Discipline

**Last Updated**: 2026-04-02
**Applies to**: All repos in phenotype-infrakit, thegent, heliosCLI, heliosApp

## Overview

This document establishes the worktree management rules to prevent the accumulation of stale worktrees and ensure clean, organized parallel development.

## The Problem (Historical)

As of 2026-04-02, the repos shelf had:
- 3 empty worktree directories (docs/, infrastructure/, phenotype-errors/)
- 1 detached HEAD worktree (cache-adapter-impl)
- Multiple worktrees with stale branches
- Total disk waste: ~2 GB in orphaned worktrees

## Worktree Rules

### 1. One Worktree Per Active Feature

**Rule**: Create one worktree per active feature branch you're working on.

**Maximum**: 3 concurrent worktrees per repository

```bash
# Good: Active feature work
git worktree add .worktrees/feat/user-auth -b feat/user-auth
git worktree add .worktrees/fix/memory-leak -b fix/memory-leak

# Bad: Too many worktrees
git worktree add .worktrees/feat/idea-1 -b feat/idea-1
git worktree add .worktrees/feat/idea-2 -b feat/idea-2
git worktree add .worktrees/feat/idea-3 -b feat/idea-3
git worktree add .worktrees/fix/bug-1 -b fix/bug-1
# ^^^ Don't do this. Finish or abandon ideas before starting new ones.
```

### 2. Clean Up After Merge

**Rule**: Remove worktree within 48 hours of branch merge.

```bash
# After PR is merged
git worktree remove .worktrees/feat/user-auth
git branch -d feat/user-auth  # Delete the local branch too
```

### 3. Naming Convention

**Rule**: Use consistent naming for worktrees.

```
Format: .worktrees/<type>/<description>

Types:
- feat/   - Feature development
- fix/    - Bug fixes
- chore/  - Maintenance tasks
- docs/   - Documentation updates
- spike/  - Research/experimental work

Examples:
- .worktrees/feat/health-checker-timeout
- .worktrees/fix/gitignore-case
- .worktrees/chore/update-deps
```

### 4. No Detached HEADs

**Rule**: Never leave worktrees in detached HEAD state.

```bash
# Check if worktree is detached
cd .worktrees/feat/my-feature
git branch --show-current
# If empty, you're in detached HEAD - fix it!

# Fix: Create branch from current commit
git checkout -b feat/my-feature-recovered
```

### 5. Prune Stale Worktrees

**Rule**: Run worktree audit weekly.

```bash
# List all worktrees with their state
git worktree list

# Identify stale worktrees (not on main, no recent commits)
for dir in .worktrees/*; do
  echo "=== $dir ==="
  cd "$dir" && git log --oneline -1 && cd - > /dev/null
done

# Remove stale worktrees
git worktree remove .worktrees/stale-feature
```

## Quick Commands

```bash
# List all worktrees with last commit
git worktree list --porcelain | grep -E "(worktree|HEAD|branch)"

# Create new worktree from main
git worktree add -b feat/new-feature .worktrees/feat/new-feature main

# Remove worktree (fails if uncommitted changes)
git worktree remove .worktrees/feat/old-feature

# Force remove (discards uncommitted changes)
git worktree remove -f .worktrees/feat/abandoned

# Prune worktrees with missing directories
git worktree prune
```

## Audit Checklist (Run Weekly)

- [ ] List all worktrees: `git worktree list`
- [ ] Check for empty directories in `.worktrees/`
- [ ] Verify no detached HEADs
- [ ] Confirm merged branches have their worktrees removed
- [ ] Check worktree age: `find .worktrees -maxdepth 1 -type d -mtime +7`

## Recovery Procedures

### Recover From Detached HEAD

```bash
cd .worktrees/detached-worktree
git checkout -b feat/recovered-$(date +%Y%m%d)
git push origin feat/recovered-$(date +%Y%m%d)
# Create PR from recovered branch
```

### Clean Up Orphan Worktrees

```bash
# Find worktrees not registered in git
git worktree prune --dry-run

# Actually prune them
git worktree prune

# Remove empty directories
find .worktrees -type d -empty -delete
```

## Emergency Cleanup

If worktrees have accumulated and you need to clean up:

```bash
# WARNING: Destructive - removes ALL worktrees except main
# Use only in extreme situations

cd /Users/<REDACTED>/CodeProjects/Phenotype/repos

# 1. List all worktrees except main
git worktree list | grep -v "$(pwd) " | awk '{print $1}'

# 2. Remove each (check for uncommitted work first!)
for wt in $(git worktree list | grep -v "$(pwd) " | awk '{print $1}'); do
  echo "Checking $wt..."
  cd "$wt" && git status --short && cd - > /dev/null
done

# 3. If all clear, remove them
for wt in $(git worktree list | grep -v "$(pwd) " | awk '{print $1}'); do
  git worktree remove "$wt" 2>/dev/null || git worktree remove -f "$wt"
done

# 4. Clean up empty directories
find .worktrees -type d -empty -delete 2>/dev/null
```

## References

- [Git Worktrees Documentation](https://git-scm.com/docs/git-worktree)
- `docs/sessions/20260402-polyrepo-audit/` - Worktree audit results
- Spec 021: Polyrepo Ecosystem Stabilization
