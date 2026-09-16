# v2 Shortlist (user-corrected, local picks locked)

_Updated 2026-07-04 after user correction._

## Decisions

- No local BF16 plan for 24 B+ models. BF16 was never a local consideration for the 3090 Ti plan.
- No stale round-2 local SKUs are forward-looking picks.
- Local self-hosted set is locked to exactly three models until a written exception is added.
- Prefer models released no earlier than March 2026 unless the doc gives a specific exception.
- Cloud baselines are evaluated through ForgeCode -> OpenRouter via `omniroute-dev`, with direct-provider cells allowed only for controlled measurement.

## Locked Local Self-Hosted Models

| Role | Canonical alias | Model | Engine candidates | Status |
|---|---|---|---|---|
| T0 drafter / tiny worker | `local/qwen35-08b` | Qwen3.5 0.8B | llama.cpp, MLX fallback | HF exact id probe needed; no download yet |
| T2 workhorse / alt-arch | `local/lfm25-8b-a1b` | LiquidAI LFM 2.5 8B-A1B | SGLang, vLLM, TensorRT-LLM compile-once | HF exact id probe needed; no download yet |
| T2 workhorse / coding-agent comparison | `local/ornith-8b` | Ornith 8B | SGLang, vLLM | HF exact id probe needed; no download yet |

No other local model may be added to forward-looking tier tables without a new ADR.

## OpenRouter Cloud Medley

Configured in `config/openrouter_eval_models.yaml`; scrape before eval with
`scripts/scrape_openrouter_models.py`.

| Role | Model id |
|---|---|
| Primary cloud baseline | `inclusionai/ling-2.6-flash` |
| Cheap micro baseline | `ibm-granite/granite-4.0-h-micro` |
| Alt-architecture MoE baseline | `liquid/lfm-2-24b-a2b` |
| Small cloud baseline | `arcee-ai/trinity-mini` |
| Enterprise 8B baseline | `ibm-granite/granite-4.1-8b` |
| Coding cloud baseline | `poolside/laguna-xs-2.1` |
| Preview cloud baseline | `tencent/hy3-preview` |
| Qwen flash cloud baseline | `qwen/qwen3.5-flash-02-23` |

## Speculative / Diffusion Decode Research Requirements

Forward-looking inference docs must account for:

- DFlash / DSpark-style diffusion speculative decoding
- JetSpec
- MTP
- DDTree
- parallel tree drafting
- "speculative speculative decoding": branching over multiple plausible token/action continuations, not only one draft path
- EAGLE / P-EAGLE only as part of the broader speculative family, not as the whole plan

## Sign-Off State

- Local picks: locked by user.
- Cloud medley: locked by user, but OpenRouter API/page scrape required before eval.
- HF token: provided for gated metadata probes only. Do not write it to disk, commit it, or echo it in logs.
- Downloads: none authorized by this file.
- Local server starts: none authorized by this file.
