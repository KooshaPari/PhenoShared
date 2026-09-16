# Desktop NVIDIA Dual-GPU Lane — operator guide

> Canonical guide for the Desktop NVIDIA dual-GPU lane
> (Qwen3.5-0.8B, DAG phase 2). Last revised: 2026-08-05 (DAG-36).

This guide is the operator runbook for tasks DAG-26 to DAG-40. It
mirrors `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` (DAG-86 sibling) but
covers the in-process / planned-execution desktop lane rather than the
remote WSL2 + Fedora 44 stack.

## Overview

The Desktop NVIDIA dual-GPU lane is the *local* counterpart to the
WSL2/Fedora 44 remote lane. It runs the Qwen3.5-0.8B model on a single
desktop box with 2× NVIDIA GPUs, partitioned by `CUDA_VISIBLE_DEVICES`
per `config/desktop_nvidia_qwen35_lane.yaml`. All runtimes
(`vllm`, `sglang`, `llama.cpp`, `tensorrt_llm`) share the lane.

DAG composition (phase 2 of the 100-task WBS/PERT DAG, tasks 26-40):

| DAG | Script / artifact | Role |
|-----|-------------------|------|
| 26 | `config/desktop_nvidia_qwen35_lane.yaml` | lane spec (canonical) |
| 27 | `scripts/provision_desktop_worktree.py` | tailscale-bootstrap worktree |
| 28 | `scripts/run_desktop_lane_eval.py` | CLI entrypoint (dry-run + execute) |
| 29 | `scripts/validate_desktop_evidence.py` | evidence binding check |
| 30 | `evidence_label` wiring | contract ↔ envelope |
| 31 | `config/launch/desktop_nvidia_qwen35_lane.yaml` | launchd entry |
| 32-35 | `tests/test_desktop_lane_*.py` | schema + provision + run + validate |
| 36 | **this file** | operator guide |
| 37 | `docs/sessions/20260802-desktop-nvidia-mvp/04_dag_wbs.md` | MVP session outcome |
| 38 | `evidence/dual_gpu/check.sh` | daily nvidia-smi heartbeat |
| 39 | `evidence/dual_gpu/heartbeat.json` | rolling tail |
| 40 | phase 2 gate | all 15 tasks green |

The lane is **planning-only** until an explicit execution window is
granted. See `execution_policy.require_explicit_window` in the contract.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Hardware | 2× RTX 3090 Ti (24 GB) per `AGENTS.md` §2.3 — only the 3090 Ti is sanctioned. The lane also supports a 1080 Ti as the *helper* role (see lane config). |
| OS | Linux or WSL2 distro on the desktop host. No macOS inference. |
| NVIDIA driver | recent `nvidia-smi` on `PATH`; CUDA 12.x toolkit. |
| CUDA toolkit | matching the driver; both `vllm` and `llama.cpp` builds pinned in the lane contract. |
| Tailscale | the desktop rig is on the same tailnet as the Mac dev box (provisioned via DAG-27). |
| Lane config | `config/desktop_nvidia_qwen35_lane.yaml` (DAG-26). All scripts read this file at startup. |
| Model | `Qwen/Qwen3.5-0.8B` (no BF16 eval artifacts; quantized only per `AGENTS.md` §2.3). |
| `evidence/dual_gpu/` | writable; the daily check appends here. |

`CUDA_VISIBLE_DEVICES` is **runtime-specific** and must be verified
against the captured device manifest — see `visibility_notes` in the
lane config.

## Install

### 1. Provision a worktree on the desktop rig (DAG-27)

```sh
# On the Mac dev box:
python3 scripts/provision_desktop_worktree.py \
  --host <REDACTED>@100.x.x.x \
  --branch fix/desktop-vllm-runtime \
  --worktree-dir /home/<REDACTED>/pheno-harness
```

The script:
1. Pings the rig over SSH (tailscale).
2. Clones `fix/desktop-vllm-runtime` into a fresh worktree.
3. Records the entry in `evidence/dual_gpu/worktrees.json`
   (idempotent; re-runs are safe).
4. Supports `--dry-run` for record-only operation.

### 2. Install the dual-GPU stack

```sh
# On the desktop rig (WSL2 distro or bare Linux):
sudo bash scripts/install_wsl_pheno_serve.sh \
  --branch main \
  --repo-url https://github.com/<REDACTED>/pheno-harness.git
```

Idempotent. The installer writes the lane config, pins CUDA runtimes,
and registers the daily evidence check (DAG-38) under launchd.

## Run

`run_desktop_lane_eval.py` is the CLI entrypoint (DAG-28). It never
launches or terminates a server — it *plans* a run by default, and
only invokes `run_perf_suite.py` when `--execute` is set together with
an explicit `--window-id`.

