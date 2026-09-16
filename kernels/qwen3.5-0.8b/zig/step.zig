// step.zig — Low-level extern "c" bindings for the Qwen3.5 0.8B kernel engine.
//
// Mirrors include/kernel_engine.h (host C ABI) and include/qwen3_5.h
// (architecture constants).  The host orchestrator (decode.zig) composes
// these into a high-level decode loop; engine.zig wraps them in a
// type-safe RAII handle.
//
// Conventions:
//   - All pointers are `[*c]` opaque pointers; the C side accepts raw
//     host memory and treats it as a Metal device pointer (zero-copy on
//     Apple Silicon unified memory).
//   - Status codes are returned as `pheno_status_t` (u32) and converted
//     into Zig errors by the `toStatus` helper in engine.zig.
//   - Architecture constants (`QWEN3_5_*`) are exposed via `@cImport` so
//     they stay in sync with the C header.

const std = @import("std");

// ---------------------------------------------------------------------------
// @cImport pulls the C ABI in directly.  On Apple Silicon we get the Metal
// frameworks transitively through the static link of cpp_lib; on other
// targets the call sites fall back to stub mode (PHENO_ERR_NO_KERNEL).
// ---------------------------------------------------------------------------

pub const c = @cImport({
    @cInclude("kernel_engine.h");
    @cInclude("qwen3_5.h");
});

// ---------------------------------------------------------------------------
// Re-export the architecture constants we need for decode-loop indexing.
// These are #define-derivable on the C side so the values are present at
// compile time and stable across rebuilds.
// ---------------------------------------------------------------------------

pub const NUM_HIDDEN_LAYERS: u32 = c.QWEN3_5_NUM_HIDDEN_LAYERS;
pub const HIDDEN_SIZE: u32 = c.QWEN3_5_HIDDEN_SIZE;
pub const INTERMEDIATE_SIZE: u32 = c.QWEN3_5_INTERMEDIATE_SIZE;
pub const FULL_HEADS: u32 = c.QWEN3_5_FULL_HEADS;
pub const FULL_KV_HEADS: u32 = c.QWEN3_5_FULL_KV_HEADS;
pub const FULL_HEAD_DIM: u32 = c.QWEN3_5_FULL_HEAD_DIM;
pub const FULL_Q_DIM: u32 = c.QWEN3_5_FULL_Q_DIM;
pub const FULL_KV_DIM: u32 = c.QWEN3_5_FULL_KV_DIM;
pub const FULL_QKV_DIM: u32 = c.QWEN3_5_FULL_QKV_DIM;
pub const ROT_DIM: u32 = c.QWEN3_5_ROT_DIM;
pub const LIN_KEY_HEADS: u32 = c.QWEN3_5_LIN_KEY_HEADS;
pub const LIN_KEY_HEAD_DIM: u32 = c.QWEN3_5_LIN_KEY_HEAD_DIM;
pub const LIN_VALUE_HEAD_DIM: u32 = c.QWEN3_5_LIN_VALUE_HEAD_DIM;
pub const LIN_NUM_LAYERS: u32 = c.QWEN3_5_LIN_NUM_LAYERS;
pub const LIN_STATE_PER_LAYER_F32: usize = c.QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES;
pub const VOCAB_SIZE: u32 = c.QWEN3_5_VOCAB_SIZE;

/// Hybrid schedule accessor.  Returns true for layers that are full
/// (GQA flash attention); false for linear (DeltaNet).  Mirrors
/// `QWEN3_5_LAYER_IS_FULL` from the C header.
pub fn layerIsFull(layer_index: u32) bool {
    if (layer_index >= NUM_HIDDEN_LAYERS) return false;
    return c.QWEN3_5_LAYER_IS_FULL[layer_index] != 0;
}

// ---------------------------------------------------------------------------
// Status code aliases.  These are the raw C enum values; engine.zig
// converts them to Zig errors via `toStatus`.
// ---------------------------------------------------------------------------

pub const PHENO_OK: u32 = c.PHENO_OK;
pub const PHENO_ERR_INVALID_ARG: u32 = c.PHENO_ERR_INVALID_ARG;
pub const PHENO_ERR_NO_DEVICE: u32 = c.PHENO_ERR_NO_DEVICE;
pub const PHENO_ERR_NO_LIBRARY: u32 = c.PHENO_ERR_NO_LIBRARY;
pub const PHENO_ERR_NO_KERNEL: u32 = c.PHENO_ERR_NO_KERNEL;
pub const PHENO_ERR_NO_MEMORY: u32 = c.PHENO_ERR_NO_MEMORY;
pub const PHENO_ERR_ENCODE: u32 = c.PHENO_ERR_ENCODE;
pub const PHENO_ERR_COMMIT: u32 = c.PHENO_ERR_COMMIT;
pub const PHENO_ERR_WAIT: u32 = c.PHENO_ERR_WAIT;
pub const PHENO_ERR_INTERNAL: u32 = c.PHENO_ERR_INTERNAL;

// ---------------------------------------------------------------------------
// Per-op C ABI surface.  Each function corresponds 1:1 to the
// `kernel_engine_*` declarations in kernel_engine.h.  We declare them
// as extern so Zig will generate the correct platform calling
// convention and link symbols.
//
// Naming: `extern_<op>` so the file's `c` namespace doesn't collide
// with the imported C names.  Call sites can `usingnamespace` this
// module or prefix with `step.extern_<op>`.
// ---------------------------------------------------------------------------


