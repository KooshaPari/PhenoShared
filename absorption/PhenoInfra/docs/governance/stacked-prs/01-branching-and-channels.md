# Branching and Release Channels

## Branching Baseline

- Canonical branches track `main` state.
- Feature, analysis, and QA work happens in `PROJECT-wtrees/<topic>`.
- PR prep and merges stay in stacks from worktree branches.

## Channel Rules

- `alpha`: early code, guarded by flags and unit tests.
- `beta`: feature-complete slice; integration smoke + migration checks.
- `rc`: release-candidate validation; requires rollback path.
- `canary`: selective, pre-prod exposure; strict rollback monitor.
- `release`: full gating and release checklist complete.

Do not merge alpha work into release paths.
