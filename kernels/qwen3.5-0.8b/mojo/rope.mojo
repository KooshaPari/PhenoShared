"""rope.mojo — M-RoPE for Qwen3.5 0.8B (Mojo polyglot binding).

Mirrors metal/rope.metal.  Partial rotary on the first kRotDim=32 dims
(partial_rotary_factor=0.25), with M-RoPE's interleaved (T, H, W) sections.

Buffer-arg contract (per task spec):
    [0] Q              [B, S, H_q, D]   half
    [1] K              [B, S, H_kv, D]  half
    [2] freqs_cis      [S, rot_dim/2, 2] half  (cos, sin packed)
    [3] Q_out          [B, S, H_q, D]   half
    [4] K_out          [B, S, H_kv, D]  half
    [5] B              uint
    [6] S              uint
    [7] H_q            uint
    [8] H_kv           uint
    [9] D              uint
"""

from gpu import thread_idx, block_idx, block_dim
from gpu.host import DeviceContext
from gpu.memory import AddressSpace
from layout import Layout, LayoutTensor

from .qwen3_5_types import (
    kFullHeadDim,
    kRotDim,
    kRotDimHalf,
    kRuntimeBatch,
    kRuntimeSeq,
    qw_to_f16,
    qw_to_f32,
    qw_mrope_section,
)


# Per-token work: 32 threads cover the 32 rot dims (one per dim).
# 1 TG per (b, s, head).  Threads 0..31 each apply their share.
# kRotDim = kMRopeSectionT + kMRopeSectionH + kMRopeSectionW = 32, so
# every thread lands in the in-range path of qw_mrope_section().
comptime kRopeThreads: Int = 32


@parameter
fn rope_kernel(
    Q: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    K: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    freqs_cis: LayoutTensor[DType.float16, layout_3d, MutAnyOrigin],
    Q_out: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    K_out: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    B: UInt32,
    S: UInt32,
    H_q: UInt32,
    H_kv: UInt32,
    D: UInt32,
):
    """M-RoPE kernel.  1 TG per (b, s, head), 32 threads.

    Each thread applies the rotation to one (pair) of the rot dims.  We
    only touch the first kRotDim=32 dims of D=256; the rest is copied
    through unchanged by the host.  For dims i in [0, kRotDimHalf) and i
    in [kRotDimHalf, kRotDim), we pair (i, i + kRotDimHalf).
    """
    var b = UInt32(block_idx.x)
    var s = UInt32(block_idx.y)
    var h = UInt32(block_idx.z)
    if b >= B or s >= S:
        return
    # h is the combined head index across Q and K (host launches grid
    # with z = H_q + H_kv).  We split Q-heads from K-heads on the fly
    # so the host doesn't have to launch two separate grids.
    var h_total = H_q + H_kv
    if h >= h_total:
        return
    var is_q = h < H_q
    var head = h - (0 if is_q else H_q)

    var tid = UInt32(thread_idx.x)
    if tid >= 32:
        return

    # M-RoPE frequency: each dim index i in [0, kRotDim) maps to one of
    # the three sections (T, H, W) via mod-3.  The host pre-computed
    # freqs_cis with the per-section frequency table, so the per-section
    # index is *implicit* in `freqs_cis` — we compute `section` here to
    # mirror the metal/rope.metal pattern (so visual diffs stay 1:1)
    # but it does not affect the rotation itself.
    var i = Int(tid)
    var section = qw_mrope_section(i)

    # Read cos/sin for this dim, this token.
    var cos_v = qw_to_f32(freqs_cis[s, i, 0])
    var sin_v = qw_to_f32(freqs_cis[s, i, 1])

    # Pair index for the half-rotation.
    var j: Int
    if i < kRotDimHalf:
        j = i + kRotDimHalf
    else:
        j = i - kRotDimHalf

    # Read x[..., i] and x[..., j].  Apply rotation.  Q and K are
    # separate buffers with different head dims (H_q vs H_kv) and
    # different bases, so we dispatch on is_q:
    #   is_q=true  -> read Q, write Q_out
    #   is_q=false -> read K, write K_out
    # The `base` offset uses the per-buffer head count, so it must be
    # selected per-head as well.
    var x_i: Float32
    var x_j: Float32
    var base: UInt32
    if is_q:
        base = ((b * S + s) * H_q + head) * D
        x_i = qw_to_f32(Q[base + UInt32(i)])
        x_j = qw_to_f32(Q[base + UInt32(j)])
    else:
        base = ((b * S + s) * H_kv + head) * D
        x_i = qw_to_f32(K[base + UInt32(i)])
        x_j = qw_to_f32(K[base + UInt32(j)])

    var new_i = x_i * cos_v - x_j * sin_v
    var new_j = x_i * sin_v + x_j * cos_v

    # Write back to the *output* buffer.  In-place updates of Q/K would
    # corrupt the input (the host passes separate Q_out/K_out buffers
    # precisely so a follow-up layer can read the rotated activations
    # without aliasing the input).
    if is_q:
        Q_out[base + UInt32(i)] = qw_to_f16(new_i)
        Q_out[base + UInt32(j)] = qw_to_f16(new_j)
    else:
        K_out[base + UInt32(i)] = qw_to_f16(new_i)
        K_out[base + UInt32(j)] = qw_to_f16(new_j)

    # NOTE: non-rot dims (D - kRotDim = 224 per head) are passed through
    # by the host-side Python codegen's separate pass; the kernel here
    # only touches the first kRotDim=32 dims.  See
    # python/codegen.py::rope_pass_through for the copy-through step.
    # `section` is computed to mirror the metal/rope.metal pattern but
    # the actual rotation is independent of which M-RoPE section `i`
    # belongs to (the per-section frequency is already baked into
    # `freqs_cis`), so it is referenced only via `section` to keep the
    # tuple of `(i, section)` visible in stack traces.
    _ = section


