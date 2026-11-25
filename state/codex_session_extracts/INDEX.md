# Codex Session Index — omlx / LLM Kernels / Dual-GPU Inference

Extracted: 2026-07-17 from `C:\Users\koosh\.codex\sessions\`

## Primary sessions (full extracts)

| Session ID | Date | Rollout file | Extract | Topic |
|------------|------|--------------|---------|-------|
| `019f2a9c-de83-75b0-a59e-776996bd7290` | Jul 3–15 | `2026/07/03/rollout-2026-07-03T17-52-31-*.jsonl` | [rollout-2026-07-03T17-52-31-*.md](./rollout-2026-07-03T17-52-31-019f2a9c-de83-75b0-a59e-776996bd7290.md) | **Founding session**: forgecode + pheno-harness, PhenoLM rename, pheno-serve-dev layer, garden loop, local models (Qwen/LFM/Ornith), SGLang/vLLM/TRT-LLM, 1080 Ti hardware-aware placement |
| `019f6249-d74c-7540-885f-588c3d51ac3a` | Jul 14–16 | `2026/07/14/rollout-2026-07-14T13-20-34-*.jsonl` | [rollout-2026-07-14T13-20-34-*.md](./rollout-2026-07-14T13-20-34-019f6249-d74c-7540-885f-588c3d51ac3a.md) | **USCH heterogeneous inference**: custom CUDA/Metal kernels, unarchive pheno-harness, 3090/M1/phones/1080, DFlash/SSD/JetSpec, evidence registry, 1-week persistent goal |
| `019f69c7-a6b4-7bf2-980b-51b94c5f4e92` | Jul 16 | `2026/07/16/rollout-2026-07-16T00-15-19-*.jsonl` | [rollout-2026-07-16T00-15-19-*.md](./rollout-2026-07-16T00-15-19-019f69c7-a6b4-7bf2-980b-51b94c5f4e92.md) | **Continuation**: 1080 Ti install, llama.cpp Pascal path, independent workers, preservation/reconciliation |
| `019f69c7-5213-70b1-a161-e5d25a6713ae` | Jul 16 | `2026/07/16/rollout-2026-07-16T00-14-58-*.jsonl` | [rollout-2026-07-16T00-14-58-*.md](./rollout-2026-07-16T00-14-58-019f69c7-5213-70b1-a161-e5d25a6713ae.md) | Parallel thread of same goal |
| `019f2cb7-47ff-72d0-9cf4-38d06d2069a7` | Jul 4+ | `2026/07/04/rollout-2026-07-04T03-40-36-*.jsonl` | [rollout-2026-07-04T03-40-36-*.md](./rollout-2026-07-04T03-40-36-019f2cb7-47ff-72d0-9cf4-38d06d2069a7.md) | Ecosystem/registry DAG (Eventra, phenotype-omlx registry mentions); overlaps pheno-harness |

## Codex rollout summaries (pre-digested)

| File | Topic |
|------|-------|
| [2026-07-04T00-52-31-9pUQ-phenolm_pheno_serve_garden_local_artifact_tranche.md](C:/Users/koosh/.codex/memories/rollout_summaries/2026-07-04T00-52-31-9pUQ-phenolm_pheno_serve_garden_local_artifact_tranche.md) | PhenoLM / pheno-serve-dev / garden loop / LFM+Ornith artifacts |
| [2026-07-14T20-20-34-CAau-pheno_harness_research_unarchive_device_model_roadmap.md](C:/Users/koosh/.codex/memories/rollout_summaries/2026-07-14T20-20-34-CAau-pheno_harness_research_unarchive_device_model_roadmap.md) | pheno-harness unarchive, device/model roadmap |

## User prompt index (`history.jsonl`)

All user messages keyed by `session_id` live in:
`C:\Users\koosh\.codex\history.jsonl`

Key inference-related session IDs:
- `019f2a9c-de83-75b0-a59e-776996bd7290` — founding + 1080 Ti hardware-aware ask
- `019f6249-d74c-7540-885f-588c3d51ac3a` — USCH kernels + heterogeneous fleet
- `019f2cb7-47ff-72d0-9cf4-38d06d2069a7` — ecosystem forward DAG (parallel)

## Artifacts produced in-repo from these sessions

- `pheno-harness/plans/2026-07-14-usch-heterogeneous-inference-v1/` — full research packet
- `pheno-harness/config/hardware_aware_placement.yaml` — measured dual-GPU policy
- `pheno-harness/config/inference_runners.yaml` — SGLang/vLLM/llama.cpp launch templates
- `pheno-harness/pheno/serve/` — pheno-serve-dev skeleton
- `pheno-harness-preserve/` — sealed preservation packets

## What was NOT found in Codex logs

- No custom CUDA kernel source written
- No `phenotype-omlx` implementation work (registry/ecosystem only)
- `jundot/omlx` referenced as Mac MLX serving lane, not Windows CUDA target
