# 100-Task WBS/PERT DAG — pheno-harness summit (2026-08-05)

**Status:** canonical source-of-truth for the next 100 atomic tasks.
**Owner:** forge (agent CLI). **Driver:** `proc` / `proc all` / `proc <id>`.
**Dep graph:** strict topological; tasks may declare `depends_on: [list]`.
**Ac:** every task has one acceptance bullet (ac_v1 = main has the commit).

> *"Each task must be meaningfully large sized but the DAG is a PERT/WBS
> with proper atomical decomposition."* — user directive, 2026-08-05.

## Phase overview

| Phase | Tasks | Theme | Outcome |
|-------|-------|-------|---------|
| 0 | 1–5 | ground truth + HEAD alignment | reproducible baseline |
| 1 | 6–25 | LLM-host test fixture restoration | `pytest -q tests/` green |
| 2 | 26–40 | Desktop NVIDIA dual-GPU lane | `run_desktop_lane_eval.py` ships |
| 3 | 41–55 | A4 `kArchSimdgroupSize` codegen wiring | drift-guard green on `main` |
| 4 | 56–70 | non-LLM host engineering | launchd + verifier + audit closed |
| 5 | 71–80 | .gitignore hardening + drift tests | no source-tree patterns leak |
| 6 | 81–95 | WSL2/Fedora 44 remote dual-GPU lane | `start_dual_gpu_stack.ps1` runs |
| 7 | 96–100 | integrate & ship | `v0.8-pheno-harness-summit` tag |

## Ac conventions

- `ac_v1`: commit on `main` with conventional subject + DAG id in footer.
- `ac_v2`: idempotent under `git restore --worktree` + re-run.
- `ac_drift`: golden snapshots match (codegen + SOTA + bench contracts).
- `ac_test`: `pytest -q tests/ kernels/qwen3.5-0.8b/tests/` exits 0.
- `ac_cron`: `launchctl kickstart -k` fires, sidecar written.

---

## Phase 0 — Ground truth + HEAD alignment (1–5)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 1 | land this DAG (`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`) | — | ac_v1 |
| 2 | rewrite AGENTS.md against current phase (Qwen3.5-0.8B; AMC paused) | 1 | ac_v1 |
| 3 | backfill missing 2026-07-25 + 2026-07-28 SOTA snapshots | — | ac_v1 |
| 4 | verify all 4 launchd agents loaded + force-fire each | — | ac_cron |
| 5 | snapshot `git status` strip + commit `chore: 2026-08-05 HEAD capture` | 1–4 | ac_v1 |

---

## Phase 1 — LLM-host test fixture restoration (6–25)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 6 | checkout `fix/desktop-vllm-runtime` + cherry-pick `1f1f533` | 5 | ac_v1 |
| 7 | diff `tests/test_bench_runner.py` against `aec1ebf^` | 6 | ac_v1 |
| 8 | fix `TaskStatus.WRONG` logic in `bench/types.py` | 7 | ac_test |
| 9 | add `bench/mlx_stub.py` module (typing + protocol) | 7 | ac_v1 |
| 10 | wire `mlx_stub` into `bench/runner.py` | 9 | ac_test |
| 11 | restore `tests/test_metal_simdgroup_constant.py` (3 fixtures) | 6 | ac_test |
| 12 | restore `tests/test_benchmark_envelope.py` (dry-run + D-R flags) | 6 | ac_test |
| 13 | restore `tests/test_bench_skeleton.py` (compat layer) | 8 | ac_test |
| 14 | add `tests/test_eval_pillars.py` (weight sum + motion multiplier) | 8 | ac_test |
| 15 | add `tests/test_evidence_label.py` (canonical enum) | 8 | ac_test |
| 16 | add `tests/test_dry_run_envelope.py` guard | 12 | ac_test |
| 17 | add `tests/test_handoff_serialization.py` (round-trip v0.5 envelope) | 12 | ac_test |
| 18 | add `tests/test_contamination_guard.py` (training-set diff) | 14 | ac_test |
| 19 | add `tests/test_health_repo_cron.py` (mock launchd) | 4 | ac_test |
| 20 | add `tests/test_worktree_gc_cron.py` (mock gone-branch) | 4 | ac_test |
| 21 | add `tests/test_lint_branches_cron.py` (8-prefix taxonomy) | 4 | ac_test |
| 22 | add `tests/test_install_launchd_sh.py` (plist + `set -f`) | 4 | ac_test |
| 23 | add `tests/test_sota_snapshot_chain.py` (sha256 sidecar) | 19 | ac_test |
| 24 | add `tests/test_canonicalization.py` (v0.5 from `SuiteResult`) | 8,14 | ac_test |
| 25 | phase 1 gate: `pytest -q tests/` exits 0 | 8–24 | ac_test |

---

