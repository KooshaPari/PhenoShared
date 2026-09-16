# Phase 6 gate close-out — DAG-95

Date: 2026-08-07. Phase 6 of the 100-task WBS/PERT DAG
(`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`) is structurally
complete. Tasks DAG-81 through DAG-94 each landed a canonical artifact:
the Fedora 44 / WSL2 install baseline, the three Windows-side wrappers
(.ps1), the dual-GPU config derivative, the operator guide, the version
pin consolidation, the host manifest stub, the preflight probes, and the
five pytest gates. The lane is still `status: planning_only` per
`config/desktop_nvidia_dual_gpu_fedora44.yaml` because the lane
contract forbids install / launch / benchmark execution outside an
explicit window.

## Gate result

**PASS** — `pytest -q tests/test_install_wsl_pheno_serve_sh.py
tests/test_install_wsl_pheno_serve_ps1.py
tests/test_start_dual_gpu_stack_ps1.py
tests/test_run_dual_gpu_smoke_ps1.py tests/test_dual_gpu_preflight.py`
exits 0 with `33 passed, 2 skipped` and no failures.

## Tasks closed

| DAG | Title | Commit | Artifact |
|-----|-------|--------|----------|
| 81 | `scripts/install_wsl_pheno_serve.sh` (Fedora 44 baseline) | `4afe22b` | `scripts/install_wsl_pheno_serve.sh` |
| 82 | `scripts/install_wsl_pheno_serve.ps1` (Windows wrapper) | `f05bbab` | `scripts/install_wsl_pheno_serve.ps1` |
| 83 | `scripts/start_dual_gpu_stack.ps1` (vLLM + SGLang dual boot) | `f05bbab` | `scripts/start_dual_gpu_stack.ps1` |
| 84 | `scripts/run_dual_gpu_smoke.ps1` (4-min verification) | `f05bbab` | `scripts/run_dual_gpu_smoke.ps1` |
| 85 | `config/desktop_nvidia_dual_gpu_fedora44.yaml` (derivative) | `54b055b` | `config/desktop_nvidia_dual_gpu_fedora44.yaml` |
| 86 | `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` (operator guide) | `4afe22b` | `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` |
| 87 | `tests/test_install_wsl_pheno_serve_sh.py` (mock SSH) | `5c4c5c2` | `tests/test_install_wsl_pheno_serve_sh.py` |
| 88 | `tests/test_install_wsl_pheno_serve_ps1.py` (syntax) | `b0e01a9` | `tests/test_install_wsl_pheno_serve_ps1.py` |
| 89 | `tests/test_start_dual_gpu_stack_ps1.py` (mock engine start) | `8fad058` | `tests/test_start_dual_gpu_stack_ps1.py` |
| 90 | `tests/test_run_dual_gpu_smoke_ps1.py` (mock pings) | `6925060` | `tests/test_run_dual_gpu_smoke_ps1.py` |
| 91 | `docs/SETUP_VERSIONS.md` (vLLM 0.5 + SGLang 0.4 pins) | `2f904b0` | `docs/SETUP_VERSIONS.md` |
| 92 | `evidence/dual_gpu/host_manifest.yaml` (rolling 7-day tail) | `cff8e20` | `evidence/dual_gpu/host_manifest.yaml` |
| 93 | `scripts/dual_gpu/preflight.py` (PCIe + GPU memory probe) | `cda1ee1` | `scripts/dual_gpu/preflight.py` |
| 94 | `tests/test_dual_gpu_preflight.py` (mock `nvidia-smi`) | `28396f4` | `tests/test_dual_gpu_preflight.py` |
| 95 | phase 6 gate (this doc) | (this commit) | `docs/sessions/20260802-desktop-nvidia-mvp/06_phase_gate.md` |

## Test sweep

```
$ python -m pytest tests/test_install_wsl_pheno_serve_sh.py \
    tests/test_install_wsl_pheno_serve_ps1.py \
    tests/test_start_dual_gpu_stack_ps1.py \
    tests/test_run_dual_gpu_smoke_ps1.py \
    tests/test_dual_gpu_preflight.py -q --tb=line
..........ssss........................                  [100%]
33 passed, 2 skipped in 2.73s
```

- `tests/test_install_wsl_pheno_serve_sh.py` — 6 fixtures, all pass.
- `tests/test_install_wsl_pheno_serve_ps1.py` — 6 fixtures, all pass.
- `tests/test_start_dual_gpu_stack_ps1.py` — 8 fixtures, 1 skipped
  (pwsh not on PATH; the AST-parse guard returns `pytest.skip`).
- `tests/test_run_dual_gpu_smoke_ps1.py` — 7 fixtures, 1 skipped
  (same pwsh AST-parse guard).
- `tests/test_dual_gpu_preflight.py` — 8 fixtures, all pass.

## Outstanding

- DAG-100 (`tag v0.8-pheno-harness-summit + release notes`) is still
  pending; this gate is the last dependency from the Phase 6 side of
  the critical path (1 → 2 → 5 → 25 → 41 → 55 → 70 → 96 → 98 → 99 →
  100). Phase 6 itself is closed.
- The Fedora 44 lane contract remains `status: planning_only`. An
  operator window alone cannot authorize setup or a smoke run: live work
  requires an owner-issued execution authority, reviewed active policy,
  current two-device no-launch preflight, repeated no-fallback helper and
  primary results, harness evaluation, and independent promotion review.
- `evidence/dual_gpu/host_manifest.yaml` is the synthetic initial stub
  (DAG-92), not live promotion evidence. A future capture may be collected
  only after the authority and policy prerequisites above are satisfied.

## References

- DAG plan: `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`
  (Phase 6, tasks 81–95)
- Operator guide: `docs/guides/WSL_FEDORA_44_DUAL_GPU.md`
- Version pins: `docs/SETUP_VERSIONS.md`
- Lane contract: `config/desktop_nvidia_dual_gpu_fedora44.yaml`
- Session overview: `docs/sessions/20260802-desktop-nvidia-mvp/00_SESSION_OVERVIEW.md`
- Phase 2 outcome (sibling): `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md`

Refs: DAG-95; DAG-81 (`4afe22b`); DAG-82 (`f05bbab`); DAG-83 (`f05bbab`);
DAG-84 (`f05bbab`); DAG-85 (`54b055b`); DAG-86 (`4afe22b`); DAG-87
(`5c4c5c2`); DAG-88 (`b0e01a9`); DAG-89 (`8fad058`); DAG-90 (`6925060`);
DAG-91 (`2f904b0`); DAG-92 (`cff8e20`); DAG-93 (`cda1ee1`); DAG-94
(`28396f4`).
