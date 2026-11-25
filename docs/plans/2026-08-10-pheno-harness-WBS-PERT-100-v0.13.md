# 100-Task WBS/PERT DAG — pheno-harness v0.13 (2026-08-10)

**Status:** forward plan from v0.12.
**Owner:** forge (agent CLI). **Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.
**Ac:** every task has one acceptance bullet (ac_v1 = main has the commit).

> v0.13 picks up from v0.12 with concrete themes:
> (1) ship v0.12 (tag + close-out), (2) Tracera → production rollout,
> (3) AgilePlus integration when system is ready,
> (4) forge-* launchd repair.

## v0.11 → v0.12 → v0.13 carry-over

**v0.11 close:** 100% docstring coverage, 24/24 tasks done.
**v0.12 close (in progress):**
- Phase 0, 1, 6, 7 closed (33+ tasks)
- Phase 2, 3, 4, 5, 8 in flight
- 790 tests pass, 0 flakes
- Tracera integration wired (dual-write bridge, runtime config, ingest.py)
- Hermetic subset (264 tests, 42s)

**v0.13 picks up:**
- Tag v0.12 (move from `74f31504` to current HEAD with full D-deep + Tracera)
- Close remaining v0.12 phases (2, 3, 4, 5, 8)
- Begin Tracera production rollout (was feature-flagged in v0.12)
- Begin AgilePlus integration when system is ready
- Continue forge-* launchd repair

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1–5 | v0.12 close-out audit + tag hygiene | v0.12 tag at Tracera HEAD |
| 1 | 6–20 | Tracera production rollout (gradual) | dual-write ON by default in dev |
| 2 | 21–35 | AgilePlus adapter + CLI integration (if ready) | bead-ctl.sh writes to AgilePlus |
| 3 | 36–50 | Forge launchd script bodies (close-out) | 3 forge-* scripts install + force-fire |
| 4 | 51–65 | Cross-repo PR merge close-out (when auth) | 10 v0.11 PRs merged |
| 5 | 66–75 | Cockpit deprecation ladder | cockpit → Tracera + AgilePlus |
| 6 | 76–88 | Test sweep hardening v2 (post-Tracera) | hermetic subset covers Tracera |
| 7 | 89–95 | v0.13 hardening: harbor final + MCP audit | harbor 0.1.42 prod + MCP clean |
| 8 | 96–100 | integrate & ship v0.13 | `v0.13-pheno-harness-summit` tag |

## Phase 0 — v0.12 close-out audit + tag hygiene (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | audit v0.12 phases 2, 3, 4, 5, 8 final state | — | ac_v1 |
| 2 | move v0.12 tag from `74f31504` to current HEAD | 1 | ac_v1 |
| 3 | regenerate v0.12 release notes (final) | 1 | ac_v1 |
| 4 | confirm launchd agents still loaded via `launchctl list` | 3 | ac_cron |
| 5 | write `docs/plans/2026-08-10-v0.12-backlog.md` update + closure note | 4 | ac_v1 |

## Phase 1 — Tracera production rollout (15 tasks)

v0.12 wired dual-write behind `trace_bridges.dual_write: false` (env
override `TRACERA_DUAL_WRITE=1`). v0.13 promotes to production with
gradual rollout flags.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6 | add `tracera_dual_write_default: false` schema field | — | ac_v1 |
| 7 | add per-environment overrides (dev=off, staging=on, prod=on) | 6 | ac_v1 |
| 8 | add `TRACERA_DUAL_WRITE_SAMPLE_RATE` (0.0-1.0) | 7 | ac_v1 |
| 9 | implement sample-rate emit (random skip for non-cohort) | 8 | ac_test |
| 10 | add `tests/test_tracera_dual_write_sample.py` | 9 | ac_test |
| 11 | add integration test artifact for staging env | 10 | ac_v1 |
| 12 | add Tracera deployment runbook | 11 | ac_v1 |
| 13 | add Tracera rollback procedure | 12 | ac_v1 |
| 14 | verify 750+ tests pass with dual-write ON in CI | 13 | ac_test |
| 15 | enable dual-write in dev (`config/dev.yaml`) | 14 | ac_v1 |
| 16 | document dual-write cohort policies in runbook | 15 | ac_v1 |
| 17 | add Tracera metrics to `traces/metrics.py` | 16 | ac_v1 |
| 18 | add alerting for Tracera error rate > 5% | 17 | ac_v1 |
| 19 | verify hermetic subset still passes post-rollout | 18 | ac_test |
| 20 | enable dual-write in production (with auth) | 19 | ac_v1 |

