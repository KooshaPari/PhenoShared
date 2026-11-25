# Qwen3.5 0.8B — Performance Reference

This document describes the kernel-architecture choices baked into the
`kernels/qwen3.5-0.8b/` suite, the memory layout for inference, and
worked-out cost breakdowns for both the **decode** (M=1) and **prefill**
(M≥1) paths. Numbers are derived from the on-disk constants in
`arch.yaml` and the per-kernel implementations in
`python/reference.py`; see `include/qwen3_5.h:1` for the canonical C
view and `python/bench.py:1` for the live benchmarking harness.

## 1. Architecture summary

| Field | Value | Source |
|---|---|---|
| `hidden_size` | 1024 | `arch.yaml:18` |
| `num_hidden_layers` | 24 | `arch.yaml:20` |
| `vocab_size` | 248320 | `arch.yaml:17` |
| `intermediate_size` | 3584 | `arch.yaml:19` |
| `rms_norm_eps` | 1.0e-6 | `arch.yaml:22` |
| `tie_word_embeddings` | true (lm_head ≡ embed) | `arch.yaml:23` |
| `attn_output_gate` | true (sigmoid-gated attention output) | `arch.yaml:25` |
| `partial_rotary_factor` | 0.25 | `arch.yaml:26` |
| `rope_theta` | 10,000,000 | `arch.yaml:27` |
| `mrope_section` | (T=11, H=11, W=10) — `rot_dim = 32` | `arch.yaml:30` |
| Full attention heads | Q=8, KV=2, head_dim=256 (GQA 4:1) | `arch.yaml:34-36` |
| Full attention interval | every 4th layer (3, 7, 11, 15, 19, 23) | `arch.yaml:39-40` |
| Linear attention | K=16, V=16, Dk=Dv=128, conv_kernel=4 | `arch.yaml:43-50` |
| Per-token dtypes | bf16 activations, bf16 weights, fp32 state, fp32 accumulators | `arch.yaml:81-84` |

The full-attention schedule produces 6 GQA layers and 18 DeltaNet layers
in every 24-layer block, hence 6 / 24 ≈ 25% of compute is quadratic
attention and 75% is linear (constant in M for decode).

## 2. Why hybrid linear + full attention on Qwen3.5 0.8B

Qwen3.5 0.8B is the smallest of the Qwen3.5 family and is the densest
hybrid in the series (larger Qwen3.5-4B/8B actually use *more* full
attention). The hybrid schedule is a deliberate compute/quality trade:

* **Full attention is O(M²) in prefill, O(M) in decode** — KV cache size
  grows linearly with sequence length; on Qwen3.5 0.8B at 32K context,
  6 full layers × 2 KV heads × 256 head_dim × 32K × 2 bytes ≈ 192 MB
  just for KV. At 128K context, that grows to 768 MB.
* **Linear (DeltaNet) attention is O(M) in prefill, O(1) in decode** —
  state is a fixed 16 × 16 × 128 × 128 fp32 tensor per layer
  (4 MiB/layer, 72 MiB for 18 layers, **constant** in M).  The trade is
  exact-retrieval vs. associative-recall quality; DeltaNet loses some
  long-range fidelity but keeps the recurrent state tiny and parallel.
* **The hybrid pattern (every 4th full)** is a quality sweet spot — the
  full layers provide the occasional "re-sync" of the linear state to
  recent tokens, and the linear layers absorb the bulk of the context
  at a fixed memory cost.

For 0.8B specifically, this means we can serve 128K-token contexts on
a single M-series Mac (M2 Max ≈ 96 GB unified memory) with full
attention KV cache ~ 768 MB, weights ~ 1.3 GB, linear state ~ 72 MB,
and activations measured in single-digit MiB.

## 3. Why Metal MSL over CUDA

The Qwen3.5 0.8B kernel suite targets **Apple Silicon only** — there is
no CUDA build target. The reasoning is concrete, not aesthetic:

