// linear_attention.metal — DeltaNet-style linear attention for Qwen3.5 0.8B
//   Used by 18 of 24 layers (every non-full layer).
//
//   Architecture (Qwen3.5_5_0.8B text config):
//     linear_num_key_heads   = 16
//     linear_num_value_heads = 16
//     linear_key_head_dim    = 128
//     linear_value_head_dim  = 128
//     linear_conv_kernel_dim = 4     (causal 1D depthwise conv pre-attn)
//
//   Algorithm (one token, decode step):
//     Step 1: depthwise causal conv (kernel=4) on q, k, v independently.
//             Conv state = last 3 input frames (per channel).
//     Step 2: gated delta rule update:
//             decay  = exp(neg_exp * dt)        (per-head scalar)
//             v_new  = v  -  state @ k          (delta)
//             o      = state @ q
//             state += v_new  outer  k          (write-back)
//             o     *= silu(gate)               (gated output)
//
//   State shape:  [B, H_kv, D_v, D_k]  = [B, 16, 128, 128]
//                 At fp32: 16 MiB / layer
//                 18 layers ⇒ 288 MiB fp32
//                 On M1 Pro 16 GB unified this fits comfortably.
//
//   Activations: half (fp16).  State: float (fp32).  Accumulation: fp32.

#include <metal_stdlib>
#include <metal_simdgroup>
#include "types.metal"
using namespace metal;

// ---------------------------------------------------------------------------
// Compile-time geometry (constant address space at namespace scope).
// ---------------------------------------------------------------------------

namespace {
constant int kLinH           = qwen::kLinKeyHeads;       // 16
constant int kLinDk          = qwen::kLinKeyHeadDim;     // 128
constant int kLinDv          = qwen::kLinValueHeadDim;   // 128
constant int kLinConvK       = qwen::kLinConvKernel;     // 4
constant int kLinTgSize      = 128;                      // 4 warps × 32 lanes
}  // namespace

// ===========================================================================
// causal_conv1d_step  (single token, pre-attention)
// ===========================================================================
//
//   q_conv[d] = sum_{i=0..3} conv_w[c, i] * q_history[3 - i]
//
//   Layout:
//     qkv_in         [B, 3*H*Dk]   half   (3 = qkv packed, Dk = 128)
//     conv_w_qkv     [3*H, K=4]    half   (depthwise, per-channel)
//     conv_bias_qkv  [3*H]         half   (optional)
//     qkv_out        [B, 3*H*Dk]   half
//     conv_state     [B, 3*H, K=4] half   (rolling buffer; updated in place)
//
//   1 TG per (b, channel).  128 threads, 1 dim per thread.

