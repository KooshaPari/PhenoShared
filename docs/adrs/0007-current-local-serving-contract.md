# ADR 0007: Current local serving contract

**Status:** accepted  
**Date:** 2026-07-13  
**Supersedes for forward-looking local serving:** stale model and native-Windows
instructions in ADR 0003, ADR 0006, and older model-matrix prose. Historical
records remain unchanged.

## Decision

The active local evaluation set is exactly:

| Alias | Canonical model ID | Primary role |
|---|---|---|
| `local/qwen35-08b` | `Qwen/Qwen3.5-0.8B` | draft and tiny worker |
| `local/lfm25-8b-a1b` | `LiquidAI/LFM2.5-8B-A1B` | coding subagent |
| `local/ornith-8b` | `deepreinforce-ai/Ornith-1.0-9B` | coding/review comparison |

`local/ornith-8b` is a stable routing alias; its canonical checkpoint is 9B.
No other local SKU enters an evaluation manifest without a new decision.

## Serving and artifact invariants

1. SGLang is the primary path in WSL on the RTX 3090 Ti. vLLM is used for
   cross-engine checks. TensorRT-LLM is compile-once only after a stable winner.
2. The `sglang_primary` slot has `one_model_at_a_time` residency. A swap is an
   explicit operator action, not an implicit proxy side effect.
3. `scripts/pheno_slot.py` accepts only an existing local model directory from
   `PHENO_QWEN35_08B`, `PHENO_LFM25_8B_A1B`, or `PHENO_ORNITH_8B`. It refuses
   model IDs, missing paths, and therefore accidental runtime downloads.
4. Evaluation artifacts must be quantized q2 through q8, or an eligible
   NVFP4-type artifact. BF16 artifacts are excluded on the 24 GB GPU.
5. KV experiments may use q4_0, q5_0, q8_0, or experimental TQ+. Decode and
   compression experiments are candidates until engine/model compatibility is
   proven in a captured run artifact.

## Evaluation policy

- Local suites are manifest-only until the WSL GPU runtime and an approved
  local artifact are present. Manifest generation has zero provider cost.
- Cloud evaluation is disabled. It may be explicitly re-opened per model only
  after a documented full-TB2.0 cost projection of at most $1.
- A performance row is promotable only with the model checksum/artifact ID,
  engine version and command, quantization, hardware telemetry, concurrency,
  TTFT, inter-token latency, throughput, and verifier outcome.

## External gates

The next state-changing operation is WSL GPU runtime installation. The next
network/disk operation after that is an explicitly approved download of one
quantized local artifact. Neither action is performed by a planner, proxy, or
manifest generator.