1. **Unified memory architecture.**  M-series GPUs share DRAM with the
   CPU.  The 248,320 × 1024 bf16 embedding (510 MB) lives in CPU-side
   pages that the GPU can read without a copy; the same is true for the
   KV cache, the linear-attention recurrent state, and intermediate
   activations.  On a CUDA + discrete-GPU box, every decode step
   requires PCIe copies of the activation tensor; on Apple Silicon it
   is a single contiguous allocation.
2. **Token economics.**  A single M3 Max 128 GB system is
   ~ $7,000–$9,000 new; an equivalent CUDA box (48 GB RTX 6000 Ada +
   Threadripper) is ~ $12,000.  For a 0.8B-param model that fits in
   < 2 GB, the rest of the system RAM is pure headroom for context
   length and concurrency.  See `docs/PUBLISHING.md` for the operator
   cost model.
3. **MLX is the reference.**  Apple maintains MLX as the reference
   numerics path for Metal; `python/reference.py:1` is pure MLX and
   gives bf16-identical results to the hand-tuned kernels (max-abs
   diff ≤ 1e-2 per-kernel by design, see `python/validate.py:20-22`).
4. **bf16 native.**  All M-series GPUs have hardware bf16 support; the
   GEMM/BF16→FP32 accumulation pattern used in the kernel suite maps
   1:1 to the AMX matrix unit on M1+ and the dedicated matrix engine
   on M4.

The trade-off is a smaller fleet: the suite won't run on a CUDA-only
node, and a CUDA port of the kernels would be a separate project
(likely Mojo + a CUTLASS-style `Matmul`).

## 4. Memory budget

### 4.1 Constants (independent of M)

| Component | Size | Formula |
|---|---|---|
| Embedding + lm_head (tied) | 508,559,360 B = 485.2 MiB | `vocab_size × hidden_size × 2` |
| Per full-attention layer weights | ≈ 33.7 MiB | `qkv + o_proj + o_gate + 3 ffn` |
| Per linear-attention layer weights | ≈ 31.0 MiB | `qkv + o_proj + conv + 3 ffn` |
| Linear-attn recurrent state (per layer) | 4,194,304 B = 4.0 MiB | `K × V × Dv × Dk × 4 (fp32)` |
| Total linear state (18 layers) | 75,497,472 B = 72.0 MiB | `18 × 4.0 MiB` |
| Total weights (24 layers + embed) | ≈ 1.27 GiB | derived from layer counts |

### 4.2 Variable with sequence length (B=1, KV cache)

KV cache formula per full-attention layer:

```
per_layer_bytes = 2 (K, V) × full_kv_heads × head_dim × dtype_bytes × M
                = 2 × 2 × 256 × 2 × M
                = 2048 M  bytes
```

Total KV cache for 6 full layers:

```
total_kv_bytes = 6 × 2048 M  = 12288 M  bytes
              = 12 KiB × M  (where M is the number of tokens)
```

| M (tokens) | KV cache | Linear state | Activations (B=1) | Total runtime memory |
|---:|---:|---:|---:|---:|
| 1 | 12 KiB | 72.0 MiB | 4 KiB | ~ 72.0 MiB |
| 128 | 1.5 MiB | 72.0 MiB | 0.5 MiB | ~ 74.0 MiB |
| 512 | 6.0 MiB | 72.0 MiB | 2.0 MiB | ~ 80.0 MiB |
| 1024 | 12.0 MiB | 72.0 MiB | 4.0 MiB | ~ 88.0 MiB |
| 4096 | 48.0 MiB | 72.0 MiB | 16.0 MiB | ~ 136.0 MiB |
| 16384 | 192.0 MiB | 72.0 MiB | 64.0 MiB | ~ 328.0 MiB |
| 32768 | 384.0 MiB | 72.0 MiB | 128.0 MiB | ~ 584.0 MiB |
| 131072 | 1.5 GiB | 72.0 MiB | 512.0 MiB | ~ 2.1 GiB |

