# ADR 0005 — Locked Baseline and March-2026 Cutoff

Date: 2026-07-04

## Status

Accepted.

## Decision

Local self-hosted models are locked to exactly:

- Qwen3.5 0.8B (`local/qwen35-08b`)
- LiquidAI LFM 2.5 8B-A1B (`local/lfm25-8b-a1b`)
- Ornith 8B alias (`local/ornith-8b`), canonical HF repo
  `deepreinforce-ai/Ornith-1.0-9B`

No other local model SKU is a current pick. BF16 local serving for large
models is not part of the plan.

Cloud metadata baselines are ForgeCode -> OpenRouter models:

- `inclusionai/ling-2.6-flash`
- `liquid/lfm-2-24b-a2b`
- `arcee-ai/trinity-mini`
- `ibm-granite/granite-4.1-8b`
- `poolside/laguna-xs-2.1`
- `tencent/hy3-preview`
- `qwen/qwen3.5-flash-02-23`

Cloud baseline count: **7** (Granite-4.0-h-micro was dropped on 2026-07-04
per round 5 user feedback: pre-March-2026 release, no deep justification;
replaced scope is absorbed by `Qwen3.5-0.8B` running on the local
self-hosted tier at `local/qwen35-08b` via `pheno-serve-dev`).

Before eval binding, scrape both OpenRouter API metadata and the model pages.
Cloud evals are disabled by default. A cloud model may run a full
Terminal-Bench 2.0 eval only when the projected combined cost for that model is
`<= $1.00` for all 89 tasks.

## Recency Rule

Prefer models released no earlier than 2026-03-01 unless an exception is
explicitly justified.

Current exceptions:

- `Qwen/Qwen3.5-0.8B` was user-specified. HF owner repo was created
  2026-02-28 and modified 2026-03-02; GGUF derivatives exist from
  2026-03-01 onward.

## HF Probe Result

Metadata-only HF probe found:

- `Qwen/Qwen3.5-0.8B`
- `LiquidAI/LFM2.5-8B-A1B`
- `deepreinforce-ai/Ornith-1.0-9B` as the canonical repo for the user’s
  `local/ornith-8b` slot.

## Decode Research Scope

The eval plan must cover the broader speculative/diffusion family:

- DFlash / DSpark-style diffusion speculative decoding
- JetSpec
- MTP
- DDTree
- parallel tree drafting
- speculative speculative decoding, meaning multi-branch speculation over
  plausible continuations, not only one drafted path
- EAGLE / P-EAGLE as one family, not the whole plan

## Local Optimization Scope

Local sweeps may include:

- weight quantization as low as q2 and no higher than q8
- NVFP4-type variants where meaningful on the target runtime
- REAP variants, including variants produced by this repo
- TQ+ and other KV-cache quantization schemes
- q4/q5/q8 KV-cache variants

These are measurement axes, not permission to download weights or start servers.

## Consequences

- Stale local picks stay only in superseded/postmortem sections.
- `config/pheno_serve.yaml`, `config/model_engine_matrix.yaml`, and
  `config/harbor_tbench_pheno_serve.yaml` must use only the three local aliases.
- OpenRouter metadata scrape artifacts live under `state/openrouter_scrape/`.
- Cloud eval rows must carry a cost projection artifact and are skipped when the
  projected full TB2.0 cost exceeds `$1.00`.
- HF credentials remain runtime-only and must not be committed, echoed, or
  written to disk.
