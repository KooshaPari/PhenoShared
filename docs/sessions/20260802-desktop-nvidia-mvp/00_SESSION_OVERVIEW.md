# Desktop NVIDIA Qwen3.5 MVP

## Goal

Produce reproducible Qwen3.5 evidence on the desktop GTX 1080 Ti + RTX 3090 Ti
while macOS inference remains paused. Preserve all existing worktrees.

## Current result

- Lane contract and runtime-specific GPU mappings are restored.
- Launcher defaults to vLLM on the 3090 and llama.cpp on the 1080, with port
  preflight and no forced process termination.
- Historical helper diagnostic: 3/3 exact responses were captured during an
  earlier host observation; they are not current repeatability or promotion
  evidence.
- Evidence is integrity-bound and fail-closed at 5/7 promotion gates.
- Owner-issued execution authority, current primary/helper repeatability, and
  real harness evaluation remain pending.

## Provenance

- Evidence: `bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json`
- Contract: `config/desktop_nvidia_qwen35_lane.yaml`
- Latest commits: `8698368`, `c36adf8`
- Latest Airlock snapshot: `wip/20260802T0230-18c7dc285de567e8`