Weights are resident on first allocation; runtime memory above is the
**additional** footprint (KV + state + activations).  Total resident
memory at 128K context is `~ 1.27 GiB weights + 1.5 GiB KV + 72 MiB
state ≈ 2.85 GiB`, well under the 8 GB minimum M-series unified
memory.

### 4.3 Per-batch (B > 1) scaling

KV cache and linear state scale linearly in B.  Activations scale
linearly in B.  Weights are shared.  The decode-time memory is
`B × (KV + state + activations) + weights`.

## 5. Decode step cost (M=1, B=1)

Decode is the latency-critical path.  Per token, every layer runs the
following; the totals are summed over 24 layers (6 full + 18 linear):

### 5.1 Per-layer cost (token-at-a-time, all 24 layers do this)

| Op | Flops (per layer) | Bytes touched | Notes |
|---|---:|---:|---|
| `attn_rmsnorm` | 2 × 1024 = 2,048 | 1024 + 1024 | 1 read, 1 write |
| `ffn_rmsnorm` | 2 × 1024 = 2,048 | 1024 + 1024 | same |
| (full only) `qkv_proj` | 1024 × 3072 × 2 = 6.3 MFlop | 3072 + 1024 | GEMV |
| (linear) `qkv_proj` (incl. conv) | 1024 × 6144 × 2 = 12.6 MFlop | 6144 + 1024 | GEMV + depthwise conv1d K=4 |
| `rope` (M-RoPE) | rot_dim = 32 | 32 + 32 | 1 Q head, 1 K head, partial rotary |
| (full) `attention_decode` | `O(M)` in seq_len, 8 Q heads × 256 D | seq_len × 2 × 2 × 256 | score over cached KV |
| (linear) `linear_attention_step` | `O(K × V × Dv × Dk)` = 16 × 16 × 128 × 128 = 4.2 MFlop | 4 MiB state | recurrent state update |
| (full) `o_proj` (incl. attn output gate) | 1024 × 2048 × 2 = 4.2 MFlop | 2048 + 1024 + 1024 | gated |
| (linear) `o_proj` | 1024 × 2048 × 2 = 4.2 MFlop | 2048 + 1024 | no gate on linear path |
| SwiGLU `gate_up` | 1024 × 3584 × 2 × 2 = 14.7 MFlop | 2 × 3584 + 1024 | fused |
| SwiGLU `down` | 3584 × 1024 × 2 = 7.3 MFlop | 1024 + 3584 | |

### 5.2 Decode totals (M=1, B=1, per token)

Approximate per-token FLOPs (ignoring small ops):

* **Full attention layers (6 of 24)**: 6 × (2.0K rms + 6.3M qkv + 4.2M o + 14.7M gate_up + 7.3M down + 16 (rope) + 8 × 256 (attn) + …) ≈ **6 × 32.6 MFlop ≈ 196 MFlop**
* **Linear attention layers (18 of 24)**: 18 × (2.0K rms + 12.6M qkv + 4.2M o + 14.7M gate_up + 7.3M down + 16 (rope) + 4.2M lin_step) ≈ **18 × 43.1 MFlop ≈ 776 MFlop**
* **LM head**: 1024 × 248,320 × 2 ≈ **509 MFlop** (tied with embed; one big GEMV)
* **Total ≈ 1.48 GFlop / token** at M=1

A M3 Max GPU delivers ~ 5–7 TFlop/s bf16 (per Apple-published numbers);
decode should hit ~ 3,000–5,000 tok/s in bf16 numerics.  Live numbers
are in `bench/results/qwen3.5-0.8b-ref.json` (regenerate with
`python python/bench.py`).

### 5.3 Decode latency breakdown (M=1, single token)

| Stage | Approx. share | Bottleneck |
|---|---:|---|
| LM head (1024 → 248,320) | ~ 35% | 510 MB matmul, memory-bound |
| 18 × linear attention step | ~ 25% | 4 MiB state read/write per layer |
| 18 × SwiGLU up/down | ~ 20% | 1024 × 3584 GEMV |
| 6 × full attention decode | ~ 10% | O(1) at M=1, but QK softmax over 1 token |
| 6 × qkv + 6 × o_proj (full) | ~ 5% | small GEMVs |
| Sampling (gumbel argmax over 248K) | ~ 3% | one pass over logits |
| RoPE, RMSNorm, residual | ~ 2% | elementwise |