## Phase 2 — Desktop NVIDIA dual-GPU lane (26–40)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 26 | author `config/desktop_nvidia_qwen35_lane.yaml` (dual-GPU partitioning) | 5 | ac_v1 |
| 27 | author `scripts/provision_desktop_worktree.py` (tailscale-bootstrap) | 26 | ac_v1 |
| 28 | author `scripts/run_desktop_lane_eval.py` (CLI entrypoint) | 26, 27 | ac_v1 |
| 29 | author `scripts/validate_desktop_evidence.py` (binding check) | 28 | ac_v1 |
| 30 | wire `evidence_label` into desktop lane output | 28, 14 | ac_v1 |
| 31 | add `config/launch/desktop_nvidia_qwen35_lane.yaml` (launchd entry) | 26 | ac_v1 |
| 32 | add `tests/test_desktop_lane_config.py` (schema validation) | 26 | ac_test |
| 33 | add `tests/test_provision_desktop_worktree.py` (mock SSH) | 27 | ac_test |
| 34 | add `tests/test_run_desktop_lane_eval.py` (mock dual-engine) | 28 | ac_test |
| 35 | add `tests/test_validate_desktop_evidence.py` (binding) | 29 | ac_test |
| 36 | document `docs/guides/DESKTOP_NVIDIA_LANE.md` | 26–29 | ac_v1 |
| 37 | record `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md` outcome | 26–29 | ac_v1 |
| 38 | implement `evidence/dual_gpu/check.sh` (nvidia-smi parser) | 26 | ac_v1 |
| 39 | implement `evidence/dual_gpu/heartbeat.json` (rolling tail) | 38 | ac_v1 |
| 40 | phase 2 gate: desktop lane config + scripts + tests green | 26–39 | ac_test |

---

## Phase 3 — A4 `kArchSimdgroupSize` codegen wiring (41–55)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 41 | audit `kernels/qwen3.5-0.8b/python/codegen.py` for `kArchSimdgroupSize` | 25 | ac_v1 |
| 42 | regenerate `kernels/qwen3.5-0.8b/codegen/arch.json` (canonical) | 41 | ac_drift |
| 43 | regenerate `kernels/qwen3.5-0.8b/include/qwen3_5.h` | 41 | ac_drift |
| 44 | regenerate `kernels/qwen3.5-0.8b/rust/src/qwen3_5_arch.rs` | 41 | ac_drift |
| 45 | regenerate `kernels/qwen3.5-0.8b/zig/qwen3_5_consts.zig` | 41 | ac_drift |
| 46 | regenerate `kernels/qwen3.5-0.8b/mojo/qwen3_5_consts.mojo` | 41 | ac_drift |
| 47 | regenerate `kernels/qwen3.5-0.8b/nim/qwen3_5_consts.nim` | 41 | ac_drift |
| 48 | regenerate `kernels/qwen3.5-0.8b/metal/hybrid_decode_dispatch.inc` | 41 | ac_drift |
| 49 | add `kernels/qwen3.5-0.8b/tests/test_codegen_kArchSimdgroupSize.py` | 41 | ac_drift |
| 50 | add drift-guard test for `metal/hybrid_decode_dispatch.inc` | 48 | ac_drift |
| 51 | add `QWEN3_5_SIMDGROUP_SIZE_DEFAULT` macro to `arch.yaml` | 41 | ac_v1 |
| 52 | document `kernels/qwen3.5-0.8b/docs/kernel_layout.md` A4 section | 51 | ac_v1 |
| 53 | add `kernels/qwen3.5-0.8b/tests/test_simdgroup_size_host_binding.py` | 51 | ac_test |
| 54 | add `kernels/qwen3.5-0.8b/tests/test_soak.py` (5-min thermal check) | 41 | ac_v1 |
| 55 | phase 3 gate: A4 codegen tests green + drift-guard clean | 41–54 | ac_drift |

---

## Phase 4 — Non-LLM host engineering (56–70)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 56 | close-out audit-A5 follow-up: host-guard public ABI tested | 25 | ac_test |
| 57 | close-out audit-F3 follow-up: `hybrid_decode_dispatch.inc` tests | 25 | ac_test |
| 58 | close-out audit-A4 follow-up: `kArchSimdgroupSize` drift-guard | 55 | ac_drift |
| 59 | add `--backfill` flag to `scripts/cron/snapshot_sota.py` | 5 | ac_v1 |
| 60 | add `scripts/cron/force_fire_all.sh` (4 agent idempotent) | 4 | ac_cron |
| 61 | add `scripts/cron/install_launchd.sh` `--dry-run` mode | 4 | ac_v1 |
| 62 | add `config/risky_action_gate.yaml` test for `pattern_blocklist` | 25 | ac_test |
| 63 | add `verifier/risky_action.py` mainline + tests | 62 | ac_test |
| 64 | add `tests/bench/test_bench_contract_v0_5.py` (envelope round-trip) | 25 | ac_test |
| 65 | add `tests/bench/test_cell_metrics.py` (v0.2 helpers) | 25 | ac_test |
| 66 | add `bench/contracts/canonicalize.py` (v0.5 emit helper) | 64 | ac_v1 |
| 67 | add `scripts/harbor_consumer_dry_run.py` regression test | 64 | ac_v1 |
| 68 | add `config/eval_pillars.yaml` motion-multiplier test | 14 | ac_test |
| 69 | add `config/desktop_nvidia_qwen35_lane.yaml` schema linter | 26 | ac_v1 |
| 70 | phase 4 gate: cron + verifier + contracts tests green | 56–69 | ac_test |

