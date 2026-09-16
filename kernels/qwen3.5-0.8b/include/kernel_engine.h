// kernel_engine.h — C ABI for the Qwen3.5 0.8B Metal kernel engine.
//
// This is the host-side API.  It is intentionally minimal so the engine can
// be linked from C, C++, Rust (via cty/::cdecl), Zig (via @cImport), or any
// other FFI caller.  All tensor memory is on the Metal device; the host
// passes device pointers and shape constants.

#ifndef PHENO_QWEN_KERNEL_ENGINE_H
#define PHENO_QWEN_KERNEL_ENGINE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "qwen3_5.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Opaque engine handle.
// ---------------------------------------------------------------------------

typedef struct pheno_engine_s* pheno_engine_t;

// ---------------------------------------------------------------------------
// Status codes.
// ---------------------------------------------------------------------------

typedef enum {
    PHENO_OK = 0,
    PHENO_ERR_INVALID_ARG = 1,
    PHENO_ERR_NO_DEVICE  = 2,
    PHENO_ERR_NO_LIBRARY = 3,
    PHENO_ERR_NO_KERNEL  = 4,
    PHENO_ERR_NO_MEMORY  = 5,
    PHENO_ERR_ENCODE     = 6,
    PHENO_ERR_COMMIT     = 7,
    PHENO_ERR_WAIT       = 8,
    PHENO_ERR_INTERNAL   = 99,
} pheno_status_t;

// ---------------------------------------------------------------------------
// Per-layer schedule entry (describes one linear-attention layer's params).
// ---------------------------------------------------------------------------

typedef struct {
    int32_t layer_index;
    int32_t is_full_attention;     // 1 = full, 0 = linear (DeltaNet)
    int32_t conv_kernel_dim;       // 4 for Qwen3.5 0.8B linear
    int32_t num_kv_heads;          // 2 for full, 16 for linear
    int32_t head_dim;              // 256 for full, 128 for linear key/value
    int32_t key_head_dim;          // linear only (0 for full)
    int32_t value_head_dim;        // linear only (0 for full)
} pheno_layer_info_t;

// ---------------------------------------------------------------------------
// Forward-pass scratchpad sizes (per-engine).
// ---------------------------------------------------------------------------

typedef struct {
    size_t hidden_bytes;             // [B, S, H=1024] bf16
    size_t qkv_full_bytes;           // [B, S, 3072] bf16
    size_t qkv_linear_bytes;         // [B, S, 6144] bf16  (3 * 16 * 128)
    size_t attn_out_bytes;           // [B, S, 1024] bf16
    size_t ffn_inter_bytes;          // [B, S, 3584] bf16
    size_t logits_bytes;             // [B, V=248320] bf16
    size_t state_bytes_per_layer;    // fp32 state per linear layer
    size_t kv_cache_bytes_per_layer; // bf16 KV per full layer
} pheno_scratch_sizes_t;

// ---------------------------------------------------------------------------
// Lifecycle.
// ---------------------------------------------------------------------------

// Create an engine with the default MTL device and the .metallib at
// $PHENO_METAL_LIB or "./kernels.metallib".  The library is auto-built by
// the host's make/zig target if missing (fallback path: MLX / CPU).
pheno_status_t pheno_engine_create(pheno_engine_t* out_engine);

// Tear down: releases pipelines, library, command queue, device.
pheno_status_t pheno_engine_destroy(pheno_engine_t engine);

// (Re)load the .metallib from `path`.  Useful when the host wants to swap
// in a freshly-built metallib without re-creating the engine.
pheno_status_t pheno_engine_load_metallib(
    pheno_engine_t engine,
    const char* path);

// Query scratch sizes for a given (B, S) planning.
pheno_status_t pheno_engine_scratch_sizes(
    pheno_engine_t engine,
    uint32_t batch_size,
    uint32_t max_seq_len,
    pheno_scratch_sizes_t* out_sizes);

// Pre-allocate engine-owned scratch.  Optional — kernels use the buffer
// pointed to by the host if not pre-allocated.
pheno_status_t pheno_engine_alloc(
    pheno_engine_t engine,
    uint32_t batch_size,
    uint32_t max_seq_len);

// Per-layer forward (used by Zig/Rust/Nim orchestrators).  Walks one
// transformer block: pre-norm → attention dispatch (full or linear) →
// residual → pre-norm → SwiGLU → residual.  Buffers are host-owned.
pheno_status_t pheno_engine_forward_layer(
    pheno_engine_t engine,
    uint32_t layer_index,
    uint32_t batch_size,
    uint32_t seq_len,
    const void* hidden_in,        // [B, S, H] bf16
    void* hidden_out,             // [B, S, H] bf16
    const void* layer_weights,    // opaque blob, host-defined layout
    void* scratch);               // >= scratch_sizes().hidden_bytes

