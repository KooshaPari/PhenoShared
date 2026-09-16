// ffi.rs — raw FFI bindings to kernel_engine.h
//
// Hand-written mirror of the C ABI.  When the header changes, regenerate
// via `cargo build --features codegen-bindings` (uses bindgen).

#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(dead_code)]

use std::os::raw::{c_char, c_void};

// ---------------------------------------------------------------------------
// Opaque engine handle.
// ---------------------------------------------------------------------------

pub type pheno_engine_t = *mut pheno_engine_s;
pub enum pheno_engine_s {}

// ---------------------------------------------------------------------------
// Status codes (must match PHENO_* in kernel_engine.h).
// ---------------------------------------------------------------------------

pub type pheno_status_t = u32;

pub const PHENO_OK: u32 = 0;
pub const PHENO_ERR_INVALID_ARG: u32 = 1;
pub const PHENO_ERR_NO_DEVICE: u32 = 2;
pub const PHENO_ERR_NO_LIBRARY: u32 = 3;
pub const PHENO_ERR_NO_KERNEL: u32 = 4;
pub const PHENO_ERR_NO_MEMORY: u32 = 5;
pub const PHENO_ERR_ENCODE: u32 = 6;
pub const PHENO_ERR_COMMIT: u32 = 7;
pub const PHENO_ERR_WAIT: u32 = 8;
pub const PHENO_ERR_INTERNAL: u32 = 99;

#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct pheno_scratch_sizes_t {
    pub hidden_bytes: usize,
    pub qkv_full_bytes: usize,
    pub qkv_linear_bytes: usize,
    pub attn_out_bytes: usize,
    pub ffn_inter_bytes: usize,
    pub logits_bytes: usize,
    pub state_bytes_per_layer: usize,
    pub kv_cache_bytes_per_layer: usize,
}

// ---------------------------------------------------------------------------
// Lifecycle + probes.
// ---------------------------------------------------------------------------

extern "C" {
    pub fn pheno_engine_create(out_engine: *mut pheno_engine_t) -> pheno_status_t;
    pub fn pheno_engine_destroy(engine: pheno_engine_t) -> pheno_status_t;

    pub fn pheno_engine_load_metallib(engine: pheno_engine_t, path: *const c_char) -> pheno_status_t;

    pub fn pheno_engine_scratch_sizes(
        engine: pheno_engine_t,
        batch_size: u32,
        max_seq_len: u32,
        out_sizes: *mut pheno_scratch_sizes_t,
    ) -> pheno_status_t;

    pub fn pheno_engine_alloc(
        engine: pheno_engine_t,
        batch_size: u32,
        max_seq_len: u32,
    ) -> pheno_status_t;

    pub fn pheno_engine_has_metal(engine: pheno_engine_t, has_metal: *mut bool) -> pheno_status_t;

    pub fn pheno_engine_device_name(
        engine: pheno_engine_t,
        name: *mut *const c_char,
    ) -> pheno_status_t;

    pub fn pheno_engine_strerror(s: pheno_status_t) -> *const c_char;
}

// ---------------------------------------------------------------------------
// Fine-grained kernel dispatch (kernel_engine_*).
//
// Naming mirrors the metal/*.metal kernels 1:1 so a missing function is
// unambiguous.
// ---------------------------------------------------------------------------

extern "C" {
    pub fn kernel_engine_rmsnorm(
        engine: pheno_engine_t,
        x: *const c_void,
        residual: *const c_void,
        weight: *const c_void,
        out: *mut c_void,
        B: u32,
        S: u32,
        H: u32,
    ) -> pheno_status_t;

    pub fn kernel_engine_rope(
        engine: pheno_engine_t,
        x: *mut c_void,
        pos_ids: *const c_void,
        B: u32,
        H: u32,
        D: u32,
    ) -> pheno_status_t;

    pub fn kernel_engine_swiglu(
        engine: pheno_engine_t,
        gate: *mut c_void,
        up: *const c_void,
        N: u32,
    ) -> pheno_status_t;

    pub fn kernel_engine_attention_decode(
        engine: pheno_engine_t,
        Q: *const c_void,
        K: *const c_void,
        V: *const c_void,
        O: *mut c_void,
        B: u32,
        S_k: u32,
        scale: f32,
    ) -> pheno_status_t;

    pub fn kernel_engine_attention_prefill(
        engine: pheno_engine_t,
        Q: *const c_void,
        K: *const c_void,
        V: *const c_void,
        O: *mut c_void,
        B: u32,
        S: u32,
        scale: f32,
    ) -> pheno_status_t;

    pub fn kernel_engine_linear_attention_chunk(
        engine: pheno_engine_t,
        q: *const c_void,
        k: *const c_void,
        v: *const c_void,
        gate: *const c_void,
        beta: *const c_void,
        alpha_log: *const c_void,
        state: *mut c_void,
        out: *mut c_void,
        B: u32,
    ) -> pheno_status_t;

    pub fn kernel_engine_sampling(
        engine: pheno_engine_t,
        logits: *const c_void,
        out_token: *mut c_void,
        scratch_argmax: *mut c_void,
        B: u32,
        inv_T: f32,
        seed: u32,
    ) -> pheno_status_t;

    pub fn kernel_engine_tgemv(
        engine: pheno_engine_t,
        x: *const c_void,
        W: *const c_void,
        bias: *const c_void,
        y: *mut c_void,
        K: u32,
        N: u32,
    ) -> pheno_status_t;
}
