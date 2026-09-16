// norm.metal — RMSNorm + QKNorm kernels for Qwen3.5 0.8B
// Target: Apple Silicon M-series, Metal 3+.
//
// Activations: fp16 (half). Accumulation: fp32. State kept in registers
// plus a small threadgroup scratch pad for the simd reduction.
//
// Two flavors:
//   - RMSNorm (pre-norm with optional residual) — used by every layer
//   - QKNorm  (L2-normalize along head_dim)      — used by Qwen3.5 attention
//                                                   after RoPE; this is the
//                                                   q_norm / k_norm on the
//                                                   RoPE-rotated head_dim.

#include <metal_stdlib>
#include <metal_simdgroup>
#include "types.metal"
using namespace metal;

// ===========================================================================
// RMSNorm
// ===========================================================================
//
//   out = (x * rsqrt(mean(x^2) + eps)) * weight
//   Optional pre-norm residual:  x_eff = residual + x
//
// Grid:  one threadgroup per (b, s) row.  Threadgroup size = TG.
//
// Templated on (Hidden, TG) so we can specialize for the few sizes we use
// (1024 for hidden, 256 for per-head norm, etc.).
//
// Implementation note: threadgroup scratch must be declared at kernel scope
// (MSL rule — `threadgroup` storage class is not allowed inside non-qualified
// device functions).  The `run` helper takes a `threadgroup float*` and is
// driven from each kernel entry, which owns its scratch buffer.
// ===========================================================================

template <int Hidden, int TG>
struct RmsNormT {
    static_assert(Hidden % TG == 0, "Hidden must be a multiple of TG");
    static_assert(TG % QW_SIMD_WIDTH == 0, "TG must be a multiple of 32");
    // Note: kVec = Hidden / TG is a compile-time constant; we use the
    // expression directly to avoid MSL's restriction on address-space-
    // qualified struct members.

    static void run(const device half* x,
                    const device half* residual,    // nullable
                    const device half* weight,      // nullable
                    device half* out,
                    threadgroup float* warp_sums,   // size: TG / 32
                    uint rows,
                    float eps,
                    uint tgid,
                    uint tid) {
        uint row = tgid;
        if (row >= rows) return;

        const device half* x_row = x + uint(row) * Hidden;
        device half* out_row     = out + uint(row) * Hidden;
        const device half* r_row  = (residual != nullptr)
                                    ? (residual + uint(row) * Hidden) : nullptr;

        // ---- pass 1: sum of squares ----
        float ssq = 0.0f;
        for (int i = 0; i < (Hidden / TG); ++i) {
            int idx = tid + i * TG;
            float v = qw_to_f32(x_row[idx]);
            if (r_row) v += qw_to_f32(r_row[idx]);
            ssq += v * v;
        }
        // Cross-lane reduction: warp simd_sum first, then a tree over warps.
        ssq = simd_sum(ssq);
        uint warp_id = tid >> 5;        // /32
        uint lane    = tid & 31;        // %32
        if (TG > QW_SIMD_WIDTH) {
            if (lane == 0) warp_sums[warp_id] = ssq;
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (warp_id == 0) {
                float v = (lane < (TG / QW_SIMD_WIDTH)) ? warp_sums[lane] : 0.0f;
                v = simd_sum(v);
                if (lane == 0) warp_sums[0] = v;
            }
            threadgroup_barrier(mem_flags::mem_threadgroup);
            ssq = warp_sums[0];
        }

        float inv_rms = qw_fast_rsqrt(ssq / float(Hidden) + eps);

        // ---- pass 2: scale + weight + write ----
        for (int i = 0; i < (Hidden / TG); ++i) {
            int idx = tid + i * TG;
            float v = qw_to_f32(x_row[idx]);
            if (r_row) v += qw_to_f32(r_row[idx]);
            v = v * inv_rms;
            if (weight) v *= qw_to_f32(weight[idx]);
            out_row[idx] = qw_to_f16(v);
        }
    }
};

// ---- public kernels ----

