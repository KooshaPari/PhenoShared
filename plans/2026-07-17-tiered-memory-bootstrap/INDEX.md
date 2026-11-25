# Tiered memory bootstrap — 2026-07-17

Status: **research + bootstrap execution plan**. No GDDR reballing, custom VRAM boards, or greenfield memory controllers.

Hardware anchor: **RTX 3090 Ti (24 GB, ~1008 GB/s)** primary + optional **GTX 1080 Ti (11 GB)** sidecar on X570; host **64 GB DDR4** + **980 Pro NVMe** cold tier.

OKF source: [`docs/okf/kernels/tiered-memory-hierarchy.md`](../../docs/okf/kernels/tiered-memory-hierarchy.md) distilled from `ChatGPT-Modding 3090 Ti VRAM.md` (`local://sha256/7fc62190fb25086fa4634d5258c271b312b2e4c3e2054c46712199e18b916ec1`, class **L**).

## Thesis

The 3090 Ti bottleneck is **capacity**, not bandwidth. Close the enterprise-vs-consumer gap by bootstrapping **existing runtime offload**—not by inventing custom VRAM hardware. Software tiers (VRAM → pinned DDR → NVMe) plus MoE expert staging recover KV headroom and enable larger MoE models on 24 GB.

## Primary bootstrap anchors (do not reinvent)

