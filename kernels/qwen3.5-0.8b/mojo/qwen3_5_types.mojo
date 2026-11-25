"""qwen3_5_types.mojo — shared types, constants, and helpers for Qwen3.5 0.8B Mojo kernels.

Mirrors metal/types.metal so the host can dispatch either Metal or Mojo
transparently.  All numeric constants must stay in sync with arch.yaml and
include/qwen3_5.h — edit only via codegen.

Buffer-arg contract (per task spec, applies to every kernel in this lib):
    [0] in1   (input, fp16)
    [1] out   (output)
    [2] w     (weight/bias; may be null)
    [3] aux   (auxiliary: state, cache, mask, etc.)
    [4..N] dims / scalars (uint, float)

Activations / weights: `DType.float16`.  Accumulation: `DType.float32`.
"""

from std.gpu.host import DeviceContext
from std.gpu.memory import AddressSpace
from layout import Layout
from std.utils import StaticTuple
from std.collections import InlineArray
from std.gpu.primitives.warp import shuffle_xor
from std.sys import size_of
from math import exp, log, cos, sin, sqrt


# ---------------------------------------------------------------------------
# Architecture constants
# ---------------------------------------------------------------------------

comptime kVocabSize: Int = 248320
comptime kHiddenSize: Int = 1024
comptime kIntermediateSize: Int = 3584
comptime kNumHiddenLayers: Int = 24
comptime kRmsNormEps: Float32 = 1.0e-6

comptime kFullHeads: Int = 8
comptime kFullKvHeads: Int = 2
comptime kFullHeadDim: Int = 256
comptime kFullQDim: Int = 2048           # 8 * 256
comptime kFullKvDim: Int = 512           # 2 * 256
comptime kFullQkvDim: Int = 3072         # 2048 + 2*512
comptime kFullHeadsPerKv: Int = 4
comptime kFullAttnInterval: Int = 4
comptime kFullAttnNumLayers: Int = 6

comptime kRotDim: Int = 32
comptime kRotDimHalf: Int = 16
comptime kRopeTheta: Float32 = 10_000_000.0
comptime kMRopeSectionT: Int = 11
comptime kMRopeSectionH: Int = 11
comptime kMRopeSectionW: Int = 10

comptime kLinKeyHeads: Int = 16
comptime kLinValueHeads: Int = 16
comptime kLinKeyHeadDim: Int = 128
comptime kLinValueHeadDim: Int = 128
comptime kLinConvKernel: Int = 4
comptime kLinNumLayers: Int = 18
comptime kLinStateElements: Int = kLinKeyHeads * kLinValueHeads * kLinValueHeadDim * kLinKeyHeadDim

# Static initializer for the Mojo-level list of full-attention layer indices.
# The contract is: layers whose 0-based index is in this list use the
# full-attention (Qwen3-style MHA) path; the rest use linear attention
# (Qwen3.5 hybrid).  Indices must match arch.yaml and metal/types.metal.
comptime kFullAttnIndicesInit: InlineArray[Int, 6] = _build_full_attn_indices()
fn _build_full_attn_indices() -> InlineArray[Int, 6]:
    comptime _vals = (3, 7, 11, 15, 19, 23)
    var arr = InlineArray[Int, 6](uninitialized=True)
    comptime for i in range(6):
        arr[i] = _vals[i]
    return arr


