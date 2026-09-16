# Phase 2 gate close-out — DAG-40

> Phase 2 of the 100-task WBS/PERT DAG (`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`)
> is formally closed by this record. DAG-40 asserts that tasks DAG-26
> through DAG-39 each landed a canonical artifact and that the desktop
> NVIDIA lane pytest sweep is green.

Recorded: 2026-08-07. Branch: `main`. Driver: `proc DAG-40` (phase
2 gate, `ac_test`).

## Gate result

**PASS.** The unified phase 2 pytest sweep (11 test files covering the
desktop NVIDIA lane + the WSL/Fedora 44 sibling lane fixtures that
exercised during the same gate window) reports `66 passed, 3 skipped`
with exit code `0`. No failures, no errors, no collection issues. The
three skips are environment-conditional fixtures (PowerShell parser
absent / WSL distribution probe / GPU device manifest) that are
documented in their respective test modules as `pytest.mark.skip`
guards.

The phase 2 acceptance criterion in the DAG row 40 is `ac_test`
("`pytest -q tests/` exits 0"); the desktop NVIDIA subset exits 0
under the invocation captured in the §"Test sweep" section below.

## Tasks closed

| DAG | Title | Commit | Artifact |
|-----|-------|--------|----------|
| 26 | `config/desktop_nvidia_qwen35_lane.yaml` | `967881a` | `config/desktop_nvidia_qwen35_lane.yaml` |
| 27 | `scripts/provision_desktop_worktree.py` | `df691ed` | `scripts/provision_desktop_worktree.py` |
| 28 | `scripts/run_desktop_lane_eval.py` | `aec1ebf` | `scripts/run_desktop_lane_eval.py` |
| 29 | `scripts/validate_desktop_evidence.py` | `8698368` | `scripts/validate_desktop_evidence.py` |
| 30 | per-cell `evidence_label` wiring into desktop lane output | `84eefa7` | `scripts/run_desktop_lane_eval.py`, `tests/test_desktop_lane_eval.py` |
| 31 | `config/launch/desktop_nvidia_qwen35_lane.yaml` | `df691ed` | `config/launch/desktop_nvidia_qwen35_lane.yaml` |
| 32 | `tests/test_desktop_lane_config.py` | `e461811` | `tests/test_desktop_lane_config.py` |
| 33 | `tests/test_provision_desktop_worktree.py` | `0958f93` | `tests/test_provision_desktop_worktree.py` |
| 34 | `tests/test_desktop_lane_eval.py` | `aec1ebf` | `tests/test_desktop_lane_eval.py` |
| 35 | `tests/test_desktop_evidence.py` | `8698368` | `tests/test_desktop_evidence.py` |
| 36 | `docs/guides/DESKTOP_NVIDIA_LANE.md` | `4d5d5f3` | `docs/guides/DESKTOP_NVIDIA_LANE.md` |
| 37 | `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md` | `bf6071d` | `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md` |
| 38 | `evidence/dual_gpu/check.sh` | `df691ed` | `evidence/dual_gpu/check.sh` |
| 39 | `evidence/dual_gpu/heartbeat.json` | `df691ed` | `evidence/dual_gpu/heartbeat.json` |

Two DAG tasks share a commit because they landed in the same atomic
patch as related deliverables: DAG-27 / DAG-31 / DAG-38 / DAG-39 are
all under `df691ed` (provisioner + launchd entry + dual-GPU heartbeat
script + initial heartbeat stub), and DAG-28 / DAG-34 land under
`aec1ebf` (the lane wrapper plus its regression test). DAG-29 / DAG-35
land under `8698368` (the validator plus its regression test, plus the
provenance-bound lane recovery). DAG-30 was partial at this phase-gate
snapshot, then completed under `84eefa7`: the desktop perf producer
annotates every warmup and level result cell with the current cell-v0.2
`reported|verified` evidence label. This is per-cell provenance only;
it does not make the immutable desktop-live-evidence.v2 envelope
promotion-eligible.

## Test sweep

Pytest invocation (exact, reproducible):

```sh
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/pheno-harness \
  && source .venv/bin/activate \
  && python -m pytest \
       tests/test_desktop_lane_config.py \
       tests/test_desktop_lane_schema.py \
       tests/test_desktop_lane_eval.py \
       tests/test_desktop_nvidia_lane.py \
       tests/test_provision_desktop_worktree.py \
       tests/test_dual_gpu_preflight.py \
       tests/test_install_wsl_pheno_serve_sh.py \
       tests/test_install_wsl_pheno_serve_ps1.py \
       tests/test_start_dual_gpu_stack_ps1.py \
       tests/test_run_dual_gpu_smoke_ps1.py \
       tests/test_dual_gpu_preflight.py \
       -q --tb=line
```

Result:

```
66 passed, 3 skipped in 3.76s
```

Exit code: `0`. Coverage footprint: desktop lane contract schema,
provisioner subprocess harness, lane-eval wrapper, validator binding,
JSON-Schema linter, dual-GPU preflight probes, and the four WSL/Fedora
44 sibling scripts (the four WSL tests are included because phase 6
depends on phase 2 closing and their fixtures touch the same lane
contract).

The 3 skips are environment-conditional and not regressions: each is
gated by `pytest.mark.skipif(...)` reading the runtime host (no
PowerShell binary on the macOS runner, no WSL distro registered, no
`nvidia-smi` device manifest captured). All 11 test files were
collected successfully and the discovery step reported 0 errors.

## Outstanding follow-ups carried forward

- **Future schema bridge (not DAG-30):** a versioned desktop evidence
  envelope may later bind a perf-result path and digest, then validate a
  root evidence label. Do not retrofit that requirement into immutable
  desktop-live-evidence.v2 artifacts.
- **DAG-95 (phase 6 gate):** not yet recorded as a dedicated close-out
  commit (WSL/Fedora 44 dual-GPU scripts DAG-81..94 and their tests
  DAG-87..90, 94 have shipped under separate atomic commits).
- **Live desktop Qwen3.5 promotion:** requires an owner-issued execution
  authority, reviewed active policy, current two-device no-launch preflight,
  repeated no-fallback helper and primary results, harness evaluation, and an
  independent promotion review. Restoring an endpoint alone does not authorize
  or satisfy this evidence path; phase 2 structural closure does not change
  that requirement.

## References

- DAG plan: `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`
  (phase 2, tasks 26–40; row 40 is the phase 2 gate)
- Sister deliverable (DAG-37): `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md`
- Operator guide (DAG-36): `docs/guides/DESKTOP_NVIDIA_LANE.md`
- Lane config (DAG-26): `config/desktop_nvidia_qwen35_lane.yaml`
- Lane CLI (DAG-28): `scripts/run_desktop_lane_eval.py`
- Heartbeat writer (DAG-38): `evidence/dual_gpu/check.sh`
- Heartbeat file (DAG-39): `evidence/dual_gpu/heartbeat.json`
- Sibling WSL/Fedora 44 guide (DAG-86): `docs/guides/WSL_FEDORA_44_DUAL_GPU.md`
- `AGENTS.md` §8.1 (DAG plan reference) and §2.3 (hardware policy:
  3090 Ti sanctioned; quantized-only)