## Phase 2 — AgilePlus adapter + CLI integration (15 tasks)

(Only proceed if AgilePlus system is functional per user.)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 21 | inspect AgilePlus REST API | 20 | ac_v1 |
| 22 | scaffold `beads/agileplus_adapter.py` | 21 | ac_v1 |
| 23 | implement `AgilePlusBeadStore.append` | 22 | ac_test |
| 24 | implement `AgilePlusBeadStore.query` | 23 | ac_test |
| 25 | implement `AgilePlusBeadStore.dedup_check` | 24 | ac_test |
| 26 | implement `AgilePlusBeadStore.stats` | 25 | ac_test |
| 27 | add AgilePlus config schema | 26 | ac_v1 |
| 28 | refactor `beads/bead-ctl.sh` to dual-write | 27 | ac_v1 |
| 29 | add migration script `--from-jsonl` | 28 | ac_v1 |
| 30 | add `tests/test_agileplus_adapter.py` | 28 | ac_test |
| 31 | add `--backend=jsonl\|agileplus` flag | 28 | ac_v1 |
| 32 | add AgilePlus token rotation script | 31 | ac_v1 |
| 33 | document AgilePlus event-mapping | 31 | ac_v1 |
| 34 | verify 50 beads migrate cleanly | 32 | ac_v1 |
| 35 | add AgilePlus audit log | 34 | ac_v1 |

## Phase 3 — Forge launchd script bodies (15 tasks, close-out)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 36 | install forge-watchdog.sh script (host-side) | 20 | ac_v1 |
| 37 | install forge-net-heal.sh script (host-side) | 36 | ac_v1 |
| 38 | install forge-proc-reap.sh script (host-side) | 37 | ac_v1 |
| 39 | update 3 plists to point at real scripts | 38 | ac_v1 |
| 40 | force-fire 3 plists + verify scripts run | 39 | ac_cron |
| 41 | document forge-* scripts in `docs/guides/forge-launchd.md` | 40 | ac_v1 |
| 42 | add `scripts/forge_status.sh` unified status | 41 | ac_v1 |
| 43 | add tests for forge-watchdog thresholds | 42 | ac_test |
| 44 | add tests for forge-net-heal reachability | 42 | ac_test |
| 45 | add tests for forge-proc-reap zombie detection | 42 | ac_test |
| 46 | add cron agent for forge-* health reporting | 45 | ac_cron |
| 47 | add PagerDuty hook for forge-* failure | 46 | ac_v1 |
| 48 | add Slack notification for forge-* alerts | 47 | ac_v1 |
| 49 | document runbook for forge-* ops | 48 | ac_v1 |
| 50 | audit `forge-*` deploy | 49 | ac_v1 |

## Phase 4 — Cross-repo PR merge close-out (15 tasks)

(Only proceed with user auth for `gh pr merge`.)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 51 | audit 10 open PRs | 50 | ac_v1 |
| 52 | document PR-merge policy | 51 | ac_v1 |
| 53 | merge PRs Benchora#94 + Eidolon#148 | 52 | ac_v1 |
| 54 | merge PRs RepoLedger#20 + ResearchLedger#25 | 53 | ac_v1 |
| 55 | merge PRs Melosviz#184 + Grapheon#9 | 54 | ac_v1 |
| 56 | merge PRs pheno#276 + HexaKit#338 | 53 | ac_v1 |
| 57 | merge PRs AgilePlus#950 + OmniRoute#557 | 56 | ac_v1 |
| 58 | delete 10 merged feature branches | 57 | ac_v1 |
| 59 | verify all 10 repos build cleanly | 58 | ac_test |
| 60 | document post-merge state per repo | 59 | ac_v1 |
| 61 | close related beads via `bead-ctl.sh` | 60 | ac_v1 |
| 62 | write `docs/plans/2026-08-10-v0.11-cross-repo-merge-audit.md` | 61 | ac_v1 |
| 63 | append v0.11 cross-repo achievement to release notes | 62 | ac_v1 |
| 64 | verify v0.11 tag still resolves to a reachable commit | 63 | ac_v1 |
| 65 | close-out cross-repo work | 64 | ac_v1 |