# Bundle of every constant in one struct, mirroring the metal ModelConstants
# struct so the host can pass it as a single argument.  This is the *only*
# type-level surface we expose for cross-language constant passing — the
# comptime constants above are the canonical source of truth within Mojo,
# and this struct re-states them as runtime values for FFI callers (the
# host Python / Pony / Nim / Rust code) that cannot read Mojo's comptime
# scope.  Do not edit any field without also updating the comptime
# constants above (and arch.yaml); see docs/TOOLCHAINS.md §1.2.
struct ModelConstants:
    var vocab_size: Int
    var hidden_size: Int
    var intermediate_size: Int
    var num_hidden_layers: Int
    var rms_norm_eps: Float32

    var full_heads: Int
    var full_kv_heads: Int
    var full_head_dim: Int
    var full_q_dim: Int
    var full_kv_dim: Int
    var full_qkv_dim: Int
    var full_heads_per_kv: Int
    var full_attn_interval: Int
    var full_attn_num_layers: Int

    var rot_dim: Int
    var rot_dim_half: Int
    var rope_theta: Float32
    var mrope_section_t: Int
    var mrope_section_h: Int
    var mrope_section_w: Int

    var lin_key_heads: Int
    var lin_value_heads: Int
    var lin_key_head_dim: Int
    var lin_value_head_dim: Int
    var lin_conv_kernel: Int
    var lin_num_layers: Int
    var lin_state_elements: Int

    var full_attn_indices: InlineArray[Int, 6]

    fn __init__(out self):
        """Default-init from the canonical Mojo comptime constants.

        Mojo 0.26 requires an explicit ``__init__`` for structs with
        ``var`` fields (no auto-generated constructor).  This pulls every
        field from the comptime constants at the top of this file so
        MODEL stays in lock-step with arch.yaml.
        """
        self.vocab_size = kVocabSize
        self.hidden_size = kHiddenSize
        self.intermediate_size = kIntermediateSize
        self.num_hidden_layers = kNumHiddenLayers
        self.rms_norm_eps = kRmsNormEps

        self.full_heads = kFullHeads
        self.full_kv_heads = kFullKvHeads
        self.full_head_dim = kFullHeadDim
        self.full_q_dim = kFullQDim
        self.full_kv_dim = kFullKvDim
        self.full_qkv_dim = kFullQkvDim
        self.full_heads_per_kv = kFullHeadsPerKv
        self.full_attn_interval = kFullAttnInterval
        self.full_attn_num_layers = kFullAttnNumLayers

        self.rot_dim = kRotDim
        self.rot_dim_half = kRotDimHalf
        self.rope_theta = kRopeTheta
        self.mrope_section_t = kMRopeSectionT
        self.mrope_section_h = kMRopeSectionH
        self.mrope_section_w = kMRopeSectionW

        self.lin_key_heads = kLinKeyHeads
        self.lin_value_heads = kLinValueHeads
        self.lin_key_head_dim = kLinKeyHeadDim
        self.lin_value_head_dim = kLinValueHeadDim
        self.lin_conv_kernel = kLinConvKernel
        self.lin_num_layers = kLinNumLayers
        self.lin_state_elements = kLinStateElements

        self.full_attn_indices = kFullAttnIndicesInit


comptime MODEL: ModelConstants = ModelConstants()


# ---------------------------------------------------------------------------
# SIMD helpers — Apple M-series SIMD width is 32 lanes
# ---------------------------------------------------------------------------

comptime QW_SIMD_WIDTH: Int = 32
comptime QW_KVEC4: Int = 4


# ---------------------------------------------------------------------------
# Numerical helpers — fast-math on Apple Silicon (hardware reciprocal
# approximation is well within fp16 mantissa precision for inference).
# ---------------------------------------------------------------------------

fn qw_to_f32(v: Float16) -> Float32:
    return v.cast[DType.float32]()


fn qw_to_f16(v: Float32) -> Float16:
    return v.cast[DType.float16]()


fn qw_fast_exp(x: Float32) -> Float32:
    # Hardware fast-exp — Mojo maps this to metal::fast::exp.
    return exp(x)


fn qw_fast_log(x: Float32) -> Float32:
    return log(x)


fn qw_fast_sigmoid(x: Float32) -> Float32:
    return 1.0 / (1.0 + exp(-x))


fn qw_fast_silu(x: Float32) -> Float32:
    return x * qw_fast_sigmoid(x)


fn qw_fast_cos(x: Float32) -> Float32:
    return cos(x)


fn qw_fast_sin(x: Float32) -> Float32:
    return sin(x)


fn qw_fast_rsqrt(x: Float32) -> Float32:
    return 1.0 / sqrt(x)


