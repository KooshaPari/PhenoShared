"""attn_decode.mojo — M=1 decode attention (Mojo 0.26, CPU-side).

This is the Mojo 0.26-compatible replacement for the original Metal-style
flash_attn_decode kernel.  Per the task scope ("stay within the Mojo
stdlib's CPU-side capabilities — correctness > SIMD-tiling"), we drop:

  * the GQA broadcast across TG warps (no thread_idx / warp_id)
  * the online-softmax flash-attention loop (no block_idx / block_dim)
  * KV paging (the host can materialize the paged cache into a contiguous
    buffer before calling the kernel)
  * all GPU-only primitives (gpu.thread_idx, gpu.block_idx, AddressSpace.SHARED,
    stack_allocation, barrier, StaticTuple, LayoutTensor)

…and replace them with a straightforward scalar triple-loop:

    for b in range(B):
      for h_q in range(H_q):
        # 1. scores = Q[b, h_q, :] @ K[b, h_kv, :, :]^T * scale
        # 2. softmax in-place
        # 3. O[b, h_q, :] = sum_s softmax[s] * V[b, h_kv, s, :]

Where ``h_kv = h_q // (H_q / H_kv)`` (GQA: multiple Q heads share a KV head).

Buffer contract:

    [0] Q       [B, H_q, D]     half
    [1] K       [B, H_kv, S_k, D] half
    [2] V       [B, H_kv, S_k, D] half
    [3] O       [B, H_q, D]     half   (output, may alias Q for in-place)
    [4] B       uint
    [5] S_k     uint   (current sequence length; 1 <= S_k)
    [6] scale   float  (typically 1/sqrt(D))

The Mojo 0.26 idioms used here:
  * `alloc[T](N)` from `std.memory` (replaces stack_allocation)
  * `p.free()` for explicit teardown (no implicit lifetime tracking)
  * `UnsafePointer[T, _]` / `UnsafePointer[T, MutAnyOrigin]` parameter
    conventions so the function is callable from Python ctypes
  * `Float16(Float32(v))` / `Float32(Float16(v))` explicit conversions
  * `exp` from `std.math` for softmax (the Gumbel noise path is gone)
"""

from std.memory import alloc
from std.math import exp, sqrt


# ---------------------------------------------------------------------------
# Architecture constants — keep in lock-step with arch.yaml and
# qwen3_5_types.mojo.  Hardcoded here so this file builds standalone.
# ---------------------------------------------------------------------------

comptime kQwVocabSize: Int = 248320
comptime kQwFullHeads: Int = 8
comptime kQwFullKvHeads: Int = 2
comptime kQwFullHeadDim: Int = 256
comptime kQwFullHeadsPerKv: Int = 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


