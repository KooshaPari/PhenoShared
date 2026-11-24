# Custom Pheno benchmark suites

Pheno-tailored evaluation slots registered under the `custom_pheno` tier in
`config/benchmark_registry_2026-07.yaml`. These complement upstream Harbor,
DeepSWE, and knowledge benchmarks with replay, hardware, and role-specific
signals that only exist inside pheno-harness.

## Suite slots

| Slot | Registry id | Purpose | Driver |
|------|-------------|---------|--------|
| **trace-replay** | `custom_pheno_trace` | Replay real agent traces as Harbor-compatible multi-step tasks; score recoverability and escalation | `scripts/run_long_horizon.py` |
| **dual-gpu-perf** | `custom_pheno_dual_gpu` | Capacity-weighted heterogeneous serving sweep across 3090 Ti + 1080 Ti | `scripts/run_heterogeneous_perf.py` |
| **kernel-forge-loop** | (via `kernelbench_rtx3090`) | KernelBench problems executed through forgecode-fork `GpuLane::Primary3090` | `scripts/run_kernelbench_rtx3090.ps1` |
| **role-suite** | (via `eval/role_suite.py`) | Per-role trace eval — solo engineer, reviewer, planner, QA, perf, integration, advisor | `scripts/run_role_eval.py` |

## Directory layout

```
bench/custom/
├── README.md                 # this file
├── trace-replay/             # replayable task specs derived from real traces
├── dual-gpu-perf/            # fixtures and sweep configs for heterogeneous perf
├── kernel-forge-loop/        # KernelBench problem manifests (when acquired)
└── role-suite/               # human-reviewed role trace specs
```

Only `trace-replay` and `dual-gpu-perf` are first-class registry entries today.
`kernel-forge-loop` and `role-suite` share upstream or eval modules but live here
for fixture storage.

## trace-replay

Long-horizon custom tasks sourced from OmniRoute, Forge, Codex, Cursor, and
Factory Droid traces. Spec schema follows `plans/2026-07-03-forgecode-eval-profiling-v1/TRACE_EVALSET_PLAN.md`.

- Fixtures: `bench/custom/trace-replay/`
- Results: `bench/results/long_horizon/`
- **Scoreable:** false until specs are human-reviewed and verifier artifacts are pinned (see `eval/role_suite.py` manifest-first pattern).

Dry-run plan:

```powershell
python scripts/run_benchmark_matrix.py --suite custom_pheno_trace
python scripts/run_long_horizon.py --help
```

## dual-gpu-perf

Hardware-aware serving eval for the 3090 Ti (primary generation) + 1080 Ti
(legacy helper) stack documented in `config/hardware_aware_placement.yaml`.

- Smoke: `scripts/run_dual_gpu_smoke.ps1`
- Stack: `scripts/start_dual_gpu_stack.ps1`
- Sweep: `scripts/run_heterogeneous_perf.py`
- Results: `bench/results/perf/`

**Scoreable:** true for tok/s, TTFT, and queue-depth metrics (no semantic verifier).

Dry-run plan:

```powershell
python scripts/run_benchmark_matrix.py --suite custom_pheno_dual_gpu
python scripts/run_heterogeneous_perf.py --help
```

## kernel-forge-loop

KernelBench-v3 **RTX3090Bench** (43 CUDA/Triton problems, levels L1–L4).
Scoring is speedup vs PyTorch baseline on the 3090 Ti primary lane.

- Registry: `kernelbench_rtx3090` in `config/benchmark_registry_2026-07.yaml`
- Config: `config/kernelbench_rtx3090.yaml`
- Driver: `scripts/run_kernelbench_rtx3090.ps1` (dry-run by default; `-Execute` to run)
- Fixtures: `bench/custom/kernel-forge-loop/`
- Planner: `scripts/kernelbench_smoke_plan.py`
- Results: `bench/results/kernelbench/`

PyTorch device policy: `CUDA_VISIBLE_DEVICES=1` exposes the RTX 3090 Ti as
`cuda:0` (see `config/hardware_aware_placement.yaml`).

Dry-run plan:

```powershell
.\scripts\run_kernelbench_rtx3090.ps1
python scripts/run_benchmark_matrix.py --suite kernelbench_rtx3090
```

## role-suite

Eight role-specific trace eval lanes (solo engineer, coding subagent, reviewer,
planner, QA, perf, integration, advisor). Manifest-first — execution is blocked
until specs pass human review.

- Spec root: `bench/custom/role-suite/`
- Builder: `eval/role_suite.py` / `scripts/run_role_eval.py`
- Results: `bench/results/role_eval/` (when wired)

## Matrix planner

Print the full custom tier or entire registry without side effects:

```powershell
python scripts/run_benchmark_matrix.py
python scripts/run_benchmark_matrix.py --tier custom_pheno
python scripts/run_benchmark_matrix.py --priority P0
python scripts/run_benchmark_matrix.py --json
```
