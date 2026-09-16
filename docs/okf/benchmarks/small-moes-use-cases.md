---
source_file: ChatGPT-Small MoEs Use Cases.md
sha256: f7aaef2fd90263475d4eb83254d8b41882a53cc052830ad8a9d7a489cf3347c7
topics: [benchmarks, moe, inference, efficiency]
related_okf:
  - benchmarks/efficiency-evolutions-post-moe.md
  - inference/kimi-deepseek-moe-cost.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Small MoEs Use Cases

**Source:** `ChatGPT-Small MoEs Use Cases.md` (12 KB, 2026-06-14) — sha `f7aaef2f` — class **L**.

Benchmark small MoE use cases: expert sparsity, routing overhead, and eval methodology for heterogeneous inference on 3090.

## Key insights (stub)

- Small MoEs (8×7B active 2B) reduce VRAM 40% vs dense 8B; benchmark must isolate routing latency 15–30% (see benchmarks/efficiency-evolutions-post-moe.md).
- Pairwise sampling covers MoE×dense×dataset combos with ~40 trials vs 534 exhaustive (see benchmarks/pairwise-test-case-generation.md).
- Maps to `kernels/tiered-memory-hierarchy.md` expert staging (HBM→DRAM→NVMe).

## Next (N10)

- Extract [L] claims with `local://sha256/f7aaef2fd90263...` citations.
- Verify vs primary MoE papers (Switch Transformer, Mixtral) before `docs/specs/`.
- Promote to [P] after verification.

**Evidence:** `local://sha256/f7aaef2fd90263475d4eb83254d8b41882a53cc052830ad8a9d7a489cf3347c7` (class **L**).
