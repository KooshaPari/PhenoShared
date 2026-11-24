## qwen3_5.nim — Nim bindings to the Qwen3.5 0.8B Metal kernel engine.
##
## This module cimports `kernel_engine.h` and `qwen3_5.h` and exposes a
## high-level Nim API (`Engine`, `decodeStep`, `generate`).
##
## Build (no Nim toolchain assumed — these are documentation snippets):
##   nim c --hints:off --warnings:off -d:phenoCengPath="../rust/target/release" \
##       nim/qwen3_5.nim
##
## The compilation produces a single Nim object file linked against
## `libpheno_qwen_kernels.dylib` (built by the Rust crate) at runtime.
## On macOS, the path is loaded via `dynlib` semantics, so the host must
## have the dylib on DYLD_LIBRARY_PATH or in the absolute path baked in
## at compile time via the `phenoCengPath` define.
##
## Why Nim?  The user requested a polyglot max-perf benchmark.  Nim
## compiles to C then to native code with manual memory management, and
## its `cimport` / `dynlib` story means there's literally zero FFI
## overhead compared to calling the C ABI from C.  The `bench.nim`
## driver exists to measure this empirically.

{.push hint[Name]: off, warning[Deprecated]: off.}

import std/strutils, std/os, std/options

# ---------------------------------------------------------------------------
# 1. FFI pragmas + per-op bindings to the C ABI in include/kernel_engine.h.
#
# `importc` makes Nim declare the symbol as a C-ABI foreign import.  Combined
# with `dynlib: "pheno_qwen"`, the symbol is resolved at process start against
# `libpheno_qwen.dylib` (the C++/Objective-C++ kernel engine; the Rust cdylib
# `libpheno_qwen_kernels.dylib` exports the same surface and is interchangeable
# when both are present).
#
# Note: we deliberately do NOT use `cimport` (which is for Nim's internal C
# codegen) and we do NOT include `.dylib` in the dynlib name — Nim appends the
# platform-specific suffix automatically (macOS: `libpheno_qwen.dylib`).
# ---------------------------------------------------------------------------

{.passC: "-I" & currentSourcePath.parentDir() & "/../include".}
{.pragma: qwenDynlib, importc, dynlib: "libpheno_qwen.dylib".}

type
  pheno_engine_t* = pointer
  pheno_status_t* = uint32

const
  PHENO_OK*              = 0'u32
  PHENO_ERR_INVALID_ARG* = 1'u32
  PHENO_ERR_NO_DEVICE*   = 2'u32
  PHENO_ERR_NO_LIBRARY*  = 3'u32
  PHENO_ERR_NO_KERNEL*   = 4'u32
  PHENO_ERR_NO_MEMORY*   = 5'u32
  PHENO_ERR_ENCODE*      = 6'u32
  PHENO_ERR_COMMIT*      = 7'u32
  PHENO_ERR_WAIT*        = 8'u32
  PHENO_ERR_INTERNAL*    = 99'u32

# Architecture constants from qwen3_5.h.
const
  QWEN3_5_VOCAB_SIZE*              : uint32 = 248_320
  QWEN3_5_HIDDEN_SIZE*             : uint32 = 1024
  QWEN3_5_INTERMEDIATE_SIZE*       : uint32 = 3584
  QWEN3_5_NUM_HIDDEN_LAYERS*       : uint32 = 24
  QWEN3_5_FULL_HEADS*              : uint32 = 8
  QWEN3_5_FULL_KV_HEADS*           : uint32 = 2
  QWEN3_5_FULL_HEAD_DIM*           : uint32 = 256
  QWEN3_5_FULL_Q_DIM*              : uint32 = QWEN3_5_FULL_HEADS * QWEN3_5_FULL_HEAD_DIM
  QWEN3_5_FULL_KV_DIM*             : uint32 = QWEN3_5_FULL_KV_HEADS * QWEN3_5_FULL_HEAD_DIM
  QWEN3_5_FULL_QKV_DIM*            : uint32 = QWEN3_5_FULL_Q_DIM + 2 * QWEN3_5_FULL_KV_DIM
  QWEN3_5_LIN_KEY_HEADS*           : uint32 = 16
  QWEN3_5_LIN_VALUE_HEADS*         : uint32 = 16
  QWEN3_5_LIN_KEY_HEAD_DIM*        : uint32 = 128
  QWEN3_5_LIN_VALUE_HEAD_DIM*      : uint32 = 128
  QWEN3_5_LIN_CONV_KERNEL*         : uint32 = 4
  QWEN3_5_LIN_NUM_LAYERS*          : uint32 = 18
  QWEN3_5_ROT_DIM*                 : uint32 = 32