The LM head dominates at M=1 because we always materialize 248,320
logits per token.  For speculative-decode MTP the LM head is reused
across draft tokens and the per-token cost amortizes.

## 6. Prefill cost (M ≥ 1)

Prefill is throughput-critical.  Per layer, the full sequence is
processed in one matmul; cost is dominated by the GEMMs and the O(M²)
full attention.

### 6.1 Prefill per-layer (full attention layers)

| Op | Flops (M tokens) | Notes |
|---|---:|---|
| `attn_rmsnorm` + `ffn_rmsnorm` | 2 × M × 1024 | elementwise |
| `qkv_proj` | M × 1024 × 3072 × 2 = 6.3 MFlop × M | GEMM |
| `rope` (M-RoPE) | M × 32 × 2 | elementwise over partial rotary dim |
| `full_attention` (QKᵀ + softmax + PV) | M × M × 8 × 256 × 2 × 2 = 8.4 MFlop × M² | O(M²) |
| `o_proj` (incl. attn output gate) | M × 1024 × 2048 × 2 = 4.2 MFlop × M | GEMM |
| SwiGLU `gate_up` | M × 1024 × 3584 × 2 × 2 = 14.7 MFlop × M | GEMM |
| SwiGLU `down` | M × 3584 × 1024 × 2 = 7.3 MFlop × M | GEMM |

### 6.2 Prefill per-layer (linear attention layers)

| Op | Flops (M tokens) | Notes |
|---|---:|---|
| `attn_rmsnorm` + `ffn_rmsnorm` | 2 × M × 1024 | elementwise |
| `qkv_proj` (incl. conv1d) | M × 1024 × 6144 × 2 = 12.6 MFlop × M | GEMM + depthwise conv1d |
| `rope` (M-RoPE) | M × 32 × 2 | elementwise |
| `linear_attention_step` (sequential over M) | M × (4 × 16 × 16 × 128 × 128) = M × 16.8 MFlop | no parallel scan impl yet — see **§ 8** |
| `o_proj` | M × 1024 × 2048 × 2 = 4.2 MFlop × M | GEMM |
| SwiGLU `gate_up` | M × 1024 × 3584 × 2 × 2 = 14.7 MFlop × M | GEMM |
| SwiGLU `down` | M × 3584 × 1024 × 2 = 7.3 MFlop × M | GEMM |

### 6.3 Prefill totals (M tokens, B=1)

Per-token (averaged) FLOPs for prefill, all 24 layers:

* **6 full layers**: 6 × (32.6 MFlop + 8.4 MFlop × M) per token
* **18 linear layers**: 18 × (43.1 MFlop + 16.8 MFlop) per token ≈ 776 MFlop + 16.8 MFlop × M × 18 ≈ 776 + 302.4 MFlop × M
* **LM head**: M × 1024 × 248,320 × 2 = 509 MFlop × M (only last position is needed for decode; we materialize the full M for MTP)

| M | Full attn | Linear attn | LM head | Total (per token) | Total (sum) |
|---:|---:|---:|---:|---:|---:|
| 128 | 6.4 GFlop | 39.5 GFlop | 65.1 GFlop | 0.86 TFlop | 0.86 × 128 = 110 TFlop |
| 512 | 25.7 GFlop | 155.6 GFlop | 260.6 GFlop | 1.41 TFlop | 1.41 × 512 = 720 TFlop |
| 1024 | 51.5 GFlop | 309.6 GFlop | 521.2 GFlop | 2.15 TFlop | 2.15 × 1024 = 2.20 PFlop |

(Per-token = divided by M; Sum = full prefill cost across the M tokens.)