pub extern "c" fn pheno_engine_create(out_engine: [*c]?*c.pheno_engine_s) c.pheno_status_t;
pub extern "c" fn pheno_engine_destroy(engine: ?*c.pheno_engine_s) c.pheno_status_t;
pub extern "c" fn pheno_engine_load_metallib(
    engine: ?*c.pheno_engine_s,
    path: [*c]const u8,
) c.pheno_status_t;
pub extern "c" fn pheno_engine_scratch_sizes(
    engine: ?*c.pheno_engine_s,
    batch_size: u32,
    max_seq_len: u32,
    out_sizes: [*c]c.pheno_scratch_sizes_t,
) c.pheno_status_t;
pub extern "c" fn pheno_engine_alloc(
    engine: ?*c.pheno_engine_s,
    batch_size: u32,
    max_seq_len: u32,
) c.pheno_status_t;
pub extern "c" fn pheno_engine_has_metal(
    engine: ?*c.pheno_engine_s,
    has_metal: [*c]bool,
) c.pheno_status_t;
pub extern "c" fn pheno_engine_device_name(
    engine: ?*c.pheno_engine_s,
    name: [*c][*c]const u8,
) c.pheno_status_t;
pub extern "c" fn pheno_engine_strerror(s: c.pheno_status_t) [*c]const u8;

// ---- High-level C API aliases (qwen3_5_engine_*) ----

pub extern "c" fn qwen3_5_engine_create(out_engine: [*c]?*c.pheno_engine_s) c.pheno_status_t;
pub extern "c" fn qwen3_5_engine_destroy(engine: ?*c.pheno_engine_s) c.pheno_status_t;
pub extern "c" fn qwen3_5_engine_forward(
    engine: ?*c.pheno_engine_s,
    hidden_in: [*c]const u8,
    hidden_out: [*c]u8,
    weights: [*c]const u8,
    scratch: [*c]u8,
    batch_size: u32,
    seq_len: u32,
) c.pheno_status_t;
pub extern "c" fn qwen3_5_engine_decode_step(
    engine: ?*c.pheno_engine_s,
    token_id: i32,
    position: u32,
    hidden_state_out: [*c]u8,
    weights: [*c]const u8,
    kv_cache: [*c]u8,
    lin_state_cache: [*c]u8,
    scratch: [*c]u8,
    scratch_argmax: [*c]u8,
    batch_size: u32,
    inv_temperature: f32,
    seed: u32,
    out_token: [*c]i32,
) c.pheno_status_t;

// ---- Fine-grained per-op kernel_engine_* ABI ----

pub extern "c" fn kernel_engine_rmsnorm(
    engine: ?*c.pheno_engine_s,
    x: [*c]const u8,
    residual: [*c]const u8,
    weight: [*c]const u8,
    out: [*c]u8,
    B: u32,
    S: u32,
    H: u32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_rope(
    engine: ?*c.pheno_engine_s,
    x: [*c]u8,
    pos_ids: [*c]const u8,
    B: u32,
    H: u32,
    D: u32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_swiglu(
    engine: ?*c.pheno_engine_s,
    gate: [*c]u8,
    up: [*c]const u8,
    N: u32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_attention_decode(
    engine: ?*c.pheno_engine_s,
    Q: [*c]const u8,
    K: [*c]const u8,
    V: [*c]const u8,
    O: [*c]u8,
    B: u32,
    S_k: u32,
    scale: f32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_attention_prefill(
    engine: ?*c.pheno_engine_s,
    Q: [*c]const u8,
    K: [*c]const u8,
    V: [*c]const u8,
    O: [*c]u8,
    B: u32,
    S: u32,
    scale: f32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_linear_attention_chunk(
    engine: ?*c.pheno_engine_s,
    q: [*c]const u8,
    k: [*c]const u8,
    v: [*c]const u8,
    gate: [*c]const u8,
    beta: [*c]const u8,
    alpha_log: [*c]const u8,
    state: [*c]u8,
    out: [*c]u8,
    B: u32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_sampling(
    engine: ?*c.pheno_engine_s,
    logits: [*c]const u8,
    out_token: [*c]u8,
    scratch_argmax: [*c]u8,
    B: u32,
    inv_T: f32,
    seed: u32,
) c.pheno_status_t;
pub extern "c" fn kernel_engine_tgemv(
    engine: ?*c.pheno_engine_s,
    x: [*c]const u8,
    W: [*c]const u8,
    bias: [*c]const u8,
    y: [*c]u8,
    K: u32,
    N: u32,
) c.pheno_status_t;

// ---------------------------------------------------------------------------
// Tiny convenience: a single forward declaration of `qwen3_5::Engine` for
// reference.  Zig cannot represent C++ RAII directly; the C++ side exposes
// the engine as an opaque `pheno_engine_t`.  This constant is the canonical
// fully-qualified name as it would appear in C++.
// ---------------------------------------------------------------------------

pub const QWEN3_5_ENGINE_CXX_NAME: [:0]const u8 = "qwen3_5::Engine";