"""rmsnorm.mojo — RMSNorm for Qwen3.5 0.8B (Mojo polyglot binding).

Mirrors metal/norm.metal.  Per-row RMSNorm with weight + eps.

  out[b, h] = (x[b, h] / sqrt(mean(x[b, :]^2) + eps)) * w[h]

Buffer-arg contract (per task spec):
    [0] X       [B, H]   half   (input)
    [1] W       [H]      half   (learnable weight, gamma)
    [2] Y       [B, H]   half   (output)
    [3] B       uint     (batch)
    [4] H       uint     (hidden size, must equal kHiddenSize)
    [5] eps     float    (regularization, typically 1e-6)
"""

from gpu import thread_idx, block_idx, block_dim
from gpu.host import DeviceContext
from gpu.memory import AddressSpace
from layout import Layout, LayoutTensor
from math import sqrt

from .qwen3_5_types import (
    kHiddenSize,
    kRmsNormEps,
    kRuntimeBatch,
    qw_to_f16,
    qw_to_f32,
    warp_reduce_sum,
)


# Layouts — fixed at compile time.  X/Y use the runtime-batch
# placeholder; W is purely 1D over kHiddenSize (no batch dim).
comptime layout_x: Layout = Layout.row_major(kRuntimeBatch, kHiddenSize)
comptime layout_w: Layout = Layout.row_major(kHiddenSize)
comptime layout_y: Layout = Layout.row_major(kRuntimeBatch, kHiddenSize)


# Compile-time thread count for the per-row reduction.
# kHiddenSize = 1024 = 4 * 32 * 8 — pick 256 threads (4 warps) so each thread
# holds 4 fp32 partials and reduces via warp shuffles.
comptime kNormThreads: Int = 256
comptime kNormPerThread: Int = kHiddenSize // kNormThreads  # 4


@parameter
fn rmsnorm_kernel(
    X: LayoutTensor[DType.float16, layout_x, MutAnyOrigin],
    W: LayoutTensor[DType.float16, layout_w, MutAnyOrigin],
    Y: LayoutTensor[DType.float16, layout_y, MutAnyOrigin],
    B: UInt32,
    H: UInt32,
    eps: Float32,
):
    """RMSNorm kernel.  1 TG per row.  TG size = kNormThreads.

    Each thread owns kNormPerThread = 4 contiguous elements.  Reduction
    happens via warp shuffles (32-lane SIMD width).  The 4-warp reduction
    is done via shared memory.
    """
    var b = UInt32(block_idx.x)
    if b >= B:
        return

    var tid = UInt32(thread_idx.x)
    var lane = tid & 31
    var warp = tid >> 5

    # Per-thread partial sum of squares.
    var local_sq: Float32 = 0.0
    comptime for i in range(kNormPerThread):
        var d = tid * kNormPerThread + i
        var v = qw_to_f32(X[b, d])
        local_sq += v * v

    # Warp reduce.
    var w: Float32 = local_sq
    w = warp_reduce_sum(w)

    # Cross-warp via shared memory.
    var shmem = stack_allocation[8, Float32, address_space = AddressSpace.SHARED]()
    if lane == 0:
        shmem[warp] = w
    barrier()
    if warp == 0:
        var v: Float32 = 0.0
        if lane < 4:
            v = shmem[lane]
        v = warp_reduce_sum(v)
        if lane == 0:
            shmem[0] = v
    barrier()
    var mean_sq = shmem[0] / Float32(kHiddenSize)
    var inv_rms = 1.0 / sqrt(mean_sq + eps)

    # Apply weight + scale.
    comptime for i in range(kNormPerThread):
        var d = tid * kNormPerThread + i
        var x_v = qw_to_f32(X[b, d])
        var w_v = qw_to_f32(W[d])
        Y[b, d] = qw_to_f16(x_v * inv_rms * w_v)


fn rmsnorm(
    ctx: DeviceContext,
    X: LayoutTensor[DType.float16, layout_x, MutAnyOrigin],
    W: LayoutTensor[DType.float16, layout_w, MutAnyOrigin],
    Y: LayoutTensor[DType.float16, layout_y, MutAnyOrigin],
    B: UInt,
    eps: Float32 = kRmsNormEps,
) raises:
    """Launch rmsnorm_kernel on the device.  1 TG per row, kNormThreads each."""
    comptime H_const = UInt32(kHiddenSize)
    ctx.enqueue_function[rmsnorm_kernel, rmsnorm_kernel](
        X, W, Y, UInt32(B), H_const, eps,
        grid_dim=(B, 1, 1),
        block_dim=(kNormThreads, 1, 1),
    )
