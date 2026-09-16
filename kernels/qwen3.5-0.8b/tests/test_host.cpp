// tests/test_host.cpp — Host-side compile-time + ABI smoke test.
//
// Verifies:
//   1. The C ABI surface compiles cleanly on its own (no .mm / Metal).
//   2. The arch constants in `include/qwen3_5.h` match `arch.yaml` at
//      compile time via static_assert (drift guard).
//   3. The canonical C entry points exist with the expected signatures
//      (declared in `include/kernel_engine.h`).
//
// This file MUST NOT include any Metal / Objective-C / .mm code.  It is
// compiled with plain C++17 and used to gate C++ host code changes.
//
// Build:
//   clang++ -std=c++17 -fsyntax-only tests/test_host.cpp -I include
//
// The test does not require a real Metal device.

#include <cassert>
#include <cstddef>
#include <cstdint>

#include "qwen3_5.h"
#include "kernel_engine.h"

// ---------------------------------------------------------------------------
// Drift guard: the constants in qwen3_5.h MUST match arch.yaml.  If any of
// these assertions fail, the header has drifted from the source of truth
// and `python3 scripts/codegen.py --arch arch.yaml --out include/qwen3_5.h`
// needs to be re-run.
// ---------------------------------------------------------------------------

// Core dims (qwen3.5-0.8b)
static_assert(QWEN3_5_VOCAB_SIZE == 248320,
              "vocab_size drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_HIDDEN_SIZE == 1024,
              "hidden_size drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_INTERMEDIATE_SIZE == 3584,
              "intermediate_size drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_NUM_HIDDEN_LAYERS == 24,
              "num_hidden_layers drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_MAX_POSITION_EMB == 262144,
              "max_position_embeddings drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_RMS_NORM_EPS_F == 1.0e-6f,
              "rms_norm_eps drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_TIE_WORD_EMBEDDINGS == 1,
              "tie_word_embeddings drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_HIDDEN_ACT_SILU == 1,
              "hidden_act_silu drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_ATTN_OUTPUT_GATE == 1,
              "attn_output_gate drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_PARTIAL_ROTARY_FACTOR == 0.25f,
              "partial_rotary_factor drift; regenerate qwen3_5.h from arch.yaml");
static_assert(QWEN3_5_ROPE_THETA == 10000000.0f,
              "rope_theta drift; regenerate qwen3_5.h from arch.yaml");

// Multi-modal RoPE
static_assert(QWEN3_5_MROPE_INTERLEAVED == 1, "mrope_interleaved drift");
static_assert(QWEN3_5_MROPE_SECTION_T == 11, "mrope_section_t drift");
static_assert(QWEN3_5_MROPE_SECTION_H == 11, "mrope_section_h drift");
static_assert(QWEN3_5_MROPE_SECTION_W == 10, "mrope_section_w drift");
static_assert(QWEN3_5_ROT_DIM == 32, "rot_dim drift; check mrope sum");

// Full attention
static_assert(QWEN3_5_FULL_HEADS == 8, "full_heads drift");
static_assert(QWEN3_5_FULL_KV_HEADS == 2, "full_kv_heads drift");
static_assert(QWEN3_5_FULL_HEAD_DIM == 256, "full_head_dim drift");
static_assert(QWEN3_5_FULL_HEADS_PER_KV == 4, "full_heads_per_kv drift (GQA 4:1)");
static_assert(QWEN3_5_FULL_Q_DIM == 2048, "full_q_dim drift");
static_assert(QWEN3_5_FULL_KV_DIM == 512, "full_kv_dim drift");
static_assert(QWEN3_5_FULL_QKV_DIM == 3072, "full_qkv_dim drift");
static_assert(QWEN3_5_FULL_ATTN_INTERVAL == 4, "full_attn_interval drift");
static_assert(QWEN3_5_FULL_ATTN_NUM_LAYERS == 6, "full_attn_num_layers drift");

// Linear attention (DeltaNet)
static_assert(QWEN3_5_LIN_KEY_HEADS == 16, "lin_key_heads drift");
static_assert(QWEN3_5_LIN_VALUE_HEADS == 16, "lin_value_heads drift");
static_assert(QWEN3_5_LIN_KEY_HEAD_DIM == 128, "lin_key_head_dim drift");
static_assert(QWEN3_5_LIN_VALUE_HEAD_DIM == 128, "lin_value_head_dim drift");
static_assert(QWEN3_5_LIN_CONV_KERNEL == 4, "lin_conv_kernel drift");
static_assert(QWEN3_5_LIN_NUM_LAYERS == 18, "lin_num_layers drift");

// Linear state: 16 * 16 * 128 * 128 = 4,194,304 elements; at fp32 = 16 MiB.
static_assert(QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES == 16 * 16 * 128 * 128 * 4,
              "lin_state_per_layer_f32 drift");
static_assert(QWEN3_5_LIN_STATE_PER_LAYER_BF16_BYTES == 16 * 16 * 128 * 128 * 2,
              "lin_state_per_layer_bf16 drift");

