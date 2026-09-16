# 100-Task WBS/PERT DAG — pheno-harness v0.9 (2026-08-07)

**Status:** canonical source-of-truth for the next 100 atomic tasks.
**Owner:** forge (agent CLI). **Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.
**Ac:** every task has one acceptance bullet (ac_v1 = main has the commit).

> *"Each task must be meaningfully large sized but the DAG is a PERT/WBS
> with proper atomical decomposition."* — user directive, 2026-08-05.

## v0.8 → v0.9 carry-over

The v0.8 cycle (`v0.8-pheno-harness-summit`, tag pushed 2026-08-07) shipped:

- 100-task DAG walked (Phases 0–7)
- A4 `kArchSimdgroupSize` codegen wiring (DAG-41..55)
- Desktop NVIDIA dual-GPU lane (DAG-26..40) + Phase 6 WSL/Fedora 44 derivative
- Post-v0.8 audit close-out: F401 (189 → 0), F841, F821 (incl. 2 real bugs),
  F811, E731, E741, E702, E701, E402; DAG-75 .gitignore split; 31
  transient files removed; `bench/suites/browsercomp.py:265` and
  `kernels/.../validate.py:493` fixed
- Dep-gap robustness (4 test_skipif guards for huggingface_hub /
  cryptography / numpy / mlx)

