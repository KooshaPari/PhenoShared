# 100-Task WBS/PERT DAG — pheno-harness v0.10 (2026-08-08)

**Status:** canonical source-of-truth for the next 100 atomic tasks.
**Owner:** forge (agent CLI). **Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.
**Ac:** every task has one acceptance bullet (ac_v1 = main has the commit).

> "Each task must be meaningfully large sized but the DAG is a PERT/WBS
> with proper atomical decomposition." — user directive, 2026-08-05.

## v0.9 → v0.10 carry-over

The v0.9 cycle (`v0.9-pheno-harness-summit-pending` — Phase 7 not yet
tagged) shipped:

- Reconciliation preflight test fix-up (Phase 1, 16 → 0 failures)
- `evidence_registry discover()` refactor (Phase 2)
- Harbor integration + promotion (Phase 3)
- `fix/desktop-vllm-runtime` rebase + merge (Phase 5)
- 51 F841 unsafe-fix + 3 doc-only TODOs (Phase 6)
- Phase 7 cleanup (ruff auto-fix + release notes)

AMC / Agentora (Phase 4) remains **paused** per user directive — not in
v0.10 scope.

v0.10 picks up:
- 212 remaining mypy type errors (debug fixture + adapter typing)
- Dep-gap robustness expansion (httpx, huggingface_hub PinningStatus)
- Sub-package docstring coverage (eval/, verifier/, pheno/evidence)
- Bandit false-positive → nosec migration (27 medium → 0)
- 51 unsafe-fix F841 follow-up (manual review)
- MLX-stub restoration (DAG-6 follow-up)
- Test sweep hardening (per-dep skipif guards)

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1–5 | audit close-out + HEAD alignment | reproducible baseline |
| 1 | 6–25 | mypy type error sweep (212 → 0) | 0 type errors system-wide |
| 2 | 26–40 | bandit false-positive → nosec migration | 0 medium bandit |
| 3 | 41–60 | eval/ + verifier/ docstring + type narrowing | 0 mypy + 80% docstring |
| 4 | 61–75 | pheno/evidence adapter hardening | driver swimlane parity |
| 5 | 76–85 | dep-gap test_skipif expansion | 0 dep-gap collection errors |
| 6 | 86–95 | MLX-stub restoration + adapters typing | mlx + numpy + mocks green |
| 7 | 96–100 | integrate & ship | `v0.10-pheno-harness-summit` tag |

## Ac conventions

- `ac_v1`: commit on `main` with conventional subject + DAG id in footer.
- `ac_v2`: idempotent under `git restore --worktree` + re-run.
- `ac_drift`: golden snapshots match (codegen + SOTA + bench contracts).
- `ac_test`: `pytest -q tests/ kernels/qwen3.5-0.8b/tests/` exits 0.
- `ac_cron`: `launchctl kickstart -k` fires, sidecar written.

---

## Phase 0 — Audit close-out + HEAD alignment (1–5)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | land this DAG (`docs/plans/2026-08-08-pheno-harness-WBS-PERT-100-v0.10.md`) | — | ac_v1 |
| 2 | scan 212 remaining mypy errors into batched inventory doc | 1 | ac_v1 |
| 3 | scan 27 remaining bandit MEDIUM into batched inventory doc | 1 | ac_v1 |
| 4 | scan 51 deferred unsafe-fix F841 into batched inventory doc | 1 | ac_v1 |
| 5 | tag v0.9-pheno-harness-summit on the current HEAD (gated on user push auth) | 1–4 | ac_v1 |

---

## Phase 1 — Mypy type error sweep (6–25)

The post-v0.9 audit (`5433e4b`) ran mypy and found 212 type errors
after the eval/__init__.py + shim-re-export fixes. They're clustered in:

