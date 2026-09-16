---
source_file: ChatGPT-Modding 3090 Ti VRAM.md
sha256: 7fc62190fb25086fa4634d5258c271b312b2e4c3e2054c46712199e18b916ec1
topics: [kernels, inference, tiered-memory, MoE, vLLM, SGLang, dual-GPU, NVMe, DDR, consumer-vs-enterprise]
related_okf:
  - inference/vram-scaling-factors.md
  - hardware/rtx-3090-throughput.md
  - inference/agent-aware-speculative-decoding.md
evidence_class: L
---

# Tiered Memory Hierarchy (3090 Ti Corpus)

Despite the export title, this corpus is **not** a GDDR reballing guide. It rejects 3090 Ti → 48/96 GB VRAM mods and reframes the problem as **software-managed memory tiering**: treat 24 GB GDDR6X as a latency-critical **L1**, not bulk storage; stage MoE experts, KV pages, and cold weights in host DDR and NVMe; integrate via existing **vLLM** and **SGLang** offload paths; use a second GPU (1080 Ti) as a **heterogeneous sidecar**, not fake unified VRAM. Custom VRAM hardware, FPGA/CXL appliances, and ASIC memory controllers are **deferred** until trace-driven simulation proves software cannot close the gap.

## Key insights

- **Capacity wall, not bandwidth wall:** RTX 3090 Ti has ~1008 GB/s GDDR6X but only 24 GB; PCIe4 x16 (~31.5 GB/s one-way) is ~31× slower than VRAM—tiered offload works when transfers hide behind compute, not when pretending PCIe is VRAM. [L]
- **VRAM modding rejected:** 3090 Ti → 96 GB requires unsupported GDDR6X densities and memory-controller/firmware changes; 48 GB is speculative at best. Goal "96 GB for AI" should not be pursued via chip swap. [L]
- **Three-tier LLM memory OS:** Hot = VRAM (active layers, active KV, hot MoE experts, CUDA graphs); Warm = host DDR4/DDR5 (inactive layers, old KV, cold experts, shared prefix cache); Cold = NVMe/accelerator (rare experts, model shards, compressed KV, old sessions). [L]
- **Object placement table:** Current-layer weights and active decode KV stay in VRAM; next layers and hot MoE experts prefetch to DDR; cold experts and far-future layers stream from NVMe; RAG/embeddings never occupy VRAM. [L]
- **PagedAttention / RadixAttention alignment:** vLLM PagedAttention (KV as paged virtual memory) and SGLang prefix/Radix caching are the closest mainstream implementations of tiered residency—not custom GDDR. [L]
- **MoE expert staging:** Only ~5–10% of experts activate per token; full expert weights exceed VRAM but fit in DDR/CXL; route-aware expert cache + prefetch is the viable path (Qwen/DeepSeek-class MoE, future Pheno MoE). [L]
- **Dual-GPU sidecar model:** 3090 Ti = primary inference; 1080 Ti = draft/router/verifier/cold-state worker—not tensor-parallel VRAM expansion. X570 dual-GPU drops 3090 to PCIe4 x8 (~15.8 GB/s); sidecar wins when `T_saved > T_compute + T_transfer + T_sync`. [L]
- **Consumer vs enterprise gap:** Enterprise stacks get HBM capacity, NVLink, and memory orchestration; consumer path closes the gap via runtime scheduling (KV paging, prefix DAG, agent-aware batching, MoE cache, async prefetch)—not by faking enterprise VRAM. [L]
- **Simulation framework:** Compare states S0 (measured baseline) → S1 (optimal software on current HW) → S2 (modern HW) → S3 (staging appliance) → S∞ (Carnot/oracle); efficiency `η = TPS_actual / TPS_carnot`; build discrete-event memory simulator, not instruction-level CUDA emulation. [L]
- **Hardware deferral gate:** Do not build FPGA/CXL/custom PCIe DDR5 appliances until traces show expert hit rates and hidden-transfer assumptions hold (corpus cites ~78% active-byte hit on PCIe4 for 20 TPS DeepSeek-class MoE before hardware investment). [L]
- **Bootstrap stack (not greenfield):** vLLM `--moe-expert-cache-size` + LFRU eviction ([PR #37190](https://github.com/vllm-project/vllm/pull/37190)); SGLang UVM expert offload with GPU-resident compute ([PR #20126](https://github.com/sgl-project/sglang/pull/20126)); FluxMoE expert paging atop vLLM ([arXiv:2604.02715](https://arxiv.org/html/2604.02715v1)). [L]

## Memory hierarchy (reference)

```text
┌─────────────────────────────────────────────────────────┐
│ L1 HOT — 3090 Ti VRAM (24 GB, ~1008 GB/s)               │
│   active layer block · active KV window · hot experts     │
│   CUDA graph state · shared prefix KV (if reused)         │
├─────────────────────────────────────────────────────────┤
│ L2 WARM — host DDR4/DDR5 (64–512 GB, ~50–100 GB/s)      │
│   inactive layers · old KV pages · cold MoE experts       │
│   LoRA/adapters · agent prefix backup                     │
├─────────────────────────────────────────────────────────┤
│ L3 COLD — NVMe / staging appliance (TBs, ~7–14 GB/s)    │
│   rarely used experts · model variants · compressed KV    │
│   old sessions · cold model shards                        │
└─────────────────────────────────────────────────────────┘
         ▲ prefetch while GPU computes layer N
         │ evict layer N-2 after use
         ▼
   scheduler: what · when · reuse · compress · prefetch
```

## Interface bandwidth ranking (corpus)

| Interface | Bandwidth class | Acts like VRAM? | Tiered offload? |
|-----------|----------------:|:---------------:|:---------------:|
| GDDR6X (3090 Ti) | ~1008 GB/s | Yes | — |
| On-package HBM | 1–8+ TB/s | Yes | ❌ |
| NVLink | high | Partial (multi-GPU) | ✅ |
| PCIe4 x16 | ~31.5 GB/s | No | ✅ (hidden DMA) |
| CXL.mem Gen5 | ~32–64 GB/s | No | ✅ (workstation+) |
| NVMe (980 Pro class) | ~7 GB/s | No | ✅ (cold only) |

## Claims (class L)

Each claim cites `local://sha256/7fc62190fb25086fa4634d5258c271b312b2e4c3e2054c46712199e18b916ec1` until promoted to **P** via primary-source verification.

1. **[L]** 3090 Ti VRAM is **scarce, not slow**—optimize for residency and prefetch, not GDDR density upgrades.
2. **[L]** GDDR6X chip replacement on 3090 Ti cannot realistically reach 96 GB; 48 GB is unverified and firmware-bound.
3. **[L]** PCIe-attached memory must be used as **tiered cache/offload**, never as transparent VRAM replacement (~31× bandwidth gap vs GDDR6X).
4. **[L]** An **LLM memory OS** with hot/warm/cold tiers outperforms hardware VRAM expansion for local agentic inference under $1k experimentation budget.
5. **[L]** **MoE expert staging** in DDR/NVMe with GPU-resident hot cache is the primary capacity lever for 27B–35B+ MoE on 24 GB cards.
6. **[L]** **vLLM PagedAttention** and **SGLang prefix/Radix caching** are the software foundations for KV and prefix tiering—extend, do not replace.
7. **[L]** **Dual-GPU (3090 + 1080)** should use independent-process sidecar roles (draft, router, embed, verifier)—not TP=2 across mismatched GPUs.
8. **[L]** **1080 Ti** is useful for coarse async workloads; per-token tensor streaming over PCIe (~128× slower than 3090 VRAM BW) fails the sidecar inequality.
9. **[L]** **Enterprise-like serving on consumer GPU** is achievable via tensor placement profiler, KV pressure estimator, MoE expert placement, and session eviction—hardware optional in V1.
10. **[L]** **CXL Type-3 cards** (Innodisk, SMART, Gigabyte AI TOP) are real but require TRX50/W790/server platforms—not X570; prototype with CPU RAM + NVMe tiering first.
11. **[L]** **Used FPGA (Alveo U50)** is the sub-$1k hardware experiment path for DMA/compression/prefetch coprocessor—not custom GDDR boards.
12. **[L]** **Simulation before hardware:** discrete-event trace simulator with states S0–S∞ and efficiency metric η; microbenchmark-calibrated transfer/compute constants.
13. **[L]** **TPS maximization order:** (1) active KV in VRAM, (2) current+next layers resident, (3) prefix sharing across agents, (4) batch decode, (5) chunked prefill, (6) quantized old KV, (7) predictable layer/expert streaming, (8) NVMe for cold only, (9) accelerator after scheduler proof.
14. **[L]** **Agent swarm decomposition:** shared base in VRAM + many LoRA heads in DDR + shared prefix KV + routing-aware batching beats loading N independent small models.
15. **[L]** **Product wedge ("Phenotype Memory OS"):** software-only planner answering "can my GPU run this model/workload?" with max context, max agents, quant/KV dtype, offload policy, expected TPS.
16. **[L]** **MoE cache appliance** requires trace-proven hit rates before hardware; PCIe4 ~78% active-byte hit threshold cited for 20 TPS DeepSeek-class serving.
17. **[L]** **NVLink reverse-engineering** on consumer cards is low-ROI; pinned-memory prefetch + dual-process serving is the practical multi-GPU hack.
18. **[L]** Market differentiation is **memory orchestration software** (llama.cpp / vLLM / SGLang plugins), not faster GPUs or VRAM expansion boards.

## Pheno-harness links

- [`docs/okf/inference/vram-scaling-factors.md`](../inference/vram-scaling-factors.md) — KV/concurrency formulas complement tier placement.
- [`docs/okf/hardware/rtx-3090-throughput.md`](../hardware/rtx-3090-throughput.md) — tok/hour planning and replica vs TP scaling.
- [`plans/2026-07-17-tiered-memory-bootstrap/INDEX.md`](../../plans/2026-07-17-tiered-memory-bootstrap/INDEX.md) — bootstrap plan (vLLM #37190, SGLang #20126, FluxMoE).
- [`plans/2026-07-17-polyglot-forward-dag/INDEX.md`](../../plans/2026-07-17-polyglot-forward-dag/INDEX.md) — dual-GPU forward DAG; MoE offload on 3090 lane.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md) — SpecMoE, cache, and acceleration ladder gates.
- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — T3 MoE tier and 3090 Ti 24 GB constraint.

**Evidence:** `local://sha256/7fc62190fb25086fa4634d5258c271b312b2e4c3e2054c46712199e18b916ec1` (class **L**; cross-check vLLM PR #37190, SGLang PR #20126, FluxMoE arXiv:2604.02715 before **P**).
