# Hardware

Hardware selection, cost, and safety distilled from
`D:/koosh/Downloads/ChatGPT-*.md` (class **L**). All claims must be
cross-validated against vendor specs, pricing pages, and incident reports
before promotion to class **P**.

## Scope

GPU/CPU selection for pheno-harness tiers (3090 Ti primary, 1080 Ti
sidecar, M-series Metal optional), $/TFLOP analysis, rental safety,
and capacity-planning heuristics.

## Distilled corpus

| Source | SHA-256 | Distillation |
|--------|---------|--------------|
| `ChatGPT-Machine Comparison for AI.md` | (see `../corpus_manifest.json`) | `machine-comparison-for-ai.md` |
| `ChatGPT-AI Inference Hardware Costs.md` | (see manifest) | `ai-inference-hardware-costs.md` |
| `ChatGPT-Model improvements under $500.md` | (see manifest) | `model-improvements-under-500.md` |
| `ChatGPT-GPU Rentals Safety Review.md` | `db67d55b180a30d4283f7fe3e040c2fe3bea4afa933d0a15359deb1ed292ab4e` | `gpu-rentals-safety-review.md` (status: stub — N10 in-order) |
| `ChatGPT-RTX 3090 Throughput Analysis.md` | (see manifest) | `rtx-3090-throughput.md` |

## Production stack (current)

- **Primary:** RTX 3090 Ti 24 GB GDDR6X (1088 GB/s) — sglang main lane
- **Sidecar:** GTX 1080 Ti 11 GB GDDR5X (484 GB/s) — vLLM control / draft / verifier
- **Interconnect:** X570 PCIe4 x8 effective (~15.8 GB/s) — not VRAM-equivalent
- **Optional:** M1 Pro Metal (16 GB unified) — dual-harness test lane only

## Cost posture

- Local capex amortized ~36 mo vs rental; rental wins on burst but loses on
  trace provenance and `host.containers.internal:9102` scrape exposure.
- See `gpu-rentals-safety-review.md` for blast radius (vault
  `LANGFUSE_*` keys, `podman :7777` daemon, `evidence/dual_gpu/host_manifest.yaml`).

## Verification queue

Promote any class **L** claim to class **P** by attaching vendor
documentation, MLPerf public results, or a primary incident report.

## Open questions

1. When does the 1080 Ti draft sidecar become the bottleneck vs the 3090 Ti
   verify lane? — open, requires empirical PCIe4 x8 traces.
2. What is the break-even hour count for capex vs rental given current
   utilization? — open, depends on queue depth (currently paused granite
   queue per 2026-08-16 directive).
3. Does M-series Metal unified memory offer a meaningful secondary tier
   given Apple's lack of VRAM-tiered scheduling? — open, requires Metal
   scheduler profiling.

## See also

- `../kernels/tiered-memory-hierarchy.md` — tiered memory model that
  hardware selection enables
- `../inference/agent-aware-speculative-decoding.md` — draft/verify
  scheduling interacts with hardware lane choice
- `../../adr/ADR-008-Multi-Platform-Deployment.md` — multi-platform
  deployment gate