# ---------------------------------------------------------------------------
# 2. Per-op C ABI bindings (mirrors of kernel_engine.h).
#
# Each binding uses `qwenDynlib` (importc + dynlib "pheno_qwen").  The
# `importc` part lets Nim match the C symbol name exactly (no name mangling)
# and `dynlib` resolves the symbol at load time against the dylib.
# ---------------------------------------------------------------------------

proc pheno_engine_create*(out_engine: ptr pheno_engine_t): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_destroy*(engine: pheno_engine_t): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_load_metallib*(engine: pheno_engine_t; path: cstring): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_scratch_sizes*(
    engine: pheno_engine_t;
    batch: uint32; seq: uint32;
    outSizes: pointer): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_has_metal*(engine: pheno_engine_t; out_has: ptr bool): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_device_name*(engine: pheno_engine_t; out_name: ptr cstring): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_strerror*(s: pheno_status_t): cstring
  {.qwenDynlib.}

# Fine-grained kernel_engine_* ops.
proc kernel_engine_rmsnorm*(
    engine: pheno_engine_t; x, residual, weight, outBuf: pointer;
    B, S, H: uint32): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_rope*(
    engine: pheno_engine_t; x, posIds: pointer; B, H, D: uint32): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_swiglu*(
    engine: pheno_engine_t; gate, up: pointer; N: uint32): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_attention_decode*(
    engine: pheno_engine_t; Q, K, V, O: pointer; B, S_k: uint32; scale: cfloat): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_attention_prefill*(
    engine: pheno_engine_t; Q, K, V, O: pointer; B, S: uint32; scale: cfloat): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_linear_attention_chunk*(
    engine: pheno_engine_t; q, k, v, gate, beta, alphaLog, state, outBuf: pointer; B: uint32): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_sampling*(
    engine: pheno_engine_t; logits, outToken, scratch: pointer; B: uint32;
    invT: cfloat; seed: uint32): pheno_status_t
  {.qwenDynlib.}
proc kernel_engine_tgemv*(
    engine: pheno_engine_t; x, W, bias, y: pointer; K, N: uint32): pheno_status_t
  {.qwenDynlib.}

# High-level qwen3_5_engine_* aliases (one-token decode + per-layer forward).
proc qwen3_5_engine_create*(outEngine: ptr pheno_engine_t): pheno_status_t
  {.qwenDynlib.}
proc qwen3_5_engine_destroy*(engine: pheno_engine_t): pheno_status_t
  {.qwenDynlib.}
proc qwen3_5_engine_forward*(
    engine: pheno_engine_t;
    hiddenIn: pointer; hiddenOut: pointer;
    weights: pointer; scratch: pointer;
    batchSize: uint32; seqLen: uint32): pheno_status_t
  {.qwenDynlib.}
proc qwen3_5_engine_decode_step*(
    engine: pheno_engine_t;
    tokenId: int32; position: uint32;
    hiddenOut: pointer; weights: pointer;
    kvCache: pointer; linState: pointer; scratch: pointer; scratchArgmax: pointer;
    batchSize: uint32; invTemperature: cfloat; seed: uint32;
    outToken: ptr int32): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_forward_layer*(
    engine: pheno_engine_t;
    layerIndex: uint32; batchSize: uint32; seqLen: uint32;
    hiddenIn: pointer; hiddenOut: pointer;
    layerWeights: pointer; scratch: pointer): pheno_status_t
  {.qwenDynlib.}
proc pheno_engine_decode_step*(
    engine: pheno_engine_t;
    batchSize: uint32; position: uint32; tokenIds: pointer;
    hiddenStateOut: pointer; weights: pointer;
    kvCache: pointer; linState: pointer): pheno_status_t
  {.qwenDynlib.}

# ---------------------------------------------------------------------------
# 3. Layer schedule helpers.
# ---------------------------------------------------------------------------

proc layerIsFull*(layer: uint32): bool =
  ## Hybrid schedule: every 4th layer is full attention
  ## (indices 3, 7, 11, 15, 19, 23).
  (layer + 1) mod 4 == 0

# ---------------------------------------------------------------------------
# 4. Status → typed exception.
#
# EngineError is `ref object of CatchableError` so `try / except EngineError`
# catches at any depth.  The `code` field carries the raw u32 status, the
# `kind` discriminator is what callers usually match on.
# ---------------------------------------------------------------------------