kernel void causal_conv1d_step(
    const device half* qkv_in          [[buffer(0)]],
    const device half* conv_w_qkv      [[buffer(1)]],
    const device half* conv_bias_qkv   [[buffer(2)]],   // nullable
    device half* qkv_out               [[buffer(3)]],
    device half* conv_state            [[buffer(4)]],   // [B, 3H, K]
    constant uint& B                   [[buffer(5)]],
    constant uint& has_bias            [[buffer(6)]],
    uint2 tgid                         [[threadgroup_position_in_grid]],
    uint tid                           [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint c = tgid.y;
    if (b >= B) return;

    // Channel range check: c < 3*H = 48.
    if (c >= 3u * uint(kLinH)) return;

    // 1) Update conv_state in-band: shift left, append current input.
    //
    //   All 128 threads race to do the same shift (idempotent), so we only
    //   have one thread append the new input.  After the barrier, every
    //   thread sees the freshly updated state.
    //
    //   FIX: the previous code only let tid=0 write the new input and only
    //   tid=0..127 wrote one conv-out element.  All 128 dims of the channel
    //   are now written (one per thread).
    {
        // state[b, c, 0..K-1]  stride: K  (per channel)
        for (int k = 0; k < kLinConvK - 1; ++k) {
            conv_state[(b * (3 * kLinH) + c) * kLinConvK + k] =
                conv_state[(b * (3 * kLinH) + c) * kLinConvK + k + 1];
        }
        // Append: only the lane whose d_idx == tid does the write.  We use
        // d_idx = tid (since each thread owns one dim 0..kLinDk-1).
        if (tid < uint(kLinDk)) {
            conv_state[(b * (3 * kLinH) + c) * kLinConvK + (kLinConvK - 1)] =
                qkv_in[(b * 3 * kLinH + c) * kLinDk + tid];
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // 2) Compute conv output: out[d] = sum_k conv_w[c, k] * state[c, k]
    //
    //   The conv output for a depthwise channel-c dim is identical across all
    //   d in that channel.  We compute the scalar once (tid 0) and broadcast
    //   via threadgroup memory, then every thread writes its own d.
    threadgroup float conv_acc_tg;
    if (tid == 0) {
        float acc = 0.0f;
        for (int k = 0; k < kLinConvK; ++k) {
            float w = static_cast<float>(conv_w_qkv[c * kLinConvK + k]);
            float s = static_cast<float>(conv_state[(b * (3 * kLinH) + c) * kLinConvK + k]);
            acc += w * s;
        }
        if (has_bias != 0u) {
            acc += static_cast<float>(conv_bias_qkv[c]);
        }
        conv_acc_tg = acc;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    if (tid < uint(kLinDk)) {
        qkv_out[(b * 3 * kLinH + c) * kLinDk + tid] = static_cast<half>(conv_acc_tg);
    }
}

// ===========================================================================
// delta_net_decode_step  (one token, gated delta rule update)
// ===========================================================================
//
//   Inputs (after conv): q, k, v, gate, beta, alpha
//     q, k      [B, H, Dk]   half
//     v         [B, H, Dv]   half
//     gate      [B, H, Dv]   half  (sigmoid gate; attn_output_gate equivalent)
//     beta      [B, H]       half  (delta learning rate per head)
//     alpha_log [B, H]       half  (negative log-decay; exp(-alpha_log) ∈ (0,1))
//     state     [B, H, Dv, Dk]  fp32 accumulator
//
//   Step:
//     d = exp(-alpha_log)                           (decay scalar in (0,1))
//     v_new = v - beta * (state @ k)                (delta correction)
//     o     = state @ q                              (attention output)
//     state = d * state  +  outer(v_new, k)          (recurrent update)
//     o     = o * silu(gate)                        (gated output)
//
//   Per (b, h) one threadgroup.  128 threads arranged as 4 warps × 32 lanes.
//   Each thread owns one (d_v, d_k) pair: d_v = my_warp*32 + my_lane, d_k = my_lane.
//
//   Note: this is the "decode" (S=1) kernel.  For prefill (S>1) use
//   prefill_linear.metal with the chunked WY representation.

kernel void delta_net_decode_step(
    const device half* q         [[buffer(0)]],   // [B, H, Dk]
    const device half* k         [[buffer(1)]],
    const device half* v         [[buffer(2)]],   // [B, H, Dv]
    const device half* gate      [[buffer(3)]],   // [B, H, Dv]
    const device half* beta      [[buffer(4)]],   // [B, H]
    const device half* alpha_log [[buffer(5)]],   // [B, H]
    device float* state          [[buffer(6)]],   // [B, H, Dv, Dk]  fp32
    device half* out             [[buffer(7)]],   // [B, H, Dv]
    constant uint& B             [[buffer(8)]],
    uint2 tgid                   [[threadgroup_position_in_grid]],
    uint tid                     [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint h = tgid.y;
    if (b >= B) return;
    if (h >= uint(kLinH)) return;

    uint my_lane = tid & 31u;     // 0..31
    uint my_warp = tid >> 5;      // 0..3

    // Each thread owns one (d_v, d_k) pair.
    //   d_v = my_warp * 32 + my_lane  (covers Dv=128 with 4*32 threads)
    //   d_k = my_lane                 (covers Dk=128 with 32 lanes × 4 warps each)
    uint d_v_idx = my_warp * 32u + my_lane;
    uint d_k_idx = my_lane;

    // ---- Read per-head scalars (broadcast within simdgroup) ----
    float a_log = (tid == 0)
        ? static_cast<float>(alpha_log[b * kLinH + h])
        : 0.0f;
    float b_val = (tid == 0)
        ? static_cast<float>(beta[b * kLinH + h])
        : 0.0f;
    a_log = simd_broadcast_first(a_log);
    b_val = simd_broadcast_first(b_val);
    float d = metal::fast::exp(-a_log);

    // ---- Load q, k, v, gate (1 element per thread) ----
    float q_reg = static_cast<float>(q[(b * kLinH + h) * kLinDk + d_k_idx]);
    float k_reg = static_cast<float>(k[(b * kLinH + h) * kLinDk + d_k_idx]);
    float v_reg = static_cast<float>(v[(b * kLinH + h) * kLinDv + d_v_idx]);
    float g_reg = static_cast<float>(gate[(b * kLinH + h) * kLinDv + d_v_idx]);

    // ---- Read state[d_v_idx, d_k_idx] ----
    float s_val = state[((b * kLinH + h) * kLinDv + d_v_idx) * kLinDk + d_k_idx];

    // ---- Compute o_partial = s_val * q_reg (each thread holds 1 product of 128-dim dot) ----
    // Reduce across the 32 lanes of this warp (which all share d_v_idx but have
    // different d_k_idx).  After the reduction, lane 0 of each warp holds
    // o_full for that warp's d_v (which is d_v_idx when my_lane == 0).
    float o_partial = s_val * q_reg;
    float o_full = simd_sum(o_partial);

    // ---- Compute (state @ k) per d_v (for v_new = v - beta * state@k) ----
    float sk_partial = s_val * k_reg;
    float sk_full = simd_sum(sk_partial);
    float v_new = v_reg - b_val * sk_full;

    // ---- Update state[d_v_idx, d_k_idx] in place ----
    float s_new = d * s_val + v_new * k_reg;
    state[((b * kLinH + h) * kLinDv + d_v_idx) * kLinDk + d_k_idx] = s_new;

    // ---- Gated output: o = o * silu(gate) ----
    //
    // After simd_sum over d_k, every lane in the warp has the same `o_full`
    // (and same `sk_full`, but we already used that).  `o_full` corresponds
    // to d_v = my_warp*32 + my_lane.  `g_reg` is also per (d_v, lane), so
    // we use g_reg from this lane.  The full 128 d_v outputs are written
    // by all 128 threads — one per (warp, lane) pair.
    //
    // FIX: previously only lane 0 of each warp wrote (4/128 d_v values).
    // Now every lane writes its own d_v.
    {
        float silu_g = g_reg * qw_fast_sigmoid(g_reg);
        float out_val = o_full * silu_g;
        out[(b * kLinH + h) * kLinDv + d_v_idx] = static_cast<half>(out_val);
    }
}

// ===========================================================================
// Orchestration note
// ===========================================================================
//   The full linear attention block for one token:
//     1) Pack Q, K, V from hidden via fused linear (done by host GEMM)
//     2) causal_conv1d_step
//     3) delta_net_decode_step
//
//   The host calls (1), (2), (3) sequentially.  The kernels above implement
//   (2) and (3) for one token each.  For prefill (S > 1), the prefill form
//   uses the chunk-wise WY representation; see prefill_linear.metal.
