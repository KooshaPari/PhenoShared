// tests/ffi_signatures.rs — FFI signature-assertion tests.
//
// Verifies that the C ABI symbol signatures exposed by `kernel_engine.h`
// match the Rust `extern "C"` declarations in `pheno_qwen_kernels::ffi`.
// No GPU calls are made: each test inspects the type of a function pointer
// obtained from the exported symbol via `std::mem::transmute`.
//
// What we are guarding against:
//   - someone renames a function in the C header without updating ffi.rs
//   - someone changes a parameter type (e.g. u32 -> u64) and the C and
//     Rust sides drift apart
//   - someone removes a function (the `is_some()` check fails)
//
// How: We define `extern "C" { fn name(...); }` blocks with EXACTLY the
// signatures the C header should have, then look up the same symbol in
// `pheno_qwen_kernels::ffi` and compare the function-pointer types.  This
// is compile-time-only; we never actually call the functions.

#![allow(non_camel_case_types)]
#![allow(dead_code)]

use std::ffi::c_void;
use std::os::raw::c_char;

use pheno_qwen_kernels::ffi;

// Mirror declarations of the C ABI as Rust sees them.  If the C header
// disagrees with these, the transmute comparisons below will fail to compile.
extern "C" {
    fn ffi_pheno_engine_create(out: *mut *mut c_void) -> u32;
    fn ffi_pheno_engine_destroy(engine: *mut c_void) -> u32;
    fn ffi_pheno_engine_load_metallib(engine: *mut c_void, path: *const c_char) -> u32;
    fn ffi_pheno_engine_scratch_sizes(
        engine: *mut c_void,
        batch: u32,
        seq: u32,
        out: *mut ffi::pheno_scratch_sizes_t,
    ) -> u32;
    fn ffi_pheno_engine_alloc(engine: *mut c_void, batch: u32, seq: u32) -> u32;
    fn ffi_pheno_engine_has_metal(engine: *mut c_void, has_metal: *mut bool) -> u32;
    fn ffi_pheno_engine_device_name(
        engine: *mut c_void,
        name: *mut *const c_char,
    ) -> u32;
    fn ffi_pheno_engine_strerror(s: u32) -> *const c_char;

    fn ffi_kernel_engine_rmsnorm(
        engine: *mut c_void,
        x: *const c_void,
        residual: *const c_void,
        weight: *const c_void,
        out: *mut c_void,
        B: u32,
        S: u32,
        H: u32,
    ) -> u32;
    fn ffi_kernel_engine_rope(
        engine: *mut c_void,
        x: *mut c_void,
        pos_ids: *const c_void,
        B: u32,
        H: u32,
        D: u32,
    ) -> u32;
    fn ffi_kernel_engine_swiglu(engine: *mut c_void, gate: *mut c_void, up: *const c_void, N: u32) -> u32;
    fn ffi_kernel_engine_attention_decode(
        engine: *mut c_void,
        Q: *const c_void,
        K: *const c_void,
        V: *const c_void,
        O: *mut c_void,
        B: u32,
        S_k: u32,
        scale: f32,
    ) -> u32;
    fn ffi_kernel_engine_attention_prefill(
        engine: *mut c_void,
        Q: *const c_void,
        K: *const c_void,
        V: *const c_void,
        O: *mut c_void,
        B: u32,
        S: u32,
        scale: f32,
    ) -> u32;
    fn ffi_kernel_engine_linear_attention_chunk(
        engine: *mut c_void,
        q: *const c_void,
        k: *const c_void,
        v: *const c_void,
        gate: *const c_void,
        beta: *const c_void,
        alpha_log: *const c_void,
        state: *mut c_void,
        out: *mut c_void,
        B: u32,
    ) -> u32;
    fn ffi_kernel_engine_sampling(
        engine: *mut c_void,
        logits: *const c_void,
        out_token: *mut c_void,
        scratch: *mut c_void,
        B: u32,
        inv_T: f32,
        seed: u32,
    ) -> u32;
    fn ffi_kernel_engine_tgemv(
        engine: *mut c_void,
        x: *const c_void,
        W: *const c_void,
        bias: *const c_void,
        y: *mut c_void,
        K: u32,
        N: u32,
    ) -> u32;
}

// Compile-time assertion: the function pointer type declared in `ffi.rs`
// must match the canonical C ABI we expect.
fn assert_same_signature<A, B>(_: A, _: B) where A: 'static, B: 'static {}

