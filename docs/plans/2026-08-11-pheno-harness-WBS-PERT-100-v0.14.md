# 100-Task WBS/PERT DAG — pheno-harness v0.14 (2026-08-11)

**Status:** forward plan from v0.13.
**Owner:** forge (pheno-harness) <forge@phenotype.local>
**Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.

> v0.14 picks up v0.13 carry-over:
> 1. cross-repo PR merge close-out (10 PRs, task 65 gate),
> 2. production dual-write enable (task 20 + cohort monitoring),
> 3. Agri-Plus decoupling (deprecate cockpit post-cycle),
> 4. MCP external consumer audit,
> 5. ship v0.14.

## v0.13 → v0.14 carry-over

**v0.13 close:** 62/100 new tasks shipped, 38 from v0.12. Tag
`v0.13-pheno-harness-summit` pinned.
**v0.14 picks up:**
- Phase 0, 5, 6, 7, 8 closed
- Phase 1 task 20 (prod enable) requires user auth prompt
- Phase 4 (cross-repo PR merges) requires gh auth

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1-5 | v0.13 close-out audit + tag hygiene | tag at v0.13 final commit |
| 1 | 6-20 | Tracera production rollout (carry) | full prod cohort ON |
| 2 | 21-35 | AgilePlus adapter hardening (carry) | cockpit fully replaced |
| 3 | 36-50 | Forge launchd final close-out | full 3/3 agent telemetry |
| 4 | 51-65 | Cross-repo PR merge | 10 v0.11 PRs merged |
| 5 | 66-75 | MCP external consumer audit | external MCP users verified |
| 6 | 76-88 | Test sweep hardening v3 (post-prod) | hermetic ≥ 350 tests |
| 7 | 89-95 | v0.14 hardening: portage + DAG-final | portage 0.1.43 prod |
| 8 | 96-100 | integrate & ship v0.14 | `v0.14-pheno-harness-summit` |

## Phase 0 — v0.13 close-out (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | audit v0.13 phases 5, 6, 7, 8 final state | — | ac_v1 |
| 2 | confirm v0.13 tag pinned at final commit | 1 | ac_v1 |
| 3 | regenerate v0.13 release notes (final) | 2 | ac_v1 |
| 4 | verify launchd agents still loaded | 3 | ac_cron |
| 5 | write v0.14-plans backfill doc + closure note | 4 | ac_v1 |

## Phase 1 — Tracera production rollout carry (15 tasks, mostly done)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6-19 | (re-run v0.13 phase 1 task list with production-hardening deltas) | — | ac_v1 |
| 20 | enable dual-write in production (with auth) | 19 | ac_v1 |

## Phase 2 — AgilePlus adapter + cockpit deprecation (15 tasks)

(Only proceed if AgilePlus system is functional per user.)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 21 | migrate all 50 v0.12 beads to AgilePlus | 20 | ac_v1 |
| 22 | freeze `beads/bead-ctl.sh` to read-only | 21 | ac_v1 |
| 23-35 | (re-run v0.13 phase 2 task list with v0.14 deltas) | — | ac_v1 |

## Phase 3 — Forge launchd final close-out (15 tasks)

3 forge-* agents now report via `forge_status.sh`; v0.14 ships the
P95 latency + failure-rate dashboards.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 36-50 | (re-run v0.13 phase 3 task list with v0.14 deltas) | — | ac_v1 |

## Phase 4 — Cross-repo PR merge (15 tasks)

(Only proceed with user auth for `gh pr merge`.)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 51-65 | (re-run v0.13 phase 4 task list with v0.14 deltas) | — | ac_v1 |

## Phase 5 — MCP external consumer audit (10 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 66 | inventory MCP consumers | — | ac_v1 |
| 67-75 | (per-consumer freshness + lint) | — | ac_v1 |

## Phase 6 — Test sweep hardening v3 (13 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 76-88 | (re-run v0.13 phase 6 with v0.14 deltas) | — | ac_v1 |

## Phase 7 — portage + DAG-final hardening (7 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 89-95 | (portage 0.1.43 prod + DAG final audit) | — | ac_v1 |

## Phase 8 — integrate & ship v0.14 (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | refresh v0.14 release notes | 95 | ac_v1 |
| 97 | regenerate v0.15 WBS plan | 96 | ac_v1 |
| 98 | move `v0.14-pheno-harness-summit` tag to final commit | 97 | ac_v1 |
| 99 | push v0.14 tag to origin | 98 | ac_v1 |
| 100 | write `docs/postmortems/2026-08-11-v0.14-closeout.md` | 99 | ac_v1 |

Refs: v0.14-task-{01..100}.