// Single-token decode (M=1).  Embeds `token_id`, walks all 24 layers,
// runs fused argmax+temperature sampling, writes the next token into
// `out_token`.  Buffers are persistent across calls.
//
// The `weights` blob is treated as a global/opaque reserve: the embedding
// row is read from it (offset = token_id * H * sizeof(bf16)), and the
// per-layer RMSNorm weight for *every* layer points back to offset 0 of
// `weights` (i.e. is the same weight for all layers).  This is the
// compatibility entry point used by the stub-mode fallback.
//
// For real-weights integration use ``pheno_engine_decode_step_real`` below.
pheno_status_t pheno_engine_decode_step(
    pheno_engine_t engine,
    uint32_t batch_size,
    uint32_t position,
    const int32_t* token_ids,         // [B] i32
    void* hidden_state_out,           // [B, H] bf16
    const void* weights,
    void* kv_cache,                   // [num_full_layers * per_layer_bytes]
    void* lin_state_cache);           // [num_lin_layers * state_bytes]

// Real-weights variant of ``pheno_engine_decode_step``.
//
// Adds ``per_layer_weights``, an array of length
// ``QWEN3_5_NUM_HIDDEN_LAYERS`` whose entries point at the per-layer
// attn_norm_w buffer (in the host-defined weight layout).  For each
// layer L, ``per_layer_weights[L]`` is the RMSNorm weight used by the
// RMSNorm dispatch in the cross-layer batched decode step:
//
//   - If ``per_layer_weights`` is non-NULL and ``per_layer_weights[L]``
//     is non-NULL, the engine reads the bf16 weight vector (length H)
//     from that pointer.
//   - If ``per_layer_weights`` is NULL, or any entry is NULL, the
//     engine falls back to using the global ``weights`` blob (offset 0)
//     just like ``pheno_engine_decode_step``.
//
// The ``weights`` blob is still used for the embedding lookup and is
// required.  Attention / MoE weights for layers are out of scope for
// this entry point: see ``qwen3_5_engine_decode_step`` for the
// full-pipeline composition that threads per-layer attention weights
// through the same orchestrator.
pheno_status_t pheno_engine_decode_step_real(
    pheno_engine_t engine,
    uint32_t batch_size,
    uint32_t position,
    const int32_t* token_ids,             // [B] i32
    void* hidden_state_out,               // [B, H] bf16
    const void* weights,
    void* kv_cache,
    void* lin_state_cache,
    const void* const* per_layer_weights  // [QWEN3_5_NUM_HIDDEN_LAYERS]
                                          // ptr to attn_norm_w of layer i
);
// ---------------------------------------------------------------------------
// Probes / introspection.
// ---------------------------------------------------------------------------

pheno_status_t pheno_engine_has_metal(pheno_engine_t engine, bool* has_metal);
pheno_status_t pheno_engine_device_name(pheno_engine_t engine, const char** name);
const char*    pheno_engine_strerror(pheno_status_t s);

// ---------------------------------------------------------------------------
// Fine-grained per-op dispatch (host composes the layer).
//
// Each kernel takes Metal device buffers (raw `void*`/`MTLBuffer`-castable
// pointers) plus a small set of scalar shape parameters.  Naming matches
// the kernels in metal/*.metal so a missing function is unambiguous.
//
// `scratch` points to a host-allocated buffer large enough for the op's
// intermediate activations.  All buffers use MTLResourceStorageModeShared
// (CPU↔GPU zero-copy on Apple Silicon unified memory).
// ---------------------------------------------------------------------------

// rmsnorm_h1024_fused  (pre-norm with optional residual)
//   x [B*S, H] bf16,  residual [B*S, H] bf16 nullable, weight [H] bf16,
//   out [B*S, H] bf16,  B*S rows total.
pheno_status_t kernel_engine_rmsnorm(
    pheno_engine_t engine,
    const void* x,             // [B*S, H] bf16
    const void* residual,       // [B*S, H] bf16 nullable
    const void* weight,         // [H] bf16
    void* out,                  // [B*S, H] bf16
    uint32_t B,
    uint32_t S,
    uint32_t H);

// mrope_partial_decode_h1024
//   x [B, H, D] bf16 in/out, pos_ids [B, 3] i32.
pheno_status_t kernel_engine_rope(
    pheno_engine_t engine,
    void* x,                    // [B, H, D] bf16
    const void* pos_ids,        // [B, 3] i32
    uint32_t B,
    uint32_t H,
    uint32_t D);

// silu_mul_inplace  (SwiGLU pack: out = silu(gate) * up, in-place on gate)
//   gate [N] bf16 in/out, up [N] bf16 in, N = B*S*I.
pheno_status_t kernel_engine_swiglu(
    pheno_engine_t engine,
    void* gate,                 // [N] bf16 in/out
    const void* up,             // [N] bf16
    uint32_t N);

