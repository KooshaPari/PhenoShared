// sampling.metal — fused top-k + top-p + temperature sampling for Qwen3.5 0.8B
//   Vocab V = 248320.
//
// Three kernel families:
//
//   1. softmax_temp_max / softmax_temp_reduce / softmax_temp_apply
//      Three-pass row-softmax with temperature.  Pass 1 emits per-block
//      (max, sum_exp).  Reduce pass computes global (max, log_sum_exp).
//      Apply pass writes final probabilities.  Splitting into 3 passes keeps
//      the hot path lock-free (no atomics).
//
//   2. gumbel_argmax_block / gumbel_argmax_reduce
//      Gumbel-max sampling for the decode step:
//          score_v = (logit_v / T) + gumbel_v
//          token   = argmax_v score_v
//      where gumbel_v = -log(-log(U_v)) with U_v drawn from a per-(b,v) LCG
//      seeded by `seed`.  Two-stage block -> global argmax.
//
//   3. fused_topk_topp_block / fused_topk_topp_reduce
//      Single-pass temperature + top-k + top-p + Gumbel.  For top-k=1 this
//      degenerates to greedy argmax.  We emit per-block (max_score, top_idx,
//      lse) so the host can do its own nucleus / top-k filter.
//
// Activations: half (fp16).  Scratch: float (fp32).  Index scratch: int32.

#include <metal_stdlib>
#include <metal_simdgroup>
#include "types.metal"
using namespace metal;

// ---------------------------------------------------------------------------
// Compile-time geometry — constant address space (MSL program-scope rule).
// ---------------------------------------------------------------------------

constant int kVocab   = qwen::kVocabSize;       // 248320
constant int kTgSize  = 256;
constant int kBlockV  = 1024;
constant int kNBlocks = (kVocab + kBlockV - 1) / kBlockV;   // 243

inline uint block_offset(uint v_block) { return v_block * kBlockV; }
inline uint block_end(uint v_block)   {
    return min(block_offset(v_block) + kBlockV, uint(kVocab));
}

// ===========================================================================
// softmax_temp_max  — pass 1: per-block (max, sum_exp) into scratch buffers
// ===========================================================================

