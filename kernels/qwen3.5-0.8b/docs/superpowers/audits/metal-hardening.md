# Metal Kernel Hardening — Audit (2026-07-24)

## Status: 13 `.metal` files, ~3000 LoC. 12/12 MLX-vs-Metal diff PASS.

### P0 — Threadgroup Memory Budget
| Kernel | Threads | Shared Mem | Budget | Status |
|---|---|---|---|---|
| `flash_attn_decode` (attention.metal) | Br=16 | 32 KB | 48 KB M1 Pro | ✅ Under budget |
| `gumbel_argmax_block` (sampling.metal) | V=248320 | 0 | — | ✅ No shared mem needed |
| `rmsnorm_h1024_fused` (norm.metal) | TG=1024 | 2 KB | — | ✅ |

### P1 — Missing Piece: Weight Threading
`pheno_engine_decode_step` runs in **stub mode** — only RMSNorm is dispatched per layer. Q/K/V/O projections + attention + SwiGLU use synthetic stub results. Threading real weights through `kernel_engine.mm` is the remaining gap for a full Metal forward pass.

### P2 — bf16→fp16 ABI Overhead
The Metal kernels use `half*` (fp16), but MLX/bfloat16 host data must be converted at the boundary via `_fp16_bits_to_bf16_bits()` in `validate.py`. This adds ~5-10µs per kernel call. Could be removed by adding `bfloat16` support to MSL kernels (Apple AS bf16 instructions available on M1 Pro). Low priority pending weight-threading.

### P3 — FMA Utilization
`norm.metal` uses `mul` + `add` separately in the rsqrt accumulation loop (line 34-36). Replacing with `fma(x, x, sum)` would give ~2× float throughput on M1 Pro FP16 FMA pipeline.

### P4 — No Thermal Throttle Test
All benchmarks run cold (<60s). Real forward-pass workloads (>5 min) may thermal-throttle at 7W M1 Pro. Add a `--soak 300` flag to validate.py that exercises `flash_attn_decode` in a tight loop for 5 min, reporting tok/sec drop.