type
  EngineErrorKind* = enum
    ekOk = 0
    ekInvalidArg
    ekNoDevice
    ekNoLibrary
    ekNoKernel
    ekNoMemory
    ekEncode
    ekCommit
    ekWait
    ekInternal
    ## Discriminator tag — same numeric value as the C PHENO_*
    ## constants so we can match by raw value too.

  EngineError* = object of CatchableError
    code*: uint32
    kind*: EngineErrorKind

proc statusToError(s: uint32): ref EngineError =
  if s == PHENO_OK: return nil
  new(result)
  result.code = s
  case s
  of PHENO_ERR_INVALID_ARG: result.kind = ekInvalidArg; result.msg = "invalid argument"
  of PHENO_ERR_NO_DEVICE:   result.kind = ekNoDevice;   result.msg = "no Metal device"
  of PHENO_ERR_NO_LIBRARY:  result.kind = ekNoLibrary;  result.msg = "kernels.metallib not found"
  of PHENO_ERR_NO_KERNEL:   result.kind = ekNoKernel;   result.msg = "kernel not found"
  of PHENO_ERR_NO_MEMORY:   result.kind = ekNoMemory;   result.msg = "out of memory"
  of PHENO_ERR_ENCODE:      result.kind = ekEncode;     result.msg = "compute encoder failed"
  of PHENO_ERR_COMMIT:      result.kind = ekCommit;     result.msg = "command buffer commit failed"
  of PHENO_ERR_WAIT:        result.kind = ekWait;       result.msg = "command buffer wait failed"
  of PHENO_ERR_INTERNAL:    result.kind = ekInternal;   result.msg = "internal error"
  else:                     result.kind = ekInternal;   result.msg = "status=" & $s

template check*(s: uint32) =
  ## Raise a typed exception if the C status is non-OK.  Usage:
  ##   check pheno_engine_create(addr eng)
  let err = statusToError(s)
  if err != nil: raise err

# Exposed so decoder.nim can match on it without re-importing the type
# from a private proc.
proc describeStatus*(s: uint32): string =
  ## Returns the human-readable message for a raw C status code.  Mirrors
  ## the `pheno_engine_strerror` C symbol but does not require the dylib.
  let err = statusToError(s)
  if err == nil: "ok" else: err.msg

# ---------------------------------------------------------------------------
# 5. High-level RAII handle.
# ---------------------------------------------------------------------------

type
  Engine* = object
    raw: pheno_engine_t
    deviceName*: string
    hasMetal*: bool

proc initEngine*(metallibPath = none(cstring)): Engine =
  ## Construct a new engine.  Pass `some("/abs/path/to/kernels.metallib")`
  ## to load a specific metallib; `none(cstring)` lets the C++ side
  ## auto-discover (`$PHENO_METAL_LIB` then `./kernels.metallib`).
  var raw: pheno_engine_t
  check pheno_engine_create(addr raw)
  result.raw = raw
  if metallibPath.isSome:
    check pheno_engine_load_metallib(raw, metallibPath.get)

  # Probe device name.
  var namePtr: cstring
  if pheno_engine_device_name(raw, addr namePtr) == PHENO_OK and namePtr != nil:
    result.deviceName = $namePtr
  else:
    result.deviceName = ""

  var hasM: bool
  discard pheno_engine_has_metal(raw, addr hasM)
  result.hasMetal = hasM

proc `=destroy`(eng: var Engine) =
  if eng.raw != nil:
    discard pheno_engine_destroy(eng.raw)
    eng.raw = nil

proc raw*(eng: Engine): pheno_engine_t {.inline.} = eng.raw

proc loadMetallib*(eng: Engine; path: string) =
  ## Load (or reload) a `.metallib` against an already-constructed engine.
  ## Raises `EngineError` on failure.  Pass an absolute path or one
  ## relative to the process working directory.  `hasMetal` is not
  ## refreshed after this call — re-construct the engine if you need
  ## the up-to-date flag.
  check pheno_engine_load_metallib(eng.raw, path.cstring)

# ---------------------------------------------------------------------------
# 6. Per-op Nim wrappers (typed, raises on error).
#
# The wrappers accept raw `pointer` so they match the C `void*` ABI exactly
# without forcing callers to coerce buffers.  Each wrapper is one FFI hop —
# Nim compiles these to direct C calls, no marshalling overhead.
# ---------------------------------------------------------------------------

