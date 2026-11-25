# ADR-ECO-001: Tiered MoE Expert Staging on 3090 Ti (24 GB)

- **Status:** Proposed (N17, Forward DAG v2 — hidden claim from `synthesis/03-moe` + `06-hardware`)
- **Date:** 2026-08-19
- **Deciders:** pheno-harness (Codex), Chat 3 (interpretation)
- **Evidence class:** L → P pending (corpus `efficiency-evolutions-post-moe` bc4ac8fa, `kimi-deepseek-moe-cost` 6cd4b046, `tiered-memory-hierarchy` from `Modding 3090 Ti VRAM`)

## Context

8×7B MoE (2 active experts) naively needs 42 GB staged + 14 GB active — no fit on 3090 Ti 24 GB. Corpus claims (Kimi/DeepSeek) that **shared+routed experts + staged offload + MLA** makes MoE cheaper than dense 30B on the same host, but no pheno-harness ADR captures the decision: do we **stage experts across HBM→DRAM→NVMe and prefetch by router**, or do we **pin 1–2 experts and drop the rest**?

Current `pheno-serve` pins `gpu-memory-utilization 0.55` on 3090 Ti (13.5 GB) leaving 8.5 GB for unsloth — no staging. N12 (KernelBench) + N13 (Zig hand-roll) need the decision before `tg64`/`TTFT` can be compared at fixed cost.

## Decision

**Stage experts.** `pheno-serve` will support 8 experts with **2 active in HBM, 6 staged in host DRAM/NVMe**, router-predicted prefetch overlapped with attention compute, KV compressed via MLA, `gpu-memory-utilization` ≤0.65.

- **HBM budget:** 2×7B active + MLA KV ≈ 14 GB
- **Staged:** 6×7B expert weights in `D:/WSL/model-cache` (NVMe), paged to host DRAM on router hit, prefetched 1 layer ahead
- **Fallback:** if prefetch misses, stall 1 layer (measured in `bench/results/cross-perf`) — not OOM

## Consequences

- **Positive:** 8B MoE serves on single 3090 Ti at `tg64` parity with dense 30B on A100 (per `hardware/rtx-3090-throughput.md`), cost $0.50/hr vs $2/hr.
- **Negative:** needs `pheno-otel` OTLP tracing (N18) + `hardware_aware_placement.yaml` + `inference_runners.yaml` changes; N03 supervisor must not kill during expert load.
- **Risk:** NVMe → DRAM bandwidth (3 GB/s) may bottleneck if router mispredicts — mitigate via shared experts (fixed 2) + load-balancing loss.

## Verification

- N12: `scripts/run_kernelbench_rtx3090.ps1` with 43 problems, record `latency_ms` vs staged/unstaged
- N13: Zig hand-roll `tg64` vs CUDA baseline at `gpu-mem 0.55` vs `0.65` staged
- Promote to **[P]** after measuring `pheno-serve` with staged experts vs pinned

## Links

- OKF: `docs/okf/inference/efficiency-evolutions-post-moe.md`, `docs/okf/inference/kimi-deepseek-moe-cost.md`, `docs/okf/kernels/tiered-memory-hierarchy.md`
- DAG: `plans/2026-07-24-forward-dag-v2/INDEX.md` N17, `config/benchmark_registry_2026-07.yaml`, `config/hardware_aware_placement.yaml`
- Evidence: `local://sha256/bc4ac8fad8910180ebe9bd154dfdadd8334792667d3e26b796f24589802f4f97`, `local://sha256/6cd4b0460c724f63afedf5fd0a9361f6e3bd234d2783ba5a2feb00c9e7e14791`