v0.9 picks up the deferred items + the new lint sweep's unsafe-fix
backlog + outstanding test sweep failures.

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1–5 | audit close-out + HEAD alignment | reproducible baseline |
| 1 | 6–25 | reconciliation preflight test fix-up | 16 out-of-scope tests green |
| 2 | 26–35 | evidence_registry `discover()` refactor | 2 monkey-patching tests green |
| 3 | 36–50 | Harbor integration + promotion | 5 harbor-required tests green |
| 4 | 51–70 | AMC / Agentora resumption (paused → live) | AMC evaluator end-to-end |
| 5 | 71–85 | vLLM runtime work (`fix/desktop-vllm-runtime`) | LLM-host lane alive |
| 6 | 86–95 | unsafe-fix F841 + doc-only TODOs | 51 F841 + 5 doc TODOs closed |
| 7 | 96–100 | integrate & ship | `v0.9-pheno-harness-summit` tag |

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
| 1 | land this DAG (`docs/plans/2026-08-07-pheno-harness-WBS-PERT-100-v0.9.md`) | — | ac_v1 |
| 2 | capture post-v0.8 audit summary in `docs/superpowers/audits/v0.8-closeout.md` | 1 | ac_v1 |
| 3 | verify all 4 launchd agents still loaded + force-fire each | — | ac_cron |
| 4 | backfill 2026-08-08 SOTA snapshot (if cron didn't fire overnight) | 3 | ac_v1 |
| 5 | snapshot `git status` strip + commit `chore: 2026-08-07 HEAD capture` | 1–4 | ac_v1 |

---

## Phase 1 — Reconciliation preflight test fix-up (6–25)

The post-v0.8 audit (`9e9c9ae`) catalogued 16 reconciliation preflight
tests as out-of-scope failures. They exercise
`scripts/reconciliation_preflight_check.py` +
`scripts/reconciliation_preflight_checks_{infra,packet,security,security_remote}.py`
which are the canonical "is the local repo consistent with the latest
SOTA chain + remote bundle?" check. Many were failing because:
- `PreflightInputs` / `CurrentSnapshot` weren't exported (now fixed in `719cb62`)
- `Iterable` was missing from typing imports (now fixed in `719cb62`)
- Bundle header constants duplicated across modules (now fixed by daemon)
- Some tests reference old `scripts/_ev` aliases that no longer exist

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6 | audit remaining reconciliation test failures via `pytest tests/ -k 'reconciliation' --tb=short` | 5 | ac_v1 |
| 7 | `tests/test_reconciliation_preflight_infra.py::test_graph_delta_paths` — fix `_verify_local_graph` arg typing | 6 | ac_test |
| 8 | `tests/test_reconciliation_preflight_infra.py::test_delta_total_zero_for_empty` — fix `CurrentSnapshot.delta_paths = []` default | 6 | ac_test |
| 9 | `tests/test_reconciliation_preflight_packet.py::test_bundle_header_round_trip` — fix round-trip on `_BUNDLE_HEADER_MAX_BYTES` | 6 | ac_test |
| 10 | `tests/test_reconciliation_preflight_packet.py::test_verify_packet_rejects_oversize` — fix `_BUNDLE_HEADER_MAX_BYTES` shadowing | 6 | ac_test |
| 11 | `tests/test_reconciliation_preflight_security.py::test_path_inventory_signature_verifies` — fix `iter_unpack` size mismatch | 6 | ac_test |
| 12 | `tests/test_reconciliation_preflight_security_remote.py::test_branch_name_rejects_dotdot` — fix `Iterable` usage (now in 719cb62) | 6 | ac_test |
| 13 | `tests/test_reconciliation_preflight_security_remote.py::test_remote_object_validates_etag` — fix `PreflightInputs` import (now in 719cb62) | 6 | ac_test |
| 14 | re-export `_BUNDLE_HEADER_MAX_BYTES` from `reconciliation_preflight_checks_packet` to dedupe | 6 | ac_v1 |
| 15 | re-export `_SHA256_RE` from `reconciliation_preflight_checks_security` to dedupe | 6 | ac_v1 |
| 16 | add `tests/test_reconciliation_preflight_roundtrip.py` — full envelope round-trip | 14, 15 | ac_test |
| 17 | add `tests/test_reconciliation_preflight_security_remote.py::test_remote_etag_mismatch_rejects` | 6 | ac_test |
| 18 | add `tests/test_reconciliation_preflight_infra.py::test_canonical_bytes_strips_metadata` | 6 | ac_test |
| 19 | add `tests/test_reconciliation_preflight_packet.py::test_verify_tar_round_trip` | 9 | ac_test |
| 20 | update `docs/RECONCILIATION_PREFLIGHT.md` with the 16-failure post-mortem | 6–19 | ac_v1 |
| 21 | add `scripts/reconciliation_preflight_check.py --self-test` mode | 6 | ac_v1 |
| 22 | add `tests/test_reconciliation_preflight_self_test.py` | 21 | ac_test |
| 23 | add `config/reconciliation_preflight.yaml` schema + linter test | 21 | ac_test |
| 24 | add `tests/test_reconciliation_preflight_security.py::test_manifest_signature_verifies` | 11 | ac_test |
| 25 | phase 1 gate: reconciliation preflight tests green (16 → 0 failures) | 6–24 | ac_test |

---

## Phase 2 — evidence_registry `discover()` refactor (26–35)

The `scripts/evidence_registry.py` re-exports `MetadataClient` and 6
adapters for monkey-patching in tests. The current re-export pattern
shadows the sub-module lookup, so `discover()`-style tests can't find
adapters via parent-module lookup. Refactor to expose adapters via
`pheno.evidence.store.discover()` and update tests.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 26 | audit 2 remaining evidence_registry test failures | 5 | ac_v1 |
| 27 | add `pheno/evidence/store.py::discover()` (parent-module adapter lookup) | 26 | ac_v1 |
| 28 | refactor `scripts/evidence_registry.py` to use `discover()` for adapter lookup | 27 | ac_v1 |
| 29 | drop the re-export shim from `scripts/evidence_registry.py` (now redundant) | 28 | ac_v1 |
| 30 | update `tests/test_evidence_registry.py::test_arxiv_*` to call `discover()` | 28 | ac_test |
| 31 | update `tests/test_evidence_registry.py::test_metadata_client_resolution_*` to use `discover()` | 28 | ac_test |
| 32 | add `tests/test_evidence_registry_discover.py` (parent-module lookup) | 27 | ac_test |
| 33 | add `pheno/evidence/store.py::discover_all()` (full adapter enumeration) | 27 | ac_v1 |
| 34 | update `tests/test_evidence_registry_export.py` to use `discover_all()` | 33 | ac_test |
| 35 | phase 2 gate: evidence_registry tests green (2 → 0 failures) | 26–34 | ac_test |

---

## Phase 3 — Harbor integration + promotion (36–50)

5 harbor-required tests are currently skipped because `harbor>=0.6.0` and
`repo2rlenv>=0.8.0` aren't in the test venv. These tests validate the
"is the local model + container runner wired correctly for terminal-bench
+ Repo2RLEnv upstream?" check.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 36 | audit 5 harbor-required test failures via `pytest tests/ -k 'harbor' --tb=short` | 5 | ac_v1 |
| 37 | add `scripts/install_harbor_for_tests.sh` (PEP 668 override + harbor + repo2rlenv into .venv-harbor) | 36 | ac_v1 |
| 38 | add `tests/conftest_harbor.py` (skipif guard for harbor-not-installed) | 37 | ac_test |
| 39 | author `scripts/harbor_consumer_promote.py` (promote `_harbor_installed()` probe → real check) | 37 | ac_v1 |
| 40 | update `scripts/_harbor_installed()` to use `importlib.metadata.version("harbor")` strict check | 39 | ac_v1 |
| 41 | update `scripts/harbor_consumer_dry_run.py` (DAG-67 follow-up — landed in 251f3e9) to assert `harbor>=0.6.0` | 40 | ac_v1 |
| 42 | add `tests/test_harbor_consumer_dry_run.py::test_asserts_harbor_version` | 41 | ac_test |
| 43 | add `tests/test_harbor_install.py::test_installs_harbor_into_venv_harbor` | 37 | ac_test |
| 44 | add `tests/test_harbor_install.py::test_idempotent_install` | 37 | ac_test |
| 45 | add `tests/test_harbor_promote.py::test_promote_emits_advisory_only` | 39 | ac_test |
| 46 | add `docs/HARBOR.md` — Harbor + Repo2RLEnv install + promote runbook | 37–45 | ac_v1 |
| 47 | update `pyproject.toml [project.optional-dependencies] harbor` to require `harbor>=0.6.0` | 37 | ac_v1 |
| 48 | add `tests/test_harbor_optional_dep.py` (skipif pattern matches dag-67) | 47 | ac_test |
| 49 | add `tests/test_repo2rlenv_install.py::test_repo2rlenv_optional_dep` | 47 | ac_test |
| 50 | phase 3 gate: harbor-required tests green (5 → 0 failures) | 36–49 | ac_test |

---

## Phase 4 — AMC / Agentora resumption (51–70)

Per user directive (2026-08-05), AMC was paused during v0.8. v0.9 resumes
the AMC evaluator end-to-end against the now-clean harness.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 51 | `proc amc` directive — user authorization to unpause AMC | 50 | ac_v1 |
| 52 | audit current `bench/amc/` + `pheno/agentora/` state after the pause | 51 | ac_v1 |
| 53 | re-export `AMCAdapter` from `bench.adapters` (paused-era re-export may have rotted) | 52 | ac_v1 |
| 54 | update `scripts/run_amc_evaluation.py` (CLI entrypoint) for v0.9 surface | 53 | ac_v1 |
| 55 | add `bench/amc/test_amc_adapter_lifecycle.py` (mock LLM host) | 54 | ac_test |
| 56 | update `pheno/agentora/orchestrator.py` for v0.9 surface | 54 | ac_v1 |
| 57 | add `tests/test_agentora_orchestrator.py::test_orchestrator_routes_to_adapter` | 56 | ac_test |
| 58 | add `tests/test_agentora_orchestrator.py::test_orchestrator_handles_timeout` | 56 | ac_test |
| 59 | update `config/amc_evaluation.yaml` (v0.9 fixture set) | 52 | ac_v1 |
| 60 | add `tests/test_amc_evaluation_config.py` (schema validation) | 59 | ac_test |
| 61 | wire `evidence_label` into AMC output (per-cell, per DAG-30 pattern) | 54 | ac_v1 |
| 62 | add `tests/test_amc_evidence_label.py` | 61 | ac_test |
| 63 | add `scripts/run_agentora_smoke.py` (4-min end-to-end smoke) | 56 | ac_v1 |
| 64 | add `tests/test_run_agentora_smoke.py::test_smoke_exits_0` | 63 | ac_test |
| 65 | document `docs/AMC.md` (operator runbook) | 54–63 | ac_v1 |
| 66 | add `bench/amc/test_amc_replay.py` (deterministic replay) | 54 | ac_test |
| 67 | add `pheno/agentora/replay.py` (replay harness) | 66 | ac_v1 |
| 68 | update `scripts/launchd/install_amc_cron.sh` (AMC daily cron) | 54 | ac_v1 |
| 69 | force-fire AMC cron + verify `evidence/amc/2026-08-08.jsonl` | 68 | ac_cron |
| 70 | phase 4 gate: AMC + Agentora tests green | 51–69 | ac_test |

---

## Phase 5 — vLLM runtime work (`fix/desktop-vllm-runtime`) (71–85)

DAG-6 cherry-picked `1f1f533` into `fix/desktop-vllm-runtime`. The branch
exists but has not been merged into `main`. v0.9 closes that gap.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 71 | `git checkout fix/desktop-vllm-runtime` + rebase onto main | 70 | ac_v1 |
| 72 | port `bench/runner/vllm_runtime.py` (DAG-6 landed in 1f1f533) into main | 71 | ac_v1 |
| 73 | port `scripts/run_vllm_desktop.sh` (DAG-6) into main | 72 | ac_v1 |
| 74 | add `tests/test_vllm_runtime.py::test_runtime_loads_model` (mock) | 72 | ac_test |
| 75 | add `tests/test_vllm_runtime.py::test_runtime_handles_timeout` (mock) | 72 | ac_test |
| 76 | add `config/vllm_runtime.yaml` (runtime config) | 73 | ac_v1 |
| 77 | add `tests/test_vllm_runtime_config.py::test_config_validates_against_schema` | 76 | ac_test |
| 78 | wire vLLM runtime into `bench.cli run` via `--runtime vllm` | 72 | ac_v1 |
| 79 | add `tests/test_cli_vllm_runtime.py::test_cli_routes_to_vllm` | 78 | ac_test |
| 80 | update `docs/DESKTOP_NVIDIA_LANE.md` (DAG-36) with vLLM section | 72–78 | ac_v1 |
| 81 | add `bench/runner/vllm_runtime.py::warm_cache()` for 30s startup | 72 | ac_v1 |
| 82 | add `tests/test_vllm_runtime.py::test_warm_cache_reuses_model` | 81 | ac_test |
| 83 | merge `fix/desktop-vllm-runtime` into main (closes DAG-99 from v0.8) | 72, 80 | ac_v1 |
| 84 | delete `fix/desktop-vllm-runtime` branch (post-merge cleanup) | 83 | ac_v1 |
| 85 | phase 5 gate: vLLM runtime tests green + branch merged | 71–84 | ac_test |

---

## Phase 6 — Unsafe-fix F841 + doc-only TODOs (86–95)

The post-v0.8 audit's safe-mode F841 sweep cleared 59 → 8 (now 0).
The remaining 51 deferred findings need manual review per the audit's
"unsafe-fixes" note (`except ExcType as exc:` bindings where the variable
is logged but otherwise unused). Plus 5 doc-only TODOs.

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 86 | run `ruff check --select F841 --unsafe-fixes` to see deferred 51 | 85 | ac_v1 |
| 87 | review 51 unsafe F841 findings; for each: keep `as exc` (logging) or remove binding | 86 | ac_v1 |
| 88 | commit F841 unsafe-fix batch (15 files) | 87 | ac_v1 |
| 89 | commit F841 unsafe-fix batch (15 files) | 87 | ac_v1 |
| 90 | commit F841 unsafe-fix batch (15 files) | 87 | ac_v1 |
| 91 | commit F841 unsafe-fix batch (6 files, final) | 87 | ac_v1 |
| 92 | close out `bench/matrix/README.md:36` "TODO(harbor)" → update with harbor install pointer | 90 | ac_v1 |
| 93 | close out `scripts/deploy_kv_winner.ps1:24` TODO (deferred until kv-winner promotion) | — | ac_v1 |
| 94 | close out `kernels/qwen3.5-0.8b/docs/CONTRIBUTING.md:168` (doc-only TODO) | — | ac_v1 |
| 95 | phase 6 gate: F841 = 0 + 3 doc TODOs closed | 86–94 | ac_test |

---

## Phase 7 — Integrate & ship (96–100)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | verify all 4 launchd agents still loaded + force-fire each (final pre-tag) | 95 | ac_cron |
| 97 | reconcile `pheno-harness-runner-provenance` branch into main (DAG-99 v0.8 carry-over) | 95 | ac_v1 |
| 98 | write `docs/plans/2026-08-07-v0.9-pheno-harness-summit-release-notes.md` | 95 | ac_v1 |
| 99 | run full `pytest -q tests/ kernels/qwen3.5-0.8b/tests/` + ruff check | 95, 96 | ac_test |
| 100 | tag `v0.9-pheno-harness-summit` (awaits explicit user `do the push` per AGENTS.md §10.4) | 99, 98 | ac_v1 |

---

## Critical path

```
1 → 5 → 6 → 26 → 36 → 51 → 70 → 71 → 83 → 85 → 86 → 87 → 95 → 99 → 100
```

## Parallelisable clusters

- Tasks 3–4 (snapshot + launchd verify) are independent of 1–2.
- Phase 1 (reconciliation) is independent of Phase 2 (evidence_registry)
  once task 6 completes.
- Phase 4 (AMC) is independent of Phase 5 (vLLM) once task 53 lands.
- Phase 6 (F841) is independent of everything else after task 86.

## Stop signals

- `proc amc` → "AMC paused per user directive" (no DAG walk) — RESUMED in v0.9.
- `proc <paused-id>` → "paused per user directive" (no DAG walk).
- `proc <unknown-id>` → "no such task; see §8.4 of AGENTS.md".

## v0.8 → v0.9 deltas

- **New phases**: Phase 2 (evidence_registry refactor), Phase 4 (AMC resumption)
- **Renamed phases**: Phase 5 (was Phase 6 in v0.8 — gitignore hardening moved into Phase 0/Phase 5 audit items)
- **Carried over from v0.8**:
  - DAG-99 (vLLM branch merge) → Phase 5
  - 23 out-of-scope test failures → Phases 1, 2, 3
  - Doc-only TODOs → Phase 6

---

*End of DAG. Last revised 2026-08-07. Force-commit on overwrite; this is
the canonical source-of-truth for the next 100 tasks.*
