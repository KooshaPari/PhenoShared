// types.metal — shared types, constants, and helpers for Qwen3.5 0.8B Metal kernels
// Target: Apple Silicon M-series (Metal 3+)
//
// Single source of truth: this file is #included by every kernel file. All
// numeric constants live in the `constant` address space at file scope; do not
// declare them inside kernel bodies (Metal does not allow it).
//
// Convention (per task constraints):
//   - Activations / weights: `half` (fp16). The Qwen3.5 MLX default is bf16,
//     but fp16 has better Apple-M-series GPU intrinsic coverage (bf16 needs
//     the `metal_bf16` extension and is not always MMA-friendly).
//   - Accumulation: `float` (fp32) for numerical stability.
//   - Recurrent state for DeltaNet linear attention: `float` to avoid drift.

#ifndef PHENO_QWEN3_5_TYPES_H
#define PHENO_QWEN3_5_TYPES_H

#include <metal_stdlib>
#include <metal_simdgroup_matrix>
#include <metal_simdgroup>

using namespace metal;

// ---------------------------------------------------------------------------
// All Qwen3.5 0.8B architecture constants live in the `qwen` namespace under
// the `constant` address space.  Mirrors include/qwen3_5.h (keep in sync
// via codegen).
// ---------------------------------------------------------------------------

namespace qwen {

// Core dims
constant int   kVocabSize        = 248320;
constant int   kHiddenSize       = 1024;
constant int   kIntermediateSize = 3584;
constant int   kNumHiddenLayers  = 24;
constant float kRmsNormEps       = 1.0e-6f;

// Full attention (GQA 4:1)
constant int   kFullHeads        = 8;
constant int   kFullKvHeads      = 2;
constant int   kFullHeadDim      = 256;
constant int   kFullQDim         = 2048;     // 8 * 256
constant int   kFullKvDim        = 512;      // 2 * 256
constant int   kFullQkvDim       = 3072;     // 2048 + 2*512
constant int   kFullHeadsPerKv   = 4;        // GQA 4:1
constant int   kFullAttnInterval = 4;
constant int   kFullAttnNumLayers = 6;

// Partial rotary (M-RoPE)
constant int   kRotDim           = 32;       // 0.25 * 256
constant float kRopeTheta        = 10000000.0f;
constant int   kMRopeSectionT    = 11;
constant int   kMRopeSectionH    = 11;
constant int   kMRopeSectionW    = 10;

// Linear attention (DeltaNet)
constant int   kLinKeyHeads      = 16;
constant int   kLinValueHeads    = 16;
constant int   kLinKeyHeadDim    = 128;
constant int   kLinValueHeadDim  = 128;
constant int   kLinConvKernel    = 4;
constant int   kLinNumLayers     = 18;

// Derived
constant int   kRotDimHalf       = kRotDim / 2;   // 16
constant int   kLinStateElements = kLinKeyHeads * kLinValueHeads * kLinValueHeadDim * kLinKeyHeadDim;
constant int   kFullAttnIndices[6] = {3, 7, 11, 15, 19, 23};

// ---------------------------------------------------------------------------
// Bundled MODEL descriptor — single read-only constant struct that callers
// can pass as one [[buffer(N)]] argument when they need many constants at
// once.  Declared with the `constant` address space so the MSL compiler is
// happy (program-scope variables must be constant, not constexpr or plain).
//
// All constants here MUST stay in sync with arch.yaml and the C header
// include/qwen3_5.h.  Edit only via codegen.
// ---------------------------------------------------------------------------

struct ModelConstants {
    int   vocab_size;
    int   hidden_size;
    int   intermediate_size;
    int   num_hidden_layers;
    float rms_norm_eps;

    int   full_heads;
    int   full_kv_heads;
    int   full_head_dim;
    int   full_q_dim;
    int   full_kv_dim;
    int   full_qkv_dim;
    int   full_heads_per_kv;
    int   full_attn_interval;
    int   full_attn_num_layers;

    int   rot_dim;
    int   rot_dim_half;
    float rope_theta;
    int   mrope_section_t;
    int   mrope_section_h;
    int   mrope_section_w;

    int   lin_key_heads;
    int   lin_value_heads;
    int   lin_key_head_dim;
    int   lin_value_head_dim;
    int   lin_conv_kernel;
    int   lin_num_layers;
    int   lin_state_elements;