On M3 Max (~ 5 TFlop/s bf16 sustained), the prefill times would be:
* M=128: ~ 22 s  ← TODO: revise against actual measured numbers in `bench/results/`
* M=512: ~ 144 s
* M=1024: ~ 440 s

**Caveat:** these are back-of-envelope bf16 numbers; the
hand-tuned Metal kernels typically achieve 30–50% of peak in practice.
The kernel suite does *not* yet have a parallel scan for linear
attention prefill (each step is sequential over M); see **§ 8** for
the optimization path.

### 6.4 Prefill cost breakdown at M=128, M=512, M=1024

At M=128, full attention accounts for **6.4 GFlop / token**, and linear
accounts for **39.5 GFlop / token** (6.2× more).  The hybrid is paying
its keep — pure full-attention prefill at M=128 would be
~ 6 × (32.6 + 8.4 × 128) ≈ 6.4 GFlop, but at M=128 that's
~ 0.82 TFlop total, while the linear layers alone cost 39.5 GFlop
because of the recurrent state update (16.8 MFlop / token).

At M=1024 the O(M²) term dominates: full attention per layer is
8.4 MFlop × 1024 = 8.6 GFlop / token, while the linear layers
plateau at 39.5 GFlop / token (the recurrent step is O(1) per token
even though the prefill processes M of them sequentially).

## 7. Sampling cost

`ref_gumbel_argmax` in `python/reference.py:429` and the Metal
`fused_topk_topp_argmax` kernel both reduce 248,320 logits to one
sampled id per token.  Cost:

| Mode | Flops / call | Notes |
|---|---:|---|
| `greedy` | 248,320 compare-reduce | argmax |
| `gumbel` | 248,320 random + 248,320 add + argmax | gumbel-max trick |
| `topk_topp` | O(248,320 × log 248,320) for sort + categorical | nucleus filter |

At M=1 the sampling pass is ~ 3% of total decode time (see **§ 5.3**).
At M≥ 64 in a batch, sampling parallelizes cleanly across the batch
axis and amortizes to < 1%.

## 8. Optimization roadmap

The numbers above are upper bounds; the kernel suite ships several
optimization levers that have *not* yet been turned on.  When they
land, the expected wins are:

| Optimization | Effect | Status |
|---|---|---|
| **Parallel scan for linear attention prefill** | replaces the per-token recurrent loop with a `O(log M)` segmented scan; **expected ~ 4× at M=512, ~ 8× at M=1024** | spec only — see `PLAN.md` § 2.5 (Bifrost) and the future B-track items |
| **Fused RoPE + QKV split** | avoid the intermediate write of the rotated tensor | spec only |
| **Paged KV cache** | allow 131K context without 1.5 GB of contiguous allocation | spec only |
| **MTP draft** (1 speculative head) | amortize LM head cost across 2–4 draft tokens per step | wired in arch.yaml but not yet used by the harness |
| **bf16 linear state** | halves the 72 MiB linear-state footprint; risk is recurrence drift | spec only — must pass `validate.py --check --tolerance=1e-3` |
| **Quantized KV cache** (int8/int4) | 2–4× KV cache shrink at small accuracy cost | spec only |

Every optimization must keep `python/validate.py` green and pass
`tests/test_codegen.py` (which asserts the arch constants are still
consistent across C/Rust/Zig/Mojo/Nim/JSON).

## 9. See also

* `python/reference.py:1` — pure-MLX reference implementation
* `python/validate.py:1` — per-kernel numerical harness (PASS/FAIL table)
* `python/bench.py:1` — end-to-end throughput benchmark
* `python/codegen.py:1` — single-source-of-truth arch constants emitter
* `include/qwen3_5.h:1` — canonical C header (hand-written; codegen mirror
  in `iso/qwen3_5.h` for drift detection)
* `arch.yaml:1` — single source of truth for all constants
* `docs/CONTRIBUTING.md` — how to add a kernel or extend to other Qwen3.5
  sizes (1.7B / 4B / 8B)