| Anchor | What it provides | Pheno use |
|--------|------------------|-----------|
| [vLLM PR #37190](https://github.com/vllm-project/vllm/pull/37190) | `CachedWeightProvider`: expert weights in CPU pinned memory; GPU LFRU cache via `--moe-expert-cache-size N`; requires `--enforce-eager` | vLLM control lane MoE exceed-VRAM path on 3090 |
| [SGLang PR #20126](https://github.com/sgl-project/sglang/pull/20126) | UVM-based MoE expert offload; all-GPU compute via PCIe read-through; adaptive residency + cross-layer prefetch | SGLang primary lane; decode CUDA graph compatible |
| [FluxMoE (arXiv:2604.02715)](https://arxiv.org/html/2604.02715v1) | Expert paging atop vLLM; stream-in/evict-after-use; up to 3× throughput vs baseline vLLM in memory-bound regimes | Design reference for residency planner + paging abstraction |

**Explicitly out of scope:** GDDR chip swap, "VRAM expansion" PCIe cards pretending to be GDDR, custom HBM packages, consumer NVLink switches, greenfield FPGA memory appliances (Phase 4+ only if traces fail software ceiling).

## Memory tier model

```text
L1 VRAM (3090 Ti)     active KV · current layer · hot MoE experts · CUDA graphs
L2 DDR (host pinned)  cold experts · old KV pages · LoRA · prefix backup
L3 NVMe (980 Pro)     model shards · compressed KV · cold sessions · rare experts
```

Governing constraint: hide `L2/L3 → L1` transfers during layer `N` compute (prefetch `N+1`, evict `N-2`).

## Phased plan

### Phase 0 — Reject hardware VRAM path (done in OKF)

- Document 3090 Ti 96 GB mod as infeasible ([OKF claims 1–2](../../docs/okf/kernels/tiered-memory-hierarchy.md)).
- Redirect budget to software tiering + dual-GPU sidecar ([polyglot forward DAG](../2026-07-17-polyglot-forward-dag/INDEX.md)).

### Phase 1 — Software-only tiering (current)

**Goal:** Run Qwen3.6-35B-A3B-class MoE on 3090 Ti with acceptable tok/s using engine-native offload.

| Step | Action | Success gate |
|------|--------|--------------|
| 1.1 | Pin vLLM + SGLang versions that include or cherry-pick #37190 / #20126 | Engines start on 3090 (`CUDA_VISIBLE_DEVICES=1` WSL) |
| 1.2 | Baseline: all-in-GPU MoE (OOM = expected) | Record VRAM peak, tok/s, context length |
| 1.3 | vLLM: `--moe-expert-cache-size N --enforce-eager` sweep N ∈ {4,8,16,32} | Model loads; tok/s ≥ 70% of baseline or fits where baseline OOMs |
| 1.4 | SGLang: enable UVM expert offload config from #20126 | Compare tok/s, VRAM, prefill vs decode |
| 1.5 | KV tiering: vLLM `gpu_memory_utilization`, `max_num_seqs`; SGLang chunked prefill + memory pool | KV pressure curve vs concurrent agents |
| 1.6 | Prefix tier: SGLang RadixAttention / shared system-prompt across agent swarm | Prefix hit rate > 30% on coding-agent trace |

Deliverable: `bench/custom/tiered-memory-baseline.json` with S0 (naive) vs S1 (tiered software) metrics.

### Phase 2 — Trace + discrete-event simulator

**Goal:** Prove gap closure before any custom hardware.

| Step | Action | Success gate |
|------|--------|--------------|
| 2.1 | Trace runner: token, prefix hash, KV alloc/reuse, expert IDs, hit/miss, VRAM, PCIe, NVMe | JSONL trace from Phase 1 workloads |
| 2.2 | Implement S0/S1/S∞ states per OKF simulator spec | `η = TPS_actual / TPS_carnot` computed |
| 2.3 | Calibrate transfer constants from microbenchmarks (PCIe4 x8 after dual-GPU, DDR pinned, 980 Pro) | `C_transfer` within 15% of measured |
| 2.4 | Replay FluxMoE paging policy as scheduler plugin | Simulated η(S1) ≥ 0.6 × η(S∞) for MoE trace |

Deliverable: `docs/specs/tiered-memory-simulator.md` (follow-up) + go/no-go for Phase 3 hardware.

### Phase 3 — Dual-GPU heterogeneous sidecar

**Goal:** 1080 Ti adds throughput via draft/router/embed—not VRAM expansion.

| Step | Action | Success gate |
|------|--------|--------------|
| 3.1 | Dual-process: 3090 primary (:8000) + 1080 draft/embed (:8081) | [`start_dual_gpu_stack`](../../plans/2026-07-17-polyglot-forward-dag/INDEX.md) green |
| 3.2 | Sidecar inequality check: `T_saved > T_compute + T_transfer + T_sync` per workload class | Only async-friendly roles on 1080 |
| 3.3 | MoE hot experts on 3090; cold expert pool in host DDR (not 1080 VRAM streaming) | No per-token cross-GPU weight traffic |

Anti-pattern: TP=2 across 1080+3090; streaming active KV across PCIe every decode step.

### Phase 4 — Deferred hardware (gate: Phase 2 sim)

Only if Phase 1–2 cannot reach target η and traces show sufficient expert/KV hit rates:

| Option | When | Not before |
|--------|------|------------|
| Used Alveo U50 (HBM scratch + DMA) | Expert prefetch/compression coprocessor | Phase 2 sim + hit-rate proof |
| CXL Type-3 AIC (TRX50/W790 platform) | 256–512 GB warm tier | Platform upgrade + CXL BIOS |
| Custom staging appliance | Expert-page compression + DMA queues | 500+ unit product validation |

## Target workloads

| Workload | Tier focus | Primary engine |
|----------|------------|----------------|
| Qwen3.6-35B-A3B MoE long context | Expert staging + KV paging | SGLang primary |
| Agent swarm (8B base + LoRA heads) | Prefix sharing + DDR adapters | SGLang |
| DeepSeek-V4-Flash-class MoE | Expert cache hit rate | vLLM #37190 path |
| Dense 27B Q4 barely-OOM | Layer streaming + NVMe cold | llama.cpp / vLLM |

## Metrics

```text
η           = TPS_actual / TPS_carnot
gap_closed  = (η_new - η_initial) / (1 - η_initial)
KV headroom = max_concurrent_agents at fixed context
expert_hit  = hits / (hits + misses) per layer
stall_frac  = time_waiting_on_tier / total_decode_time
```

Report alongside existing pheno eval contracts (trial v2, aggregate v2)—do not sum per-request peaks.

## Dependencies

| Artifact | Link |
|----------|------|
| OKF distillation | [`docs/okf/kernels/tiered-memory-hierarchy.md`](../../docs/okf/kernels/tiered-memory-hierarchy.md) |
| VRAM formulas | [`docs/okf/inference/vram-scaling-factors.md`](../../docs/okf/inference/vram-scaling-factors.md) |
| Dual-GPU DAG | [`plans/2026-07-17-polyglot-forward-dag/INDEX.md`](../2026-07-17-polyglot-forward-dag/INDEX.md) |
| Fleet posture | [`plans/2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md`](../2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md) |
| Model matrix | [`docs/specs/003-model-engine-matrix.md`](../../docs/specs/003-model-engine-matrix.md) |

## Reading order

1. OKF article (claims + tier model)
2. Phase 1 engine bootstrap (#37190, #20126)
3. Phase 2 simulator (go/no-go)
4. Phase 3 dual-GPU sidecar
5. Phase 4 hardware (only if gated open)
