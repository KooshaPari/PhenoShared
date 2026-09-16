# Dual-GPU Version Pins — vLLM 0.5 + SGLang 0.4

> Canonical version pins for the Desktop NVIDIA / WSL2 dual-GPU lane.
> Covers **RTX 3090 Ti (Ampere, sm_86, 24 GB)** + **GTX 1080 Ti (Pascal, sm_61, 11 GB)**.
> Task WBS 91 — companion to `docs/SETUP_VERSIONS.md` and `docs/guides/DESKTOP_NVIDIA_LANE.md`.

## Summary

| Engine | Pinned range | Canonical pin | Role | Source of truth |
|--------|-------------|---------------|------|-----------------|
| **vLLM** | `0.5.x` | `vllm==0.5.*` | Secondary slot (broad model support, AWQ/GPTQ) | `docs/SETUP_VERSIONS.md` Engines table |
| **SGLang** | `0.4.x` | `sglang==0.4.*` | Primary slot on RTX 3090 Ti (prefill / shared-prefix, ADR 0006) | `docs/SETUP_VERSIONS.md` Engines table |

Both pins are the **WSL / LLM-host** pins — they are installed by
`scripts/install_wsl_pheno_serve.sh` (and `.ps1` wrapper) on the Fedora 44
WSL distro / bare-Linux desktop host, not by `pyproject.toml` on the
macOS dev workstation (`AGENTS.md` §2.2).

## Pinned versions

```
vLLM   0.5.x  — expect `vllm --version` to print 0.5.*
SGLang 0.4.x  — expect `python -c "import sglang; print(sglang.__version__)"` to print 0.4.*
```

Concrete examples (use the latest patch within the minor):

- `vllm==0.5.3` (or latest `0.5.*`)
- `sglang==0.4.6.post1` (or latest `0.4.*`)

Do not mix `0.5.x` / `0.4.x` with the newer `sglang==0.5.15.post1` / `vllm==0.25.1`
pins that appear in `config/inference_runners.yaml` on other branches — those
belong to a different lane iteration. The dual-GPU lane contract is **0.5 + 0.4**.

## Install commands

### On the LLM host (WSL Fedora 44 / desktop Linux)

Idempotent bootstrap (installs both engines per the lane):

```bash
sudo bash scripts/install_wsl_pheno_serve.sh \
  --branch wip/2026-08-20-v0.12 \
  --repo-url https://github.com/<REDACTED>/pheno-harness.git
```

Manual pip pins (inside the host venv, e.g. `~/.pheno-serve-venv`):

```bash
# vLLM 0.5
pip install 'vllm==0.5.*'

# SGLang 0.4
pip install 'sglang==0.4.*'

# Verify
vllm --version
python -c "import sglang; print(sglang.__version__)"
```

CUDA 12.x is assumed; install with the matching torch CUDA wheel:

```bash
pip install 'vllm==0.5.*' --extra-index-url https://download.pytorch.org/whl/cu121
pip install 'sglang==0.4.*' --extra-index-url https://download.pytorch.org/whl/cu121
```

### Verify on any host

```bash
grep -E 'vLLM.*0\.5|SGLang.*0\.4' docs/guides/dual_gpu_versions.md
grep -E 'vllm.*0\.5|sglang.*0\.4' docs/SETUP_VERSIONS.md
vllm --version                              # expect 0.5.x on the LLM host
python -c "import sglang; print(sglang.__version__)"  # expect 0.4.x on the LLM host
```

## Compatibility — RTX 3090 Ti + GTX 1080 Ti

| GPU | Arch | Compute | VRAM | Driver / CUDA | vLLM 0.5 | SGLang 0.4 | Notes |
|-----|------|---------|------|---------------|----------|------------|-------|
| **RTX 3090 Ti** | Ampere | sm_86 | 24 GB | CUDA 12.x, driver ≥ 535 | ✅ Primary or secondary | ✅ **Primary** (preferred per ADR 0006) | Primary slot in `config/desktop_nvidia_qwen35_lane.yaml` (`cuda:1`); SGLang primary, vLLM secondary. Supports `mem_fraction_static 0.85`, tensor-parallel off (single-GPU per engine). |
| **GTX 1080 Ti** | Pascal | sm_61 | 11 GB | CUDA 12.x, driver ≥ 535 | ✅ Legacy helper (pascal) | ⚠️ Limited — use `llama.cpp` fallback | 1080 Ti is **not** in the Ampere tensor-parallel group. SGLang 0.4 upstream dropped sm_61 wheel support in some builds; prefer `llama.cpp` (`llama_server_legacy_helper` in `config/inference_runners.yaml`) for the helper lane. See `state/sglang_build_plan_2026-07-28.json`. |

### Assignment

| Lane role | GPU | Engine | `CUDA_VISIBLE_DEVICES` |
|-----------|-----|--------|------------------------|
| Primary | RTX 3090 Ti | SGLang 0.4 (preferred) or vLLM 0.5 | `1` |
| Helper / legacy | GTX 1080 Ti | vLLM 0.5 (pascal build) or `llama.cpp` | `0` |
| Forbidden | — | Tensor-parallel across 3090 Ti + 1080 Ti | — |

- Never `tensor_parallel` the Pascal 1080 Ti with the Ampere 3090 Ti.
- `CUDA_VISIBLE_DEVICES` is per-engine; verify against `evidence/dual_gpu/host_manifest.yaml`.

### Known constraints

- **SGLang on sm_61**: upstream wheels may not ship `sm_61`; building from source requires patching (see `state/sglang_build_plan_2026-07-28.json` — decision: llama.cpp for 1080 Ti, SGLang for 3090 Ti).
- **vLLM 0.5 + torch**: requires matching torch CUDA build (`cu121` / `cu124`); mismatched `torch` / `sgl-kernel` ABI is a known failure mode.
- **BF16**: forbidden per `AGENTS.md` §2.3 — use quantized artifacts (q2–q8) even on 3090 Ti.

## Cross-references

- `docs/SETUP_VERSIONS.md` — consolidated pin index (DAG-91)
- `docs/guides/DESKTOP_NVIDIA_LANE.md` — desktop lane operator guide (DAG-36)
- `docs/guides/WSL_FEDORA_44_DUAL_GPU.md` — WSL + Fedora 44 lane
- `config/desktop_nvidia_qwen35_lane.yaml` — lane spec
- `config/inference_runners.yaml` — runner templates
- `scripts/install_wsl_pheno_serve.sh` / `.ps1` — bootstrap
- `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md` — WBS 91 entry
- `docs/sessions/20260802-desktop-nvidia-mvp/06_phase_gate.md` — phase gate