fn rope(
    ctx: DeviceContext,
    Q: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    K: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    freqs_cis: LayoutTensor[DType.float16, layout_3d, MutAnyOrigin],
    Q_out: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    K_out: LayoutTensor[DType.float16, layout_4d, MutAnyOrigin],
    B: UInt,
    S: UInt,
    H_q: UInt,
    H_kv: UInt,
) raises:
    """Launch rope_kernel.  Grid = (B, S, H_q + H_kv), block = 32."""
    comptime D = UInt32(kFullHeadDim)
    ctx.enqueue_function[rope_kernel, rope_kernel](
        Q, K, freqs_cis, Q_out, K_out, UInt32(B), UInt32(S), UInt32(H_q), UInt32(H_kv), D,
        grid_dim=(B, S, H_q + H_kv),
        block_dim=(kRopeThreads, 1, 1),
    )


# Layout helpers
# --------------
# Q/K buffers are [B, S, H_*, D].  The first two dims are runtime; the
# third (head) dim is a literal `1` because this kernel processes a
# single head per launch — the host launches the grid (B, S, H_q+H_kv)
# and passes each head separately, so the kernel never indexes into the
# head dim via LayoutTensor (manual offset arithmetic instead).  freqs_cis
# is [S, rot_dim, 2] — only S is runtime.
comptime layout_4d: Layout = Layout.row_major(kRuntimeBatch, kRuntimeSeq, 1, kFullHeadDim)
comptime layout_3d: Layout = Layout.row_major(kRuntimeSeq, kRotDim, 2)


# NOTE on build_mrope_freq_table
# -----------------------------
# The pre-computed cos/sin table for M-RoPE ([S, kRotDim, 2]) is *not*
# built by the Mojo side at all.  The Python codegen (python/codegen.py)
# produces it once at session-start time and hands the kernel a static
# tensor.  The Mojo kernel expects the host to have already filled
# `freqs_cis`; see Metal equivalent in metal/rope.metal::rope_helper
# (the same `freps_cis[s, i, {0,1}]` indexing is used here).
