# pheno-harness requirements v1 — intent capture (2026-08-21)

**Status:** draft for `droid-main` queue (rule 12). **Owner:** forge.
**Bridges:** `agileplus-specs/001-core-setup/spec.md` (execution) ↔
`phenoSpecs` (governance) ↔ `bench/contracts/canonicalize.py` (evidence).
**Scorecard:** 32 pillars (utility/usability/expandability) — this doc
makes them measurable instead of declared.

> `find or do all next` was re-scanning but intent felt underwhelming
> because the 100-task PERT polished wiring (launchd, codegen, .gitignore)
> while deferring the *user job*: `run qwen3.5-0.8b on desktop NVIDIA
> dual-GPU and get evidence` (WBS 26-40, blocked on SVM/BIOS).
> This spec re-captures that job as the primary requirement.

## 1. Primary job (JTBD)

As an operator on `koosh` desktop (RTX 4070 12GB + GTX 1080 8GB) I want to

```
run qwen3.5-0.8b on both GPUs via vLLM + SGLang → get SuiteResult v0.5
→ canonicalize to cells → seed Langfuse → verify evidence_label
```

in **< 5 min** (`bench/comparison/run_5min_benchmark.py`) without
manual `wsl --` or `podman` steps, on `Ubuntu-22.04` today and
`Fedora44` after `install_wsl_pheno_serve.sh` (81).

**Acceptance:** `tests/test_run_desktop_lane_eval.py` mock dual-engine
passes and `scripts/dual_gpu/preflight.py` (93) parses `nvidia-smi`
PCIe + VRAM correctly (mocked in `tests/test_dual_gpu_preflight.py` 94).

## 2. Scorecard → measurable contracts

| Pillar (32) | WBS | Contract | How measured |
|-------------|-----|----------|--------------|
| Utility: dual-GPU evidence | 26-40 | `config/desktop_nvidia_qwen35_lane.yaml` partitioning + `evidence/dual_gpu/host_manifest.yaml` 7-day tail | `tests/test_desktop_lane_config.py` schema validation |
| Usability: one-command lane | 28,83-84 | `scripts/run_desktop_lane_eval.py` CLI + `start_dual_gpu_stack.ps1` + `run_dual_gpu_smoke.ps1` 4-min | `tests/test_start_dual_gpu_stack_ps1.py` mock engine start |
| Expandability: federated | 81-95 | `platform/federation/composition.v0.yaml` + `fleet-proto` `capacity.fit/device.heartbeat/fleet.peers` | `tests/test_install_wsl_pheno_serve_sh.py` mock SSH + `harbor_result_to_cells.py` idempotent |
| Governance: traceability | 56-70 | `bench/types.py` `TaskStatus.WRONG` vs `PASS` + `host-guard` ABI | `tests/test_host_guard_public_abi.py` (56) + `hybrid_decode_dispatch.inc` (57) |

## 3. Requirements (atomic, testable)

- **R1** `bench/types.py::TaskStatus` aliases are identity (`PASS is OK`);
  `TaskResult(status="pass")` coerces to `OK` (covers WBS 8 audit).
- **R2** `kernels/qwen3.5-0.8b/metal/hybrid_decode_dispatch.inc` is
  codegen-owned from `arch.yaml::kernel_strategy.default_simdgroup_size = 32`
  and exposes `kArchSimdgroupSize 32u` + `kHybridFullAttn*` schedule
  `{3,7,11,15,19,23}` (WBS 57-58).
- **R3** `.gitignore` leaks no source-tree patterns (ADR 0008 §D4) —
  `tests/test_gitignore_no_source_tree_patterns.py` (73) + 6 drift guards
  74-79 must be `pytest` green (gate 80).
- **R4** `scripts/install_wsl_pheno_serve.sh` (81) is idempotent Fedora44
  baseline; `install_wsl_pheno_serve.ps1` (82) wraps `wsl -d Ubuntu-22.04`;
  both leave `bench/results/2026-07-04/_wsl_install_*.log` + heartbeat.
- **R5** `start_dual_gpu_stack.ps1` (83) boots vLLM 0.5 + SGLang 0.4
  pinned versions (WBS 91) — verified by `run_dual_gpu_smoke.ps1` (84)
  pings to both engines.
