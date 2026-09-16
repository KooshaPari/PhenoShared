# Session 04: DAG WBS outcome (Desktop NVIDIA MVP)

Date: 2026-08-02 (session start); outcome recorded 2026-08-07.

## Outcome

Phase 2 of the 100-task WBS/PERT DAG (`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`)
is structurally complete. Tasks DAG-26 through DAG-39 each landed a
canonical artifact: the lane contract, the two Python entrypoints
(provision + run + validate), the four pytest gates, the operator guide,
the daily heartbeat, and the launchd entry. The lane is still
`status: planning_only` per `config/desktop_nvidia_qwen35_lane.yaml`
because the contract forbids inference, install, and benchmark execution
without an explicit window. No live Qwen3.5 promotion happened on the
desktop during this session; the only evidence captured is the
`evidence/dual_gpu/heartbeat.json` initial stub plus the desktop
evidence ledger (`bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json`),
which was carried over from the prior recovery work.

At the time this outcome was recorded, DAG-30 was partial. It was later
completed by `84eefa7`: `run_desktop_lane_eval.py` emits the current
cell-v0.2 `reported|verified` evidence label on every warmup and level
result cell. This records per-cell provenance; it is not an envelope-level
promotion gate. DAG-40
(phase 2 gate — `pytest -q tests/test_desktop_lane_*.py` exits 0) has no
dedicated close-out commit; the lane tests pass individually but the
unified gate was never recorded.

## Tasks closed

| DAG | Title | Status | Commit | Artifact |
|-----|-------|--------|--------|----------|
| 26 | `config/desktop_nvidia_qwen35_lane.yaml` | done | `967881a` | `config/desktop_nvidia_qwen35_lane.yaml` |
| 27 | `scripts/provision_desktop_worktree.py` | done | `df691ed` | `scripts/provision_desktop_worktree.py` |
| 28 | `scripts/run_desktop_lane_eval.py` | done | `aec1ebf` | `scripts/run_desktop_lane_eval.py` |
| 29 | `scripts/validate_desktop_evidence.py` | done | `8698368` | `scripts/validate_desktop_evidence.py` |
| 30 | per-cell `evidence_label` wiring into desktop lane output | done | `84eefa7` | `scripts/run_desktop_lane_eval.py`, `tests/test_desktop_lane_eval.py` |
| 31 | `config/launch/desktop_nvidia_qwen35_lane.yaml` | done | `df691ed` | `config/launch/desktop_nvidia_qwen35_lane.yaml` |
| 32 | `tests/test_desktop_lane_config.py` | done | `e461811` | `tests/test_desktop_lane_config.py` |
| 33 | `tests/test_provision_desktop_worktree.py` | done | `0958f93` | `tests/test_provision_desktop_worktree.py` |
| 34 | `tests/test_desktop_lane_eval.py` (was `test_run_desktop_lane_eval.py`) | done | `aec1ebf` | `tests/test_desktop_lane_eval.py` |
| 35 | `tests/test_desktop_evidence.py` (was `test_validate_desktop_evidence.py`) | done | `8698368` | `tests/test_desktop_evidence.py` |
| 36 | `docs/guides/DESKTOP_NVIDIA_LANE.md` | done | `4d5d5f3` | `docs/guides/DESKTOP_NVIDIA_LANE.md` |
| 37 | this outcome doc | done | (this commit) | `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md` |
| 38 | `evidence/dual_gpu/check.sh` | done | `df691ed` | `evidence/dual_gpu/check.sh` |
| 39 | `evidence/dual_gpu/heartbeat.json` | done | `df691ed` | `evidence/dual_gpu/heartbeat.json` |

Phase 2 gate (DAG-40): not recorded as a dedicated close-out commit.
Individual pytest files (`test_desktop_lane_config`,
`test_desktop_lane_eval`, `test_provision_desktop_worktree`,
`test_desktop_evidence`, `test_desktop_launcher`,
`test_desktop_nvidia_lane`, `test_desktop_lane_schema`,
`test_desktop_agentic_fixture`, `test_desktop_harbor_gate`) all exist;
the unified `ac_test` gate was not captured.

## Evidence

- Lane contract: `config/desktop_nvidia_qwen35_lane.yaml` (DAG-26)
- Provision script: `scripts/provision_desktop_worktree.py` (DAG-27)
- Run CLI: `scripts/run_desktop_lane_eval.py` (DAG-28)
- Validator: `scripts/validate_desktop_evidence.py` (DAG-29)
- Launchd entry: `config/launch/desktop_nvidia_qwen35_lane.yaml` (DAG-31)
- Operator guide: `docs/guides/DESKTOP_NVIDIA_LANE.md` (DAG-36)
- Daily heartbeat: `evidence/dual_gpu/check.sh`, `evidence/dual_gpu/heartbeat.json` (DAG-38/39)
- Test gates: `tests/test_desktop_lane_config.py`, `tests/test_provision_desktop_worktree.py`, `tests/test_desktop_lane_eval.py`, `tests/test_desktop_evidence.py`, plus `tests/test_desktop_launcher.py`, `tests/test_desktop_nvidia_lane.py`, `tests/test_desktop_lane_schema.py`, `tests/test_desktop_agentic_fixture.py`, `tests/test_desktop_harbor_gate.py`
- Carried-over desktop evidence ledger: `bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json`
- Heartbeat stub: `evidence/dual_gpu/heartbeat.json` (`{"captured_at":"2026-08-05T00:00:00Z","host":"initial","gpus":0,"evidence_label":"reported"}`)

## Outstanding

- **Future schema bridge (not DAG-30):** introduce a versioned
  desktop-evidence envelope that binds a perf-result path and digest
  before validating a root evidence label. Do not rewrite immutable
  desktop-live-evidence.v2 artifacts to simulate this linkage.
- **DAG-40:** record the phase 2 gate (`pytest -q` over the desktop
  test files) as a dedicated close-out commit.
- **DAG-95 (phase 6 gate):** WSL/Fedora 44 dual-GPU scripts (DAG-81..94)
  and their tests (DAG-87..90, 94) have shipped
  (`54b055b`, `4afe22b`, `5c4c5c2`, `b0e01a9`, `8fad058`, `6925060`,
  `cda1ee1`, `28396f4`); the unified phase 6 gate was not recorded.
- **Live desktop Qwen3.5 promotion:** requires an owner-issued execution
  authority, reviewed active policy, current two-device no-launch preflight,
  repeated no-fallback helper and primary results, harness evaluation, and an
  independent promotion review. Restoring an endpoint alone does not authorize
  or satisfy this evidence path.

## References

- DAG plan: `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`
  (phase 2, tasks 26–40)
- Operator guide (DAG-36): `docs/guides/DESKTOP_NVIDIA_LANE.md`
- Lane config (DAG-26): `config/desktop_nvidia_qwen35_lane.yaml`
- Sibling WSL/Fedora 44 guide (DAG-86): `docs/guides/WSL_FEDORA_44_DUAL_GPU.md`
- `AGENTS.md` §2.2 (WSL2 / Fedora 44 / dual-GPU hardware context)
- `AGENTS.md` §8.1 (DAG plan reference)
- Session siblings: `docs/sessions/20260802-desktop-nvidia-mvp/00_SESSION_OVERVIEW.md`,
  `01_RESEARCH.md`, `02_SPECIFICATIONS.md`, `03_DAG_WBS.md`,
  `04_IMPLEMENTATION_STRATEGY.md`, `05_KNOWN_ISSUES.md`,
  `06_TESTING_STRATEGY.md`
