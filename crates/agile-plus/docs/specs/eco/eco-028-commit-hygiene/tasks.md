# Tasks: Commit / Branch Hygiene

## WP-01: Conventional Commits
**Effort:** S
- [ ] T001 — Author `.commitlintrc.json` at the AgilePlus root.
- [ ] T002 — Add commit-msg hook in `.githooks/`.

## WP-02: Branch naming
**Effort:** S
- [ ] T003 — Document naming rule in `AgilePlus/docs/git-hygiene.md`.
- [ ] T004 — Add pre-push hook.

## WP-03: Stale-worktree sweep
**Effort:** S
- [ ] T005 — Author `scripts/sweep-stale-worktrees.sh`.
- [ ] T006 — Schedule weekly via cron or GitHub Action.

## WP-04: Cleanup pass
**Effort:** M
- [ ] T007 — Run `worktree-cleanup.sh` (existing) against the 130 stale + 14 merged candidates.
- [ ] T008 — Push or reset the 17 dirty-ahead divergences.

## WP-05: CI gate
**Effort:** S
- [ ] T009 — `.github/workflows/branch-hygiene.yml` flags `commits-since-pushed == 0 && uncommitted-changes > 0` on PR creation.
