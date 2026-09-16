# 100-Task WBS/PERT DAG — pheno-harness v0.12 (2026-08-09)

**Status:** canonical source-of-truth for the next 100 atomic tasks.
**Owner:** forge (agent CLI). **Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.
**Ac:** every task has one acceptance bullet (ac_v1 = main has the commit).

> v0.12 picks up from v0.11 with three concrete themes:
> (1) Tracera + AgilePlus integration (cockpit deprecation path),
> (2) launchd placeholder repair (forge-* scripts + airlock variants),
> (3) cross-repo PR merge close-out + post-v0.11 hygiene.

## v0.10 → v0.11 → v0.12 carry-over

**v0.10 close (tagged 2026-08-08):**
- 720 tests passing, mypy 0 errors, bandit 0 MEDIUM
- 22 TypedDicts, 5 Protocols
- 750+ tests collected; one known flake (sota cron UTC date rollover)

**v0.11 close (2026-08-09):**
- Lane A: 5 phenoforge launchd plists rewritten as valid XML
- Lane B: 5 stale branches deleted (partial: preserve-launchd-installer
  remains a frozen snapshot)
- Lane C: harbor dist-info + namespace shadow resolved (rename to harbor_cli)
- Lane D: 100% docstring coverage achieved (828/828) across pheno+bench+eval+verifier+traces
- Lane E: 6 cross-repo WBS.md files pushed (Benchora, Grapheon, Eidolon,
  RepoLedger, ResearchLedger, Melosviz)
- Lane F: 28 cross-repo type-ignores removed (15 pheno + 6 HexaKit +
  3 AgilePlus + 4 OmniRoute)
- 24/24 actionable tasks closed (B2 partial)
- 19 D-deep atomic batches (165 docstrings)