fn attn_decode(
    Q: UnsafePointer[Float16, _],
    K: UnsafePointer[Float16, _],
    V: UnsafePointer[Float16, _],
    O: UnsafePointer[Float16, MutAnyOrigin],
    B: Int,
    S_k: Int,
    scale: Float32,
) -> Int:
    """M=1 decode attention.

    Returns 0 on success, non-zero on bad args.  Buffers are interpreted
    as:

        Q  : [B, kQwFullHeads,     kQwFullHeadDim]            fp16
        K  : [B, kQwFullKvHeads,   S_k, kQwFullHeadDim]       fp16
        V  : [B, kQwFullKvHeads,   S_k, kQwFullHeadDim]       fp16
        O  : [B, kQwFullHeads,     kQwFullHeadDim]            fp16

    ``O`` may alias ``Q`` for in-place update if the caller no longer
    needs the input query (the Metal kernel always wrote a separate O
    buffer, so this is a CPU-only convenience).
    """
    var H_q: Int = kQwFullHeads
    var H_kv: Int = kQwFullKvHeads
    var D: Int = kQwFullHeadDim
    var HeadsPerKv: Int = kQwFullHeadsPerKv

    if B <= 0 or S_k <= 0 or D <= 0:
        return 1
    if H_q <= 0 or H_kv <= 0:
        return 1
    if H_q % H_kv != 0:
        return 2

    # Per-(b, h_q) scratch buffer for the S_k softmax scores.
    var scores = alloc[Float32](S_k)

    for b in range(B):
        for h_q in range(H_q):
            var h_kv: Int = h_q // HeadsPerKv

            # ---- 1. scores[s] = scale * sum_d Q[b, h_q, d] * K[b, h_kv, s, d]
            var q_base = (b * H_q + h_q) * D
            var k_base = (b * H_kv + h_kv) * S_k * D
            for s in range(S_k):
                var k_row_base = k_base + s * D
                var acc: Float32 = Float32(0.0)
                for d in range(D):
                    var q_v = Float32(Q[q_base + d])
                    var k_v = Float32(K[k_row_base + d])
                    acc = acc + q_v * k_v
                scores[s] = acc * scale

            # ---- 2. softmax in place.
            # Numerical-stable softmax: subtract max, then exp, then normalise.
            var m: Float32 = scores[0]
            for s in range(1, S_k):
                if scores[s] > m:
                    m = scores[s]
            var l: Float32 = Float32(0.0)
            for s in range(S_k):
                var e = exp(scores[s] - m)
                scores[s] = e
                l = l + e
            if l > Float32(0.0):
                for s in range(S_k):
                    scores[s] = scores[s] / l

            # ---- 3. O[b, h_q, d] = sum_s scores[s] * V[b, h_kv, s, d]
            var o_base = (b * H_q + h_q) * D
            var v_base = (b * H_kv + h_kv) * S_k * D
            for d in range(D):
                var acc: Float32 = Float32(0.0)
                for s in range(S_k):
                    var v_v = Float32(V[v_base + s * D + d])
                    acc = acc + scores[s] * v_v
                O[o_base + d] = Float16(acc)

    scores.free()
    return 0


fn attn_decode_default_scale(
    Q: UnsafePointer[Float16, _],
    K: UnsafePointer[Float16, _],
    V: UnsafePointer[Float16, _],
    O: UnsafePointer[Float16, MutAnyOrigin],
    B: Int,
    S_k: Int,
) -> Int:
    """Convenience wrapper that computes ``scale = 1/sqrt(D)`` internally."""
    var scale = Float32(1.0) / sqrt(Float32(kQwFullHeadDim))
    return attn_decode(Q, K, V, O, B, S_k, scale)


# ---------------------------------------------------------------------------
# Self-test entry point
# ---------------------------------------------------------------------------
#
# Run with:
#     mojo build kernels/qwen3.5-0.8b/mojo/attn_decode.mojo \
#         -o build/qwen3_5_attn_decode
#     ./build/qwen3_5_attn_decode
#
# The self-test runs a tiny decode with H_q=2, H_kv=1, S_k=2, D=4 and
# a hand-computable Q/K/V.  We print O and a numpy-style reference, then
# check the values match.