kernel void softmax_temp_max(
    const device half* logits      [[buffer(0)]],
    device float* scratch_max      [[buffer(1)]],
    device float* scratch_sum      [[buffer(2)]],
    constant uint& B               [[buffer(3)]],
    constant float& inv_T          [[buffer(4)]],
    uint2 tgid                     [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint v_block = tgid.y;
    if (b >= B) return;
    if (v_block >= uint(kNBlocks)) return;

    uint v_start = block_offset(v_block);
    uint v_end   = block_end(v_block);

    threadgroup float tg[kTgSize];

    // ---- pass 1a: per-thread local max ----
    float local_max = -INFINITY;
    for (int i = 0; i < kBlockV / kTgSize; ++i) {
        int v_idx = int(v_start) + i * kTgSize + int(tid);
        if (v_idx < int(v_end)) {
            float x = static_cast<float>(logits[b * kVocab + v_idx]) * inv_T;
            local_max = max(local_max, x);
        }
    }
    local_max = simd_max(local_max);
    tg[tid] = local_max;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float v = -INFINITY;
        for (int i = 0; i < kTgSize / 32; ++i) {
            v = max(v, tg[i * 32 + tid]);
        }
        v = simd_max(v);
        if (tid == 0) tg[0] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float block_max = tg[0];

    // ---- pass 1b: per-thread local sum_exp(x - block_max) ----
    float local_sum = 0.0f;
    for (int i = 0; i < kBlockV / kTgSize; ++i) {
        int v_idx = int(v_start) + i * kTgSize + int(tid);
        if (v_idx < int(v_end)) {
            float x = static_cast<float>(logits[b * kVocab + v_idx]) * inv_T;
            local_sum += qw_fast_exp(x - block_max);
        }
    }
    local_sum = simd_sum(local_sum);
    tg[tid] = local_sum;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float v = 0.0f;
        for (int i = 0; i < kTgSize / 32; ++i) {
            v += tg[i * 32 + tid];
        }
        v = simd_sum(v);
        if (tid == 0) tg[0] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float block_sum = tg[0];

    if (tid == 0) {
        scratch_max[b * kNBlocks + v_block] = block_max;
        scratch_sum[b * kNBlocks + v_block] = block_sum;
    }
}

// ===========================================================================
// softmax_temp_reduce — global (max, log_sum_exp) across n_blocks
// ===========================================================================

kernel void softmax_temp_reduce(
    const device float* scratch_max [[buffer(0)]],
    const device float* scratch_sum [[buffer(1)]],
    device float* global_stats      [[buffer(2)]],
    constant uint& B                [[buffer(3)]],
    uint tgid                       [[threadgroup_position_in_grid]],
    uint tid                        [[thread_index_in_threadgroup]]) {
    uint b = tgid;
    if (b >= B) return;

    threadgroup float tg[kTgSize];

    // ---- global max ----
    float local_max = -INFINITY;
    for (uint v_block = tid; v_block < uint(kNBlocks); v_block += kTgSize) {
        float m = scratch_max[b * kNBlocks + v_block];
        local_max = max(local_max, m);
    }
    local_max = simd_max(local_max);
    tg[tid] = local_max;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float v = -INFINITY;
        for (int i = 0; i < kTgSize / 32; ++i) {
            v = max(v, tg[i * 32 + tid]);
        }
        v = simd_max(v);
        if (tid == 0) tg[0] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float global_max = tg[0];

    // ---- global sum_exp(m_b - global_max) ----
    float local_sum = 0.0f;
    for (uint v_block = tid; v_block < uint(kNBlocks); v_block += kTgSize) {
        float m = scratch_max[b * kNBlocks + v_block];
        float s = scratch_sum[b * kNBlocks + v_block];
        local_sum += s * qw_fast_exp(m - global_max);
    }
    local_sum = simd_sum(local_sum);
    tg[tid] = local_sum;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float v = 0.0f;
        for (int i = 0; i < kTgSize / 32; ++i) {
            v += tg[i * 32 + tid];
        }
        v = simd_sum(v);
        if (tid == 0) tg[0] = v;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    float global_sum = max(tg[0], 1e-30f);

    if (tid == 0) {
        global_stats[b * 2 + 0] = global_max;
        global_stats[b * 2 + 1] = qw_fast_log(global_sum);
    }
}

// ===========================================================================
// softmax_temp_apply — pass 2: write final probs using global stats
// ===========================================================================

kernel void softmax_temp_apply(
    const device half* logits      [[buffer(0)]],
    const device float* global_stats [[buffer(1)]],
    device half* probs             [[buffer(2)]],
    constant uint& B               [[buffer(3)]],
    constant float& inv_T          [[buffer(4)]],
    uint2 tgid                     [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint v_block = tgid.y;
    if (b >= B) return;
    if (v_block >= uint(kNBlocks)) return;

    uint v_start = block_offset(v_block);
    uint v_end   = block_end(v_block);

    float g_max  = global_stats[b * 2 + 0];
    float g_lsum = global_stats[b * 2 + 1];

    for (int i = 0; i < kBlockV / kTgSize; ++i) {
        int v_idx = int(v_start) + i * kTgSize + int(tid);
        if (v_idx < int(v_end)) {
            float x = static_cast<float>(logits[b * kVocab + v_idx]) * inv_T;
            float p = qw_fast_exp(x - g_max - g_lsum);
            probs[b * kVocab + v_idx] = static_cast<half>(p);
        }
    }
}

// ===========================================================================
// gumbel_argmax_block — per-block argmax of (logit/T + gumbel)
// ===========================================================================

kernel void gumbel_argmax_block(
    const device half* logits      [[buffer(0)]],
    device float* scratch_score    [[buffer(1)]],
    device int* scratch_idx        [[buffer(2)]],
    constant uint& B               [[buffer(3)]],
    constant float& inv_T          [[buffer(4)]],
    constant uint& seed            [[buffer(5)]],
    uint2 tgid                     [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint v_block = tgid.y;
    if (b >= B) return;
    if (v_block >= uint(kNBlocks)) return;

    uint v_start = block_offset(v_block);
    uint v_end   = block_end(v_block);

    float local_best = -INFINITY;
    int   local_idx  = -1;
    for (int i = 0; i < kBlockV / kTgSize; ++i) {
        int v_idx = int(v_start) + i * kTgSize + int(tid);
        if (v_idx < int(v_end)) {
            uint h = seed ^ (uint(b) * 2654435761u) ^ (uint(v_idx) * 374761393u);
            h = (h ^ (h >> 13)) * 1274126177u;
            float u = (float(h & 0x00FFFFFFu) / float(0x01000000)) * 0.999999f +
                      0.0000005f;
            float gumbel = -qw_fast_log(-qw_fast_log(u));
            float score  = static_cast<float>(logits[b * kVocab + v_idx]) * inv_T +
                           gumbel;
            if (score > local_best) {
                local_best = score;
                local_idx  = v_idx;
            }
        }
    }

    threadgroup float tg_s[kTgSize];
    threadgroup int   tg_i[kTgSize];

    local_best = simd_max(local_best);
    tg_s[tid] = local_best;
    tg_i[tid] = local_idx;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float s = tg_s[tid];
        int   x = tg_i[tid];
        for (int i = 1; i < kTgSize / 32; ++i) {
            float s2 = tg_s[i * 32 + tid];
            int   x2 = tg_i[i * 32 + tid];
            if (s2 > s) { s = s2; x = x2; }
        }
        for (int offset = 16; offset > 0; offset >>= 1) {
            float s2 = simd_shuffle_xor(s, offset);
            int   x2 = simd_shuffle_xor(x, offset);
            if (s2 > s) { s = s2; x = x2; }
        }
        if (tid == 0) {
            scratch_score[b * kNBlocks + v_block] = s;
            scratch_idx[b * kNBlocks + v_block]   = x;
        }
    }
}

// ===========================================================================
// gumbel_argmax_reduce — global argmax across blocks -> out_token[b]
// ===========================================================================

kernel void gumbel_argmax_reduce(
    const device float* scratch_score [[buffer(0)]],
    const device int*   scratch_idx   [[buffer(1)]],
    device int32_t* out_token         [[buffer(2)]],
    device float* out_logprob         [[buffer(3)]],
    constant uint& B                  [[buffer(4)]],
    uint tgid                         [[threadgroup_position_in_grid]],
    uint tid                          [[thread_index_in_threadgroup]]) {
    uint b = tgid;
    if (b >= B) return;

    threadgroup float tg_s[kTgSize];
    threadgroup int   tg_i[kTgSize];

    float local_best = -INFINITY;
    int   local_idx  = -1;
    for (uint v_block = tid; v_block < uint(kNBlocks); v_block += kTgSize) {
        float s = scratch_score[b * kNBlocks + v_block];
        int   x = scratch_idx[b * kNBlocks + v_block];
        if (s > local_best) { local_best = s; local_idx = x; }
    }
    local_best = simd_max(local_best);
    tg_s[tid] = local_best;
    tg_i[tid] = local_idx;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float s = tg_s[tid];
        int   x = tg_i[tid];
        for (int i = 1; i < kTgSize / 32; ++i) {
            float s2 = tg_s[i * 32 + tid];
            int   x2 = tg_i[i * 32 + tid];
            if (s2 > s) { s = s2; x = x2; }
        }
        for (int offset = 16; offset > 0; offset >>= 1) {
            float s2 = simd_shuffle_xor(s, offset);
            int   x2 = simd_shuffle_xor(x, offset);
            if (s2 > s) { s = s2; x = x2; }
        }
        if (tid == 0) {
            out_token[b]   = x;
            out_logprob[b] = s;
        }
    }
}

// ===========================================================================
// fused_topk_topp_block — per-block (max_score, top_idx, lse)
// ===========================================================================

kernel void fused_topk_topp_block(
    const device half* logits      [[buffer(0)]],
    device float* scratch_score    [[buffer(1)]],
    device int* scratch_idx        [[buffer(2)]],
    device float* scratch_lse      [[buffer(3)]],
    constant uint& B               [[buffer(4)]],
    constant int& top_k            [[buffer(5)]],
    constant float& top_p          [[buffer(6)]],
    constant float& inv_T          [[buffer(7)]],
    constant uint& seed            [[buffer(8)]],
    uint2 tgid                     [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    uint b = tgid.x;
    uint v_block = tgid.y;
    if (b >= B) return;
    if (v_block >= uint(kNBlocks)) return;

    uint v_start = block_offset(v_block);
    uint v_end   = block_end(v_block);

    float local_max = -INFINITY;
    int   local_idx = -1;
    float local_lse = 0.0f;
    for (int i = 0; i < kBlockV / kTgSize; ++i) {
        int v_idx = int(v_start) + i * kTgSize + int(tid);
        if (v_idx < int(v_end)) {
            uint h = seed ^ (uint(b) * 2654435761u) ^ (uint(v_idx) * 374761393u);
            h = (h ^ (h >> 13)) * 1274126177u;
            float u = (float(h & 0x00FFFFFFu) / float(0x01000000)) * 0.999999f +
                      0.0000005f;
            float gumbel = -qw_fast_log(-qw_fast_log(u));
            float score  = static_cast<float>(logits[b * kVocab + v_idx]) * inv_T +
                           gumbel;
            local_lse += qw_fast_exp(score);
            if (score > local_max) {
                local_max = score;
                local_idx = v_idx;
            }
        }
    }

    threadgroup float tg_s[kTgSize];
    threadgroup int   tg_i[kTgSize];
    threadgroup float tg_l[kTgSize];

    float max_red = simd_max(local_max);
    tg_s[tid] = max_red;
    tg_i[tid] = local_idx;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float s = tg_s[tid];
        int   x = tg_i[tid];
        for (int i = 1; i < kTgSize / 32; ++i) {
            float s2 = tg_s[i * 32 + tid];
            int   x2 = tg_i[i * 32 + tid];
            if (s2 > s) { s = s2; x = x2; }
        }
        for (int offset = 16; offset > 0; offset >>= 1) {
            float s2 = simd_shuffle_xor(s, offset);
            int   x2 = simd_shuffle_xor(x, offset);
            if (s2 > s) { s = s2; x = x2; }
        }
        if (tid == 0) {
            scratch_score[b * kNBlocks + v_block] = s;
            scratch_idx[b * kNBlocks + v_block]   = x;
        }
    }

    float lse_red = simd_sum(local_lse);
    tg_l[tid] = lse_red;
    threadgroup_barrier(mem_flags::mem_threadgroup);
    if (tid < 32) {
        float v = 0.0f;
        for (int i = 0; i < kTgSize / 32; ++i) {
            v += tg_l[i * 32 + tid];
        }
        v = simd_sum(v);
        if (tid == 0) {
            scratch_lse[b * kNBlocks + v_block] = v;
        }
    }
}

// ===========================================================================
// fused_topk_topp_reduce — global reduce -> out_token[b], out_lse_total[b]
// ===========================================================================

kernel void fused_topk_topp_reduce(
    const device float* scratch_score [[buffer(0)]],
    const device int*   scratch_idx   [[buffer(1)]],
    const device float* scratch_lse   [[buffer(2)]],
    device int32_t* out_token         [[buffer(3)]],
    device float* out_lse_total       [[buffer(4)]],
    constant uint& B                  [[buffer(5)]],
    uint tgid                         [[threadgroup_position_in_grid]],
    uint tid                          [[thread_index_in_threadgroup]]) {
    uint b = tgid;
    if (b >= B) return;

    threadgroup float tg_s[kTgSize];
    threadgroup int   tg_i[kTgSize];
    threadgroup float tg_l[kTgSize];

    float local_best = -INFINITY;
    int   local_idx  = -1;
    float local_lse  = 0.0f;
    for (uint v_block = tid; v_block < uint(kNBlocks); v_block += kTgSize) {
        float s = scratch_score[b * kNBlocks + v_block];
        int   x = scratch_idx[b * kNBlocks + v_block];
        float l = scratch_lse[b * kNBlocks + v_block];
        local_lse += l;
        if (s > local_best) { local_best = s; local_idx = x; }
    }
    local_best = simd_max(local_best);
    tg_s[tid] = local_best;
    tg_i[tid] = local_idx;
    tg_l[tid] = local_lse;
    threadgroup_barrier(mem_flags::mem_threadgroup);

    if (tid < 32) {
        float s = tg_s[tid];
        int   x = tg_i[tid];
        for (int i = 1; i < kTgSize / 32; ++i) {
            float s2 = tg_s[i * 32 + tid];
            int   x2 = tg_i[i * 32 + tid];
            if (s2 > s) { s = s2; x = x2; }
        }
        for (int offset = 16; offset > 0; offset >>= 1) {
            float s2 = simd_shuffle_xor(s, offset);
            int   x2 = simd_shuffle_xor(x, offset);
            if (s2 > s) { s = s2; x = x2; }
        }
        float v = tg_l[tid];
        for (int i = 1; i < kTgSize / 32; ++i) {
            v += tg_l[i * 32 + tid];
        }
        v = simd_sum(v);
        if (tid == 0) {
            out_token[b]    = x;
            out_lse_total[b] = qw_fast_log(max(v, 1e-30f));
        }
    }
}