**v0.12 picks up:**
- Tracera persistent-trace-repository integration (Grapheon branch)
- AgilePlus work-tracking API integration (replace JSONL backing store)
- Forge-* launchd script bodies (currently `/usr/bin/true` placeholders)
- 10 open cross-repo PRs from v0.11 (Benchora#94, Eidolon#148,
  RepoLedger#20, ResearchLedger#25, Melosviz#184, Grapheon#9,
  pheno#276, HexaKit#338, AgilePlus#950, OmniRoute#557)
- Test sweep hardening (UTC date rollover flake + flaky benchmarks)
- b2 harbor install finalization + airlock v2 audit

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1–5 | v0.11 close-out audit + tag hygiene | v0.11 tag stable at D-deep HEAD |
| 1 | 6–20 | Tracera adapter + test suite | traces persisted to Grapheon Tracera |
| 2 | 21–35 | AgilePlus adapter + CLI integration | bead-ctl.sh writes to AgilePlus |
| 3 | 36–50 | Forge launchd script bodies | 3 forge-* scripts install + force-fire |
| 4 | 51–65 | Cross-repo PR merge close-out | 10 v0.11 PRs merged + branches deleted |
| 5 | 66–75 | Cockpit deprecation ladder | cockpit → Tracera + AgilePlus |
| 6 | 76–88 | Test sweep hardening | 0 known flakes |
| 7 | 89–95 | harbor install finalization | harbor 0.1.42 prod-ready |
| 8 | 96–100 | integrate & ship v0.12 | `v0.12-pheno-harness-summit` tag |

## Phase 0 — v0.11 close-out audit + tag hygiene (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | audit v0.11 D-deep batches 1-19 (165 docstrings across 80+ files) | — | ac_v1 |
| 2 | verify v0.11 tag at `74f31504` + write tag-move RFC if user wants `4525eacb` | 1 | ac_v1 |
| 3 | regenerate `docs/audits/v0.11-launchd-agent-audit.md` post-daemon updates | 2 | ac_v1 |
| 4 | confirm 5 phenoforge plists still loaded via `launchctl list` | 3 | ac_cron |
| 5 | write `docs/plans/2026-08-09-v0.11-backlog.md` update + closure note | 4 | ac_v1 |

## Phase 1 — Tracera adapter + test suite (15 tasks)

Tracera is the persistent trace repository (Grapheon
`feat/tracera-persistent-trace-repository` branch). Phase 1 builds a
Python adapter that mirrors `traces/` events into Tracera.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6 | clone Grapheon `feat/tracera-persistent-trace-repository` worktree | 5 | ac_v1 |
| 7 | inspect Tracera API (port, auth, schema) — write `docs/integrations/tracera-api.md` | 6 | ac_v1 |
| 8 | scaffold `pheno/trace_store/tracera.py` (TraceraAdapter skeleton) | 7 | ac_v1 |
| 9 | implement `TraceraAdapter.append_event(event: TraceEvent) -> str` | 8 | ac_test |
| 10 | implement `TraceraAdapter.query(session_id: str) -> list[TraceEvent]` | 9 | ac_test |
| 11 | implement `TraceraAdapter.flush()` (batched async write) | 10 | ac_test |
| 12 | add Tracera config to `pheno-runtime-config` schema | 9 | ac_v1 |
| 13 | add `tests/test_tracera_adapter.py` (5 unit tests + 1 integration) | 11 | ac_test |
| 14 | add `bench/results/tracera_integration_test.json` artifact | 13 | ac_v1 |
| 15 | document Tracera event-mapping in `docs/integrations/tracera-events.md` | 13 | ac_v1 |
| 16 | add `traces/tracera_bridge.py` — dual-write TraceCollector events | 14 | ac_v1 |
| 17 | add Tracera dual-write to `pheno/runtime.py` (feature-flagged) | 16 | ac_v1 |
| 18 | add Tracera cleanup to `scripts/run_*_fixture.py` (test-only teardown) | 17 | ac_v1 |
| 19 | verify all 750 existing tests pass with Tracera dual-write disabled | 18 | ac_test |
| 20 | enable Tracera dual-write for `traces/ingest.py` (production path) | 19 | ac_v1 |

## Phase 2 — AgilePlus adapter + CLI integration (15 tasks)

AgilePlus is the work-tracking system. Phase 2 replaces the JSONL
backing store with an AgilePlus API adapter.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 21 | inspect AgilePlus REST API (auth, endpoint, schema) — `docs/integrations/agileplus-api.md` | 5 | ac_v1 |
| 22 | scaffold `beads/agileplus_adapter.py` (AgilePlusBeadStore skeleton) | 21 | ac_v1 |
| 23 | implement `AgilePlusBeadStore.append(bead: Bead) -> str` | 22 | ac_test |
| 24 | implement `AgilePlusBeadStore.query(target: str) -> list[Bead]` | 23 | ac_test |
| 25 | implement `AgilePlusBeadStore.dedup_check(bead: Bead) -> bool` | 24 | ac_test |
| 26 | implement `AgilePlusBeadStore.stats() -> dict[str, int]` | 25 | ac_test |
| 27 | add AgilePlus config to `~/.agileplus/config.json` schema | 21 | ac_v1 |
| 28 | refactor `beads/bead-ctl.sh` to dual-write: JSONL (legacy) + AgilePlus | 26 | ac_v1 |
| 29 | add `beads/bead-ctl.sh migrate --from-jsonl` (one-time migration script) | 28 | ac_v1 |
| 30 | add `tests/test_agileplus_adapter.py` (6 unit tests + 1 integration) | 28 | ac_test |
| 31 | add `--backend=jsonl\|agileplus` flag to `bead-ctl.sh` | 28 | ac_v1 |
| 32 | add AgilePlus token rotation script `beads/refresh-agileplus-token.sh` | 31 | ac_v1 |
| 33 | document AgilePlus event-mapping in `docs/integrations/agileplus-events.md` | 31 | ac_v1 |
| 34 | verify 50 beads from session 2026-08-09 migrate cleanly to AgilePlus | 32 | ac_v1 |
| 35 | add AgilePlus audit log (`~/.agileplus/audit.jsonl`) mirroring bead-ctl.sh writes | 34 | ac_v1 |

## Phase 3 — Forge launchd script bodies (15 tasks)

The 3 forge-* plists currently point to `/usr/bin/true` (placeholder).
Phase 3 builds the actual monitoring scripts.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 36 | scaffold `~/.forge/bin/forge-watchdog.sh` (disk/memory/process monitoring) | 5 | ac_v1 |
| 37 | implement disk pressure alert (notify at ≥95% used) | 36 | ac_test |
| 38 | implement memory pressure alert (notify at ≥90% used) | 36 | ac_test |
| 39 | implement process count monitor (alert if > 1000 long-running procs) | 36 | ac_test |
| 40 | implement `forge-watchdog.sh status` + `forge-watchdog.sh check` sub-commands | 38 | ac_v1 |
| 41 | scaffold `~/.forge/bin/forge-net-heal.sh` (DNS + TCP reachability) | 5 | ac_v1 |
| 42 | implement DNS resolution check for 5 critical hosts (github.com, pypi.org, etc.) | 41 | ac_test |
| 43 | implement TCP reachability check (8 critical endpoints) | 41 | ac_test |
| 44 | implement `forge-net-heal.sh report` sub-command (markdown report) | 42 | ac_v1 |
| 45 | scaffold `~/.forge/bin/forge-proc-reap.sh` (zombie process reaper) | 5 | ac_v1 |
| 46 | implement zombie reaper (kill -9 processes in Z state > 1h old) | 45 | ac_test |
| 47 | implement orphaned worktree detector (clean up `worktrees/*/.git/lock`) | 45 | ac_test |
| 48 | implement `forge-proc-reap.sh report` sub-command | 47 | ac_v1 |
| 49 | update 3 plists to point at real scripts (replacing `/usr/bin/true`) | 48 | ac_cron |
| 50 | force-fire 3 plists + verify scripts run (not no-op) | 49 | ac_cron |

## Phase 4 — Cross-repo PR merge close-out (15 tasks)

10 PRs were opened during v0.11 (Batches 6-19). Phase 4 merges them
once user authorizes `gh pr merge`.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 51 | audit 10 open PRs via `gh pr list --state=open --json number,repo,headRefName` | 5 | ac_v1 |
| 52 | document PR-merge policy in `AGENTS.md §10.6` (only after user "merge Lane E/F PRs" auth) | 51 | ac_v1 |
| 53 | merge PRs Benchora#94 + Eidolon#148 (Lane E group) | 52 | ac_v1 |
| 54 | merge PRs RepoLedger#20 + ResearchLedger#25 (Lane E group) | 53 | ac_v1 |
| 55 | merge PRs Melosviz#184 + Grapheon#9 (Lane E group) | 54 | ac_v1 |
| 56 | merge PRs pheno#276 + HexaKit#338 (Lane F group) | 53 | ac_v1 |
| 57 | merge PRs AgilePlus#950 + OmniRoute#557 (Lane F group) | 56 | ac_v1 |
| 58 | delete 10 merged feature branches via `gh api -X DELETE` | 57 | ac_v1 |
| 59 | verify all 10 repos build cleanly on main (mypy 0 errors + bandit 0 medium) | 58 | ac_test |
| 60 | document post-merge state per repo in `docs/cross-repo/post-merge-2026-08-10.md` | 59 | ac_v1 |
| 61 | close related beads via `bead-ctl.sh complete` for each merged PR | 60 | ac_v1 |
| 62 | write `docs/plans/2026-08-10-v0.11-cross-repo-merge-audit.md` | 61 | ac_v1 |
| 63 | append v0.11 cross-repo achievement to release notes | 62 | ac_v1 |
| 64 | verify v0.11 tag still resolves to a reachable commit on origin | 63 | ac_v1 |
| 65 | close-out cross-repo work; signal "back to single-repo focus" | 64 | ac_v1 |

## Phase 5 — Cockpit deprecation ladder (10 tasks)

Once Tracera + AgilePlus are functional, the cockpit transitions from
active PM viewer to archived snapshot.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 66 | document cockpit deprecation ladder in `docs/plans/cockpit-deprecation.md` | 65 | ac_v1 |
| 67 | add `cockpit/DEPRECATED.md` with migration timeline | 66 | ac_v1 |
| 68 | freeze `beads/bead-ctl.sh` to JSONL-only (AgilePlus is primary, JSONL is snapshot) | 35 | ac_v1 |
| 69 | mark `cockpit/*.html` snapshots as read-only | 68 | ac_v1 |
| 70 | document AgilePlus import path (`from agileplus.work_tracking import BeadStore`) | 35 | ac_v1 |
| 71 | add Tracera UI surface (web component) for trace search | 20 | ac_v1 |
| 72 | add AgilePlus UI surface (web component) for work search | 35 | ac_v1 |
| 73 | update cockpit landing page to link to Tracera + AgilePlus dashboards | 71,72 | ac_v1 |
| 74 | deprecate `beads/bead-ctl.sh` to `beads/bead-ctl.sh.deprecated` after 1 cycle | 73 | ac_v1 |
| 75 | write `docs/postmortems/2026-08-10-cockpit-deprecation.md` (close-out postmortem) | 74 | ac_v1 |

## Phase 6 — Test sweep hardening (13 tasks)

Address the known flake + harden the suite.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 76 | fix `tests/test_sota_snapshot_chain.py::test_sota_chain_has_no_gap_in_last_5_days` UTC flake | — | ac_test |
| 77 | add `--strict-date` flag to sota test (force deterministic date) | 76 | ac_test |
| 78 | add skipif guard for `bench/suites/container_runner.py` tests on missing Docker | 76 | ac_test |
| 79 | add skipif guard for MLX-dependent tests on non-Apple-Silicon | 78 | ac_test |
| 80 | add skipif guard for harbor-dependent tests on missing harbor 0.1.42 | 79 | ac_test |
| 81 | audit all `tests/test_*.py` for `pytest.skip` vs `pytest.mark.skipif` consistency | 80 | ac_v1 |
| 82 | add `tests/test_bench_runner_hermetic.py` (no-network, no-MLX, no-harbor) | 81 | ac_test |
| 83 | verify 750+ tests pass on hermetic run (zero flakes) | 82 | ac_test |
| 84 | add `scripts/run_hermetic_tests.sh` wrapper for CI smoke | 83 | ac_v1 |
| 85 | document hermetic test policy in `docs/guides/hermetic-testing.md` | 84 | ac_v1 |
| 86 | audit `conftest.py` for shared fixture leaks across hermetic + integration | 85 | ac_v1 |
| 87 | add `tests/test_conftest_isolation.py` (fixture-level isolation test) | 86 | ac_test |
| 88 | final hermetic run: 750 tests pass, 0 flakes | 87 | ac_test |

## Phase 7 — Harbor install finalization (7 tasks)

Finalize harbor install (post-C1, post-C2).

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 89 | verify harbor 0.1.42 pip install (no namespace shadow, no stale dist-info) | — | ac_v1 |
| 90 | add `scripts/install_harbor.sh` (canonical install) | 89 | ac_v1 |
| 91 | add harbor CI smoke test (verify import path + version) | 90 | ac_test |
| 92 | document harbor install in `docs/guides/harbor-install.md` | 91 | ac_v1 |
| 93 | verify 32 harbor-dependent tests pass post-install | 92 | ac_test |
| 94 | add harbor health check (`scripts/check_harbor.sh`) | 93 | ac_v1 |
| 95 | write harbor install audit (`docs/audits/v0.12-harbor-install-audit.md`) | 94 | ac_v1 |

## Phase 8 — Integrate & ship v0.12 (5 tasks)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | refresh `docs/plans/2026-08-10-v0.12-pheno-harness-summit-release-notes.md` | 95 | ac_v1 |
| 97 | regenerate `docs/plans/2026-08-10-pheno-harness-WBS-PERT-100-v0.13.md` (forward look) | 96 | ac_v1 |
| 98 | move `v0.12-pheno-harness-summit` tag to final commit | 97 | ac_v1 |
| 99 | push v0.12 tag to origin | 98 | ac_v1 |
| 100 | write `docs/postmortems/2026-08-10-v0.12-closeout.md` (postmortem + v0.13 plan) | 99 | ac_v1 |

## Ac conventions

- `ac_v1`: commit on `main` with conventional subject + DAG id in footer.
- `ac_test`: `pytest -q tests/` exits 0 (or specific test passes).
- `ac_cron`: `launchctl kickstart -k <plist>` fires, sidecar written.

## Stats inheritance from v0.11

| Metric | v0.11 → v0.12 start |
|--------|---------------------|
| Tests | 750 (1 known flake) |
| mypy errors | 0 (incl. --strict on eval/verifier) |
| bandit MEDIUM | 0 |
| Public-API docstring coverage | **100% (828/828)** |
| TypedDicts added (cumulative) | 22 |
| Protocols added (cumulative) | 5 |
| Tracera integration | not started |
| AgilePlus integration | not started |

## Notes

- AMC / Agentora remains paused per user directive.
- Cross-repo PR merges (tasks 53-57) are gated on user "merge Lane E/F PRs"
  authorization per AGENTS.md §10.4.
- Forge-* script installation (tasks 49-50) is host-side state mutation,
  also gated on user authorization.
- Tracera and AgilePlus tasks (1-35, 71-72) require those systems to be
  functional per the v0.12 goal. If either is blocked, Phase 1-2 can be
  reordered to defer blockers.

---

*v0.12 plan: 100 tasks, 8 phases, 4 explicit user-auth gates, primary
themes Tracera+AgilePlus integration, forge launchd repair, cross-repo
PR merge close-out, cockpit deprecation.*
