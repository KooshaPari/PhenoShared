"""argmax_sample.mojo — Vocab-wide argmax sampler (Mojo 0.26, CPU-side).

This is the Mojo 0.26-compatible replacement for the original Metal-style
two-stage argmax+Gumbel kernel.  Per the task scope ("stay within the Mojo
stdlib's CPU-side capabilities — correctness > SIMD-tiling"), we drop:

  * the two-stage block reduction (gumbel_argmax_block / gumbel_argmax_reduce)
  * the Gumbel noise injection (the host can do that with numpy/mlx if needed)
  * the per-(b, v) LCG (no GPU state available)
  * all GPU-only primitives (gpu.thread_idx, gpu.block_idx, AddressSpace.SHARED,
    stack_allocation, barrier)

…and replace them with a single straight-line scan over the [B, V] logits
buffer.  The contract is still:

    [0] logits       [B, V]   half
    [1] out_token    [B]      int32

We keep the same buffer order so the Python orchestrator can dispatch either
the Metal fused sampler or this CPU reference without changing the call
site.

The Mojo 0.26 idioms used here:
  * `alloc[T](N)` from `std.memory` (replaces stack_allocation)
  * `p.free()` for explicit teardown (no implicit lifetime tracking)
  * `UnsafePointer[T, _]` / `UnsafePointer[T, MutAnyOrigin]` parameter
    conventions so the function is callable from Python ctypes
  * `Float16(Float32(v))` / `Float32(Float16(v))` explicit conversions
    (no implicit numeric promotion in 0.26)
"""

from std.memory import alloc


# ---------------------------------------------------------------------------
# Architecture constants — keep in lock-step with arch.yaml and
# qwen3_5_types.mojo.  Hardcoded here so this file builds standalone
# (no relative-import dependency on qwen3_5_types).
# ---------------------------------------------------------------------------

comptime kQwVocabSize: Int = 248320
comptime kQwFullHeads: Int = 8
comptime kQwFullKvHeads: Int = 2
comptime kQwFullHeadDim: Int = 256
comptime kQwFullHeadsPerKv: Int = 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


fn argmax_sample(
    logits: UnsafePointer[Float16, _],
    out_token: UnsafePointer[Int32, MutAnyOrigin],
    B: Int,
    V: Int,
) -> Int:
    """Vocab-wide argmax.  Returns 0 on success, non-zero on bad args.

    For each batch row, walks the V-dim logits row and writes the index
    of the largest value into ``out_token[b]``.  Ties go to the *lower*
    index (matches numpy.argmax's behaviour).
    """
    if B <= 0 or V <= 0:
        return 1
    for b in range(B):
        var row_base = b * V
        var best_val = logits[row_base]
        var best_idx: Int = 0
        for v in range(1, V):
            var cur = logits[row_base + v]
            if cur > best_val:
                best_val = cur
                best_idx = v
        out_token[b] = Int32(best_idx)
    return 0


# ---------------------------------------------------------------------------
# Self-test entry point
# ---------------------------------------------------------------------------
#
# Run with:
#     mojo build kernels/qwen3.5-0.8b/mojo/argmax_sample.mojo \
#         -o build/qwen3_5_argmax_sample
#     ./build/qwen3_5_argmax_sample
#
# The self-test allocates a small [4, 8] logits buffer with a known argmax
# at index 3 (and a duplicate at index 7) and prints the result.  We
# expect out_token = [3, 5, 0, 2].


fn main() raises:
    print("[argmax_sample] Mojo 0.26 CPU reference — vocab-wide argmax")
    var B: Int = 4
    var V: Int = 8

    # Allocate contiguous buffers (B*V halfs for logits; B int32 for output).
    var logits_buf = alloc[Float16](B * V)
    var out_buf = alloc[Int32](B)

    # Row 0: peak at v=3, duplicate (==) at v=7 — expect index 3.
    # Row 1: peak at v=5.
    # Row 2: all negative, peak at v=0.
    # Row 3: peak at v=2.
    # We seed logits_buf directly with explicit per-element writes since
    # InlineArray[T, N](v1, v2, ...) is not a supported 0.26 constructor.
    var src = alloc[Float16](B * V)
    src[0] = Float16(1.0)
    src[1] = Float16(2.0)
    src[2] = Float16(-1.0)
    src[3] = Float16(5.0)
    src[4] = Float16(3.0)
    src[5] = Float16(0.5)
    src[6] = Float16(-2.0)
    src[7] = Float16(5.0)
    src[8] = Float16(0.0)
    src[9] = Float16(0.0)
    src[10] = Float16(0.0)
    src[11] = Float16(0.0)
    src[12] = Float16(0.0)
    src[13] = Float16(9.0)
    src[14] = Float16(0.0)
    src[15] = Float16(1.0)
    src[16] = Float16(-0.5)
    src[17] = Float16(-1.5)
    src[18] = Float16(-2.0)
    src[19] = Float16(-3.0)
    src[20] = Float16(-4.0)
    src[21] = Float16(-5.0)
    src[22] = Float16(-6.0)
    src[23] = Float16(-7.0)
    src[24] = Float16(0.0)
    src[25] = Float16(0.0)
    src[26] = Float16(4.0)
    src[27] = Float16(0.0)
    src[28] = Float16(0.0)
    src[29] = Float16(0.0)
    src[30] = Float16(0.0)
    src[31] = Float16(0.0)
    for i in range(B * V):
        logits_buf[i] = src[i]
    src.free()

    var status = argmax_sample(logits_buf, out_buf, B, V)
    print("[argmax_sample] status:", status)

    var expected = alloc[Int32](B)
    expected[0] = Int32(3)
    expected[1] = Int32(5)
    expected[2] = Int32(0)
    expected[3] = Int32(2)
    var pass_count: Int = 0
    for b in range(B):
        var got = out_buf[b]
        var exp = expected[b]
        if got == exp:
            print("  row", b, "->", got, "(ok)")
            pass_count += 1
        else:
            print("  row", b, "->", got, "(FAIL, expected", exp, ")")
    print("[argmax_sample]", pass_count, "/", B, "rows correct")

    expected.free()
    logits_buf.free()
    out_buf.free()

    if pass_count == B:
        print("[argmax_sample] SMOKE OK")
    else:
        print("[argmax_sample] SMOKE FAIL")
