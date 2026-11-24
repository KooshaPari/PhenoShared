# Speculative Decoding

Speculative decoding research distilled from `D:/koosh/Downloads/ChatGPT-*.md`
(class **L**). All claims must be cross-validated against arXiv/GitHub before
promotion to class **P**.

## Scope

Draft-target verification with adaptive routing, tree-structured candidates,
agent-aware priors, and heterogeneous draft/verify lanes on 3090 Ti /
1080 Ti / M-series Metal.

## Primary corpus

- `ChatGPT-Agent-Aware Speculative Decoding.md` — `sha256: 40367eafa68468ff0b8e4c58101d5437e4793997aebaa6d3a1dcdeb29ac5e5dc`

Distilled to: `../inference/agent-aware-speculative-decoding.md` (cross-tagged:
speculative-decode is the primary category, inference is the secondary).

## Distilled topics

| Topic | Method | Cross-link |
|-------|--------|------------|
| Parallel tree drafting | JetSpec, DDTree/CaDDTree | `../inference/agent-aware-speculative-decoding.md` |
| Block-diffusion drafters | DFlash | `../inference/agent-aware-speculative-decoding.md` |
| Adaptive overlap | PEARL | `../inference/agent-aware-speculative-decoding.md` |
| EAGLE family | P-EAGLE, EAGLE 3.1 | `../inference/agent-aware-speculative-decoding.md` |
| Repo-local suffix cache | n-gram + suffix-LRU | `../inference/agent-aware-speculative-decoding.md` |
| Bandit router on telemetry | CASCADE | `../routing/latentmas-vs-textmas.md` |

## Research state (as of 2026-08-27)

- All entries class **L** (corpus-derived only). No arXiv or primary-source
  verification has been attached yet.
- Pheno-harness production lane: vanilla EAGLE-3 in sglang/vLLM control
  plane only. Research spec methods (JetSpec, DDTree, DFlash, MTP)
  gated behind production baselines (see
  `../../plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md`).

## Verification queue

Promote any class **L** claim to class **P** by attaching at least one
primary source:

- JetSpec → arXiv 2504.XXXXXXXX (verify ID before citation)
- DDTree/CaDDTree → GitHub `ddtree-project/DDTree` (verify URL)
- PEARL → arXiv 2407.XXXXX
- EAGLE-3 / EAGLE-3.1 → GitHub `SafeAILab/EAGLE`
- DFlash → GitHub `mit-han-lab/DFlash`

## Open questions

1. Which method wins on `pheno-harness` control lane (Qwen3.5-9B sglang on
   3090 Ti) under agent tool-call workloads? — open, requires live benchmark.
2. Does the CASCADE bandit router beat static EAGLE-3 when acceptance-contract
   telemetry is available? — open.
3. Can the 1080 Ti draft sidecar keep up with 3090 Ti verify at >24 tok/s
   per request without saturating PCIe4 x8 (~15.8 GB/s)? — open.

## See also

- `../inference/agent-aware-speculative-decoding.md` — primary distillation
- `../kernels/tiered-memory-hierarchy.md` — memory tiering interacts with
  draft/verify scheduling on dual-GPU
- `../routing/latentmas-vs-textmas.md` — multi-agent MAS routing context
