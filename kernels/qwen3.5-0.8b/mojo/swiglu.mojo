"""swiglu.mojo — SwiGLU MLP activation for Qwen3.5 0.8B (Mojo polyglot binding).

Mirrors metal/activation.metal.  Elementwise:
    y = silu(gate) * up

Where silu(x) = x * sigmoid(x).

Buffer-arg contract (per task spec):
    [0] gate       [B*S, I]   half   (gate projection)
    [1] up         [B*S, I]   half   (up projection)
    [2] out        [B*S, I]   half   (output)
    [3] N          uint              (total elements = B*S*I)
"""

from gpu import thread_idx, block_idx, block_dim
from gpu.host import DeviceContext
from gpu.memory import AddressSpace
from layout import Layout, LayoutTensor
from math import exp

from .qwen3_5_types import (
    kRuntimeFlat,
    qw_to_f16,
    qw_to_f32,
    qw_fast_silu,
)


# 4-wide vectorized loads/stores.  1 TG = 256 threads = 1024 fp16 / TG.
comptime kGluThreads: Int = 256
comptime kGluVecWidth: Int = 4  # half4 = 8 bytes per load


# 1D elementwise layout.  kRuntimeFlat=1 is the static placeholder for
# the runtime N = B*S*I size; see qwen3_5_types.mojo §"Static dim
# convention" for the rationale.
comptime layout_1d: Layout = Layout.row_major(kRuntimeFlat)


@parameter
fn swiglu_kernel(
    gate: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    up: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    output_buf: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    N: UInt32,
):
    """SwiGLU kernel.  1 TG per kGluThreads*kGluVecWidth = 1024 elements."""
    var block_id = UInt32(block_idx.x)
    var tid = UInt32(thread_idx.x)

    var base = (block_id * kGluThreads + tid) * kGluVecWidth
    if base + kGluVecWidth - 1 >= N:
        return

    # Vectorized 4-wide load via LayoutTensor SIMD gather.
    var g_v = gate.load[width=kGluVecWidth](base)
    var u_v = up.load[width=kGluVecWidth](base)

    var o_v: SIMD[DType.float16, kGluVecWidth]
    for i in range(kGluVecWidth):
        var g_f = qw_to_f32(g_v[i])
        var u_f = qw_to_f32(u_v[i])
        var s = qw_fast_silu(g_f)
        o_v[i] = qw_to_f16(s * u_f)

    output_buf.store(base, o_v)


fn swiglu(
    ctx: DeviceContext,
    gate: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    up: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    output_buf: LayoutTensor[DType.float16, layout_1d, MutAnyOrigin],
    N: UInt,
) raises:
    """Launch swiglu_kernel.  Grid = ceil(N / (kGluThreads * kGluVecWidth))."""
    var per_block = UInt32(kGluThreads) * UInt32(kGluVecWidth)
    var n_blocks: UInt = (N + UInt(per_block) - 1) // UInt(per_block)
    ctx.enqueue_function[swiglu_kernel, swiglu_kernel](
        gate, up, output_buf, UInt32(N),
        grid_dim=(n_blocks, 1, 1),
        block_dim=(kGluThreads, 1, 1),
    )
