# 100-Task WBS/PERT DAG — pheno-harness v0.15 (2026-08-12)

**Status:** forward plan from v0.14.
**Owner:** forge (pheno-harness) <forge@phenotype.local>
**Driver:** `proc` / `proc all` / `proc <id>`.

> v0.15 picks up v0.14 carry-over:
> 1. **Cross-repo PR merge close-out** (10 PRs, task 65 gate — long-overdue).
> 2. **Production dual-write enable** (task 20 — long-overdue).
> 3. **External MCP consumer hardening** (post-audit follow-ups).
> 4. **v0.14.1 patch cycle** (any final regressions).
> 5. **Ship v0.15**.

## Phase overview

| Phase | Tasks | Theme |
|-------|-------|-------|
| 0 | 1-5 | v0.14 close-out + tag hygiene |
| 1 | 6-20 | Tracera prod-enable: live cohort + runbook |
| 2 | 21-35 | AgilePlus adapter expansion + consumers |
| 3 | 36-50 | Forge launchd final: PagerDuty + Slack integration |
| 4 | 51-65 | Cross-repo PR merges (when auth) |
| 5 | 66-75 | External MCP consumer hardening |
| 6 | 76-88 | Test sweep hardening v4 (post-prod) |
| 7 | 89-95 | portage 0.1.44 + DAG-final |
| 8 | 96-100 | Ship v0.15 |

## Phase 0 — v0.14 close-out (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | audit v0.14 phases 3, 5, 6, 7 final state | — | ac_v1 |
| 2 | confirm v0.14 tag pinned at final commit | 1 | ac_v1 |
| 3 | regenerate v0.14 release notes (final) | 2 | ac_v1 |
| 4 | verify hermetic ≥ 190 tests in runner | 3 | ac_test |
| 5 | write v0.15-plans backfill doc + closure note | 4 | ac_v1 |

## Phase 1 — Tracera prod-enable (15 tasks)

Carry from v0.13 with v0.14 deltas.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6-19 | (re-run v0.13/14 phase 1 with v0.15 prod-hardening deltas) | — | ac_v1 |
| 20 | enable dual-write in production (with auth) | 19 | ac_v1 |

## Phase 2 — AgilePlus adapter expansion (15 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 21-35 | (re-run v0.13/14 phase 2 with v0.15 adapter deltas) | — | ac_v1 |

## Phase 3 — Forge launchd final (15 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 36-50 | (re-run v0.13/14 phase 3 with v0.15 PagerDuty/Slack deltas) | — | ac_v1 |

## Phase 4 — Cross-repo PR merge (15 tasks, auth-gated)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 51-65 | (re-run v0.13/14 phase 4 with v0.15 PR list deltas) | — | ac_v1 |

## Phase 5 — External MCP consumer hardening (10 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 66-75 | (re-run v0.14 phase 5 with v0.15 hardening deltas) | — | ac_v1 |

## Phase 6 — Test sweep hardening v4 (13 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 76-88 | (re-run v0.14 phase 6 with v0.15 hardening deltas) | — | ac_v1 |

## Phase 7 — portage 0.1.44 + DAG-final (7 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 89-95 | (portage 0.1.44 prod + DAG-final) | — | ac_v1 |

## Phase 8 — Ship v0.15 (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | refresh v0.15 release notes | 95 | ac_v1 |
| 97 | regenerate v0.16 WBS plan | 96 | ac_v1 |
| 98 | move `v0.15-pheno-harness-summit` tag | 97 | ac_v1 |
| 99 | push v0.15 tag to origin | 98 | ac_v1 |
| 100 | write `docs/postmortems/2026-08-12-v0.15-closeout.md` | 99 | ac_v1 |

Refs: v0.15-task-{01..100}.