- 6–10: `bench/adapters*.py` (Mock/MLX/OpenAI/Anthropic typing)
- 11–15: `bench/comparison/*.py` (adapter mock typing)
- 16–20: `bench/matrix/*.py` (str/protocol typing)
- 21–24: `bench/cli.py`, `bench/registry.py`, `bench/parallel.py` (entrypoint)
- 25: phase 1 gate (mypy 0 errors)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6 | fix `bench/adapters.py:246` (mock adapter MockModel typing) | 5 | ac_v1 |
| 7 | fix `bench/adapters_mlx.py:127` (None has no .encode) | 6 | ac_v1 |
| 8 | fix `bench/adapters_openai.py:62` (module-level Any annotation) | 7 | ac_v1 |
| 9 | fix `bench/adapters_anthropic.py:23` (module-level Any annotation) | 8 | ac_v1 |
| 10 | fix `bench/adapters_mock.py` (mock adapter protocol conformance) | 9 | ac_v1 |
| 11 | fix `bench/comparison/_forge_reply_parser.py` (MockModel.message protocol) | 10 | ac_v1 |
| 12 | fix `bench/comparison/stock_vs_ours_adapters.py:207` (MLXDirect.model_id) | 11 | ac_v1 |
| 13 | fix `bench/comparison/run_minimax_m3.py:188` (suite.subset method lookup) | 12 | ac_v1 |
| 14 | fix `bench/comparison/run_5min_matrix.py:114` (object * float operator) | 13 | ac_v1 |
| 15 | fix `bench/comparison/run_5min_matrix.py:375` (str → float assignment) | 14 | ac_v1 |
| 16 | fix `bench/matrix/run_ablation.py:153` (str has no .ok) | 15 | ac_v1 |
| 17 | fix `bench/matrix/run_ablation.py:160` (str has no .wall_clock_s) | 16 | ac_v1 |
| 18 | fix `bench/perf.py:221` (List[dict] not assignable to List[PerfReading]) | 17 | ac_v1 |
| 19 | fix `bench/registry.py:131` (Callable → Task return) | 18 | ac_v1 |
| 20 | fix `bench/report.py:244` (asdict arg type) | 19 | ac_v1 |
| 21 | fix `bench/cli.py:211` (Any import — already done; verify) | 20 | ac_v1 |
| 22 | fix `bench/parallel.py:227` (create_task Awaitable → Coroutine) | 21 | ac_v1 |
| 23 | fix `bench/console.py:52` (None → Console assignment) | 22 | ac_v1 |
| 24 | fix `bench/energy.py:241` (override return type mismatch) | 23 | ac_v1 |
| 25 | phase 1 gate: `mypy --no-incremental` returns 0 errors | 6–24 | ac_test |

---

## Phase 2 — Bandit false-positive → nosec migration (26–40)

The post-v0.9 audit reduced bandit HIGH from 1 → 0 and MEDIUM from 32
→ 27. The remaining 27 are all reviewed false positives (B310, B108,
B311, B608, B603). Each needs a `# nosec Bxxx` annotation with audit
rationale.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 26 | add nosec to B310 in `bench/adapters.py:162` (urllib HTTP API) | 25 | ac_v1 |
| 27 | add nosec to B310 in `bench/adapters_anthropic.py:52` | 26 | ac_v1 |
| 28 | add nosec to B310 in `bench/adapters_openai.py:49` | 27 | ac_v1 |
| 29 | add nosec to B310 in `bench/runner/model_adapter.py:241` | 28 | ac_v1 |
| 30 | add nosec to B310 in `pheno/serve/server.py:43,194,301,327,369` | 29 | ac_v1 |
| 31 | add nosec to B310 in `scripts/probe_*.py` (6 files) | 30 | ac_v1 |
| 32 | add nosec to B310 in `scripts/scrape_*.py` (2 files) | 31 | ac_v1 |
| 33 | add nosec to B310 in `scripts/perf_probe.py:82` | 32 | ac_v1 |
| 34 | add nosec to B310 in `scripts/diagnose_pheno_backend.py:39` | 33 | ac_v1 |
| 35 | add nosec to B310 in `scripts/run_desktop_lane_eval.py:38` | 34 | ac_v1 |
| 36 | add nosec to B108 in `bench/comparison/stock_vs_ours_adapters.py:115` (hardcoded /tmp) | 35 | ac_v1 |
| 37 | add nosec to B311 in `bench/suites/dataset_loader.py:153,159` (random for synth) | 36 | ac_v1 |
| 38 | add nosec to B608 in `pheno/.../sql.py` (SQL string composition) | 37 | ac_v1 |
| 39 | add nosec to B603 in `bench/cli.py` + `scripts/*.py` (subprocess patterns) | 38 | ac_v1 |
| 40 | phase 2 gate: `bandit -r --severity-level medium` → 0 findings | 26–39 | ac_test |

---

## Phase 3 — eval/ + verifier/ docstring + type narrowing (41–60)