fn qw_mrope_section(k: Int) -> Int:
    """Section picker for M-RoPE (interleaved).  mod-3 mapping.

    Returns 0 (T), 1 (H), or 2 (W).  IMPORTANT: must be mod-3, not mod-4:
    ``k & 3`` would be a bitwise mask on the low 2 bits, yielding the
    sequence [0,1,2,3,0,1,2,3,...] (the 3 collides with the W fallback).
    The correct sequence for Qwen3.5 M-RoPE is [0,1,2,0,1,2,...], which
    matches metal/types.metal::qw_mrope_section exactly:

        m = k - 3 * (k / 3)
    """
    var m = k - 3 * (k // 3)
    if m == 0:
        return 0  # T section
    if m == 1:
        return 1  # H section
    return 2      # W section


# ---------------------------------------------------------------------------
# Warp-level reductions (shared across kernels)
# ---------------------------------------------------------------------------
# Apple M-series SIMD width is 32 lanes.  We expose two helpers — a
# butterfly sum and a paired (score, index) argmax — that map directly
# to MSL's `simd_sum` / `simd_max` patterns.  Both helpers rely on
# `std.gpu.primitives.warp.shuffle_xor` (the canonical Mojo 0.26
# location, where shuffle_xor lowers to llvm.air.simd_shuffle_xor on
# Apple GPUs) so they preserve the same numerical pattern as the Metal
# port.
#
# IMPORTANT: Float32 in Mojo IS `SIMD[DType.float32, 1]`, so calling
# `shuffle_xor(x, mask)` on a Float32 is well-typed — the result is
# also SIMD[1] = Float32.  The reduction is closed under addition.
#
# These functions must be called only from kernel-device code (i.e.
# inside a `@parameter fn ...` body that has been launched via
# `ctx.enqueue_function[...]`); they have no CPU-side semantics because
# shuffle_xor is a GPU-only intrinsic.

@always_inline("nodebug")
fn warp_reduce_sum(v: Float32) -> Float32:
    """Warp-butterfly sum across 32 lanes.  Matches MSL's `simd_sum`."""
    from std.gpu.primitives.warp import shuffle_xor
    var x = v
    x += Float32(shuffle_xor(x, UInt32(16)))
    x += Float32(shuffle_xor(x, UInt32(8)))
    x += Float32(shuffle_xor(x, UInt32(4)))
    x += Float32(shuffle_xor(x, UInt32(2)))
    x += Float32(shuffle_xor(x, UInt32(1)))
    return x


@always_inline("nodebug")
fn warp_reduce_argmax(s: Float32, x: Int32) -> Tuple[Float32, Int32]:
    """Warp-butterfly argmax across 32 lanes.  Returns (score, idx).

    The score and index are shuffled in lockstep so the index of the
    winning lane always travels with the winning score.  Matches the
    MSL `metal::simd_max` + index-tracking pattern.
    """
    from std.gpu.primitives.warp import shuffle_xor
    var s_cur = s
    var x_cur = x
    var masks = StaticTuple[Int, 5](16, 8, 4, 2, 1)
    comptime kWarpArgmaxSteps: Int = 5
    for i in range(kWarpArgmaxSteps):
        var mask = masks[i]
        var s2 = Float32(shuffle_xor(s_cur, UInt32(mask)))
        var x2 = Int32(shuffle_xor(x_cur, UInt32(mask)))
        if s2 > s_cur:
            s_cur = s2
            x_cur = x2
    return (s_cur, x_cur)


# ---------------------------------------------------------------------------
# Layout helpers — pass-through row-major
#
# Static dim convention
# ---------------------
# Mojo's `LayoutTensor` types the shape at compile time.  Dimensions that
# vary at run-time (batch, sequence length, paging blocks) cannot be
# represented as `Int` literals in the layout, so we use *named*
# comptime placeholders that document the convention rather than bare
# `1`s scattered across the kernel files.  Every kernel that needs a
# runtime-sized leading dim should pull the placeholder in from this
# module instead of inlining `Layout.row_major(1, ...)` etc.
#
# The numerical value `1` is intentional: Mojo layouts only care about
# the *stride pattern*, not the static size, when the host passes a
# `LayoutTensor` with the real shape.  We pick `1` (not `UNKNOWN`) so
# the layout is concrete at compile time and the SIMD load/store widths
# can still be inferred.
# ---------------------------------------------------------------------------

# Named runtime-dim placeholders.  Import these into a kernel file as:
#
#     from .qwen3_5_types import (
#         kRuntimeBatch, kRuntimeSeq, kRuntimePagedBlocks, kRuntimeFlat,
#     )
comptime kRuntimeBatch: Int = 1        # batch dim B     (runtime)
comptime kRuntimeSeq: Int = 1          # sequence dim S  (runtime, e.g. KV S_max)
comptime kRuntimePagedBlocks: Int = 1  # KV paging block count (runtime)
comptime kRuntimeFlat: Int = 1         # 1D elementwise (runtime N)


comptime layout_2d_n_h: Layout = Layout.row_major(kRuntimeBatch, kHiddenSize)
comptime layout_1d_h: Layout = Layout.row_major(kHiddenSize)
comptime layout_1d_flat: Layout = Layout.row_major(kRuntimeFlat)