- **R6** Evidence is canonical: `SuiteResult → canonicalize.py → cells v0.5`
  → `harbor_result_to_cells.py` → `platform/federation/out/cells-*.json`
  (ignored, not committed) → `seed_langfuse` via `LANGFUSE_*` vault binding
  (not `apps/bench-cockpit/.env`).

## 3.1 Testability hardening (makes R1-R6 green/red unambiguous)

| Req | Threshold / schema | Negative case | Gate |
|-----|-------------------|---------------|------|
| **R1** | Enum `TaskStatus` {`OK`,`PASS`,`WRONG`,`FAIL`}; identity `assert TaskStatus.PASS is TaskStatus.OK`; coercion `{"pass","PASS","ok","OK"} → OK`; `mypy --strict` | invalid `"done"` → `ValueError` | `pytest -q tests/test_task_status.py` + `mypy bench/types.py` |
| **R2** | `arch.yaml` JSON-schema `kernel_strategy.default_simdgroup_size: 32`; `codegen.py` output hash pinned; schedule indexed by layer `{3,7,11,15,19,23}` | `validate.py --quick` byte-mismatch → fail | `python kernels/qwen3.5-0.8b/python/validate.py --quick` |
| **R3** | Forbidden regexes `^bench/results/.*\.json` (except `*.sha256`), `^\.env`; allowlist `bench/results/**/*.sha256`; 6 guards = `test_gitignore_no_source_tree_patterns.py` + `test_drift_{codegen,contracts,evidence,host,preflight,smoke}.py` | any `*.json` not `*.sha256` → fail | `pytest -q tests/test_gitignore* tests/test_drift*` (gate 80) |
| **R4** | Idempotency = 2nd run exits 0 no diff; baseline `Fedora44` packages `sglang==0.4.2 vllm==0.5.1` locked in `uv.lock`; heartbeat JSON `{"device.heartbeat":{"ts": iso, "wsl": "Fedora44", "gpu": "4070+1080"}}`; log `bench/results/_wsl_install_*.log` rotated 7 days | 2nd run diff → fail | `tests/test_install_wsl_pheno_serve_sh.py` mock SSH |
| **R5** | Pins `vLLM==0.5.1` + `SGLang==0.4.2` in `pyproject.toml`; env `VLLM_PORT=8000 SGLANG_PORT=30000`; smoke `curl /health` timeout 30s; failure mode `one engine down → gen_ok 0` | timeout or missing pin → fail | `tests/test_start_dual_gpu_stack_ps1.py` |
| **R6** | Schema `bench/contracts/EVAL_RESULT_CONTRACT.md` `gen_ok 0/1`, `verified_pass_at_1 0-1`, `evidence_label reported/verified`; CLI `python bench/contracts/verify_contract.py cells.json`; vault `Doppler` keys `LANGFUSE_HOST/KEY` project `pheno-harness-v5` dataset `pheno-harness-v5`; `cells-*.json` ignored `platform/federation/out/.gitignore` | missing `evidence_label` → fail | `bench/contracts/verify_contract.py` |

## 4. What was weak

- **Capture gap:** `agileplus-specs/001-core-setup` and `phenoSpecs/WORKLOG.md`
  split the source-of-truth; no contract test linked `eval_pillars.yaml`
  motion multiplier (WBS 14) to dashboard `planned(5)`.
- **SOTA gap:** `launchd` sidecars fire but `pheno-serve` (`:8090`) not
  live — so `snapshot_sota.py --backfill` labels `backfilled` without a
  `live verified` golden to compare against.

Fix: this doc is the contract; `proc all` will now make `87-90,93-94`
mock tests real (see `scripts/dual_gpu/preflight.py`).

## 5. Path to each stage

1. **Usable (now):** `pytest -q kernels/qwen3.5-0.8b/tests/` 5 passed +
   `tests/` 17 passed — harness is usable headless.
2. **Useful:** land `98/99` via `droid-sync` (C rebase) → `PHASE 7` tag
   `v0.8-pheno-harness-summit` on `main`.
3. **Used:** BIOS `SVM Enabled` → `wsl --shutdown` → `Fedora44` import
   → `start_dual_gpu_stack.ps1` → `run_dual_gpu_smoke.ps1` 4-min green
   → `host_manifest.yaml` rolling tail.

---
*End requirements v1. Queue to `droid-main` per AGENTS.md §15.*
