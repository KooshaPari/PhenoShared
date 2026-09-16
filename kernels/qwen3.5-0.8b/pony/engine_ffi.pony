// engine_ffi.pony — Pony FFI bindings to libpheno_qwen.dylib.
//
// All C ABI symbols are declared via top-level `use @` so the Pony runtime
// treats them as direct foreign calls without actor wrapping.
//
// Build (after building the dylib):
//   ponyc --path . --output ../build .
//
// Linker resolves libpheno_qwen via:
//   LDFLAGS="-L../build -lpheno_qwen -framework Metal -framework Foundation"

use "lib:pheno_qwen"
use "lib:c"

use @memcpy[Pointer[U8] tag](
  dst: Pointer[U8] tag,
  src: Pointer[U8] tag,
  n: USize)
  /// Standard libc memcpy.

// --- FFI declarations -----------------------------------------------------
//
// NOTE: Pony grammar requires ALL `use @` FFI declarations to appear
// BEFORE any type/primitive/actor/class definitions, in the same source
// file or any file it `use`s.
//
// We use Pointer[U8] tag everywhere because the C ABI uses void* for all
// buffer parameters and `tag` is the sendable capability required for
// actor behaviour parameters.

// --- Lifecycle ------------------------------------------------------------

use @pheno_engine_create[I32](engine: Pointer[Pointer[U8]])
  /// Allocate a new engine.

use @pheno_engine_destroy[I32](engine: Pointer[U8] tag)
  /// Release the engine.

use @pheno_engine_load_metallib[I32](
  engine: Pointer[U8] tag,
  path: Pointer[U8] tag)
  /// Load kernels.metallib from `path`.

use @pheno_engine_has_metal[I32](engine: Pointer[U8] tag)
  /// Non-zero when a Metal device is available.

use @pheno_engine_device_name[I32](
  engine: Pointer[U8] tag,
  out_name: Pointer[Pointer[U8]])
  /// Copy the GPU name pointer into `out_name`.

use @pheno_engine_strerror[Pointer[U8] tag](s: I32)
  /// C string describing a status code.

// --- Per-op dispatch ------------------------------------------------------

use @kernel_engine_rmsnorm[I32](
  engine: Pointer[U8] tag,
  x: Pointer[U8] tag,
  residual: Pointer[U8] tag,
  weight: Pointer[U8] tag,
  out: Pointer[U8] tag,
  B: U32, S: U32, H: U32)
  /// RMSNorm pre-norm + optional residual.

use @kernel_engine_rope[I32](
  engine: Pointer[U8] tag,
  x: Pointer[U8] tag,
  pos_ids: Pointer[I32] tag,
  B: U32, H: U32, D: U32)
  /// M-RoPE partial decode (M=1).

use @kernel_engine_swiglu[I32](
  engine: Pointer[U8] tag,
  gate: Pointer[U8] tag,
  up: Pointer[U8] tag,
  N: U32)
  /// SwiGLU in-place on gate: gate = silu(gate) * up.

use @kernel_engine_attention_decode[I32](
  engine: Pointer[U8] tag,
  Q: Pointer[U8] tag, K: Pointer[U8] tag, V: Pointer[U8] tag,
  O: Pointer[U8] tag, B: U32, S_k: U32, scale: F32)
  /// Flash attention decode (M=1).

use @kernel_engine_sigmoid_gate[I32](
  engine: Pointer[U8] tag,
  o: Pointer[U8] tag,
  og: Pointer[U8] tag,
  N: U32)
  /// Sigmoid gate-mul: o = o * sigmoid(o_gate).

use @kernel_engine_sampling[I32](
  engine: Pointer[U8] tag,
  logits: Pointer[U8] tag,
  out_token: Pointer[I32] tag,
  scratch: Pointer[U8] tag,
  B: U32, inv_T: F32, seed: U32)
  /// Fused gumbel argmax + temperature.

use @kernel_engine_tgemv[I32](
  engine: Pointer[U8] tag,
  x: Pointer[U8] tag,
  W: Pointer[U8] tag,
  bias: Pointer[U8] tag,
  y: Pointer[U8] tag,
  K: U32, N: U32)
  /// Transposed GEMV (decode projection).

use @pheno_engine_forward_layer[I32](
  engine: Pointer[U8] tag,
  layer_index: U32, batch_size: U32, seq_len: U32,
  hidden_in: Pointer[U8] tag,
  hidden_out: Pointer[U8] tag,
  layer_weights: Pointer[U8] tag,
  scratch: Pointer[U8] tag)
  /// Batched forward-pass for one transformer layer.

use @pheno_engine_decode_step[I32](
  engine: Pointer[U8] tag,
  batch_size: U32, position: U32,
  token_ids: Pointer[I32] tag,
  hidden_state_out: Pointer[U8] tag,
  weights: Pointer[U8] tag,
  kv_cache: Pointer[U8] tag,
  lin_state_cache: Pointer[U8] tag)
  /// Cross-layer batched decode for one token.

// --- Type aliases & helpers (must come AFTER all `use @`) -----------------

// Opaque engine handle (C void*).  Internally a tag pointer so it can be
// passed to actor behaviours, but Pony auto-converts from ref↔tag at the
// PhenoEngine-as-typed boundary.
type PhenoEngine is Pointer[U8]

// Status codes (must match include/kernel_engine.h)
primitive Status
  fun ok():             I32 => 0
  fun err_invalid():    I32 => -1
  fun err_no_device():  I32 => -2
  fun err_no_library(): I32 => -3
  fun err_no_kernel():  I32 => -4
  fun err_no_memory():  I32 => -5
  fun err_encode():     I32 => -6
  fun err_commit():     I32 => -7
  fun err_wait():       I32 => -8

  fun strerror(s: I32): String =>
    match s
    | 0  => "ok"
    | -1 => "invalid argument"
    | -2 => "no Metal device"
    | -3 => "metallib not found"
    | -4 => "kernel not in library"
    | -5 => "out of memory"
    | -6 => "encoder failed"
    | -7 => "commit failed"
    | -8 => "wait failed"
    else   "internal error"
    end

primitive PhenoHelpers
  fun create_engine(): PhenoEngine =>
    """
    Allocate a new engine.  Returns the (possibly null) handle.
    Use Status.strerror() to inspect the failure reason after the call.
    """
    var h: Pointer[U8] = Pointer[U8]
    @pheno_engine_create(addressof h)
    h

  fun load_metallib(engine: PhenoEngine, path: String): I32 =>
    @pheno_engine_load_metallib(engine, path.cstring())

  fun has_metal(engine: PhenoEngine): Bool =>
    (@pheno_engine_has_metal(engine)) != 0

  fun device_name(engine: PhenoEngine): String =>
    recover val
      var name: Pointer[U8] = Pointer[U8]
      @pheno_engine_device_name(engine, addressof name)
      if name.is_null() then "unknown"
      else String.copy_cpointer(name, 0) end
    end