---

## Phase 5 — .gitignore hardening + drift tests (71–80)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 71 | audit `.gitignore` against ADR 0008 §D4 (no source-tree patterns) | 5 | ac_v1 |
| 72 | remove 5 toxic source-tree patterns (per `4bf638c` review) | 71 | ac_v1 |
| 73 | add `tests/test_gitignore_no_source_tree_patterns.py` | 72 | ac_test |
| 74 | add `tests/test_gitignore_symlink_dirs.py` (ADR 0008 §D4) | 72 | ac_test |
| 75 | add `tests/test_gitignore_bench_results_only.py` (json in, sha out) | 72 | ac_test |
| 76 | add `tests/test_gitignore_dogfood_live.py` (`.dogfood-live-*`) | 72 | ac_test |
| 77 | add `tests/test_gitignore_kernels_zig.py` (`kernels/.../.zig-cache/`) | 72 | ac_test |
| 78 | add `tests/test_gitignore_kernels_rust_target.py` | 72 | ac_test |
| 79 | add `tests/test_gitignore_eval_traces.py` (`.jsonl` + `.profile.csv`) | 72 | ac_test |
| 80 | phase 5 gate: `.gitignore` audit + 9 drift tests green | 71–79 | ac_test |

---

## Phase 6 — WSL2/Fedora 44 remote dual-GPU lane (81–95)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 81 | author `scripts/install_wsl_pheno_serve.sh` (Fedora 44 baseline) | 40 | ac_v1 |
| 82 | author `scripts/install_wsl_pheno_serve.ps1` (Windows-side wrapper) | 81 | ac_v1 |
| 83 | author `scripts/start_dual_gpu_stack.ps1` (vLLM + SGLang dual boot) | 81 | ac_v1 |
| 84 | author `scripts/run_dual_gpu_smoke.ps1` (4-min verification) | 83 | ac_v1 |
| 85 | author `config/desktop_nvidia_dual_gpu_fedora44.yaml` (derivative) | 26 | ac_v1 |
| 86 | author `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` (operator guide) | 81–85 | ac_v1 |
| 87 | add `tests/test_install_wsl_pheno_serve_sh.py` (mock SSH) | 81 | ac_test |
| 88 | add `tests/test_install_wsl_pheno_serve_ps1.py` (syntax) | 82 | ac_test |
| 89 | add `tests/test_start_dual_gpu_stack_ps1.py` (mock engine start) | 83 | ac_test |
| 90 | add `tests/test_run_dual_gpu_smoke_ps1.py` (mock pings) | 84 | ac_test |
| 91 | add `documentation` for vLLM 0.5 + SGLang 0.4 version pins | 83 | ac_v1 |
| 92 | add `evidence/dual_gpu/host_manifest.yaml` (rolling 7-day tail) | 38 | ac_v1 |
| 93 | add `scripts/dual_gpu/preflight.py` (PCIe + GPU memory probe) | 83 | ac_v1 |
| 94 | add `tests/test_dual_gpu_preflight.py` (mock `nvidia-smi`) | 93 | ac_test |
| 95 | phase 6 gate: WSL/Fedora 44 dual-GPU scripts + tests green | 81–94 | ac_test |

---

## Phase 7 — Integrate & ship (96–100)

| ID | Title | depends_on | ac |
|----|-------|------------|----|
| 96 | close-out audit-A2 follow-up: ablation dry-run banner CI | 70 | ac_v1 |
| 97 | backfill 2026-08-05 → 2026-08-06 SOTA snapshots | 5 | ac_v1 |
| 98 | cherry-pick `fix/desktop-vllm-runtime` branch (LLM-host wiring) | 25, 96 | ac_v1 |
| 99 | reconcile `pheno-harness-runner-provenance` branch into `main` | 98 | ac_v1 |
| 100 | tag `v0.8-pheno-harness-summit` + release notes | 97, 99 | ac_v1 |

---

## Critical path

```
1 → 2 → 5 → 8 → 25 → 41 → 55 → 70 → 96 → 98 → 99 → 100
```

## Parallelisable clusters

- Tasks 3–4 (snapshot backfill + launchd verify) are independent of 1–2.
- Tasks 26–40 (Desktop NVIDIA) are independent of 41–55 (A4 codegen) once
  task 5 is merged.
- Tasks 71–80 (.gitignore) are independent of everything else.
- Tasks 81–95 (WSL/Fedora lane) depend on 26–40 (Desktop NVIDIA lane).

## Stop signals

- `proc amc` → "AMC paused per user directive" (no DAG walk).
- `proc <paused-id>` → "paused per user directive" (no DAG walk).
- `proc <unknown-id>` → "no such task; see §8.4 of AGENTS.md".

---

*End of DAG. Last revised 2026-08-05. Force-commit on overwrite; this is
the canonical source-of-truth for the next 100 tasks.*
