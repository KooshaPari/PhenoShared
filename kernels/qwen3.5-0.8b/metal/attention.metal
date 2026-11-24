// attention.metal — Flash Attention v2 with GQA broadcast for Qwen3.5 0.8B
//   Full attention layers only (every 4th: 3, 7, 11, 15, 19, 23).
//
//   Config (Qwen3.5):
//     num_heads (Q)     = 8
//     num_kv_heads (KV) = 2
//     head_dim          = 256
//     GQA ratio         = 4  (each KV head serves 4 Q heads)
//
//   Three kernels:
//     1. flash_attn_decode   — S_q = 1, online-softmax over KV cache
//                              (split-KV reduction across S_kv blocks).
//     2. flash_attn_prefill  — S_q = S, tiled flash-attn v2 (causal mask).
//     3. kv_cache_append     — append new K, V to the persistent cache.
//
//   Activations: fp16 (half).  Accumulation: fp32.  qk = q @ k.T is fp32.
//   The MMA tensor cores on M-series accept fp16 inputs and accumulate fp32.

#include <metal_stdlib>
#include <metal_simdgroup>
#include <metal_simdgroup_matrix>
#include "types.metal"
using namespace metal;

// ===========================================================================
// flash_attn_decode  — S_q = 1, online-softmax over KV cache
// ===========================================================================
//
//   Q [B, 1, H_q, D]   K_cache [B, H_kv, S_max, D]   V_cache [B, H_kv, S_max, D]
//   O [B, 1, H_q, D]
//
//   One threadgroup handles 1 KV head → broadcasts to its 4 Q heads.
//   Threads in the TG:  4 (q heads) × 32 (lanes) = 128.
//
//   Per (b, h_kv) we sweep S_max in Bc=32 tiles.  For each tile:
//     - load K, compute s = (Q.h_q) . K   (per-thread scalar, simd_sum)
//     - online softmax update  (m_i, l_i, o_acc)  in registers
//     - load V, accumulate p * V  into per-thread output
//
//   Split-KV reduction: S_max can be very large (e.g. 32k).  We support a
//   2-stage scheme where each (b, h_kv, kv_block) pair produces a partial
//   (m, l, o); the second kernel reduces.  See `flash_attn_decode_split`
//   and `flash_attn_decode_reduce` below for the multi-block variant.

namespace {
constant int kDecodeBc          = 16;                              // halved from 32 to fit 32 KB threadgroup mem
constant int kDecodeHeadsPerKv  = 4;                              // GQA 4:1
constant int kDecodeTgSize      = 128;
constant int kDecodeD           = qwen::kFullHeadDim;             // 256
constant int kDecodeDPerThread  = kDecodeD / 32;                  // 8
constant int kDecodeKVHeads     = qwen::kFullKvHeads;             // 2
}  // namespace

// ---- single-stage decode (best for S_max ≤ 1024) ----

