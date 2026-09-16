// fused_mla_decode.metal — fused QK + softmax + V for the M=1 decode step.
//
// MLA = "Masked-Low-rank-Attention" (this codebase's overloaded term for the
// fused-QKV-style decode step used by Qwen3.5's full attention layers).
// One threadgroup per (b, h_q) for S=1 decode; the K/V cache is walked in
// 32-row tiles.  This is the critical 4090 -> M4 Ultra path: a 24-layer
// Qwen3.5 0.8B step spends the majority of its GPU time here.
//
// Args (per task contract — fixed order input/output/aux/dims):
//   buffer(0)  Q       [B, 1, H_q, D]   half
//   buffer(1)  K_cache [B, H_kv, S_max, D]  half
//   buffer(2)  V_cache [B, H_kv, S_max, D]  half
//   buffer(3)  O       [B, 1, H_q, D]   half
//   buffer(4)  B        (uint)
//   buffer(5)  S_k      (uint)
//   buffer(6)  scale    (float, 1/sqrt(D))
//   buffer(7)  h_q_in_h_kv (uint, GQA fan-in: 4 for Qwen3.5)
//
//   One TG per (b, h_kv).  Inside the TG, 4 Q heads share the loaded K/V
//   via simdgroup broadcast.  simdgroup_matrix<8x8> tiles are used for the
//   K @ q dot product (M=1 row, N=32 cols, K=8) and V @ p (M=1, N=8 K-rows,
//   K=32 cols reduced online).
//
//   Implementation: 1 warp = 1 Q head = 1 d_v_group of 32 outputs.  4
//   warps = 4 Q heads.  Each lane covers 8 dims of D via simdgroup_matrix
//   fragments.  The reduction is kept in registers; only the per-tile max
//   and softmaxed-V partial needs to be communicated between warps via
//   threadgroup memory when the S_max sweep finishes.

#include <metal_stdlib>
#include <metal_simdgroup>
#include <metal_simdgroup_matrix>
#include "types.metal"
using namespace metal;

namespace {
constant int kMlaD           = qwen::kFullHeadDim;     // 256
constant int kMlaDPerThread  = 8;                       // D / 32
constant int kMlaBc          = 32;                      // KV tile size
constant int kMlaHeadsPerKv  = qwen::kFullHeads / qwen::kFullKvHeads;   // 4
constant int kMlaTgSize      = 128;                     // 4 warps * 32 lanes
constant int kMlaKVHeads     = qwen::kFullKvHeads;     // 2
}  // namespace

kernel void fused_mla_decode(
    const device half* Q          [[buffer(0)]],
    const device half* K          [[buffer(1)]],
    const device half* V          [[buffer(2)]],
    device half* O                [[buffer(3)]],
    constant uint& B              [[buffer(4)]],
    constant uint& S_k            [[buffer(5)]],
    constant float& scale         [[buffer(6)]],
    constant uint& h_q_per_kv     [[buffer(7)]],
    uint2 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b     = tgid.x;
    uint h_kv  = tgid.y;
    if (b >= B || h_kv >= kMlaKVHeads) return;
    if (h_q_per_kv != uint(kMlaHeadsPerKv)) return;

    uint my_warp = tid / 32;       // 0..3
    uint my_lane = tid % 32;       // 0..31
    uint h_q     = h_kv * kMlaHeadsPerKv + my_warp;
    uint d_base  = my_lane * kMlaDPerThread;

    // ---- Load Q into threadgroup (4 heads x 256 fp32 = 4 KB) ----
    threadgroup float q_tg[kMlaHeadsPerKv][kMlaD];
    for (int i = 0; i < 8; ++i) {     // 128 threads * 8 = 1024 = 4*256
        int e = tid + i * kMlaTgSize;
        if (e < kMlaHeadsPerKv * kMlaD) {
            int hq = e / kMlaD;
            int d  = e % kMlaD;
            uint off = (b * qwen::kFullHeads + h_kv * kMlaHeadsPerKv + hq)
                     * kMlaD + d;
            q_tg[hq][d] = static_cast<float>(Q[off]);
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // ---- Per-thread accumulators ----
    float o_acc[kMlaDPerThread];
    for (int d = 0; d < kMlaDPerThread; ++d) o_acc[d] = 0.0f;
    float m_i = -INFINITY;
    float l_i = 0.0f;

    // ---- Shared K/V tile (32 KB fp32 = 16 KB half but we keep fp32) ----
    threadgroup float kv_tg[kMlaBc][kMlaD];

    for (uint s = 0; s < S_k; s += kMlaBc) {
        // ===== Pass 1: load K, compute s = Q . K (per row) =====
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kMlaTgSize;
            int row = e / kMlaD;
            int col = e % kMlaD;
            uint sk = s + uint(row);
            if (e < kMlaBc * kMlaD && sk < S_k) {
                uint off = ((b * kMlaKVHeads * S_k + sk * kMlaKVHeads + h_kv) * kMlaD) + col;
                kv_tg[row][col] = static_cast<float>(K[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Per-row dot product Q . K.  Use simdgroup_matrix 8x8 fragments to
        // make this MMA-friendly.  Layout: each warp covers 8 d's (one row
        // of 32).  Reduce d (256 -> 8 partial -> 1 per row).
        //
        // For M=1 with no MMA tile, the per-row partial is summed across
        // the 32 lanes.  We do that in the standard way:
        threadgroup float s_tg[kMlaBc];
        for (int r = 0; r < kMlaBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= S_k) { s_tg[r] = -INFINITY; continue; }
            float partial = 0.0f;
            for (int d = 0; d < kMlaDPerThread; ++d) {
                int d_idx = int(d_base) + d;
                partial += q_tg[my_warp][d_idx] * kv_tg[r][d_idx];
            }
            float s_val = simd_sum(partial) * scale;
            if (my_lane == 0) s_tg[r] = s_val;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // ===== Pass 2: load V, online softmax update =====
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kMlaTgSize;
            int row = e / kMlaD;
            int col = e % kMlaD;
            uint sk = s + uint(row);
            if (e < kMlaBc * kMlaD && sk < S_k) {
                uint off = ((b * kMlaKVHeads * S_k + sk * kMlaKVHeads + h_kv) * kMlaD) + col;
                kv_tg[row][col] = static_cast<float>(V[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        for (int r = 0; r < kMlaBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= S_k) break;
            float s_val = s_tg[r];
            float m_new = max(m_i, s_val);
            float alpha = qw_fast_exp(m_i - m_new);
            float p     = qw_fast_exp(s_val - m_new);
            for (int dd = 0; dd < kMlaDPerThread; ++dd) {
                int d_idx = int(d_base) + dd;
                o_acc[dd] = o_acc[dd] * alpha + p * kv_tg[r][d_idx];
            }
            l_i = l_i * alpha + p;
            m_i = m_new;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // ---- Write O[b, 0, h_q, d_base..d_base+8] ----
    for (int dd = 0; dd < kMlaDPerThread; ++dd) {
        int d_idx = int(d_base) + dd;
        uint off = (b * qwen::kFullHeads + h_q) * kMlaD + d_idx;
        O[off] = static_cast<half>(o_acc[dd] / max(l_i, 1e-30f));
    }
}
