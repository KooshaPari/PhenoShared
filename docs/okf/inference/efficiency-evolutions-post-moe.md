---
source_file: ChatGPT-Efficiency Evolutions Post-MoE.md
sha256: bc4ac8fad8910180ebe9bd154dfdadd8334792667d3e26b796f24589802f4f97
topics: [inference, moe, efficiency, post-moe, architecture]
related_okf:
  - inference/agent-aware-speculative-decoding.md
  - inference/vram-scaling-factors.md
  - kernels/tiered-memory-hierarchy.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Efficiency Evolutions Post-MoE

**Source:** `ChatGPT-Efficiency Evolutions Post-MoE.md` (35.5 KB, 2026-06-14) + rev (1) 35.5 KB — class **L**.

Post-MoE efficiency is not just sparser experts but **tighter coupling of routing, KV, and hardware tiers**. The corpus traces how DeepSeek/Kimi-style MoE (shared experts + routed experts, MLA, multi-token prediction) broke the "more experts = more VRAM" assumption by **staging experts across HBM → DRAM → NVMe** and overlapping expert load with attention compute — the same tiered-memory hierarchy that `Modding 3090 Ti VRAM` mis-titled but correctly described for 24 GB cards.

## Key insights (stub — full distillation pending N10)

- **Shared + routed experts:** fixed shared experts capture common knowledge; routed experts specialize — reduces active params per token without losing capacity (cf. `synthesis/03-moe-and-post-moe-frontiers.md`).
- **Expert staging:** on 3090 Ti (24 GB) only ~2 experts fit in HBM; others spill to host DRAM/NVMe and are prefetched by router prediction — `pheno-serve` can serve 8 experts at 8 GB active if `gpu-memory-utilization` is tuned (see `N18` pheno-otel tracing).
- **MLA + MTP:** Multi-head Latent Attention compresses KV; Multi-Token Prediction improves speculative acceptance — both compound with MoE to keep `tg64`/`TTFT` flat as model scales.
- **Pheno-harness link:** Forward DAG N12→N13 (KernelBench + Zig hand-roll) and N17 (hidden-claim → ADR) should cite this corpus before spec'ing post-MoE kernels.

## Next (N10)

- Extract full `[L]` claims with `local://sha256/bc4ac8fad891...` citations.
- Verify against DeepSeek-V3/Kimi-K2 arXiv before promoting to **[P]** and to `docs/specs/`.
- Cross-link to `docs/okf/kernels/tiered-memory-hierarchy.md` and `plans/2026-07-24-forward-dag-v2/INDEX.md` N12/N13.

**Evidence:** `local://sha256/bc4ac8fad8910180ebe9bd154dfdadd8334792667d3e26b796f24589802f4f97` (class **L**).