The eval/ + verifier/ subpackages have minimal docstring coverage and
several type-narrowing issues. Target: 80% docstring coverage + 0 mypy
errors in these subpackages.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 41 | add docstrings to `eval/budget.py` (5 functions) | 40 | ac_v1 |
| 42 | add docstrings to `eval/deepswe.py` (8 functions) | 41 | ac_v1 |
| 43 | add docstrings to `eval/long_horizon.py` (12 functions) | 42 | ac_v1 |
| 44 | add docstrings to `eval/nested_rlvr.py` (10 functions) | 43 | ac_v1 |
| 45 | add docstrings to `eval/pillars.py` (15 functions) | 44 | ac_v1 |
| 46 | add docstrings to `eval/tbench.py` (8 functions) | 45 | ac_v1 |
| 47 | add docstrings to `verifier/harness.py` (12 functions) | 46 | ac_v1 |
| 48 | add docstrings to `verifier/rewards.py` (15 functions) | 47 | ac_v1 |
| 49 | add docstrings to `verifier/risky_action_gate.py` (8 functions) | 48 | ac_v1 |
| 50 | add docstrings to `verifier/audit.py` (10 functions) | 49 | ac_v1 |
| 51 | narrow `eval/budget.py` return types (dict[str, Any] → dataclass) | 50 | ac_v1 |
| 52 | narrow `eval/pillars.py` return types (pillar_score → PillarScore) | 51 | ac_v1 |
| 53 | narrow `eval/long_horizon.py` return types (manifest → LongHorizonManifest) | 52 | ac_v1 |
| 54 | narrow `verifier/harness.py` return types (verdict → Verdict dataclass) | 53 | ac_v1 |
| 55 | narrow `verifier/rewards.py` return types (reward → Reward dataclass) | 54 | ac_v1 |
| 56 | add `tests/test_eval_docstrings.py` (docstring coverage gate) | 41–55 | ac_test |
| 57 | add `tests/test_verifier_docstrings.py` (docstring coverage gate) | 56 | ac_test |
| 58 | add `mypy --strict` runner for eval/ + verifier/ as separate target | 57 | ac_v1 |
| 59 | fix any mypy --strict findings in eval/ + verifier/ | 58 | ac_v1 |
| 60 | phase 3 gate: 80% docstring + 0 mypy strict in eval/ + verifier/ | 41–59 | ac_test |

---

## Phase 4 — pheno/evidence adapter hardening (61–75)

The 6 evidence adapters (arxiv, github, hf, openalex, semantic_scholar,
wikipedia) have inconsistent error handling and no retry policy. v0.10
standardizes the adapter contract.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 61 | audit current adapter error handling across 6 adapters | 60 | ac_v1 |
| 62 | add `pheno/evidence/adapters/base.py` retry policy (exponential backoff) | 61 | ac_v1 |
| 63 | apply retry policy to `pheno/evidence/adapters/arxiv.py` | 62 | ac_v1 |
| 64 | apply retry policy to `pheno/evidence/adapters/github.py` | 63 | ac_v1 |
| 65 | apply retry policy to `pheno/evidence/adapters/hf.py` | 64 | ac_v1 |
| 66 | apply retry policy to `pheno/evidence/adapters/openalex.py` | 65 | ac_v1 |
| 67 | apply retry policy to `pheno/evidence/adapters/semantic_scholar.py` | 66 | ac_v1 |
| 68 | apply retry policy to `pheno/evidence/adapters/wikipedia.py` | 67 | ac_v1 |
| 69 | add `pheno/evidence/adapters/rate_limit.py` (per-adapter rate limit) | 68 | ac_v1 |
| 70 | add `tests/test_evidence_adapters_retry.py` (retry policy tests) | 69 | ac_test |
| 71 | add `tests/test_evidence_adapters_rate_limit.py` | 69 | ac_test |
| 72 | add `pheno/evidence/adapters/circuit_breaker.py` (per-adapter circuit breaker) | 69 | ac_v1 |
| 73 | add `tests/test_evidence_adapters_circuit_breaker.py` | 72 | ac_test |
| 74 | add `docs/EVIDENCE_ADAPTERS.md` (operator runbook) | 62–73 | ac_v1 |
| 75 | phase 4 gate: 6 adapters with retry + rate limit + circuit breaker | 61–74 | ac_test |

---

## Phase 5 — Dep-gap test_skipif expansion (76–85)

