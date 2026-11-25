# Issue: 9 AgilePlus worktrees with uncommitted/stale changes

**Severity:** Medium
**Category:** Hygiene
**Reporter:** OWL (management loop)
**Date:** 2026-05-02

## Summary

9 worktrees in `AgilePlus-wtrees/` have uncommitted or unmerged changes. These represent completed or abandoned work that should either be merged, committed, or cleaned up.

## Stale Worktrees

| Worktree | Uncommitted | Notes |
|----------|-------------|-------|
| cargo-deny-full-rollout-2026-04-27 | 1 | CODEOWNERS added — merge or discard |
| container-base-bump | 11 | Dockerfile.rust modified, files deleted — needs review |
| cve-cross-bump | 1 | time crate upgrade — likely ready to merge |
| cve-sweep-residual | 10 | quinn-proto bump, files deleted — needs review |
| dep-high | 17 | 5 high-severity Rust Dependabot fixes — likely ready to merge |
| dep-pyjwt-lodash | 21 | lodash-es + pyjwt bumps — likely ready to merge |
| dup-route-fix | 10 | Route conflict fix — likely ready to merge |
| portage-eval-suite | 2 | New eval-suite spec — in progress? |
| spec-014-observability-stack-completion | 1 | spec.md modified — in progress |

## Recommended Actions

1. **Quick merges** (low risk, clear value): cve-cross-bump, dep-high, dep-pyjwt-lodash, dup-route-fix
2. **Needs review** (file deletions): container-base-bump, cve-sweep-residual
3. **In progress** (keep): portage-eval-suite, spec-014
4. **Trivial** (decide): cargo-deny-full-rollout

## Acceptance Criteria

- [ ] Each stale worktree is either merged to main or deleted
- [ ] No worktree has uncommitted changes older than 1 week
- [ ] Active worktrees documented in AgilePlus/kitty-specs/ tasks