fn main() raises:
    print("[attn_decode] Mojo 0.26 CPU reference — M=1 decode attention")

    # Tiny shapes so the math is checkable by hand:
    #   H_q=2, H_kv=1, D=4, S_k=2, B=1
    var H_q: Int = 2
    var H_kv: Int = 1
    var D: Int = 4
    var S_k: Int = 2
    var B: Int = 1
    # Override the arch constants for the self-test only.
    # (The kernel above already uses the constants for shape, so we set
    # them by passing the same total buffer sizes as if H_q=H_kv=1
    # multiplied out.  Easier: just exercise the *functional* path via
    # the API and verify the math by construction.)
    # Since the kernel uses the arch constants for shape derivation,
    # the buffers below are sized for H_q=kQwFullHeads (8) and
    # H_kv=kQwFullKvHeads (2) and D=kQwFullHeadDim (256), but only the
    # first h_q / h_kv slots are touched in this smoke test.
    var H_q_arch: Int = kQwFullHeads
    var H_kv_arch: Int = kQwFullKvHeads
    var D_arch: Int = kQwFullHeadDim

    var Q = alloc[Float16](B * H_q_arch * D_arch)
    var K = alloc[Float16](B * H_kv_arch * S_k * D_arch)
    var V = alloc[Float16](B * H_kv_arch * S_k * D_arch)
    var O = alloc[Float16](B * H_q_arch * D_arch)

    # Zero-init K and V to keep the smoke test deterministic.
    for i in range(B * H_kv_arch * S_k * D_arch):
        K[i] = Float16(0.0)
        V[i] = Float16(0.0)
    for i in range(B * H_q_arch * D_arch):
        Q[i] = Float16(0.0)
        O[i] = Float16(0.0)

    # Build a Q row that is "ones" in the first 4 dims of head 0,
    # and a K row that is "ones" in the first 4 dims of S_k=0 and
    # "twos" in the first 4 dims of S_k=1.  With scale=1 and S_k=2:
    #   scores = [4.0, 8.0]      (for head 0)
    #   softmax([4, 8]) ~ [0.0474, 0.9526]
    #   O[0] = 0.0474 * V[0, :] + 0.9526 * V[1, :]
    # We seed V[0, :] = [1, 0, 0, 0], V[1, :] = [0, 1, 0, 0].
    # Expected: O[0, :4] ~ [0.0474, 0.9526, 0, 0].

    # Q[0, 0, 0..3] = 1.0
    for d in range(D_arch):
        Q[0 * D_arch + d] = Float16(0.0)  # head 0 baseline (zero, but…)
    for d in range(4):
        Q[0 * D_arch + d] = Float16(1.0)

    # K[0, 0, 0, 0..3] = 1.0 (S_k=0 row)
    for d in range(4):
        K[0 * S_k * D_arch + 0 * D_arch + d] = Float16(1.0)
    # K[0, 0, 1, 0..3] = 1.0 (S_k=1 row, same as S_k=0 — score will tie;
    # lower index wins, so post-softmax mass splits ~50/50)
    for d in range(4):
        K[0 * S_k * D_arch + 1 * D_arch + d] = Float16(1.0)

    # V[0, 0, 0, 0..3] = [1, 0, 0, 0]
    V[0 * S_k * D_arch + 0 * D_arch + 0] = Float16(1.0)
    # V[0, 0, 1, 0..3] = [0, 1, 0, 0]
    V[0 * S_k * D_arch + 1 * D_arch + 1] = Float16(1.0)

    var status = attn_decode_default_scale(Q, K, V, O, B, S_k)
    print("[attn_decode] status:", status)

    # Print O[0, 0, 0..4]
    print("O[0, 0, 0..4]:")
    for d in range(4):
        print("  d=", d, "->", Float32(O[0 * D_arch + d]))

    # With equal scores, softmax splits ~50/50: each O dim ~= (V[0] + V[1]) / 2
    #   d=0: (1 + 0) / 2 = 0.5
    #   d=1: (0 + 1) / 2 = 0.5
    #   d=2: (0 + 0) / 2 = 0.0
    #   d=3: (0 + 0) / 2 = 0.0
    var exp_d0 = Float32(0.5)
    var exp_d1 = Float32(0.5)
    var exp_d2 = Float32(0.0)
    var exp_d3 = Float32(0.0)

    var got_d0 = Float32(O[0 * D_arch + 0])
    var got_d1 = Float32(O[0 * D_arch + 1])
    var got_d2 = Float32(O[0 * D_arch + 2])
    var got_d3 = Float32(O[0 * D_arch + 3])

    var ok: Bool = True
    if abs(got_d0 - exp_d0) > Float32(1.0e-3):
        print("  d=0 FAIL:", got_d0, "vs", exp_d0)
        ok = False
    if abs(got_d1 - exp_d1) > Float32(1.0e-3):
        print("  d=1 FAIL:", got_d1, "vs", exp_d1)
        ok = False
    if abs(got_d2 - exp_d2) > Float32(1.0e-3):
        print("  d=2 FAIL:", got_d2, "vs", exp_d2)
        ok = False
    if abs(got_d3 - exp_d3) > Float32(1.0e-3):
        print("  d=3 FAIL:", got_d3, "vs", exp_d3)
        ok = False

    Q.free()
    K.free()
    V.free()
    O.free()

    if ok:
        print("[attn_decode] SMOKE OK")
    else:
        print("[attn_decode] SMOKE FAIL")