    int   full_attn_indices[6];
};

// File-scope MODEL with the canonical Qwen3.5 0.8B values.  Kernels may pass
// `&MODEL` as a single [[buffer(N)]] argument or pull individual fields.
//
// IMPORTANT: declared with `constant` address space (not `constexpr`); MSL
// rejects program-scope variables that are not `constant`.
constant ModelConstants MODEL = {
    /*vocab_size*/            248320,
    /*hidden_size*/           1024,
    /*intermediate_size*/     3584,
    /*num_hidden_layers*/     24,
    /*rms_norm_eps*/          1.0e-6f,

    /*full_heads*/            8,
    /*full_kv_heads*/         2,
    /*full_head_dim*/         256,
    /*full_q_dim*/            2048,
    /*full_kv_dim*/           512,
    /*full_qkv_dim*/          3072,
    /*full_heads_per_kv*/     4,
    /*full_attn_interval*/    4,
    /*full_attn_num_layers*/  6,

    /*rot_dim*/               32,
    /*rot_dim_half*/          16,
    /*rope_theta*/            10000000.0f,
    /*mrope_section_t*/       11,
    /*mrope_section_h*/       11,
    /*mrope_section_w*/       10,

    /*lin_key_heads*/         16,
    /*lin_value_heads*/       16,
    /*lin_key_head_dim*/      128,
    /*lin_value_head_dim*/    128,
    /*lin_conv_kernel*/       4,
    /*lin_num_layers*/        18,
    /*lin_state_elements*/    16 * 16 * 128 * 128,

    /*full_attn_indices*/     {3, 7, 11, 15, 19, 23},
};

}  // namespace qwen

// ---------------------------------------------------------------------------
// SIMD helpers
// ---------------------------------------------------------------------------

// Apple M-series SIMD width.  Declared `constant` (program scope).
constant int QW_SIMD_WIDTH = 32;
constant int QW_KVEC4     = 4;  // 4-wide vectorized loads/stores

// ---------------------------------------------------------------------------
// Numerical helpers — use fast-math on Apple Silicon (hardware reciprocal
// approximation is well within fp16 mantissa precision for inference).
// ---------------------------------------------------------------------------

inline half  qw_h(half v)                  { return v; }
inline float qw_f(float v)                { return v; }
inline float qw_to_f32(half v)            { return static_cast<float>(v); }
inline half  qw_to_f16(float v)           { return static_cast<half>(v); }
inline half2 qw_h2(half lo, half hi)      { return half2(lo, hi); }
inline half4 qw_h4(half a, half b, half c, half d) { return half4(a, b, c, d); }

inline float qw_fast_inv(float x)         { return metal::fast::divide(1.0f, x); }
inline float qw_fast_rsqrt(float x)       { return metal::fast::rsqrt(x); }
inline float qw_fast_exp(float x)         { return metal::fast::exp(x); }
inline float qw_fast_log(float x)         { return metal::fast::log(x); }
inline float qw_fast_pow(float x, float y) { return metal::fast::pow(x, y); }
inline float qw_fast_sigmoid(float x)     { return 1.0f / (1.0f + metal::fast::exp(-x)); }
inline float qw_fast_silu(float x)        { return x * qw_fast_sigmoid(x); }
inline float qw_fast_cos(float x)         { return metal::fast::cos(x); }
inline float qw_fast_sin(float x)         { return metal::fast::sin(x); }

// Load 4 fp16 values as float4.
inline float4 qw_load4f(const device half* p) {
    return float4(static_cast<float>(p[0]),
                  static_cast<float>(p[1]),
                  static_cast<float>(p[2]),
                  static_cast<float>(p[3]));
}

// Store 4 fp32 values as fp16.
inline void qw_store4f(device half* p, float4 v) {
    p[0] = static_cast<half>(v.x);
    p[1] = static_cast<half>(v.y);
    p[2] = static_cast<half>(v.z);
    p[3] = static_cast<half>(v.w);
}

// ---------------------------------------------------------------------------
// Section picker for M-RoPE (interleaved).
//   idx % 3 == 0  → T
//   idx % 3 == 1  → H
//   idx % 3 == 2  → W
// ---------------------------------------------------------------------------

inline int qw_mrope_section(int k) {
    // Branchless mod-3.  (`k & 3` would be mod-4 — that's a different sequence.)
    int m = k - 3 * (k / 3);
    if (m == 0) return 0;     // T section
    if (m == 1) return 1;     // H section
    return 2;                 // W section
}

#endif  // PHENO_QWEN3_5_TYPES_H
