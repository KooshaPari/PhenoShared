# AgilePlus Branch Audit — 2026-05-05

**Repo:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus`
**Executed:** 2026-05-05
**Tool:** `git branch -vv --no-color`, `git branch --merged main`, `git rev-list --count`

---

## Summary

| Category | Count |
|---|---|
| Total local branches (excl. main) | 98 |
| **SAFE TO PRUNE** — merged into main, no unique commits | 1 |
| **KEEP** — ahead of main with unique commits | 92 |
| **KEEP** — ahead AND gone upstream (work unmerged) | 6 |
| Behind only | 0 |
| Diverged (ahead + behind) | 0 |

---

## SAFE TO PRUNE — Fully Merged into main

These branches contain no unique commits not already in `main`. Safe to delete with `git branch -D`.

| Branch | Unique Commits vs main | Notes |
|---|---|---|
| `cherry-mech-7` | 0 | Behind main by 3 commits; no ahead commits |

---

## KEEP — Ahead of main, unique unmerged commits

These branches have unique commits not yet merged into `main`. Do NOT delete.

| Branch | Ahead (unique) | Behind main | Notes |
|---|---|---|---|
| `fix/rust-supply-chain-agent-readiness` | 340 | 237 | Largest branch |
| `fix/policy-gate-agileplus` | 307 | 237 | |
| `<REDACTED>/commit-chain-2026-05-02` | 119 | 3 | |
| `wp-015-plugin-interface` | 117 | 3 | |
| `feat/portage-eval-suite` | 110 | 3 | |
| `chore/20260430-pin-actions-v2` | 76 | 237 | |
| `gov/trufflehog` | 68 | 3 | |
| `chore/trufflehog-bootstrap` | 63 | 3 | |
| `chore/trufflehog-clean` | 63 | 3 | |
| `spec/017-cli-tools-consolidation-expand` | 62 | 3 | |
| `spec/eco-001-expand` | 56 | 3 | |
| `spec/eco-005-expand` | 56 | 3 | |
| `spec/001-expand` | 53 | 3 | |
| `spec/002-expand` | 52 | 3 | |
| `spec/003-expand` | 52 | 3 | |
| `spec/014-observability-stack-completion` | 43 | 3 | |
| `eco-004-hexagonal-migration-kitty` | 42 | 3 | |
| `spec-015-expand` | 42 | 3 | |
| `spec/013-infrakit-stabilization-expand` | 42 | 3 | |
| `spec/016-agent-framework-expansion` | 42 | 3 | |
| `spec/021-polyrepo-ecosystem-stabilization-expand` | 42 | 3 | |
| `spec/003-platform-completion-tasks` | 41 | 3 | |
| `chore/trufflehog-20260502` | 30 | 3 | |
| `ci/quality-gate` | 29 | 3 | |
| `ci/trufflehog-final` | 27 | 3 | |
| `ci/trufflehog-gov-fix-2` | 26 | 3 | |
| `ci/trufflehog-gov-fix` | 25 | 3 | |
| `cve-cross-bump` | 20 | 3 | |
| `specs/plans-015-019-flesh-2026-04` | 20 | 3 | |
| `security/20260430-pin-actions-v2` | 19 | 3 | |
| `fix/policy-gate-v2` | 16 | 169 | |
| `fix/policy-gate-v3` | 14 | 169 | |
| `layer/agileplus-docs-spec-backfill` | 14 | 169 | |
| `agileplus/feat/docs-site` | 13 | 169 | |
| `docs/recover-user-journeys` | 13 | 165 | |
| `chore/apply-governance-standards` | 12 | 169 | |
| `release/adopt-release-cut` | 12 | 165 | |
| `chore/add-libs-cargo-toml` | 9 | 168 | |
| `chore/consolidate-changes` | 9 | 165 | |
| `fix/workpackage-builder-timestamps` | 8 | 169 | |
| `cherry/release-cut-mechanical-7` | 7 | 55 | |
| `agileplus/chore/codex-local-boot` | 6 | 169 | |
| `docs/org-maintenance-specs` | 6 | 25 | |
| `feat/bidirectional-sync-completion` | 6 | 169 | |
| `agileplus/chore/dashboard-extraction-clean` | 5 | 169 | |
| `agileplus/spec/004-modules-and-cycles` | 5 | 25 | |
| `agileplus/chore/dashboard-extraction` | 4 | 169 | |
| `agileplus/refactor/cli-event-flow-clean` | 4 | 169 | |
| `chore/pin-github-actions-20260430` | 4 | 4 | |
| `fix/task-77-contents-read` | 4 | 0 | |
| `pr-239` | 4 | 198 | |
| `agileplus/chore/runtime-local-deploy-clean` | 3 | 169 | |
| `chore/cargo-deny-fix-tonic-2026-05-04` | 3 | 2 | |
| `feat/journey-impl` | 3 | 25 | |
| `chore/container-base-bump` | 2 | 25 | |
| `chore/delete-codeowners` | 2 | 168 | |
| `chore/update-lockfile-AgilePlus` | 2 | 25 | |
| `fix/dependabot-agileplus-pyjwt-lodash` | 2 | 165 | |
| `fix/policy-gate-final` | 2 | 168 | |
| `fix/policy-gate-v4` | 2 | 168 | |
| `layer/agileplus-governance-baseline` | 2 | 169 | |
| `layer/agileplus-security-alerts-20260426` | 2 | 67 | |
| `pr-464` | 2 | 12 | |
| `preserve/local-main-divergence-20260427` | 2 | 75 | |
| `agile-fix-wt` | 42 | 3 | **EXPLICITLY KEEP** per instruction |
| `agileplus/chore/current-state-baseline-20260402` | 1 | 169 | |
| `agileplus/chore/governance-baseline` | 1 | 169 | |
| `agileplus/chore/runtime-local-deploy` | 1 | 169 | |
| `agileplus/docs/worklog-and-spec-backfill` | 1 | 169 | |
| `agileplus/feat/release-cut-workflow` | 1 | 3 | |
| `agileplus/refactor/cli-event-flow` | 1 | 169 | |
| `cherry/cargo-deny-rustls-pemfile-cleanup` | 1 | 68 | |
| `chore/deps/lodash-es` | 1 | 165 | |
| `chore/deps/pyjwt` | 1 | 165 | |
| `chore/eco-batch-supersede` | 1 | 81 | |
| `chore/spec-population-audit-20260402` | 1 | 169 | |
| `ci/cargo-deny-full-rollout-2026-04-27` | 1 | 48 | |
| `ci/cargo-deny-rollout-2026-04-27` | 1 | 48 | |
| `ci/scope-cargo-machete-workflow` | 1 | 13 | |
| `ci/trufflehog-clean` | 1 | 237 | |
| `cve-sweep-residual-2026-04-25` | 1 | 95 | |
| `docs/add-readme-20260504` | 1 | 0 | |
| `fix/dependabot-agileplus-high` | 1 | 165 | |
| `fix/duplicate-stream-route` | 1 | 82 | |
| `fix/hooks-canonical-path` | 1 | 94 | |
| `fix/policy-gate` | 1 | 168 | |
| `fmt-sweep-2026-04` | 1 | 77 | |
| `gt/birch/1eb0ee53` | 1 | 124 | |
| `hygiene/20260430-sladge` | 1 | 10 | |
| `pyjwt-fix` | 1 | 92 | |
| `spec/013-cancelled-marker` | 1 | 71 | |
| `spec/013-plan-tasks` | 1 | 84 | |
| `spec/016-plan-tasks-docs` | 1 | 83 | |
| `spec/eco-002-expand` | 1 | 237 | |
| `specs/crate-consolidation-2026-04` | 1 | 81 | |

---

## KEEP — Gone Upstream (remote branch deleted)

These branches have a `[gone]` upstream marker meaning the tracking branch no longer exists on the remote. However, they still contain unique commits not in `main`. Do NOT delete unless you confirm the work is fully merged.

| Branch | Ahead | Behind main | Tracking Remote (gone) |
|---|---|---|---|
| `chore/cargo-deny-fix-tonic-2026-05-04` | 3 | 2 | `origin/chore/cargo-deny-fix-tonic-2026-05-04` |
| `chore/container-base-bump` | 2 | 25 | `origin/agileplus/feat/docs-lockfile-update` |
| `chore/pin-github-actions-20260430` | 4 | 4 | `origin/agileplus/feat/docker-shas` |
| `fix/dependabot-agileplus-high` | 1 | 165 | `origin/agileplus/fix/high-dep-alerts` |
| `fix/duplicate-stream-route` | 1 | 82 | `origin/agileplus/fix/dashboard-route` |
| `spec/014-plan-tasks` | 1 | 83 | `origin/agileplus/spec/014-plan-tasks` |

---

## Pruning Action Taken

Only `cherry-mech-7` qualifies for deletion as it is fully merged into `main` with zero unique commits.

```bash
git branch -D cherry-mech-7
```

**Final branch count after pruning: 97 (down from 98)**

---

## Notes

- `agile-fix-wt` is ahead of main by 42 unique commits and behind by 3. Explicitly kept per instruction.
- No force-push operations were performed.
- No branch content was modified — only listing and analysis.
- Many branches are 169+ commits behind main, indicating long-stale work that may warrant future review or rebase.
