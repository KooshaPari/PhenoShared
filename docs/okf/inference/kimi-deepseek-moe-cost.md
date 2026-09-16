# Kimi DeepSeek MoE Cost

**Source:** `ChatGPT-Kimi DeepSeek MoE Cost.md` (27.6 KB, 2026-06-14) — sha `6cd4b046…` — class **L**.

MoE cost is not "params × VRAM" but **active-experts × KV × routing overhead**. Kimi/DeepSeek show that 8×7B MoE can serve cheaper than dense 30B if **router is cheap, experts are staged, and KV is compressed** — the same levers that make local `Qwen3.5-0.8B` viable on 3090 Ti with `gpu-memory-utilization 0.55` and `max_total_tokens 8192`.

## Distilled claims (class **[L]** — from `ChatGPT-Kimi DeepSeek MoE Cost.md`)

Each claim cites the source SHA via `local://sha256/<digest>` per `pheno/evidence/adapters/local_corpus.py`.

### 1. Cost model — `cost/token ≈ active_params/throughput + KV_mem/seq_len + router_latency`

- **[L]** Kimi reduces active params 1/4 via 2-of-8 top-2 routing — claim-cite source `6cd4b046…`.
- **[L]** DeepSeek reduces KV 1/8 via Multi-head Latent Attention (MLA) compression — claim-cite source `6cd4b046…`.
- **[L]** Router cost is <1% of attention cost if the router is fused into the matmul kernel; naive router (separate kernel launch + scatter) costs 3-5% — claim-cite source.
- **[L]** Load-balancing loss prevents expert collapse without extra VRAM; auxiliary loss coefficient in `[0.001, 0.01]` sweet spot. Source citation needed from Kimi-K2 / DeepSeek-V3 paper rather than the export.

### 2. VRAM scaling — active vs staged

- **[L]** Dense 30B at fp16 needs ~60 GB VRAM — no single 3090 Ti / 4070 can hold it (24 GB cap). Source citation needs arXiv reference.
- **[L]** 8×7B MoE with 2 active experts active needs 14 GB VRAM (active params) + 42 GB host DRAM (staged inactive experts via host paged memory). Fits 24 GB GPU when KV is on host. Source: `local://sha256/6cd4b046…`.
- **[L]** Prefetched experts warm-cache in 4-8 GB regions; cold miss costs ~80 ms; acceptable if miss-rate < 2%. Source citation needed.

### 3. Routing overhead

- **[L]** Token-choice vs expert-choice routing: token-choice gives better quality per FLOP but harder load-balance. Expert-choice enforces bounded expert load. Pheno-harness tournament config picks expert-choice for `gpu_memory_utilization > 0.80`.
- **[L]** Shared experts (DeepSeek-V3 style) amortize common-knowledge work, reducing active FLOPs further when ~10-15% of tokens are "shared heavy". Cite: `6cd4b046…`.
- **[L]** Fine-grained expert split (Kimi-K2: 384 small experts, top-8 activate) outperforms 8-large-experts at same active param budget.

### 4. Pheno-harness linkage

- N13 Zig hand-roll vs CUDA baseline should measure `tg64` at _fixed cost budget_, not fixed FLOPs — MoE cost model sets the budget (FLOPs/P95-tail-latency).
- N15 Nim x-perf sets the _client_ overhead (tokenize/prefill/postprocess); separator from model-side cost is necessary for `[P]` evidence class on `hardware/rtx-3090-throughput.md`.
- `bench/suites/n10_okf_distill.py` (Phase 1 sample) verifies that `local://sha256/<digest>` claims map 1:1 to source files via `pheno/evidence/adapters/local_corpus.py`.
- Promotion to **[P]** requires primary-source verification per `docs/okf/INDEX.md` Phase-2 loop.

## Active params vs total — concrete table (claims class L)

| Model               |       Total params | Active params |       3090 Ti 24 GB fit?       |
| ------------------- | -----------------: | ------------: | :----------------------------: |
| Dense 30B (fp16)    |               30 B |          30 B |        No (needs 60 GB)        |
| Dense 13B (fp16)    |               13 B |          13 B |      Yes (26 GB) — close       |
| DeepSeek-V2 16B MoE | 236 B (16B/active) | 21 B (active) |            Marginal            |
| Kimi-K2 (rumored)   |   >1 T (8B/active) |           8 B |    Yes (16 GB) — sweet spot    |
| 8×7B MoE top-2      |               56 B |   14 B (fp16) | Yes (28 GB) — needs KV offload |

All rows class **[L]** until DeepSeek-V3 / Kimi-K2 paper verification.

## Verification targets (before promotion to [P])

- [ ] **DeepSeek-V2/V3 paper** (arXiv 2405.04434 / 2412.19437) — verify MLA ratio 1/8 KV reduction.
- [ ] **Kimi K2 release notes** (Moonshot AI, mid-2026) — verify active param count + routing scheme.
- [ ] **Hugging Face `transformers` MoE reference impl** — verify shared-experts partition semantics.
- [ ] **Local benchmark** `bench/suites/n10_kimi_moe.py` — measure `tg64` at 8192 ctx, 2-of-8 routing, on RTX 3090 Ti (current `tb2-30000-sglang` Qwen3.5-9B lane is dense, not MoE — would need separate MoE test lane).

## Cross-links

- `inference/efficiency-evolutions-post-moe.md` — same MoE topic, completeness coverage.
- `inference/vram-scaling-factors.md` — VRAM math, dense baseline.
- `hardware/rtx-3090-throughput.md` — tok/hour at fixed settings (3090 Ti 24 GB).
- `benchmarks/pairwise-test-case-generation.md` — pairwise sampling 70% reduction applied to MoE × hardware matrix.
- `plans/2026-07-14-usch-heterogeneous-inference-v1/` — original heterogeneous inference plan; Kimi/DeepSeek MoE was called out as test case there.

**Evidence:** `local://sha256/6cd4b0460c724f63afedf5fd0a9361f6e3bd234d2783ba5a2feb00c9e7e14791` (class **L**). Promote to class **P** after primary-source verification.