// Standard hidden_size=1024 RMSNorm, with optional residual, 1024-thread TG.
kernel void rmsnorm_h1024(
    const device half* x           [[buffer(0)]],
    const device half* residual    [[buffer(1)]],   // nullable
    const device half* weight      [[buffer(2)]],   // nullable
    device half* out               [[buffer(3)]],
    constant uint& rows            [[buffer(4)]],   // B * S
    constant float& eps            [[buffer(5)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    threadgroup float warp_sums[1024 / 32];
    RmsNormT<1024, 1024>::run(x, residual, weight, out, warp_sums,
                              rows, eps, tgid, tid);
}

// Smaller-tile variant (256 thread TG) for cases where TG=1024 is too big.
kernel void rmsnorm_h1024_small_tg(
    const device half* x           [[buffer(0)]],
    const device half* residual    [[buffer(1)]],
    const device half* weight      [[buffer(2)]],
    device half* out               [[buffer(3)]],
    constant uint& rows            [[buffer(4)]],
    constant float& eps            [[buffer(5)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    threadgroup float warp_sums[256 / 32];
    RmsNormT<1024, 256>::run(x, residual, weight, out, warp_sums,
                             rows, eps, tgid, tid);
}

// Final RMSNorm before logits (no residual).
kernel void rmsnorm_final(
    const device half* x           [[buffer(0)]],
    const device half* weight      [[buffer(1)]],
    device half* out               [[buffer(2)]],
    constant uint& rows            [[buffer(3)]],
    constant float& eps            [[buffer(4)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    threadgroup float warp_sums[1024 / 32];
    RmsNormT<1024, 1024>::run(x, nullptr, weight, out, warp_sums,
                              rows, eps, tgid, tid);
}

// ===========================================================================
// QKNorm — per-head L2 normalization on RoPE-rotated head_dim=256
// ===========================================================================
//
//   out = x * rsqrt(mean(x^2) + eps)   (no learnable weight, no residual)
//
// Operates on the LAST 256 dims of each row (the rotated-and-normed slice).
// This matches Qwen3.5's `q_norm` / `k_norm` layout where the head_dim is
// 256 and the rotary section is just the first 32 dims; the norm runs over
// the full 256.
//
// Grid: one threadgroup per (b, s, h).
// ===========================================================================

template <int HeadDim, int TG>
struct QkNormT {
    static_assert(HeadDim == 256, "QKNorm specialized for HeadDim=256");
    static_assert(HeadDim % TG == 0, "HeadDim must be a multiple of TG");
    static_assert(TG % QW_SIMD_WIDTH == 0, "TG must be a multiple of 32");
    // kVec = HeadDim / TG is a compile-time constant; we use the expression
    // directly to avoid MSL's restriction on address-space-qualified struct
    // members.

    static void run(const device half* x,
                    device half* out,
                    threadgroup float* warp_sums,
                    uint tgid,
                    uint tid) {
        const device half* x_row = x + uint(tgid) * HeadDim;
        device half* out_row     = out + uint(tgid) * HeadDim;

        float ssq = 0.0f;
        for (int i = 0; i < (HeadDim / TG); ++i) {
            int idx = tid + i * TG;
            float v = qw_to_f32(x_row[idx]);
            ssq += v * v;
        }
        ssq = simd_sum(ssq);
        uint warp_id = tid >> 5;
        uint lane    = tid & 31;
        if (TG > QW_SIMD_WIDTH) {
            if (lane == 0) warp_sums[warp_id] = ssq;
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (warp_id == 0) {
                float v = (lane < (TG / QW_SIMD_WIDTH)) ? warp_sums[lane] : 0.0f;
                v = simd_sum(v);
                if (lane == 0) warp_sums[0] = v;
            }
            threadgroup_barrier(mem_flags::mem_threadgroup);
            ssq = warp_sums[0];
        }
        float inv_rms = qw_fast_rsqrt(ssq / float(HeadDim) + 1e-6f);
        for (int i = 0; i < (HeadDim / TG); ++i) {
            int idx = tid + i * TG;
            out_row[idx] = qw_to_f16(qw_to_f32(x_row[idx]) * inv_rms);
        }
    }
};

// QKNorm on 4D tensor [B, S, H, D=256] — q_norm and k_norm use this.
kernel void qknorm_4d(
    const device half* x           [[buffer(0)]],   // [B*S*H, 256]
    device half* out               [[buffer(1)]],
    constant uint& rows            [[buffer(2)]],   // B*S*H
    constant float& eps            [[buffer(3)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    threadgroup float warp_sums[256 / 32];
    QkNormT<256, 256>::run(x, out, warp_sums, tgid, tid);
    (void)rows;  // unused: row count encoded in grid
    (void)eps;   // unused: eps hard-coded inside run() for safety
}

// In-place QKNorm variant.
kernel void qknorm_4d_inplace(
    device half* x                 [[buffer(0)]],
    constant uint& rows            [[buffer(1)]],
    constant float& eps            [[buffer(2)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    threadgroup float warp_sums[256 / 32];
    QkNormT<256, 256>::run(x, x, warp_sums, tgid, tid);
    (void)rows;
    (void)eps;
}