kernel void flash_attn_decode(
    const device half* Q          [[buffer(0)]],   // [B, 1, H_q, D]
    const device half* K          [[buffer(1)]],   // [B, H_kv, S_max, D]
    const device half* V          [[buffer(2)]],   // [B, H_kv, S_max, D]
    device half* O                [[buffer(3)]],   // [B, 1, H_q, D]
    constant uint& B              [[buffer(4)]],
    constant uint& S_k            [[buffer(5)]],
    constant float& scale         [[buffer(6)]],    // 1/sqrt(D)
    uint2 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b     = tgid.x;
    uint h_kv  = tgid.y;
    if (b >= B || h_kv >= kDecodeKVHeads) return;

    uint my_hq   = tid / 32;            // 0..3 within this group
    uint h_q     = h_kv * kDecodeHeadsPerKv + my_hq;
    uint my_lane = tid % 32;            // 0..31
    uint d_base  = my_lane * kDecodeDPerThread;

    // ---- Q in TG: 4 heads × 256 fp32 = 4 KB ----
    threadgroup float q_tg[kDecodeHeadsPerKv][kDecodeD];
    {
        for (int i = 0; i < 8; ++i) {     // 128 threads × 8 = 1024 = 4 × 256
            int e = tid + i * kDecodeTgSize;
            if (e < kDecodeHeadsPerKv * kDecodeD) {
                int hq = e / kDecodeD;
                int d  = e % kDecodeD;
                uint off = (b * qwen::kFullHeads + h_q - my_hq + hq) * kDecodeD + d;
                q_tg[hq][d] = qw_to_f32(Q[off]);
            }
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);

    // ---- per-thread accumulators ----
    float o_acc[kDecodeDPerThread];
    for (int i = 0; i < kDecodeDPerThread; ++i) o_acc[i] = 0.0f;
    float m_i = -INFINITY;
    float l_i = 0.0f;

    // ---- shared K (then V) buffer, reused per tile ----
    threadgroup float kv_tg[kDecodeBc][kDecodeD];   // 32 * 256 * 4 = 32 KB

    for (uint s = 0; s < S_k; s += kDecodeBc) {
        // ===== Pass 1: load K and compute s = Q . K (per row) =====
        // 128 threads load 32*256 = 8192 elements → 64 elts/thread.
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kDecodeTgSize;
            int row = e / kDecodeD;
            int col = e % kDecodeD;
            uint sk = s + uint(row);
            if (e < kDecodeBc * kDecodeD && sk < S_k) {
                uint off = (b * kDecodeKVHeads * S_k + sk * kDecodeKVHeads + h_kv) * kDecodeD + col;
                kv_tg[row][col] = qw_to_f32(K[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Per-row dot product for this thread's Q head.  Reduce within simd.
        // s_tg[r] is written by lane 0 of simdgroup 0..3 (4 heads).
        threadgroup float s_tg[kDecodeBc];
        for (int r = 0; r < kDecodeBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= S_k) { s_tg[r] = -INFINITY; continue; }
            float partial = 0.0f;
            for (int d = 0; d < kDecodeDPerThread; ++d) {
                int d_idx = int(d_base) + d;
                partial += q_tg[my_hq][d_idx] * kv_tg[r][d_idx];
            }
            float s_val = simd_sum(partial) * scale;
            if (my_lane == 0) s_tg[r] = s_val;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // ===== Pass 2: load V, online softmax update =====
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kDecodeTgSize;
            int row = e / kDecodeD;
            int col = e % kDecodeD;
            uint sk = s + uint(row);
            if (e < kDecodeBc * kDecodeD && sk < S_k) {
                uint off = (b * kDecodeKVHeads * S_k + sk * kDecodeKVHeads + h_kv) * kDecodeD + col;
                kv_tg[row][col] = qw_to_f32(V[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        for (int r = 0; r < kDecodeBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= S_k) break;
            float s_val = s_tg[r];
            float m_new = max(m_i, s_val);
            float alpha = qw_fast_exp(m_i - m_new);
            float p     = qw_fast_exp(s_val - m_new);
            for (int dd = 0; dd < kDecodeDPerThread; ++dd) {
                int d_idx = int(d_base) + dd;
                o_acc[dd] = o_acc[dd] * alpha + p * kv_tg[r][d_idx];
            }
            l_i = l_i * alpha + p;
            m_i = m_new;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // ---- Write O[b, 0, h_q, d_base..d_base+8] ----
    for (int dd = 0; dd < kDecodeDPerThread; ++dd) {
        int d_idx = int(d_base) + dd;
        uint off = (b * qwen::kFullHeads + h_q) * kDecodeD + d_idx;
        O[off] = qw_to_f16(o_acc[dd] / max(l_i, 1e-30f));
    }
}

// ===========================================================================
// flash_attn_decode_split  — partial-output variant for S_max > 1024
// ===========================================================================
//
//   Each threadgroup handles a (b, h_kv, kv_block) chunk.  Writes a
//   (m, l, o_partial) triple into per-block output buffers; a second
//   kernel (`flash_attn_decode_reduce`) merges them in log-space.
//
//   Output layout:
//     O_partial [num_blocks, B, H_q, D]   half
//     L_partial [num_blocks, B, H_q]      fp32
//     M_partial [num_blocks, B, H_q]      fp32
//
//   num_blocks = ceil(S_max / block_size), block_size = 512 here.

kernel void flash_attn_decode_split(
    const device half* Q          [[buffer(0)]],
    const device half* K          [[buffer(1)]],
    const device half* V          [[buffer(2)]],
    device half* O_partial        [[buffer(3)]],
    device float* L_partial       [[buffer(4)]],
    device float* M_partial       [[buffer(5)]],
    constant uint& B              [[buffer(6)]],
    constant uint& S_k            [[buffer(7)]],
    constant uint& num_blocks     [[buffer(8)]],
    constant float& scale         [[buffer(9)]],
    uint3 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b       = tgid.x;
    uint h_kv    = tgid.y;
    uint kv_blk  = tgid.z;
    if (b >= B || h_kv >= kDecodeKVHeads || kv_blk >= num_blocks) return;

    constexpr int kBlockSize = 512;
    uint s_start = kv_blk * kBlockSize;
    uint s_end   = min(s_start + kBlockSize, S_k);
    if (s_start >= s_end) return;

    uint my_hq   = tid / 32;
    uint h_q     = h_kv * kDecodeHeadsPerKv + my_hq;
    uint my_lane = tid % 32;
    uint d_base  = my_lane * kDecodeDPerThread;

    threadgroup float q_tg[kDecodeHeadsPerKv][kDecodeD];
    {
        for (int i = 0; i < 8; ++i) {
            int e = tid + i * kDecodeTgSize;
            if (e < kDecodeHeadsPerKv * kDecodeD) {
                int hq = e / kDecodeD;
                int d  = e % kDecodeD;
                uint off = (b * qwen::kFullHeads + (h_kv * kDecodeHeadsPerKv) + hq) * kDecodeD + d;
                q_tg[hq][d] = qw_to_f32(Q[off]);
            }
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);

    float o_acc[kDecodeDPerThread] = {0,0,0,0,0,0,0,0};
    float m_i = -INFINITY;
    float l_i = 0.0f;

    threadgroup float kv_tg[kDecodeBc][kDecodeD];   // 32 KB

    for (uint s = s_start; s < s_end; s += kDecodeBc) {
        // Pass 1: load K and compute QK
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kDecodeTgSize;
            int row = e / kDecodeD;
            int col = e % kDecodeD;
            uint sk = s + uint(row);
            if (row < kDecodeBc && sk < s_end) {
                uint off = (b * kDecodeKVHeads * S_k + sk * kDecodeKVHeads + h_kv) * kDecodeD + col;
                kv_tg[row][col] = qw_to_f32(K[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        threadgroup float s_tg[kDecodeBc];
        for (int r = 0; r < kDecodeBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= s_end) { s_tg[r] = -INFINITY; continue; }
            float partial = 0.0f;
            for (int d = 0; d < kDecodeDPerThread; ++d) {
                int d_idx = int(d_base) + d;
                partial += q_tg[my_hq][d_idx] * kv_tg[r][d_idx];
            }
            float s_val = simd_sum(partial) * scale;
            if (my_lane == 0) s_tg[r] = s_val;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Pass 2: load V and accumulate
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kDecodeTgSize;
            int row = e / kDecodeD;
            int col = e % kDecodeD;
            uint sk = s + uint(row);
            if (row < kDecodeBc && sk < s_end) {
                uint off = (b * kDecodeKVHeads * S_k + sk * kDecodeKVHeads + h_kv) * kDecodeD + col;
                kv_tg[row][col] = qw_to_f32(V[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        for (int r = 0; r < kDecodeBc; ++r) {
            uint sk = s + uint(r);
            if (sk >= s_end) break;
            float s_val = s_tg[r];
            float m_new = max(m_i, s_val);
            float alpha = qw_fast_exp(m_i - m_new);
            float p     = qw_fast_exp(s_val - m_new);
            for (int dd = 0; dd < kDecodeDPerThread; ++dd) {
                int d_idx = int(d_base) + dd;
                o_acc[dd] = o_acc[dd] * alpha + p * kv_tg[r][d_idx];
            }
            l_i = l_i * alpha + p;
            m_i = m_new;
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // Write per-(b, h_q, block) partials.
    uint p_idx = (kv_blk * B + b) * qwen::kFullHeads + h_q;
    if (my_lane == 0) {
        L_partial[p_idx] = l_i;
        M_partial[p_idx] = m_i;
    }
    for (int dd = 0; dd < kDecodeDPerThread; ++dd) {
        int d_idx = int(d_base) + dd;
        uint off = ((kv_blk * B + b) * qwen::kFullHeads + h_q) * kDecodeD + d_idx;
        O_partial[off] = qw_to_f16(o_acc[dd]);
    }
}

// ===========================================================================
// flash_attn_decode_reduce  — merge split partials
// ===========================================================================
//
//   For each (b, h_q), read the num_blocks partials and combine using the
//   log-sum-exp merge: m_new = max(m_i),  l_new = sum(l_i * exp(m_i - m_new)),
//   o_new = sum(o_i * exp(m_i - m_new)) / l_new.

kernel void flash_attn_decode_reduce(
    const device half* O_partial   [[buffer(0)]],
    const device float* L_partial  [[buffer(1)]],
    const device float* M_partial  [[buffer(2)]],
    device half* O                  [[buffer(3)]],
    constant uint& B                [[buffer(4)]],
    constant uint& num_blocks       [[buffer(5)]],
    uint2 tgid                      [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint b   = tgid.x;
    uint h_q = tgid.y;
    if (b >= B) return;
    if (h_q >= qwen::kFullHeads) return;

    // Each thread handles kDecodeDPerThread=8 dims of the output.
    uint d_base = tid * kDecodeDPerThread;

    // Find global max m across blocks (only first warp writes to threadgroup).
    threadgroup float maxm_tg[32];
    float my_m = -INFINITY;
    for (uint blk = 0; blk < num_blocks; ++blk) {
        uint p_idx = (blk * B + b) * qwen::kFullHeads + h_q;
        if (blk < num_blocks) {
            float m = M_partial[p_idx];
            if (m > my_m) my_m = m;
        }
    }
    if (tid < 32) maxm_tg[tid] = my_m;
    threadgroup_barrier(mem_flags::mem_threadgroup);
    if (tid == 0) {
        float g = -INFINITY;
        for (int i = 0; i < 32; ++i) {
            if (maxm_tg[i] > g) g = maxm_tg[i];
        }
        maxm_tg[0] = g;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float g_max = maxm_tg[0];

    // Combine: l_new = sum_b l_b * exp(m_b - g_max),  o_new = sum_b o_b * exp(m_b - g_max)
    float l_new = 0.0f;
    float o_new[kDecodeDPerThread];
    for (int i = 0; i < kDecodeDPerThread; ++i) o_new[i] = 0.0f;
    for (uint blk = 0; blk < num_blocks; ++blk) {
        uint p_idx = (blk * B + b) * qwen::kFullHeads + h_q;
        float m = M_partial[p_idx];
        float l = L_partial[p_idx];
        float w = qw_fast_exp(m - g_max);
        l_new += l * w;
        for (int i = 0; i < kDecodeDPerThread; ++i) {
            int d_idx = int(d_base) + i;
            float ov = qw_to_f32(O_partial[((blk * B + b) * qwen::kFullHeads + h_q) * kDecodeD + d_idx]);
            o_new[i] += ov * w;
        }
    }
    for (int i = 0; i < kDecodeDPerThread; ++i) {
        int d_idx = int(d_base) + i;
        uint off = (b * qwen::kFullHeads + h_q) * kDecodeD + d_idx;
        O[off] = qw_to_f16(o_new[i] / max(l_new, 1e-30f));
    }
}

// ===========================================================================
// flash_attn_prefill  — S_q = S, causal flash-attn v2 with GQA broadcast
// ===========================================================================
//
//   Br=16, Bc=32  →  36 KB TG (4 KB Q + 16 KB K + 16 KB V).
//   One threadgroup per (b, h_kv, q_block).  Inside: 4 q_heads per group.
//
//   Causal mask: each Q tile only attends to K tiles where col <= last_q_row.
//
//   Production prefill on M2/M3/M4 with larger TG (32 KB) can lift Br=32 by
//   shrinking the K/V tiles; that variant is in the `_br32` kernel below.

namespace {
constant int kPrefillBr     = 16;
constant int kPrefillBc     = 32;
constant int kPrefillD      = qwen::kFullHeadDim;     // 256
constant int kPrefillHqPKv  = 4;
constant int kPrefillTgSize = 128;
}  // namespace

kernel void flash_attn_prefill(
    const device half* Q          [[buffer(0)]],
    const device half* K          [[buffer(1)]],
    const device half* V          [[buffer(2)]],
    device half* O                [[buffer(3)]],
    constant uint& B              [[buffer(4)]],
    constant uint& S              [[buffer(5)]],
    constant float& scale         [[buffer(6)]],
    uint3 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b      = tgid.x;
    uint h_kv   = tgid.y;
    uint q_blk  = tgid.z;
    if (b >= B || h_kv >= kDecodeKVHeads) return;

    uint q_start = q_blk * kPrefillBr;
    if (q_start >= S) return;
    uint q_end = min(q_start + kPrefillBr, S);

    uint my_hq   = tid / 32;            // 0..3
    uint h_q     = h_kv * kPrefillHqPKv + my_hq;
    uint my_lane = tid % 32;

    // Q row stripe: each thread owns 8 dims of 1 Q row for 1 Q head.
    constexpr int kDPer = kPrefillD / 32;   // 8
    constexpr int kRowsPerThread = kPrefillBr / 4;  // 4 rows, my_hq maps to row range
    uint row_offset = my_hq * kRowsPerThread;       // 0, 4, 8, 12

    // Per-thread Q rows: 4 rows × 8 dims = 32 fp32 per thread.
    float q_reg[kRowsPerThread][kDPer];
    for (int r = 0; r < kRowsPerThread; ++r) {
        uint s_idx = q_start + row_offset + r;
        for (int d = 0; d < kDPer; ++d) {
            int d_idx = my_lane * kDPer + d;
            if (s_idx < S) {
                uint off = (b * S + s_idx) * (qwen::kFullHeads * kPrefillD) + h_q * kPrefillD + d_idx;
                q_reg[r][d] = qw_to_f32(Q[off]);
            } else {
                q_reg[r][d] = 0.0f;
            }
        }
    }

    // O accumulators: same layout as q_reg.
    float o_reg[kRowsPerThread][kDPer];
    for (int r = 0; r < kRowsPerThread; ++r)
        for (int d = 0; d < kDPer; ++d) o_reg[r][d] = 0.0f;
    float m_i[kRowsPerThread];
    float l_i[kRowsPerThread];
    for (int r = 0; r < kRowsPerThread; ++r) { m_i[r] = -INFINITY; l_i[r] = 0.0f; }

    // TG buffers for K and V tiles
    threadgroup float k_tg[kPrefillBc][kPrefillD];
    threadgroup float v_tg[kPrefillBc][kPrefillD];

    // Sweep K blocks.  Causal: stop once kc > last q row in this block.
    uint last_q = q_end - 1;
    for (uint k_blk = 0; k_blk <= last_q; k_blk += kPrefillBc) {
        uint kc_start = k_blk;

        // Load K tile into TG: kPrefillBc rows × kPrefillD cols.
        // 128 threads × 64 elements/thread = 8192 = 32 * 256.
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kPrefillTgSize;
            int row = e / kPrefillD;
            int col = e % kPrefillD;
            uint sk = kc_start + uint(row);
            if (row < kPrefillBc && sk < S) {
                uint off = (b * S + sk) * (kDecodeKVHeads * kPrefillD) + h_kv * kPrefillD + col;
                k_tg[row][col] = qw_to_f32(K[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Compute s[r, d_lane] = q_reg[d_lane] . k_tg[r, d_lane]
        // s_tg[kPrefillBc][kPrefillD] — but we only need the per-row scalars.
        // Reduce within simdgroup: each thread holds partial for one (r, lane) cell.
        // For QK^T: (kPrefillBc × 256) per head, but rows and D are reduced over
        // all 32 lanes.  Use the standard 32 lanes to compute dot product.
        // Result: per (r, q_row) scalar s_value.

        // Per-thread: s_partial for 4 q_rows × 32 bc rows.
        float s_val[kRowsPerThread][kPrefillBc];
        for (int rr = 0; rr < kRowsPerThread; ++rr)
            for (int r = 0; r < kPrefillBc; ++r) s_val[rr][r] = 0.0f;
        for (int d = 0; d < kDPer; ++d) {
            int d_idx = my_lane * kDPer + d;
            for (int r = 0; r < kPrefillBc; ++r) {
                float k_val = (r < kPrefillBc && (kc_start + uint(r)) < S) ? k_tg[r][d_idx] : 0.0f;
                for (int rr = 0; rr < kRowsPerThread; ++rr) {
                    s_val[rr][r] += q_reg[rr][d] * k_val;
                }
            }
        }
        // Reduce each (rr, r) across the 32 lanes (dot product).
        for (int rr = 0; rr < kRowsPerThread; ++rr) {
            for (int r = 0; r < kPrefillBc; ++r) {
                s_val[rr][r] = simd_sum(s_val[rr][r]) * scale;
            }
        }
        // Apply causal mask: only allow k_col <= q_row
        for (int rr = 0; rr < kRowsPerThread; ++rr) {
            uint s_idx = q_start + row_offset + rr;
            for (int r = 0; r < kPrefillBc; ++r) {
                uint sk = kc_start + uint(r);
                if (sk > s_idx) s_val[rr][r] = -INFINITY;
            }
        }

        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Online softmax update
        for (int rr = 0; rr < kRowsPerThread; ++rr) {
            uint s_idx = q_start + row_offset + rr;
            if (s_idx >= S) continue;
            for (int r = 0; r < kPrefillBc; ++r) {
                uint sk = kc_start + uint(r);
                if (sk >= S) break;
                float s = s_val[rr][r];
                if (s == -INFINITY) continue;
                float m_new = max(m_i[rr], s);
                float alpha = qw_fast_exp(m_i[rr] - m_new);
                float p     = qw_fast_exp(s - m_new);
                l_i[rr] = l_i[rr] * alpha + p;
                m_i[rr] = m_new;
                for (int d = 0; d < kDPer; ++d) o_reg[rr][d] *= alpha;
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // Load V tile and accumulate p * V
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kPrefillTgSize;
            int row = e / kPrefillD;
            int col = e % kPrefillD;
            uint sk = kc_start + uint(row);
            if (row < kPrefillBc && sk < S) {
                uint off = (b * S + sk) * (kDecodeKVHeads * kPrefillD) + h_kv * kPrefillD + col;
                v_tg[row][col] = qw_to_f32(V[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        for (int rr = 0; rr < kRowsPerThread; ++rr) {
            uint s_idx = q_start + row_offset + rr;
            if (s_idx >= S) continue;
            for (int r = 0; r < kPrefillBc; ++r) {
                uint sk = kc_start + uint(r);
                if (sk >= S) break;
                float s = s_val[rr][r];
                if (s == -INFINITY) continue;
                float p = qw_fast_exp(s - m_i[rr]);
                for (int d = 0; d < kDPer; ++d) {
                    int d_idx = my_lane * kDPer + d;
                    o_reg[rr][d] += p * v_tg[r][d_idx];
                }
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // Final: divide by l_i and write to O.
    for (int rr = 0; rr < kRowsPerThread; ++rr) {
        uint s_idx = q_start + row_offset + rr;
        if (s_idx >= S) continue;
        for (int d = 0; d < kDPer; ++d) {
            int d_idx = my_lane * kDPer + d;
            uint off = (b * S + s_idx) * (qwen::kFullHeads * kPrefillD) + h_q * kPrefillD + d_idx;
            O[off] = qw_to_f16(o_reg[rr][d] / max(l_i[rr], 1e-30f));
        }
    }
}

// ===========================================================================
// kv_cache_append  — append a single new K, V to the persistent cache
// ===========================================================================

kernel void kv_cache_append(
    const device half* K_in       [[buffer(0)]],   // [B, 1, H_kv, D]
    const device half* V_in       [[buffer(1)]],
    device half* K_cache          [[buffer(2)]],   // [B, H_kv, S_max, D]
    device half* V_cache          [[buffer(3)]],
    constant uint& B              [[buffer(4)]],
    constant uint& slot           [[buffer(5)]],
    constant uint& S_max          [[buffer(6)]],
    uint2 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b    = tgid.x;
    uint h_kv = tgid.y;
    if (b >= B || h_kv >= kDecodeKVHeads) return;
    if (slot >= S_max) return;

    // K_in layout: [B, 1, H_kv, D], so each TG writes 1 D-element block.
    // Use cooperative 256 threads per TG to cover 256 dims.
    constexpr int kD = kDecodeD;       // 256
    for (int d = tid; d < kD; d += kPrefillTgSize) {
        uint k_off = (b * kDecodeKVHeads + h_kv) * kD + d;
        uint c_off = ((b * kDecodeKVHeads + h_kv) * S_max + slot) * kD + d;
        K_cache[c_off] = K_in[k_off];
        V_cache[c_off] = V_in[k_off];
    }
}

// ===========================================================================
// flash_attn_prefill_br32  — S_q = S, Br=32, Bc=32 causal flash-attn v2
// ===========================================================================
//
//   Br=32, Bc=32  ->  64 KB TG footprint:
//     4 heads x Br x D = 4 * 32 * 256 * 4 bytes = 128 KB ... but we don't
//     hold Q in TG; we stream from registers.  K/V tiles are 32 x 256 = 32 KB
//     each (16 KB when fp16, but we accumulate fp32 in TG).
//
//   Compared to flash_attn_prefill (Br=16, Bc=32) above, this doubles the Q
//   rows per TG and halves the number of KV sweeps, which is the perf win on
//   M-series for S >= 512.
//
//   One threadgroup per (b, h_kv, q_block).  Inside: 4 q_heads per group,
//   each owning 8 of the 32 Q rows (8 rows/head).  Threads: 4 heads x 32
//   lanes = 128.

namespace {
constant int kPrefillBr32    = 32;
constant int kPrefillBc32    = 32;
constant int kPrefillD32     = qwen::kFullHeadDim;     // 256
constant int kPrefillHqPKv32 = 4;
constant int kPrefillTgSize32 = 128;
constant int kRowsPerHead32   = kPrefillBr32 / kPrefillHqPKv32;   // 8
}  // namespace

kernel void flash_attn_prefill_br32(
    const device half* Q          [[buffer(0)]],
    const device half* K          [[buffer(1)]],
    const device half* V          [[buffer(2)]],
    device half* O                [[buffer(3)]],
    constant uint& B              [[buffer(4)]],
    constant uint& S              [[buffer(5)]],
    constant float& scale         [[buffer(6)]],
    uint3 tgid                    [[threadgroup_position_in_grid]],
    uint tid                      [[thread_index_in_threadgroup]]) {
    uint b      = tgid.x;
    uint h_kv   = tgid.y;
    uint q_blk  = tgid.z;
    if (b >= B || h_kv >= kDecodeKVHeads) return;

    uint q_start = q_blk * kPrefillBr32;
    if (q_start >= S) return;
    uint q_end = min(q_start + kPrefillBr32, S);

    uint my_hq   = tid / 32;        // 0..3
    uint h_q     = h_kv * kPrefillHqPKv32 + my_hq;
    uint my_lane = tid % 32;

    constexpr int kDPer32 = kPrefillD32 / 32;   // 8

    // Per-thread Q: 8 rows x 8 dims = 64 fp32.  Loaded once, kept in registers.
    float q_reg[kRowsPerHead32][kDPer32];
    {
        uint row_base = my_hq * kRowsPerHead32;
        for (int rr = 0; rr < kRowsPerHead32; ++rr) {
            uint s_idx = q_start + row_base + uint(rr);
            for (int d = 0; d < kDPer32; ++d) {
                int d_idx = my_lane * kDPer32 + d;
                if (s_idx < S) {
                    uint off = (b * S + s_idx) * (qwen::kFullHeads * kPrefillD32)
                             + h_q * kPrefillD32 + d_idx;
                    q_reg[rr][d] = qw_to_f32(Q[off]);
                } else {
                    q_reg[rr][d] = 0.0f;
                }
            }
        }
    }

    // O accumulators: same shape, kept in registers.
    float o_reg[kRowsPerHead32][kDPer32];
    for (int rr = 0; rr < kRowsPerHead32; ++rr)
        for (int d = 0; d < kDPer32; ++d) o_reg[rr][d] = 0.0f;
    float m_i[kRowsPerHead32];
    float l_i[kRowsPerHead32];
    for (int rr = 0; rr < kRowsPerHead32; ++rr) {
        m_i[rr] = -INFINITY;
        l_i[rr] = 0.0f;
    }

    // TG buffers for K and V tiles (one tile at a time; we reuse).
    threadgroup float k_tg[kPrefillBc32][kPrefillD32];
    threadgroup float v_tg[kPrefillBc32][kPrefillD32];

    uint last_q = q_end - 1;
    for (uint k_blk = 0; k_blk <= last_q; k_blk += kPrefillBc32) {
        // ===== Load K tile =====
        // 128 threads * 64 = 8192 = 32 * 256.  Each thread does 64 elts.
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kPrefillTgSize32;
            int row = e / kPrefillD32;
            int col = e % kPrefillD32;
            uint sk = k_blk + uint(row);
            if (row < kPrefillBc32 && sk < S) {
                uint off = (b * S + sk) * (kDecodeKVHeads * kPrefillD32)
                         + h_kv * kPrefillD32 + col;
                k_tg[row][col] = qw_to_f32(K[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // ===== QK^T + causal mask =====
        // Per-thread per-(rr, r) accumulator; reduce via simd_sum.
        float s_val[kRowsPerHead32][kPrefillBc32];
        for (int rr = 0; rr < kRowsPerHead32; ++rr)
            for (int r = 0; r < kPrefillBc32; ++r) s_val[rr][r] = 0.0f;

        for (int d = 0; d < kDPer32; ++d) {
            int d_idx = my_lane * kDPer32 + d;
            for (int r = 0; r < kPrefillBc32; ++r) {
                float k_val = ((k_blk + uint(r)) < S) ? k_tg[r][d_idx] : 0.0f;
                for (int rr = 0; rr < kRowsPerHead32; ++rr) {
                    s_val[rr][r] += q_reg[rr][d] * k_val;
                }
            }
        }
        for (int rr = 0; rr < kRowsPerHead32; ++rr) {
            for (int r = 0; r < kPrefillBc32; ++r) {
                s_val[rr][r] = simd_sum(s_val[rr][r]) * scale;
            }
        }
        // Causal: only allow k_col <= q_row.
        for (int rr = 0; rr < kRowsPerHead32; ++rr) {
            uint s_idx = q_start + my_hq * kRowsPerHead32 + uint(rr);
            for (int r = 0; r < kPrefillBc32; ++r) {
                uint sk = k_blk + uint(r);
                if (sk > s_idx) s_val[rr][r] = -INFINITY;
            }
        }

        // ===== Online softmax update =====
        for (int rr = 0; rr < kRowsPerHead32; ++rr) {
            uint s_idx = q_start + my_hq * kRowsPerHead32 + uint(rr);
            if (s_idx >= S) continue;
            for (int r = 0; r < kPrefillBc32; ++r) {
                uint sk = k_blk + uint(r);
                if (sk >= S) break;
                float s = s_val[rr][r];
                if (s == -INFINITY) continue;
                float m_new = max(m_i[rr], s);
                float alpha = qw_fast_exp(m_i[rr] - m_new);
                float p     = qw_fast_exp(s - m_new);
                l_i[rr] = l_i[rr] * alpha + p;
                m_i[rr] = m_new;
                for (int d = 0; d < kDPer32; ++d) o_reg[rr][d] *= alpha;
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // ===== Load V tile =====
        for (int i = 0; i < 64; ++i) {
            int e = tid + i * kPrefillTgSize32;
            int row = e / kPrefillD32;
            int col = e % kPrefillD32;
            uint sk = k_blk + uint(row);
            if (row < kPrefillBc32 && sk < S) {
                uint off = (b * S + sk) * (kDecodeKVHeads * kPrefillD32)
                         + h_kv * kPrefillD32 + col;
                v_tg[row][col] = qw_to_f32(V[off]);
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);

        // ===== p * V accumulation =====
        for (int rr = 0; rr < kRowsPerHead32; ++rr) {
            uint s_idx = q_start + my_hq * kRowsPerHead32 + uint(rr);
            if (s_idx >= S) continue;
            for (int r = 0; r < kPrefillBc32; ++r) {
                uint sk = k_blk + uint(r);
                if (sk >= S) break;
                float s = s_val[rr][r];
                if (s == -INFINITY) continue;
                float p = qw_fast_exp(s - m_i[rr]);
                for (int d = 0; d < kDPer32; ++d) {
                    int d_idx = my_lane * kDPer32 + d;
                    o_reg[rr][d] += p * v_tg[r][d_idx];
                }
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    // ===== Final writeback =====
    for (int rr = 0; rr < kRowsPerHead32; ++rr) {
        uint s_idx = q_start + my_hq * kRowsPerHead32 + uint(rr);
        if (s_idx >= S) continue;
        for (int d = 0; d < kDPer32; ++d) {
            int d_idx = my_lane * kDPer32 + d;
            uint off = (b * S + s_idx) * (qwen::kFullHeads * kPrefillD32)
                     + h_q * kPrefillD32 + d_idx;
            O[off] = qw_to_f16(o_reg[rr][d] / max(l_i[rr], 1e-30f));
        }
    }
}
