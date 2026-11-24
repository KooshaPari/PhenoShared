# WSL2 + Fedora 44 + Dual-GPU Lane — operator guide

> Canonical guide for the WSL2 + Fedora 44 + tailscale remote dual-GPU
> lane. Last revised: 2026-08-05 (DAG-86).

## Topology

```
[Mac dev box]  --tailscale-->  [Windows 11]
                                    |
                                    | WSL2
                                    v
                              [Fedora 44 distro]
                                    |
                                    | PCIe passthrough
                                    v
                              [2x NVIDIA GPUs]
                                    |
                                    | vLLM + SGLang
                                    v
                              [Qwen3.5-0.8B MLX/Metal host]
```

The Mac dev box is the operator station. The Fedora 44 WSL distro is
the LLM host. Tailscale provides the secure tunnel.

## Install (one-time per rig)

```sh
# On the WSL Fedora 44 distro (sudo required for dnf + /etc/cron.d):
sudo bash scripts/install_wsl_pheno_serve.sh \
  --branch main \
  --repo-url https://github.com/KooshaPari/pheno-harness.git
```

The script is idempotent — re-run safely after a config change.

## Start the dual-GPU stack

```powershell
# On Windows (PowerShell):
.\scripts\start_dual_gpu_stack.ps1 -Port 19000
```

The script:
1. Verifies tailscale reachability to the WSL distro.
2. Boots vLLM on GPU 0 + SGLang on GPU 1.
3. Records the boot in `evidence/dual_gpu/heartbeat.json`.
4. Returns the OpenAI-compatible endpoints:
   - vLLM:    `http://127.0.0.1:19000/v1`
   - SGLang:  `http://127.0.0.1:19001/v1`

## Verify the stack is healthy

```sh
# 4-minute smoke (run on the WSL distro):
bash scripts/dual_gpu_smoke.ps1
```

The smoke emits:
- `bench/results/desktop_nvidia/<YYYY-MM-DD>/<host>.log`
- `evidence/dual_gpu/heartbeat.json`
- `bench/results/sota/<YYYY-MM-DD>/snapshot.json` (with `evidence_label: live_verified`)

## Schedule

| Cron | Schedule (UTC) | Wrapper |
|------|----------------|---------|
| sota-snapshot | daily 04:00 | `scripts/cron/snapshot_sota.py` |
| health-repo | Mon 03:00 | `scripts/cron/health_repo_cron.sh` |
| worktree-gc | Wed 04:00 | `scripts/cron/worktree_gc_cron.sh` |
| lint-branches | Fri 04:00 | `scripts/cron/lint_branches_cron.sh` |
| dual-gpu-check | daily 04:30 | `evidence/dual_gpu/check.sh` |

## Failure modes

| Mode | Evidence label | Promotion |
|------|----------------|-----------|
| ssh unreachable | `blocked` | no |
| vLLM start failed | `blocked` | no |
| SGLang start failed | `blocked` | no |
| bench passed | `live_verified` | yes (gated on 2 green) |
| bench partial | `reported` | no |

## Two-consecutive-green gate

Per the garden loop (`docs/GARDEN_LOOP.md`), a candidate is promoted
only after 2 consecutive green windows. The check is in
`bench/contracts/garden.py` (DAG-56 close-out).

## Cross-references

- `config/desktop_nvidia_qwen35_lane.yaml` — the lane spec
- `config/launch/desktop_nvidia_qwen35_lane.yaml` — the launchd entry
- `scripts/provision_desktop_worktree.py` — worktree provisioning
- `scripts/validate_desktop_evidence.py` — evidence binding
- `evidence/dual_gpu/check.sh` — daily nvidia-smi heartbeat
- `AGENTS.md` §2.2 — the LLM-host contract
