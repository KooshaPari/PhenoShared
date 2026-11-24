# Traceability Matrix — 32 pillars → 4 meta-pillars → WBS → file → test gate

> **Status:** active — closes 32-pillar gap from `pheno-harness-requirements-v1.md`
> **Source:** `docs/specs/pheno-harness-requirements-v1.md` §§ 2, 3.1 (scorecard + testability hardening)
> **Bridges:** `.agileplus/specs/001-core-setup/spec.md` ↔ `phenoSpecs` ↔ `bench/contracts/canonicalize.py`
> **Commit pin (agileplus-specs/001-core-setup):** `81cd975064ebdaec693cfbfba91744dc78b28d09` — `chore(agileplus): bootstrap .agileplus/specs, .phenotype, scorecard, governance` (2026-08-19); `origin/main` at `640fe02a045b2fb42ffe9c09c801fc8daa4113ed`
> **Owner:** forge | **Generated:** 2026-08-21

## 0. How to read

* **Meta-pillars:** 4 — Utility / Usability / Expandability / Governance (requirements §2 rows).
* **WBS:** work-breakdown references from requirements §§ 2, 3.1 and `agileplus-specs/001-core-setup` WPs.
* **File / Contract:** source-of-truth file or contract the pillar is measured against.
* **Test gate:** red/green gate that makes the pillar unambiguous (requirements §3.1).

## 1. Meta-pillar summary

| Meta-pillar | Pillars | WBS span | Contract theme |
|-------------|---------|----------|----------------|
| **Utility** | P01–P08 (8) | 26–40 | dual-GPU evidence → SuiteResult → cells |
| **Usability** | P09–P16 (8) | 28, 83–84, 93–94 | one-command lane, preflight, smoke |
| **Expandability** | P17–P24 (8) | 81–95 | federated composition, fleet-proto, WSL |
| **Governance** | P25–P32 (8) | 56–70, 73–80 | TaskStatus, codegen ABI, gitignore, contract |

## 2. Traceability table (32 pillars)