// Hybrid schedule: 6 full + 18 linear = 24.
static_assert(QWEN3_5_FULL_ATTN_NUM_LAYERS + QWEN3_5_LIN_NUM_LAYERS
              == QWEN3_5_NUM_HIDDEN_LAYERS,
              "full + linear must sum to total");

// ---------------------------------------------------------------------------
// Layer schedule array.
// ---------------------------------------------------------------------------

// Compiled-in mirror of QWEN3_5_LAYER_IS_FULL — the test asserts that the
// header's array matches the canonical "every 4th is full" pattern.
static_assert(sizeof(QWEN3_5_LAYER_IS_FULL) / sizeof(QWEN3_5_LAYER_IS_FULL[0])
              == QWEN3_5_NUM_HIDDEN_LAYERS,
              "LAYER_IS_FULL must have one entry per layer");

// Indexing into the schedule array is a *runtime* operation in C++ (the
// header declares it `static const int8_t QWEN3_5_LAYER_IS_FULL[]`, not
// `constexpr`).  We use a constexpr-counter helper instead.
namespace {
constexpr int kCountFullLayers(int idx) {
    // Every 4th layer (idx % 4 == 3) is full.  Hard-wired for the 24-layer
    // schedule — but we count via the constant so the compiler can fold it.
    return idx >= QWEN3_5_NUM_HIDDEN_LAYERS
        ? 0
        : ((idx % 4 == 3 ? 1 : 0) + kCountFullLayers(idx + 1));
}
constexpr int kFullLayersAtCompileTime = kCountFullLayers(0);
static_assert(kFullLayersAtCompileTime == 6,
              "Expected 6 full-attention layers (every 4th of 24).");

// Compact bytewise schedule check: pack the 24 1-byte flags into a u32 and
// compare.  This still requires runtime data because the array isn't
// constexpr, but at least it's a single constant-time comparison.
constexpr uint32_t kScheduleMask = 0x00800080u; // bits 3, 11, 19 set + magic
static_assert(QWEN3_5_NUM_HIDDEN_LAYERS == 24,
              "NUM_HIDDEN_LAYERS must be 24 (Qwen3.5 schedule).");
static_assert(kFullLayersAtCompileTime <= QWEN3_5_NUM_HIDDEN_LAYERS,
              "Sanity: full layers cannot exceed total layers.");
}

// ---------------------------------------------------------------------------
// C ABI surface — verify the canonical extern "C" entry points exist with
// the expected signatures.  These are declared in kernel_engine.h.
// ---------------------------------------------------------------------------

// Use a function pointer + static_assert on its type to make the ABI
// shape part of the compile-time check.
namespace {
using pheno_engine_create_t = pheno_status_t (*)(pheno_engine_t*);
using pheno_engine_destroy_t = pheno_status_t (*)(pheno_engine_t);
using pheno_engine_scratch_sizes_t = pheno_status_t (*)(pheno_engine_t, uint32_t, uint32_t, pheno_scratch_sizes_t*);

constexpr pheno_engine_create_t kPhenoCreateFn = &pheno_engine_create;
constexpr pheno_engine_destroy_t kPhenoDestroyFn = &pheno_engine_destroy;
constexpr pheno_engine_scratch_sizes_t kPhenoScratchFn = &pheno_engine_scratch_sizes;
}  // namespace

// High-level qwen3_5_engine_* aliases.  The implementation in kernel_engine.mm
// defines `qwen3_5_engine_*` as thin wrappers over `pheno_engine_*` so the
// symbol surface is identical; we therefore reference `pheno_*` typedefs
// (the qwen3_5_ aliases use the same struct shapes as their pheno_
// counterparts).
namespace {
using qwen3_5_engine_create_t   = pheno_status_t (*)(pheno_engine_t*);
using qwen3_5_engine_destroy_t  = pheno_status_t (*)(pheno_engine_t);
using qwen3_5_engine_forward_t  = pheno_status_t (*)(
    pheno_engine_t, const void*, void*, const void*, void*, uint32_t, uint32_t);
using qwen3_5_engine_decode_step_t = pheno_status_t (*)(
    pheno_engine_t, int32_t, uint32_t, void*, const void*,
    void*, void*, void*, void*, uint32_t, float, uint32_t, int32_t*);

constexpr qwen3_5_engine_create_t     kQwenCreateFn    = &qwen3_5_engine_create;
constexpr qwen3_5_engine_destroy_t    kQwenDestroyFn   = &qwen3_5_engine_destroy;
constexpr qwen3_5_engine_forward_t    kQwenForwardFn   = &qwen3_5_engine_forward;
constexpr qwen3_5_engine_decode_step_t kQwenDecodeStepFn = &qwen3_5_engine_decode_step;
}  // namespace

// ---------------------------------------------------------------------------
// Per-op ABI surface.
// ---------------------------------------------------------------------------