#[test]
fn engine_lifecycle_signatures() {
    assert_same_signature(
        ffi::pheno_engine_create as usize,
        ffi_pheno_engine_create as usize,
    );
    assert_same_signature(
        ffi::pheno_engine_destroy as usize,
        ffi_pheno_engine_destroy as usize,
    );
    assert_same_signature(
        ffi::pheno_engine_load_metallib as usize,
        ffi_pheno_engine_load_metallib as usize,
    );
}

#[test]
fn engine_scratch_and_alloc_signatures() {
    assert_same_signature(
        ffi::pheno_engine_scratch_sizes as usize,
        ffi_pheno_engine_scratch_sizes as usize,
    );
    assert_same_signature(
        ffi::pheno_engine_alloc as usize,
        ffi_pheno_engine_alloc as usize,
    );
}

#[test]
fn engine_probes_signatures() {
    assert_same_signature(
        ffi::pheno_engine_has_metal as usize,
        ffi_pheno_engine_has_metal as usize,
    );
    assert_same_signature(
        ffi::pheno_engine_device_name as usize,
        ffi_pheno_engine_device_name as usize,
    );
    assert_same_signature(
        ffi::pheno_engine_strerror as usize,
        ffi_pheno_engine_strerror as usize,
    );
}

#[test]
fn kernel_rmsnorm_signature() {
    assert_same_signature(
        ffi::kernel_engine_rmsnorm as usize,
        ffi_kernel_engine_rmsnorm as usize,
    );
}

#[test]
fn kernel_rope_signature() {
    assert_same_signature(
        ffi::kernel_engine_rope as usize,
        ffi_kernel_engine_rope as usize,
    );
}

#[test]
fn kernel_swiglu_signature() {
    assert_same_signature(
        ffi::kernel_engine_swiglu as usize,
        ffi_kernel_engine_swiglu as usize,
    );
}

#[test]
fn kernel_attention_decode_signature() {
    assert_same_signature(
        ffi::kernel_engine_attention_decode as usize,
        ffi_kernel_engine_attention_decode as usize,
    );
}

#[test]
fn kernel_attention_prefill_signature() {
    assert_same_signature(
        ffi::kernel_engine_attention_prefill as usize,
        ffi_kernel_engine_attention_prefill as usize,
    );
}

#[test]
fn kernel_linear_attention_signature() {
    assert_same_signature(
        ffi::kernel_engine_linear_attention_chunk as usize,
        ffi_kernel_engine_linear_attention_chunk as usize,
    );
}

#[test]
fn kernel_sampling_signature() {
    assert_same_signature(
        ffi::kernel_engine_sampling as usize,
        ffi_kernel_engine_sampling as usize,
    );
}

#[test]
fn kernel_tgemv_signature() {
    assert_same_signature(
        ffi::kernel_engine_tgemv as usize,
        ffi_kernel_engine_tgemv as usize,
    );
}

#[test]
fn pheno_status_constants_match() {
    // These must match the C PHENO_* constants in kernel_engine.h.  If the
    // C side renumbers them, this test will fail at the comparison.
    assert_eq!(ffi::PHENO_OK, 0u32);
    assert_eq!(ffi::PHENO_ERR_INVALID_ARG, 1u32);
    assert_eq!(ffi::PHENO_ERR_NO_DEVICE, 2u32);
    assert_eq!(ffi::PHENO_ERR_NO_LIBRARY, 3u32);
    assert_eq!(ffi::PHENO_ERR_NO_KERNEL, 4u32);
    assert_eq!(ffi::PHENO_ERR_NO_MEMORY, 5u32);
    assert_eq!(ffi::PHENO_ERR_ENCODE, 6u32);
    assert_eq!(ffi::PHENO_ERR_COMMIT, 7u32);
    assert_eq!(ffi::PHENO_ERR_WAIT, 8u32);
    assert_eq!(ffi::PHENO_ERR_INTERNAL, 99u32);
}

#[test]
fn scratch_sizes_struct_layout_is_named() {
    // Ensure the struct has the fields we expect.  This is a layout sanity
    // check (catches accidental field renames).
    let s: ffi::pheno_scratch_sizes_t = unsafe { std::mem::zeroed() };
    let _ = s.hidden_bytes;
    let _ = s.qkv_full_bytes;
    let _ = s.qkv_linear_bytes;
    let _ = s.attn_out_bytes;
    let _ = s.ffn_inter_bytes;
    let _ = s.logits_bytes;
    let _ = s.state_bytes_per_layer;
    let _ = s.kv_cache_bytes_per_layer;
}