// flash_attn_decode  (S_q = 1, online-softmax over KV cache)
//   Q [B, 8, D] bf16, K [B, 2, S_k, D] bf16, V [B, 2, S_k, D] bf16,
//   O [B, 8, D] bf16.
pheno_status_t kernel_engine_attention_decode(
    pheno_engine_t engine,
    const void* Q,
    const void* K,
    const void* V,
    void* O,
    uint32_t B,
    uint32_t S_k,
    float scale);

// flash_attn_prefill  (causal flash-attn v2 with GQA broadcast)
//   Q [B, S, 8, D] bf16, K [B, S, 2, D] bf16, V [B, S, 2, D] bf16,
//   O [B, S, 8, D] bf16.
pheno_status_t kernel_engine_attention_prefill(
    pheno_engine_t engine,
    const void* Q,
    const void* K,
    const void* V,
    void* O,
    uint32_t B,
    uint32_t S,
    float scale);

// delta_net_decode_step  (one-token linear-attention chunk update)
//   q, k [B, H, Dk] bf16, v, gate [B, H, Dv] bf16, beta, alpha_log [B, H] bf16,
//   state [B, H, Dv, Dk] fp32 in/out, out [B, H, Dv] bf16.
pheno_status_t kernel_engine_linear_attention_chunk(
    pheno_engine_t engine,
    const void* q,
    const void* k,
    const void* v,
    const void* gate,
    const void* beta,
    const void* alpha_log,
    void* state,
    void* out,
    uint32_t B);

// gumbel_argmax_sample  (single-token sampling)
//   logits [B, V] bf16, out_token [B] i32, scratch [B, V] fp32.
pheno_status_t kernel_engine_sampling(
    pheno_engine_t engine,
    const void* logits,         // [B, V] bf16
    void* out_token,            // [B] i32
    void* scratch_argmax,       // [B, V] fp32, zeroed before call
    uint32_t B,
    float inv_T,
    uint32_t seed);

// gemv_decode  (1×K → N: critical kernel for autoregressive decode)
//   x [K] bf16, W [K, N] bf16, bias [N] bf16 nullable, y [N] bf16.
pheno_status_t kernel_engine_tgemv(
    pheno_engine_t engine,
    const void* x,              // [K] bf16
    const void* W,              // [K, N] bf16
    const void* bias,           // [N] bf16 nullable
    void* y,                    // [N] bf16
    uint32_t K,
    uint32_t N);

// ===========================================================================
// High-level qwen3_5_engine_* C ABI aliases.
//
// Thin wrappers over the per-op API and the qwen3_5::Engine class.  All
// hosts (Zig, Rust, Nim) reach the engine through these symbols.  See
// cpp/kernel_engine.mm lines 1020-1148 for implementations.
// ===========================================================================

// Create / destroy.
pheno_status_t qwen3_5_engine_create(pheno_engine_t* out_engine);
pheno_status_t qwen3_5_engine_destroy(pheno_engine_t engine);

// qwen3_5_engine_forward — high-level prefill across all 24 layers.
//
// Composes rmsnorm → rope → qkv_proj → attention(prefill) → out_proj → residual
// → pre-norm → SwiGLU → residual for each layer in the schedule.  Layout-
// agnostic: the caller passes the opaque `weights` blob and the host decides
// offsets based on the layer index (full vs linear).
pheno_status_t qwen3_5_engine_forward(
    pheno_engine_t engine,
    const void* hidden_in,             // [B, S, H] bf16
    void* hidden_out,                  // [B, S, H] bf16
    const void* weights,               // opaque
    void* scratch,                     // >= scratch_sizes().hidden_bytes
    uint32_t batch_size,
    uint32_t seq_len);

// qwen3_5_engine_decode_step — single-token decode with KV cache append.
//
// M=1 decode: runs one token through all 24 layers (full + linear), appends
// to the per-layer KV cache for full-attn layers, advances the linear state
// for linear-attn layers, then samples the next token via fused argmax +
// temperature.
//
// `kv_cache` layout:         [num_full_layers, 2, B, max_seq, full_kv_dim] bf16
// `lin_state_cache` layout:  [num_lin_layers, B, value_heads, dv, dk]      fp32
// `scratch` layout:          union of the slots reported by pheno_engine_scratch_sizes
// `scratch_argmax` layout:   [B, V] i32 / fp32 (zeroed before call)
pheno_status_t qwen3_5_engine_decode_step(
    pheno_engine_t engine,
    int32_t token_id,
    uint32_t position,
    void* hidden_state_out,           // [B, H] bf16
    const void* weights,
    void* kv_cache,
    void* lin_state_cache,
    void* scratch,
    void* scratch_argmax,             // [B, V] i32
    uint32_t batch_size,
    float inv_temperature,
    uint32_t seed,
    int32_t* out_token);

#ifdef __cplusplus
}
#endif

#endif  // PHENO_QWEN_KERNEL_ENGINE_H
