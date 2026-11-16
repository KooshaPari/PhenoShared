// AUTO-GENERATED from arch.yaml — DO NOT EDIT.
// Regenerate with: python3 python/codegen.py --arch arch.yaml
// Verification: tests/test_codegen.py asserts byte-equality.

#ifndef PHENO_QWEN3_5_0_8B_H
#define PHENO_QWEN3_5_0_8B_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define QWEN3_5_MODEL_ID        "Qwen3.5-0.8B"
#define QWEN3_5_HF_REPO         "Qwen/Qwen3.5-0.8B"
#define QWEN3_5_FAMILY          "qwen3.5"
#define QWEN3_5_KIND            "hybrid_attention"

#define QWEN3_5_VOCAB_SIZE             248320
#define QWEN3_5_HIDDEN_SIZE            1024
#define QWEN3_5_INTERMEDIATE_SIZE      3584
#define QWEN3_5_NUM_HIDDEN_LAYERS      24
#define QWEN3_5_MAX_POSITION_EMB       262144
#define QWEN3_5_RMS_NORM_EPS_F         1.0e-6f
#define QWEN3_5_TIE_WORD_EMBEDDINGS    1
#define QWEN3_5_HIDDEN_ACT_SILU        1
#define QWEN3_5_ATTN_OUTPUT_GATE       1
#define QWEN3_5_PARTIAL_ROTARY_FACTOR  0.25f
#define QWEN3_5_ROPE_THETA             10000000.0f

#define QWEN3_5_MROPE_INTERLEAVED 1
#define QWEN3_5_MROPE_SECTION_T    11
#define QWEN3_5_MROPE_SECTION_H    11
#define QWEN3_5_MROPE_SECTION_W    10
// Total rotated dim = 11 + 11 + 10 = 32 = 0.25 * 256 (head_dim)

#define QWEN3_5_ROT_DIM            32   // = head_dim * partial_rotary_factor


// Full attention (GQA 4:1)

#define QWEN3_5_FULL_HEADS          8
#define QWEN3_5_FULL_KV_HEADS       2
#define QWEN3_5_FULL_HEAD_DIM       256
#define QWEN3_5_FULL_HEADS_PER_KV   (QWEN3_5_FULL_HEADS / QWEN3_5_FULL_KV_HEADS)  // 4
#define QWEN3_5_FULL_Q_DIM          (QWEN3_5_FULL_HEADS    * QWEN3_5_FULL_HEAD_DIM) // 2048
#define QWEN3_5_FULL_KV_DIM         (QWEN3_5_FULL_KV_HEADS * QWEN3_5_FULL_HEAD_DIM) // 512
#define QWEN3_5_FULL_QKV_DIM        (QWEN3_5_FULL_Q_DIM + 2 * QWEN3_5_FULL_KV_DIM)  // 3072

#define QWEN3_5_FULL_ATTN_INTERVAL        4
#define QWEN3_5_FULL_ATTN_NUM_LAYERS      6
// indices 3, 7, 11, 15, 19, 23


// Linear attention (DeltaNet-style gated recurrent)

#define QWEN3_5_LIN_KEY_HEADS        16
#define QWEN3_5_LIN_VALUE_HEADS      16
#define QWEN3_5_LIN_KEY_HEAD_DIM     128
#define QWEN3_5_LIN_VALUE_HEAD_DIM   128
#define QWEN3_5_LIN_CONV_KERNEL      4
#define QWEN3_5_LIN_NUM_LAYERS       18

// Recurrent state per linear layer:
//   [key_heads=16, value_heads=16, value_head_dim=128, key_head_dim=128]
// = 16 * 16 * 128 * 128 = 4,194,304 elements
// At fp32 (4 bytes) = 16 MiB per layer
// At bfloat16 packed (2 bytes) = 8 MiB per layer

#define QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES  (16 * 16 * 128 * 128 * 4)   // 16 MiB
#define QWEN3_5_LIN_STATE_PER_LAYER_BF16_BYTES (16 * 16 * 128 * 128 * 2)   // 8 MiB


// L = linear (DeltaNet), F = full (GQA flash)
// 24 layers; every 4th is full.

static const int8_t QWEN3_5_LAYER_IS_FULL[QWEN3_5_NUM_HIDDEN_LAYERS] = {
    0, 0, 0, 1,   // 0-3
    0, 0, 0, 1,   // 4-7
    0, 0, 0, 1,   // 8-11
    0, 0, 0, 1,   // 12-15
    0, 0, 0, 1,   // 16-19
    0, 0, 0, 1,   // 20-23
};


// Kernel dispatch (DAG-41 — propagates kArchSimdgroupSize)

#define QWEN3_5_SIMDGROUP_SIZE_DEFAULT  32     // Metal simdgroup size
// Backwards-compat alias (DAG-51): keep the old name working for any caller
// that still references QWEN3_5_DEFAULT_SIMDGROUP_SIZE.
#define QWEN3_5_DEFAULT_SIMDGROUP_SIZE  QWEN3_5_SIMDGROUP_SIZE_DEFAULT
#define QWEN3_5_THREADGROUP_SIZE_DEFAULT  256    // 8 * 32
#define QWEN3_5_DTYPE_COMPUTE          "bfloat16"
#define QWEN3_5_DTYPE_ACCUMULATOR       "float"
#define QWEN3_5_DTYPE_STATE_CACHE       "bfloat16"
#define QWEN3_5_DTYPE_RECURRENT_STATE   "float32"

_Static_assert(QWEN3_5_HIDDEN_SIZE == 1024, "hidden_size mismatch");
_Static_assert(QWEN3_5_FULL_HEAD_DIM == 256, "head_dim mismatch");
_Static_assert(QWEN3_5_FULL_HEADS % QWEN3_5_FULL_KV_HEADS == 0, "GQA must divide");
_Static_assert(QWEN3_5_ROT_DIM == 32, "rot dim = 0.25 * 256");
_Static_assert(QWEN3_5_SIMDGROUP_SIZE_DEFAULT == 32, "simdgroup size = 32 (Apple Silicon)");
_Static_assert(QWEN3_5_THREADGROUP_SIZE_DEFAULT % QWEN3_5_SIMDGROUP_SIZE_DEFAULT == 0, "threadgroup must be simdgroup-aligned");

#ifdef __cplusplus
}
#endif

#endif  // PHENO_QWEN3_5_0_8B_H