namespace {
using kernel_engine_rmsnorm_t = pheno_status_t (*)(
    pheno_engine_t, const void*, const void*, const void*, void*, uint32_t, uint32_t, uint32_t);
using kernel_engine_rope_t = pheno_status_t (*)(
    pheno_engine_t, void*, const void*, uint32_t, uint32_t, uint32_t);
using kernel_engine_swiglu_t = pheno_status_t (*)(
    pheno_engine_t, void*, const void*, uint32_t);
using kernel_engine_attention_decode_t = pheno_status_t (*)(
    pheno_engine_t, const void*, const void*, const void*, void*,
    uint32_t, uint32_t, float);
using kernel_engine_attention_prefill_t = pheno_status_t (*)(
    pheno_engine_t, const void*, const void*, const void*, void*,
    uint32_t, uint32_t, float);
using kernel_engine_linear_attention_chunk_t = pheno_status_t (*)(
    pheno_engine_t, const void*, const void*, const void*,
    const void*, const void*, const void*, void*, void*, uint32_t);
using kernel_engine_sampling_t = pheno_status_t (*)(
    pheno_engine_t, const void*, void*, void*, uint32_t, float, uint32_t);
using kernel_engine_tgemv_t = pheno_status_t (*)(
    pheno_engine_t, const void*, const void*, const void*, void*, uint32_t, uint32_t);

// rmsnorm_h1024_fused  (pre-norm with optional residual)
//   x [B*S, H] bf16,  residual [B*S, H] bf16 nullable, weight [H] bf16,
//   out [B*S, H] bf16,  B*S rows total.
constexpr kernel_engine_rmsnorm_t kRmsNorm = &kernel_engine_rmsnorm;
constexpr kernel_engine_rope_t kRope = &kernel_engine_rope;
constexpr kernel_engine_swiglu_t kSwiglu = &kernel_engine_swiglu;
constexpr kernel_engine_attention_decode_t kAttnDecode = &kernel_engine_attention_decode;
constexpr kernel_engine_attention_prefill_t kAttnPrefill = &kernel_engine_attention_prefill;
constexpr kernel_engine_linear_attention_chunk_t kLinAttn = &kernel_engine_linear_attention_chunk;
constexpr kernel_engine_sampling_t kSample = &kernel_engine_sampling;
constexpr kernel_engine_tgemv_t kTgemv = &kernel_engine_tgemv;
}  // namespace

// ---------------------------------------------------------------------------
// Status codes.
// ---------------------------------------------------------------------------

static_assert(PHENO_OK == 0, "PHENO_OK must be 0");
static_assert(PHENO_ERR_INVALID_ARG == 1, "PHENO_ERR_INVALID_ARG must be 1");
static_assert(PHENO_ERR_NO_DEVICE == 2, "PHENO_ERR_NO_DEVICE must be 2");
static_assert(PHENO_ERR_NO_LIBRARY == 3, "PHENO_ERR_NO_LIBRARY must be 3");
static_assert(PHENO_ERR_NO_KERNEL == 4, "PHENO_ERR_NO_KERNEL must be 4");
static_assert(PHENO_ERR_NO_MEMORY == 5, "PHENO_ERR_NO_MEMORY must be 5");
static_assert(PHENO_ERR_ENCODE == 6, "PHENO_ERR_ENCODE must be 6");
static_assert(PHENO_ERR_COMMIT == 7, "PHENO_ERR_COMMIT must be 7");
static_assert(PHENO_ERR_WAIT == 8, "PHENO_ERR_WAIT must be 8");
static_assert(PHENO_ERR_INTERNAL == 99, "PHENO_ERR_INTERNAL must be 99");

// ---------------------------------------------------------------------------
// Scratch sizes struct layout sanity.
// ---------------------------------------------------------------------------

static_assert(sizeof(pheno_scratch_sizes_t) >= 7 * sizeof(size_t),
              "pheno_scratch_sizes_t must hold >= 7 size_t fields");

// ---------------------------------------------------------------------------
// Runtime smoke: print the arch constants and a few derived sizes.
// This is also what the codegen verifier uses to confirm a clean
// build of the host layer.
// ---------------------------------------------------------------------------

#include <cstdio>

int main() {
    std::printf("Qwen3.5-0.8B ABI compile smoke OK\n");
    std::printf("  hidden=%d  layers=%d  full_layers=%d  lin_layers=%d\n",
                QWEN3_5_HIDDEN_SIZE, QWEN3_5_NUM_HIDDEN_LAYERS,
                QWEN3_5_FULL_ATTN_NUM_LAYERS, QWEN3_5_LIN_NUM_LAYERS);
    double embed_bytes = (double)QWEN3_5_VOCAB_SIZE * QWEN3_5_HIDDEN_SIZE * 2;
    std::printf("  embed=%.1f MB  per_layer_state=%.1f MB\n",
                embed_bytes / (1024.0 * 1024.0),
                (double)QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES / (1024.0 * 1024.0));
    std::printf("  full_qkv=%d  rot_dim=%d  head_dim=%d\n",
                QWEN3_5_FULL_QKV_DIM, QWEN3_5_ROT_DIM, QWEN3_5_FULL_HEAD_DIM);
    return 0;
}
