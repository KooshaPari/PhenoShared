// fused_l2norm.metal — lightweight L2 normalization for sampling scaling.
//
// Used by the host sampler to normalize a per-row logit vector before
// temperature scaling:  y = x / ||x||_2.  Single-pass, in-place optional.
//
// Layout:
//   X [B, N]  half, row-major, leading dim N
//   Y [B, N]  half, row-major, leading dim N   (Y can alias X for in-place)
//
// Args (per task contract — fixed order input/output/aux/dims):
//   buffer(0)  X  (in)
//   buffer(1)  Y  (out, may alias X)
//   buffer(2)  B  (uint)
//   buffer(3)  N  (uint)
//   buffer(4)  eps (float, optional regularization)
//
// Strategy: 1 TG per row.  TG size 256; each thread owns N/256 elements.
//   Pass 1: compute per-row sum of squares -> 1/N + eps regularization
//   Pass 2: divide by sqrt(...)

#include <metal_stdlib>
#include <metal_simdgroup>
#include "types.metal"
using namespace metal;

constant int kL2TgSize = 256;

kernel void fused_l2norm(
    const device half* X           [[buffer(0)]],
    device half* Y                 [[buffer(1)]],
    constant uint& B               [[buffer(2)]],
    constant uint& N               [[buffer(3)]],
    constant float& eps            [[buffer(4)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    uint b = tgid;
    if (b >= B) return;

    threadgroup float tg_sum_sq[kL2TgSize];

    // ---- pass 1: sum of squares ----
    float local_sum_sq = 0.0f;
    for (uint n = tid; n < N; n += kL2TgSize) {
        float v = static_cast<float>(X[b * N + n]);
        local_sum_sq += v * v;
    }
    local_sum_sq = simd_sum(local_sum_sq);
    tg_sum_sq[tid] = local_sum_sq;
    threadgroup_barrier(mem_flags::mem_threadgroup);
    if (tid < 32) {
        float v = 0.0f;
        for (int i = 0; i < kL2TgSize / 32; ++i) {
            v += tg_sum_sq[i * 32 + tid];
        }
        v = simd_sum(v);
        if (tid == 0) tg_sum_sq[0] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float denom = sqrt(max(tg_sum_sq[0] / float(N) + eps, 1e-30f));

    // ---- pass 2: scale ----
    for (uint n = tid; n < N; n += kL2TgSize) {
        float v = static_cast<float>(X[b * N + n]);
        Y[b * N + n] = static_cast<half>(v / denom);
    }
}