## Phase 5 — Cockpit deprecation ladder (10 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 66 | document cockpit deprecation ladder | 65 | ac_v1 |
| 67 | add `cockpit/DEPRECATED.md` with timeline | 66 | ac_v1 |
| 68 | freeze `beads/bead-ctl.sh` to JSONL-only | 35 | ac_v1 |
| 69 | mark cockpit snapshots as read-only | 68 | ac_v1 |
| 70 | document AgilePlus import path | 35 | ac_v1 |
| 71 | add Tracera UI surface | 20 | ac_v1 |
| 72 | add AgilePlus UI surface | 35 | ac_v1 |
| 73 | update cockpit landing page | 71, 72 | ac_v1 |
| 74 | deprecate `bead-ctl.sh` after 1 cycle | 73 | ac_v1 |
| 75 | write cockpit-deprecation postmortem | 74 | ac_v1 |

## Phase 6 — Test sweep hardening v2 (post-Tracera) (13 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 76 | audit hermetic subset post-Tracera rollout | 35 | ac_v1 |
| 77 | extend hermetic subset with Tracera unit tests | 76 | ac_test |
| 78 | add `skipif_no_tracera_server` marker | 77 | ac_v1 |
| 79 | add `tests/test_runtime_config_inheritance.py` | 78 | ac_test |
| 80 | add `tests/test_tracera_bridge_concurrency.py` | 79 | ac_test |
| 81 | add `tests/test_tracera_flush_throughput.py` | 80 | ac_test |
| 82 | audit skipif consistency (v0.13 refresh) | 81 | ac_v1 |
| 83 | expand hermetic subset to 350 tests | 82 | ac_test |
| 84 | verify 850+ tests pass | 83 | ac_test |
| 85 | document hermetic testing v2 | 84 | ac_v1 |
| 86 | audit conftest (v0.13 refresh) | 85 | ac_v1 |
| 87 | add conftest isolation test (v0.13 refresh) | 86 | ac_test |
| 88 | final hermetic run (850+ pass, 0 flakes) | 87 | ac_test |

## Phase 7 — v0.13 hardening: harbor final + MCP audit (7 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 89 | verify harbor 0.1.42 (production-grade) | 88 | ac_v1 |
| 90 | install harbor in CI image | 89 | ac_v1 |
| 91 | add harbor CI smoke test | 90 | ac_test |
| 92 | document harbor install in `docs/guides/harbor-install.md` | 91 | ac_v1 |
| 93 | verify 50+ harbor-dependent tests pass | 92 | ac_test |
| 94 | add harbor health check | 93 | ac_v1 |
| 95 | audit harbor install + MCP integration | 94 | ac_v1 |

## Phase 8 — integrate & ship v0.13 (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | refresh `docs/plans/2026-08-11-v0.13-pheno-harness-summit-release-notes.md` | 95 | ac_v1 |
| 97 | regenerate `docs/plans/2026-08-11-pheno-harness-WBS-PERT-100-v0.14.md` | 96 | ac_v1 |
| 98 | move `v0.13-pheno-harness-summit` tag to final commit | 97 | ac_v1 |
| 99 | push v0.13 tag to origin | 98 | ac_v1 |
| 100 | write `docs/postmortems/2026-08-11-v0.13-closeout.md` | 99 | ac_v1 |

## Ac conventions

- `ac_v1`: commit on `main` with conventional subject + DAG id in footer.
- `ac_test`: `pytest -q tests/` exits 0 (or specific test passes).
- `ac_cron`: `launchctl kickstart -k <plist>` fires, sidecar written.

## Stats inheritance from v0.12

| Metric | v0.12 → v0.13 start |
|--------|---------------------|
| Tests | 801 (790 passed, 11 skipped, 0 flakes) |
| mypy errors | 0 |
| bandit MEDIUM | 0 |
| Public-API docstring coverage | 100% (828/828) |
| Tracera integration | dual-write bridge wired (default OFF) |
| AgilePlus integration | not started |
| Hermetic subset | 264 tests, 42s |

## Notes

- AMC / Agentora remains paused per user directive.
- Cross-repo PR merges (tasks 53-57) require user auth for `gh pr merge`.
- Forge-* launchd script installation (tasks 36-50) is host-side state mutation.
- Tracera rollout (tasks 6-20) is feature-flagged; production enable requires auth.

---

*v0.13 plan: 100 tasks, 8 phases, ~6 explicit user-auth gates, primary
themes: ship v0.12 (tag), Tracera production rollout, AgilePlus
integration (when ready), forge launchd repair, cockpit deprecation.*
