// rope.metal — Multi-modal Rotary Position Embedding (M-RoPE) for Qwen3.5
// Qwen3.5 specifics:
//   - partial_rotary_factor = 0.25  →  only 32 dims of 256 are rotated
//   - mrope_interleaved = true      →  T/H/W sections interleaved across half
//   - mrope_section = [11, 11, 10]  →  32 = 11+11+10
//   - rope_theta = 10_000_000
//
// We pass position_ids[T,H,W] (3 position indices per token, same for text
// prefill, varying for image/video). For text-only prefill+decode, T=H=W=t.
//
// Algorithm (Qwen3_5TextRotaryEmbedding, mrope_interleaved=true):
//   for k in 0..D_rot/2:
//     m = k % 3
//     if m == 0: pos = pos_t
//     if m == 1: pos = pos_h
//     if m == 2: pos = pos_w
//     angle_k = pos * (1 / theta^(2k / D_rot))
//     c = cos(angle_k), s = sin(angle_k)
//     out[..., 2k]   = c * x[2k]   - s * x[2k+1]
//     out[..., 2k+1] = s * x[2k]   + c * x[2k+1]
//   remaining (head_dim - D_rot) dims are passed through.

#include <metal_stdlib>
#include "types.metal"
using namespace metal;

// ===========================================================================
// mrope_partial_inplace
//   In-place rotary on [B, S, H, D] where only the FIRST kRotDim=32 elements
//   of head_dim=256 are rotated.  The remaining 224 dims are passed through.
//
//   One threadgroup per (b, h), 16 threads (one per k in [0..D_rot/2)).
//   Each thread handles 1 (2-element) rotated pair.
//
// Buffers:
//   x           [B*S*H, D]   half, in/out
//   pos_ids     [B*S, 3]     i32   (T, H, W position ids)
//   B, S, H, D  scalars
// ===========================================================================

kernel void mrope_partial_inplace(
    device half* x                 [[buffer(0)]],
    const device int32_t* pos_ids   [[buffer(1)]],
    constant uint& B                [[buffer(2)]],
    constant uint& S                [[buffer(3)]],
    constant uint& H                [[buffer(4)]],
    constant uint& D                [[buffer(5)]],
    uint3 tgid                      [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint s = tgid.y;
    uint h = tgid.z;
    if (b >= B || s >= S || h >= H) return;

    int k = int(tid);
    if (k >= qwen::kRotDimHalf) return;

    int pos_t = pos_ids[(b * S + s) * 3 + 0];
    int pos_h = pos_ids[(b * S + s) * 3 + 1];
    int pos_w = pos_ids[(b * S + s) * 3 + 2];

    int sect = qw_mrope_section(k);
    int pos  = (sect == 0) ? pos_t : (sect == 1 ? pos_h : pos_w);

    // inv_freq[k] = 1 / (theta ^ (2*k / D_rot))
    float e   = (2.0f * float(k)) / float(qwen::kRotDim);
    float inv = qw_fast_inv(qw_fast_pow(qwen::kRopeTheta, e));
    float angle = float(pos) * inv;
    float c = qw_fast_cos(angle);
    float s_ = qw_fast_sin(angle);

    uint base = ((b * S + s) * H + h) * D;
    int idx0 = int(base) + 2 * k;
    int idx1 = idx0 + 1;

    float v0 = qw_to_f32(x[idx0]);
    float v1 = qw_to_f32(x[idx1]);
    x[idx0] = qw_to_f16(c * v0 - s_ * v1);
    x[idx1] = qw_to_f16(s_ * v0 + c * v1);
}

// ===========================================================================
// mrope_partial_decode
//   Single-token decode path: 1 threadgroup per (b, h), 16 threads.
//
// Buffers:
//   x           [B*H, D]     half  (single-token view: [B, 1, H, D])
//   pos_ids     [B, 3]       i32
// ===========================================================================

kernel void mrope_partial_decode(
    device half* x                 [[buffer(0)]],
    const device int32_t* pos_ids   [[buffer(1)]],
    constant uint& B                [[buffer(2)]],
    constant uint& H                [[buffer(3)]],
    constant uint& D                [[buffer(4)]],
    uint2 tgid                      [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint h = tgid.y;
    if (b >= B || h >= H) return;

    int k = int(tid);
    if (k >= qwen::kRotDimHalf) return;

    int pos_t = pos_ids[b * 3 + 0];
    int pos_h = pos_ids[b * 3 + 1];
    int pos_w = pos_ids[b * 3 + 2];
    int sect  = qw_mrope_section(k);
    int pos   = (sect == 0) ? pos_t : (sect == 1 ? pos_h : pos_w);

    float e   = (2.0f * float(k)) / float(qwen::kRotDim);
    float inv = qw_fast_inv(qw_fast_pow(qwen::kRopeTheta, e));
    float angle = float(pos) * inv;
    float c = qw_fast_cos(angle);
    float s_ = qw_fast_sin(angle);

    uint base = (b * H + h) * D;
    int idx0 = int(base) + 2 * k;
    int idx1 = idx0 + 1;
    float v0 = qw_to_f32(x[idx0]);
    float v1 = qw_to_f32(x[idx1]);
    x[idx0] = qw_to_f16(c * v0 - s_ * v1);
    x[idx1] = qw_to_f16(s_ * v0 + c * v1);
}

// ===========================================================================
// mrope_partial_decode_qk
//   Decode variant that takes Q and K separately (separate buffers, single
//   position broadcast per batch).  Used when Q and K are split tensors
//   after QKV projection.
// ===========================================================================

kernel void mrope_partial_decode_qk(
    device half* Q                  [[buffer(0)]],   // [B, H_q, D]
    device half* K                  [[buffer(1)]],   // [B, H_kv, D]
    const device int32_t* pos_ids   [[buffer(2)]],   // [B, 3]
    constant uint& B                [[buffer(3)]],
    constant uint& H_q              [[buffer(4)]],
    constant uint& H_kv             [[buffer(5)]],
    constant uint& D                [[buffer(6)]],
    uint3 tgid                      [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    // tgid.z encodes Q (0) or K (1) tensor selection.
    bool is_q = (tgid.z == 0);
    uint b = tgid.x;
    uint h = tgid.y;
    uint H = is_q ? H_q : H_kv;
    if (b >= B || h >= H) return;

    int k = int(tid);
    if (k >= qwen::kRotDimHalf) return;

    int pos_t = pos_ids[b * 3 + 0];
    int pos_h = pos_ids[b * 3 + 1];
    int pos_w = pos_ids[b * 3 + 2];
    int sect  = qw_mrope_section(k);
    int pos   = (sect == 0) ? pos_t : (sect == 1 ? pos_h : pos_w);

    float e   = (2.0f * float(k)) / float(qwen::kRotDim);
    float inv = qw_fast_inv(qw_fast_pow(qwen::kRopeTheta, e));
    float angle = float(pos) * inv;
    float c = qw_fast_cos(angle);
    float s_ = qw_fast_sin(angle);

    device half* x = is_q ? Q : K;
    uint base = (b * H + h) * D;
    int idx0 = int(base) + 2 * k;
    int idx1 = idx0 + 1;
    float v0 = qw_to_f32(x[idx0]);
    float v1 = qw_to_f32(x[idx1]);
    x[idx0] = qw_to_f16(c * v0 - s_ * v1);
    x[idx1] = qw_to_f16(s_ * v0 + c * v1);
}