```sh
# 1. Dry-run (prints the plan as JSON; no side effects):
python3 scripts/run_desktop_lane_eval.py \
  --runtime primary \
  --window-id <explicit-window-id> \
  --output bench/results/desktop/eval.json \
  --manifest-output bench/results/desktop/manifest.json

# 2. Execute (requires a granted execution window):
python3 scripts/run_desktop_lane_eval.py \
  --runtime primary \
  --window-id <explicit-window-id> \
  --output bench/results/desktop/eval.json \
  --manifest-output bench/results/desktop/manifest.json \
  --execute
```

What it writes (under `bench/results/desktop/`):

- `eval.json` — the perf-suite result envelope
- `manifest.json` — provenance + `contract_sha256` + `result_sha256`
- on dry-run: a plan JSON (no eval, no manifest)

The helper runtime (`--runtime helper`) targets the 1080 Ti via the
1080 Ti ↔ 3090 Ti mapping in the lane config. The primary runtime
targets the 3090 Ti (vLLM on `cuda:0`).

## Verify

### 1. Check the daily evidence heartbeat (DAG-38/39)

```sh
# Last heartbeat:
cat evidence/dual_gpu/heartbeat.json

# Rolling 7-day host manifest:
cat evidence/dual_gpu/host_manifest.yaml

# Force a check now (writes both):
bash evidence/dual_gpu/check.sh
```

`heartbeat.json` records `nvidia-smi` summary, PCIe link, and per-GPU
memory pressure. `host_manifest.yaml` is the rolling tail used by the
two-consecutive-green promotion gate.

### 2. Validate the evidence envelope (DAG-29)

```sh
# Validate the canonical live evidence (default path):
python3 scripts/validate_desktop_evidence.py

# Validate a specific envelope (CI mode):
python3 scripts/validate_desktop_evidence.py \
  --evidence bench/results/desktop/eval.json \
  --require-promotable
```

The validator checks schema version, contract SHA, source commit
reachability, model canonical-id, dual-GPU device manifest, runtime
provenance, repeatability counts, and the 7 promotion gates. Exit
codes: `0` valid, `2` invalid, `3` not promotable (with
`--require-promotable`).

## Troubleshoot

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `CUDA_VISIBLE_DEVICES` rejected at boot | not set in the launchd env | export per `hardware.devices.<gpu>.cuda_visible_devices` in the lane config; re-run `install_launchd.sh` |
| `nvidia-smi: command not found` | NVIDIA driver not on `PATH` | install the driver, then re-run `evidence/dual_gpu/check.sh`; the heartbeat will report `nvidia_smi: []` until then |
| `provision_desktop_worktree.py` records `ssh_ok: false` | tailscale not joined or WSL distro off | verify `tailscale status` on both ends; the WSL distro must be up |
| Worktree dirty on the rig | the live lane wrote to a tracked file | reset with `git restore --worktree` (never `--hard`); re-run DAG-27 |
| `validate_desktop_evidence.py` exits 2 (invalid) | envelope schema drift or missing `contract_sha256` | re-run DAG-28 to re-emit the manifest; verify `config/desktop_nvidia_qwen35_lane.yaml` SHA |
| `evidence_label: blocked` | a promotion gate failed | inspect `promotion.gates` in the envelope; the gate names match `EXPECTED_GATES` in `validate_desktop_evidence.py` |
| `tensor_parallel` accidentally enabled | lane contract forbids it for 1080 Ti | check `runtime_policy.qwen35_08b.helper.tensor_parallel`; it must read `forbidden` |
| BF16 inference attempted | against `AGENTS.md` §2.3 policy | use a quantized artifact (q2–q8); reject the run |

## References

- `config/desktop_nvidia_qwen35_lane.yaml` — the lane spec (DAG-26)
- `config/launch/desktop_nvidia_qwen35_lane.yaml` — the launchd entry (DAG-31)
- `scripts/provision_desktop_worktree.py` — tailscale-bootstrap worktree (DAG-27)
- `scripts/run_desktop_lane_eval.py` — CLI entrypoint (DAG-28)
- `scripts/validate_desktop_evidence.py` — evidence binding (DAG-29)
- `evidence/dual_gpu/check.sh` — daily nvidia-smi heartbeat (DAG-38)
- `evidence/dual_gpu/heartbeat.json` — rolling tail (DAG-39)
- `evidence/dual_gpu/host_manifest.yaml` — 7-day device manifest (DAG-92)
- `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md` — phase 2 tasks 26-40
- `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` — sibling guide for the WSL2/Fedora 44 remote lane (DAG-86)
- `AGENTS.md` §2.3 — hardware policy (only 3090 Ti sanctioned; quantized-only)
