// activation.metal — fused SwiGLU + sigmoid-gated attention output
// Qwen3.5 FFN:  out = down_proj( silu(gate) * up )
//   gate, up, down:  Linear projections of (H, I) or (I, H) half
//   silu(x) = x * sigmoid(x)
//
//   For maximum throughput we fuse:
//     - read gate and up from the GEMM output
//     - apply silu(gate) * up
//     - write the partial result in a single memory pass
//   The actual GEMM runs separately (use MPS or our simdgroup GEMM).
//   This kernel finishes the activation in one pass.

#include <metal_stdlib>
#include "types.metal"
using namespace metal;

// ===========================================================================
// silu_mul
//   out[i] = silu(gate[i]) * up[i]   (half, out-of-place)
//
//   Grid:  ceil(N / (TG * VEC)) threadgroups of TG threads, each thread
//          processes VEC=4 elements (vectorized load/store).
//
//   N = B * S * I   where I = intermediate_size = 3584
// ===========================================================================

constant int QW_ACT_TG  = 256;
constant int QW_ACT_VEC = 4;

kernel void silu_mul(
    const device half* gate        [[buffer(0)]],
    const device half* up          [[buffer(1)]],
    device half* out               [[buffer(2)]],
    constant uint& N                [[buffer(3)]],
    uint tgid                       [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint base = (tgid * QW_ACT_TG + tid) * QW_ACT_VEC;
    if (base >= N) return;
    if (base + QW_ACT_VEC <= N) {
        // 4-wide vectorized
        float4 g = qw_load4f(gate + base);
        float4 u = qw_load4f(up + base);
        float4 r;
        r.x = (g.x / (1.0f + qw_fast_exp(-g.x))) * u.x;
        r.y = (g.y / (1.0f + qw_fast_exp(-g.y))) * u.y;
        r.z = (g.z / (1.0f + qw_fast_exp(-g.z))) * u.z;
        r.w = (g.w / (1.0f + qw_fast_exp(-g.w))) * u.w;
        qw_store4f(out + base, r);
    } else {
        // tail
        for (int i = 0; i < QW_ACT_VEC; ++i) {
            uint idx = base + i;
            if (idx >= N) break;
            float g = qw_to_f32(gate[idx]);
            float u = qw_to_f32(up[idx]);
            out[idx] = qw_to_f16((g * qw_fast_sigmoid(g)) * u);
        }
    }
}

// In-place silu_mul:  gate[i] = silu(gate[i]) * up[i]
//   Note: still reads `up`, writes to `gate`.
kernel void silu_mul_inplace(
    device half* gate              [[buffer(0)]],
    const device half* up          [[buffer(1)]],
    constant uint& N                [[buffer(2)]],
    uint tgid                       [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint base = (tgid * QW_ACT_TG + tid) * QW_ACT_VEC;
    if (base >= N) return;
    if (base + QW_ACT_VEC <= N) {
        float4 g = qw_load4f(gate + base);
        float4 u = qw_load4f(up + base);
        float4 r;
        r.x = (g.x / (1.0f + qw_fast_exp(-g.x))) * u.x;
        r.y = (g.y / (1.0f + qw_fast_exp(-g.y))) * u.y;
        r.z = (g.z / (1.0f + qw_fast_exp(-g.z))) * u.z;
        r.w = (g.w / (1.0f + qw_fast_exp(-g.w))) * u.w;
        qw_store4f(gate + base, r);
    } else {
        for (int i = 0; i < QW_ACT_VEC; ++i) {
            uint idx = base + i;
            if (idx >= N) break;
            float g = qw_to_f32(gate[idx]);
            float u = qw_to_f32(up[idx]);
            gate[idx] = qw_to_f16((g * qw_fast_sigmoid(g)) * u);
        }
    }
}

// ===========================================================================
// sigmoid_gate_attn_out
//   out[i] = o[i] * sigmoid(o_gate[i])
//   Used in attention block after out_proj, before residual add.
//   Qwen3.5 attn_output_gate = true.
//
//   Grid:  N = B * S * H
// ===========================================================================

kernel void sigmoid_gate_mul(
    device half* o                  [[buffer(0)]],     // in/out
    const device half* og           [[buffer(1)]],     // in
    constant uint& N                [[buffer(2)]],
    uint tgid                       [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint base = (tgid * QW_ACT_TG + tid) * QW_ACT_VEC;
    if (base >= N) return;
    if (base + QW_ACT_VEC <= N) {
        float4 v = qw_load4f(o + base);
        float4 g = qw_load4f(og + base);
        v.x *= qw_fast_sigmoid(g.x);
        v.y *= qw_fast_sigmoid(g.y);
        v.z *= qw_fast_sigmoid(g.z);
        v.w *= qw_fast_sigmoid(g.w);
        qw_store4f(o + base, v);
    } else {
        for (int i = 0; i < QW_ACT_VEC; ++i) {
            uint idx = base + i;
            if (idx >= N) break;
            float v = qw_to_f32(o[idx]);
            float g = qw_to_f32(og[idx]);
            o[idx] = qw_to_f16(v * qw_fast_sigmoid(g));
        }
    }
}

// ===========================================================================
// silu_inplace — out-of-band activation sometimes needed
//   x[i] = silu(x[i])
// ===========================================================================

kernel void silu_inplace(
    device half* x                  [[buffer(0)]],
    constant uint& N                [[buffer(1)]],
    uint tgid                       [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint idx = tgid * QW_ACT_TG + tid;
    if (idx >= N) return;
    float v = qw_to_f32(x[idx]);
    x[idx] = qw_to_f16(v * qw_fast_sigmoid(v));
}