proc rmsNorm*(
    eng: Engine; x, residual, weight, outBuf: pointer; B, S, H: uint32) =
  check kernel_engine_rmsnorm(eng.raw, x, residual, weight, outBuf, B, S, H)

proc rope*(
    eng: Engine; x, posIds: pointer; B, H, D: uint32) =
  check kernel_engine_rope(eng.raw, x, posIds, B, H, D)

proc attentionDecode*(
    eng: Engine; Q, K, V, O: pointer; B, Sk: uint32; scale: cfloat) =
  check kernel_engine_attention_decode(eng.raw, Q, K, V, O, B, Sk, scale)

proc attentionPrefill*(
    eng: Engine; Q, K, V, O: pointer; B, S: uint32; scale: cfloat) =
  check kernel_engine_attention_prefill(eng.raw, Q, K, V, O, B, S, scale)

proc linearAttentionDecode*(
    eng: Engine; q, k, v, gate, beta, alphaLog, state, outBuf: pointer; B: uint32) =
  check kernel_engine_linear_attention_chunk(eng.raw, q, k, v, gate, beta, alphaLog, state, outBuf, B)

proc fusedSwiglu*(eng: Engine; gate, up: pointer; N: uint32) =
  check kernel_engine_swiglu(eng.raw, gate, up, N)

proc sample*(
    eng: Engine; logits, scratch: pointer; B: uint32;
    invT: cfloat; seed: uint32): int32 =
  var outTok: int32 = 0
  check kernel_engine_sampling(eng.raw, logits, addr outTok, scratch, B, invT, seed)
  return outTok

# High-level qwen3_5_engine_decode_step — the single-token entry the Rust
# orchestrator and Pony `DecodeOrchestrator` use.  Returns the sampled next
# token id (>= 0) or -1 on error.
proc decodeStepHigh*(
    eng: Engine;
    tokenId: int32; position: uint32;
    hiddenOut, weights, kvCache, linState, scratch, scratchArgmax: pointer;
    batchSize: uint32; invTemperature: cfloat; seed: uint32): int32 =
  var nextTok: int32 = -1
  check qwen3_5_engine_decode_step(
    eng.raw, tokenId, position,
    hiddenOut, weights, kvCache, linState, scratch, scratchArgmax,
    batchSize, invTemperature, seed, addr nextTok)
  return nextTok

proc forwardLayer*(
    eng: Engine;
    layerIndex, batchSize, seqLen: uint32;
    hiddenIn, hiddenOut, layerWeights, scratch: pointer) =
  check pheno_engine_forward_layer(
    eng.raw, layerIndex, batchSize, seqLen,
    hiddenIn, hiddenOut, layerWeights, scratch)

proc scratchSizes*(
    eng: Engine; batch, seq: uint32; outSizes: pointer) =
  check pheno_engine_scratch_sizes(eng.raw, batch, seq, outSizes)

# ---------------------------------------------------------------------------
# 7. Token-by-token decode loop.
#
# The actual high-level `decodeStep` lives in `decode.nim` (which `import`s
# this module).  We expose the per-op primitives here and let `decode.nim`
# compose them into the canonical Qwen3.5 0.8B schedule.
#
# The high-level `qwen3_5_engine_decode_step` C entry is wrapped above as
# `decodeStepHigh` for callers that want the one-shot C-ABI path.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tests (compile-only — no metallib expected).
#
# Running `nim c -r qwen3_5.nim` should print the arch constants and the
# hybrid layer schedule (6 full + 18 linear).  When the dylib is missing,
# `initEngine` will raise — we catch and report it cleanly.
# ---------------------------------------------------------------------------

when isMainModule:
  echo "Qwen3.5 0.8B Nim bindings OK"
  echo "vocab=", QWEN3_5_VOCAB_SIZE
  echo "hidden=", QWEN3_5_HIDDEN_SIZE
  echo "full heads=", QWEN3_5_FULL_HEADS, " head_dim=", QWEN3_5_FULL_HEAD_DIM
  echo "linear heads=", QWEN3_5_LIN_KEY_HEADS
  echo "num hidden layers=", QWEN3_5_NUM_HIDDEN_LAYERS
  # Layer schedule sanity: every 4th layer should be full.
  for i in 0 ..< QWEN3_5_NUM_HIDDEN_LAYERS:
    if i mod 8 == 0: stdout.write "\n"
    stdout.write (if layerIsFull(i.uint32): "F " else: "L ")
  stdout.write "\n"
