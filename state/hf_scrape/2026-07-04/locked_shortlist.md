# Locked Shortlist

Date: 2026-07-04

## Local Self-Hosted

Only these local model families are current picks:

| Alias | Model | Notes |
|---|---|---|
| `local/qwen35-08b` | `Qwen/Qwen3.5-0.8B` | Tiny drafter / local worker. User-specified exception to March-only rule: created 2026-02-28, modified 2026-03-02; GGUF candidates exist from 2026-03-01+. |
| `local/lfm25-8b-a1b` | `LiquidAI/LFM2.5-8B-A1B` | Main local workhorse. Created 2026-05-28, modified 2026-07-02. GGUF and MLX variants exist. |
| `local/ornith-8b` | `deepreinforce-ai/Ornith-1.0-9B` | Coding-agent comparison local workhorse. User refers to this slot as Ornith 8B; canonical HF repo is Ornith 1.0 9B. |

No BF16 plan is accepted for large local models. Do not add other local SKUs
without superseding ADR 0005.

## Local Watchlist (Not Active)

These models are noted for later research but are not part of the active local
eval set:

- `Nanbeige/Nanbeige4.1-3B`
- `Zyphra/ZAYA1-8B`
- other March-2026-or-newer candidates discovered by HF scrapes

Adding any watchlist model to the active local eval set requires a new ADR.

## OpenRouter Cloud Baselines

Cloud evals are disabled by default. A cloud model may run a full
Terminal-Bench 2.0 eval only when the projected combined cost for that model is
`<= $1.00` for all 89 tasks. Metadata scraping remains allowed.

Current projection artifact:
`state/openrouter_scrape/2026-07-04/tbench20_cost_projection.json`.
Using 50k prompt tokens + 3k completion tokens per task, all eight configured
OpenRouter models project below `$1.00` for one 89-task TB2.0 attempt. Re-run
the projection before any cloud eval because pricing and actual token budgets
can change.

| Model id | Role |
|---|---|
| `inclusionai/ling-2.6-flash` | primary cloud baseline |
| `liquid/lfm-2-24b-a2b` | alt-architecture MoE baseline |
| `arcee-ai/trinity-mini` | small cloud baseline |
| `ibm-granite/granite-4.1-8b` | enterprise 8B baseline |
| `poolside/laguna-xs-2.1` | coding cloud baseline |
| `tencent/hy3-preview` | preview cloud baseline |
| `qwen/qwen3.5-flash-02-23` | Qwen flash cloud baseline |

Before any eval binding, run:

```powershell
python scripts\scrape_openrouter_models.py
```

The scrape must read both OpenRouter API metadata and model pages. It must not
make completions calls.

## Decode Research Watch

Do not reduce the decode plan to EAGLE/P-EAGLE only. Track DFlash/DSpark,
JetSpec, MTP, DDTree, parallel tree drafting, and speculative speculative
decoding across local and cloud eval notes.

## Local Quantization / Runtime Search

Local sweeps may test:

- weight quants from q2 through q8, with q8 as the maximum
- NVFP4-type variants where hardware/runtime support exists
- REAP variants, including local experiments produced by this repo
- TQ+ and other KV-cache quantization schemes
- q4/q5/q8 KV cache variants and long-context spill behavior

No sweep may download weights or start local servers without explicit approval.