| # | Pillar | Meta-pillar | WBS | File / Contract | Test gate |
|---|--------|-------------|-----|-----------------|-----------|
| P01 | dual-GPU partitioning (4070 12GB + 1080 8GB) | Utility | 26–40 | `config/desktop_nvidia_qwen35_lane.yaml` | `tests/test_desktop_lane_config.py` schema validation |
| P02 | lane YAML validity | Utility | 26 | `config/desktop_nvidia_qwen35_lane.yaml` | `tests/test_desktop_lane_config.py` |
| P03 | PCIe topology parse | Utility | 93 | `scripts/dual_gpu/preflight.py` | `tests/test_dual_gpu_preflight.py` (mock nvidia-smi) |
| P04 | VRAM budget enforcement | Utility | 30–33 | `config/desktop_nvidia_qwen35_lane.yaml` | `tests/test_desktop_lane_config.py` |
| P05 | host manifest 7-day tail | Utility | 40 | `evidence/dual_gpu/host_manifest.yaml` | `host_manifest.yaml` rotation check |
| P06 | SuiteResult v0.5 emission | Utility | 35–38 | `bench/types.py` + `bench/contracts/EVAL_RESULT_CONTRACT.md` | `tests/test_run_desktop_lane_eval.py` (mock dual-engine) |
| P07 | canonicalize to cells v0.5 | Utility | 38 | `bench/contracts/canonicalize.py` → `platform/federation/out/cells-*.json` | `bench/contracts/verify_contract.py cells.json` |
| P08 | <5 min benchmark | Utility | 26–40 | `bench/comparison/run_5min_benchmark.py` | `tests/test_run_desktop_lane_eval.py` + `run_5min_benchmark.py` <5 min |
| P09 | one-command lane CLI | Usability | 28 | `scripts/run_desktop_lane_eval.py` | `tests/test_dual_gpu_stack.py` (script existence) |
| P10 | dual-engine boot | Usability | 83 | `scripts/start_dual_gpu_stack.ps1` | `tests/test_dual_gpu_stack.py` (script existence + structure) |
| P11 | smoke ping (4-min) | Usability | 84 | `scripts/run_dual_gpu_smoke.ps1` | `tests/test_dual_gpu_stack.py` + `curl /health` 30s |
| P12 | engine pins vLLM 0.5.1 + SGLang 0.4.2 | Usability | 91 | `pyproject.toml` + `uv.lock` (`sglang==0.4.2`, `vllm==0.5.1`) | `tests/test_dual_gpu_stack.py` (version pin check) |
| P13 | port binding + health | Usability | 83–84 | `VLLM_PORT=8000` `SGLANG_PORT=30000` | `run_dual_gpu_smoke.ps1` `curl /health` timeout 30s; `one engine down → gen_ok 0` |
| P14 | mock dual-engine eval | Usability | 28 | `scripts/run_desktop_lane_eval.py` | `tests/test_run_desktop_lane_eval.py` (mock dual-engine passes) |
| P15 | preflight nvidia-smi parse | Usability | 93 | `scripts/dual_gpu/preflight.py` | `tests/test_dual_gpu_preflight.py` |
| P16 | WSL-free desktop run (no manual `wsl --`/`podman`) | Usability | 28, 93–94 | `scripts/run_desktop_lane_eval.py` + `scripts/dual_gpu/preflight.py` | `tests/test_run_desktop_lane_eval.py` + `tests/test_dual_gpu_preflight.py` |
| P17 | federated composition | Expandability | 81–95 | `platform/federation/composition.v0.yaml` | `tests/test_install_wsl_pheno_serve_sh.py` (mock SSH) |
| P18 | fleet-proto `capacity.fit` | Expandability | 88 | `platform/federation/composition.v0.yaml` (`fleet-proto`) | `harbor_result_to_cells.py` idempotent |
| P19 | fleet-proto `device.heartbeat` | Expandability | 90 | `platform/federation/composition.v0.yaml` + `bench/results/_wsl_install_*.log` heartbeat JSON | `heartbeat JSON {"device.heartbeat":{"ts": iso, "wsl":"Fedora44","gpu":"4070+1080"}}` |
| P20 | fleet-proto `fleet.peers` | Expandability | 89 | `platform/federation/composition.v0.yaml` | `tests/test_install_wsl_pheno_serve_sh.py` |
| P21 | Fedora44 baseline idempotent | Expandability | 81 | `scripts/install_wsl_pheno_serve.sh` | `tests/test_install_wsl_pheno_serve_sh.py` mock SSH (2nd run exits 0 no diff) |
| P22 | WSL wrapper Ubuntu-22.04 | Expandability | 82 | `scripts/install_wsl_pheno_serve.ps1` (`wsl -d Ubuntu-22.04`) | `tests/test_install_wsl_pheno_serve_sh.py` |
| P23 | harbor_result_to_cells idempotent | Expandability | 85 | `platform/federation/out/cells-*.json` (gitignored) + `bench/contracts/harbor_result_to_cells.py` | idempotent re-run no diff; `platform/federation/out/.gitignore` |
| P24 | Langfuse seed via vault | Expandability | 86 | `LANGFUSE_HOST/KEY` Doppler vault `pheno-harness-v5` dataset `pheno-harness-v5` (not `apps/bench-cockpit/.env`) | `seed_langfuse` + `bench/contracts/verify_contract.py` |
| P25 | TaskStatus aliases identity | Governance | 8, 56 | `bench/types.py::TaskStatus` (`PASS is OK`) | `tests/test_task_status.py` identity + `mypy --strict bench/types.py` |
| P26 | TaskStatus coercion + ValueError | Governance | 8 | `bench/types.py::TaskResult(status="pass") → OK` | `tests/test_task_status.py` (invalid `"done"` → ValueError) |
| P27 | host-guard public ABI | Governance | 56 | `bench/types.py` `TaskStatus.WRONG` vs `PASS` + `host-guard` ABI | `tests/test_host_guard_public_abi.py` |
| P28 | hybrid decode dispatch codegen-owned | Governance | 57 | `kernels/qwen3.5-0.8b/metal/hybrid_decode_dispatch.inc` | `tests/test_host_guard_public_abi.py` + `hybrid_decode_dispatch.inc` presence |
| P29 | arch.yaml simdgroup + schedule | Governance | 57–58 | `kernels/qwen3.5-0.8b/arch.yaml` `kernel_strategy.default_simdgroup_size=32` + `kHybridFullAttn* {3,7,11,15,19,23}` | `python kernels/qwen3.5-0.8b/python/validate.py --quick` (hash pinned) |
| P30 | .gitignore no source-tree leaks | Governance | 73 | `.gitignore` (ADR 0008 §D4) | `pytest -q tests/test_gitignore_no_source_tree_patterns.py` (forbidden `^bench/results/.*\.json`, `^\.env`; allow `*.sha256`) |
| P31 | drift guards (6) + gate 80 | Governance | 74–80 | `tests/test_gitignore_drift_suite.py` (consolidated) | `pytest -q tests/test_gitignore_drift_suite.py tests/test_gitignore_no_source_tree_patterns.py` (gate 80 green) |
| P32 | EVAL_RESULT_CONTRACT verify | Governance | 60–70 | `bench/contracts/EVAL_RESULT_CONTRACT.md` (`gen_ok 0/1`, `verified_pass_at_1 0-1`, `evidence_label reported/verified`) | `python scripts/verify_contract.py cells.json` (missing `evidence_label` → fail) |

## 3. Gap closure

* Requirements §2 scorecard (4 rows) was declared but not per-pillar traceable — this matrix expands to 32 auditable pillars (8×4) with file + gate pins so `agileplus-specs/001-core-setup` is no longer split-brain with `phenoSpecs/WORKLOG.md`.
* Section 3.1 negative cases and thresholds are now bound to `Test gate` column — any `*.json` non-`*.sha256`, missing pin, byte-mismatch, or heartbeat diff fails the gate.
* Commit pin `81cd975` anchors the `agileplus-specs/001-core-setup` execution bridge referenced in requirements header; future `proc all` (WBS 87–90, 93–94) promotes mock tests to live verified against `host_manifest.yaml` rolling tail.

---
*End traceability matrix. Source commit `640fe02a045b2fb42ffe9c09c801fc8daa4113ed` (origin/main) + `81cd975064ebdaec693cfbfba91744dc78b28d09` (agileplus bootstrap).*