5 tests are currently guarded with skipif for missing deps. v0.10 expands
the skipif pattern to cover all dep-gap tests.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 76 | audit remaining collection errors via `pytest --collect-only` | 75 | ac_v1 |
| 77 | add `pytest.importorskip('httpx')` to `tests/test_*.py` (httpx-required) | 76 | ac_v1 |
| 78 | add `pytest.importorskip('huggingface_hub')` to remaining tests | 77 | ac_v1 |
| 79 | add `pytest.importorskip('numpy')` to remaining tests | 78 | ac_v1 |
| 80 | add `pytest.importorskip('mlx')` to remaining tests | 79 | ac_v1 |
| 81 | add `pytest.importorskip('cryptography')` to remaining tests | 80 | ac_v1 |
| 82 | add `pytest.importorskip('harbor')` to remaining tests | 81 | ac_v1 |
| 83 | add `tests/test_dep_gap_collection.py` (regression guard) | 82 | ac_test |
| 84 | add `scripts/check_dep_gaps.py` (CI gate) | 83 | ac_v1 |
| 85 | phase 5 gate: `pytest tests/ --collect-only` → 0 collection errors | 76–84 | ac_test |

---

## Phase 6 — MLX-stub restoration + adapters typing (86–95)

DAG-6 cherry-picked `aec1ebf` into `fix/desktop-vllm-runtime` for the
mlx-stub module. The reference impl isn't yet in main. v0.10 restores it.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 86 | audit `tests/test_bench_runner.py` mlx-stub failures | 85 | ac_v1 |
| 87 | port `bench/runner/mlx_stub.py` (DAG-6 cherry-pick aec1ebf) | 86 | ac_v1 |
| 88 | add `tests/test_bench_runner.py::test_mlx_stub_load` | 87 | ac_test |
| 89 | add `tests/test_bench_runner.py::test_mlx_stub_generate` | 87 | ac_test |
| 90 | add `tests/test_bench_runner.py::test_mlx_stub_handles_timeout` | 87 | ac_test |
| 91 | type-annotate `bench/runner/adapter*` MockModel (already in 759cb0e) | 87 | ac_v1 |
| 92 | add `tests/test_adapter_protocol.py` (Protocol conformance) | 91 | ac_test |
| 93 | add `bench/runner/adapters_typing.py` (typed Adapter protocol) | 92 | ac_v1 |
| 94 | update `bench/runner/model_adapter.py` to use typed protocol | 93 | ac_v1 |
| 95 | phase 6 gate: mlx-stub + typed adapter protocol green | 86–94 | ac_test |

---

## Phase 7 — Integrate & ship (96–100)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | verify all 4 launchd agents still loaded + force-fire each | 95 | ac_cron |
| 97 | reconcile `chore/preserve-launchd-installer` if it has unique commits | 95 | ac_v1 |
| 98 | write `docs/plans/2026-08-08-v0.10-pheno-harness-summit-release-notes.md` | 95 | ac_v1 |
| 99 | run `pytest -q tests/ kernels/qwen3.5-0.8b/tests/` + mypy + ruff + bandit | 95, 96 | ac_test |
| 100 | tag `v0.10-pheno-harness-summit` (awaits explicit user `do the push` per AGENTS.md §10.4) | 99, 98 | ac_v1 |

---

## Critical path

```
1 → 2 → 5 → 6 → 25 → 26 → 40 → 41 → 60 → 61 → 75 → 76 → 85 → 86 → 95 → 99 → 100
```

## Parallelisable clusters

- Tasks 3–4 (bandit + F841 inventory) are independent of 2.
- Phase 1 (mypy) is independent of Phase 2 (bandit) after task 25 completes.
- Phase 4 (adapter hardening) is independent of Phase 5 (dep-gap) after task 60.
- Phase 6 (mlx-stub) is independent of everything else after task 85.

## Stop signals

- `proc amc` → "AMC paused per user directive" (no DAG walk).
- `proc <paused-id>` → "paused per user directive" (no DAG walk).
- `proc <unknown-id>` → "no such task; see §8.4 of AGENTS.md".

## v0.9 → v0.10 deltas

- **New phases**: Phase 1 (mypy sweep), Phase 2 (bandit nosec), Phase 3 (docstrings), Phase 4 (adapter hardening), Phase 5 (dep-gap), Phase 6 (mlx-stub)
- **Carried over from v0.9**:
  - Phase 4 (AMC) → still paused, not in v0.10
  - Phase 7 finalize → tag push → still gated on user
- **Out of scope**:
  - Kv-winner promotion (paused)
  - Cross-repo PRs (the 100-PR backlog from other sessions)

---

*End of DAG. Last revised 2026-08-08. Force-commit on overwrite; this is
the canonical source-of-truth for the next 100 tasks in the v0.10 cycle.*
