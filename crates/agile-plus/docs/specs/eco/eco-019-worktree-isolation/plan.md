# Plan: Worktree Isolation

## Objective
Codify and enforce fresh-worktree-only code changes so canonical `main` remains integration-only.

## Scope
Applies to all Phenotype repos, agents, local implementation sessions, and CI policy gates.

## Implementation Steps
1. Document mandatory worktree creation before edits.
2. Add CI/policy checks that reject direct-to-main pushes and non-worktree branch merges.
3. Require change evidence: worktree path, branch name, and eco-017 disk-floor confirmation.
