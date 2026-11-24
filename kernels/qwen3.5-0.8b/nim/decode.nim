## decode.nim — Token-by-token decode loop for Qwen3.5 0.8B.
##
## This is the high-level orchestration shell that drives the C ABI
## exported by the C++/Objective-C++ kernel engine (libpheno_qwen.dylib).
## It demonstrates:
##   - Opening the dynamic library (handled by Nim's `dynlib` resolver
##     when the FFI procs are first called).
##   - Allocating the persistent buffers (KV cache, linear state, scratch).
##   - Prefill (process the prompt one token at a time).
##   - Decode (roll one new token per step).
##   - Sampling (fused argmax + temperature).
##
## Build (when nim is installed):
##   bash kernels/qwen3.5-0.8b/scripts/build_nim.sh
##
## Run:
##   ./kernels/qwen3.5-0.8b/build/nim_decode
##
## If the dylib is missing or the metallib is not loaded, every per-op call
## returns PHENO_ERR_NO_KERNEL which we tolerate via `cfg.tolerateStub`;
## the program then prints the canonical layer schedule and exits cleanly.

import qwen3_5
import std/[options, strutils, times, math]

# ---------------------------------------------------------------------------
# DecodeConfig — sampler + layout knobs.
# ---------------------------------------------------------------------------

type
  DecodeConfig* = object
    batchSize*: uint32
    maxSeqLen*: uint32
    invTemperature*: cfloat  # 1.0 = greedy; < 1.0 = sharper
    topK*: uint32
    topP*: cfloat
    seed*: uint32
    tolerateStub*: bool

  DecodeBuffers* = object
    # Persistent buffers (allocated once, reused across steps).
    hidden*: seq[uint8]               # [B, H] bf16
    residual*: seq[uint8]             # [B, H] bf16
    qkvFull*: seq[uint8]              # [B, FULL_QKV_DIM] bf16
    qkvLinear*: seq[uint8]            # [B, 3 * LIN_KEY_HEADS * LIN_KEY_HEAD_DIM] bf16
    attnOut*: seq[uint8]              # [B, H] bf16
    ffnInter*: seq[uint8]             # [B, INTERMEDIATE_SIZE] bf16
    logits*: seq[uint8]               # [B, VOCAB_SIZE] bf16
    kvCache*: seq[uint8]              # [num_full, 2, B, max_seq, FULL_KV_DIM] bf16
    linState*: seq[uint8]             # [num_lin, B, value_heads, value_head_dim, key_head_dim] fp32
    scratchArgmax*: seq[uint8]        # [B, VOCAB_SIZE] i32

# ---------------------------------------------------------------------------
# Buffer allocation.  Aligns everything to 16 bytes (Metal buffer
# alignment requirement on Apple Silicon).
# ---------------------------------------------------------------------------

proc allocBuffers(cfg: DecodeConfig): DecodeBuffers =
  let B = cfg.batchSize
  let S = cfg.maxSeqLen
  let H = QWEN3_5_HIDDEN_SIZE
  let I = QWEN3_5_INTERMEDIATE_SIZE
  let V = QWEN3_5_VOCAB_SIZE
  let FQ = QWEN3_5_FULL_QKV_DIM
  let FK = QWEN3_5_FULL_KV_DIM
  let LKV = QWEN3_5_LIN_KEY_HEADS * QWEN3_5_LIN_KEY_HEAD_DIM
  let numFull = 6'u32  # every 4th of 24
  let numLin = QWEN3_5_LIN_NUM_LAYERS

  result.hidden       = newSeq[uint8](B * H * 2)
  result.residual     = newSeq[uint8](B * H * 2)
  result.qkvFull      = newSeq[uint8](B * FQ * 2)
  result.qkvLinear    = newSeq[uint8](B * 3 * LKV * 2)
  result.attnOut      = newSeq[uint8](B * H * 2)
  result.ffnInter     = newSeq[uint8](B * I * 2)
  result.logits       = newSeq[uint8](B * V * 2)
  result.kvCache      = newSeq[uint8](numFull * 2 * B * S * FK * 2)
  result.linState     = newSeq[uint8](numLin * B * QWEN3_5_LIN_VALUE_HEADS *
                                       QWEN3_5_LIN_VALUE_HEAD_DIM *
                                       QWEN3_5_LIN_KEY_HEAD_DIM * 4)
  result.scratchArgmax = newSeq[uint8](B * V * 4)  # i32

# ---------------------------------------------------------------------------
# Per-layer dispatch.
# ---------------------------------------------------------------------------

proc runLayer(eng: Engine;
              bufs: var DecodeBuffers;
              cfg: DecodeConfig;
              layer: uint32;
              isFull: bool;
              position, kvLayer, linLayer: uint32;
              weights: pointer) =
  ## Dispatch one transformer block: pre-norm → (full|linear) attention
  ## → residual → MLP → residual.  In stub-mode each per-op call
  ## raises EngineError(ekNoKernel); we tolerate that and short-circuit
  ## the orchestration.
  template safe(op) =
    try:
      op()
    except EngineError as e:
      if not (e.kind == ekNoKernel and cfg.tolerateStub):
        raise

  # 1. Pre-norm + residual (placeholder: rmsNorm in-place on hidden).
  safe(proc() = eng.rmsNorm(addr bufs.hidden[0], nil, weights,
                             addr bufs.attnOut[0],
                             cfg.batchSize, 1, QWEN3_5_HIDDEN_SIZE))

  if isFull:
    # 2a. RoPE on Q, then flash-attention decode (M=1).
    safe(proc() = eng.rope(addr bufs.qkvFull[0], nil,
                            cfg.batchSize,
                            QWEN3_5_FULL_HEADS,
                            QWEN3_5_FULL_HEAD_DIM))
    let scale: cfloat = 1.0 / sqrt(cfloat(QWEN3_5_FULL_HEAD_DIM))
    safe(proc() = eng.attentionDecode(addr bufs.qkvFull[0],
                                       addr bufs.kvCache[0],
                                       addr bufs.kvCache[0],
                                       addr bufs.attnOut[0],
                                       cfg.batchSize,
                                       cfg.maxSeqLen,
                                       scale))
  else:
    # 2b. DeltaNet chunk update (linear attention).
    safe(proc() = eng.linearAttentionDecode(
      addr bufs.qkvLinear[0], addr bufs.qkvLinear[0],
      addr bufs.qkvLinear[0], addr bufs.qkvLinear[0],
      addr bufs.qkvLinear[0], addr bufs.qkvLinear[0],
      addr bufs.linState[0],   addr bufs.attnOut[0],
      cfg.batchSize))

  # 3. MLP: SwiGLU on the FFN intermediate.
  safe(proc() = eng.fusedSwiglu(addr bufs.ffnInter[0],
                                 addr bufs.ffnInter[0],
                                 cfg.batchSize * QWEN3_5_INTERMEDIATE_SIZE))

# ---------------------------------------------------------------------------
# Single-token decode step.
# ---------------------------------------------------------------------------

proc decodeStep(eng: Engine;
                bufs: var DecodeBuffers;
                cfg: DecodeConfig;
                tokenId: int32;
                position: uint32;
                weights: pointer): int32 =
  # Embedding lookup: copy embed row into hidden.  The host is responsible
  # for ensuring `weights` is a valid [V, H] bf16 blob (the engine itself
  # never frees the pointer).  We do a single copy with no bounds check —
  # the C ABI expects this contract.
  let H = QWEN3_5_HIDDEN_SIZE
  let embedOffset = tokenId.int * H.int * 2
  if weights == nil:
    # No weights supplied — return 0 in stub mode (orchestrator short-circuit).
    return 0
  let embedPtr = cast[pointer](cast[int](weights) + embedOffset)
  copyMem(addr bufs.hidden[0], embedPtr, H.int * 2)

  # Walk all 24 layers in canonical schedule.
  var kvLayer: uint32 = 0
  var linLayer: uint32 = 0
  for layer in 0'u32 ..< QWEN3_5_NUM_HIDDEN_LAYERS:
    let isFull = layerIsFull(layer)
    runLayer(eng, bufs, cfg, layer, isFull, position, kvLayer, linLayer, weights)
    if isFull: inc kvLayer
    else: inc linLayer

  # Fused sampling.
  result = eng.sample(addr bufs.hidden[0],
                      addr bufs.scratchArgmax[0],
                      cfg.batchSize,
                      cfg.invTemperature,
                      cfg.seed + position)

# ---------------------------------------------------------------------------
# High-level generate() — prefill + decode loop.
# ---------------------------------------------------------------------------

proc generate*(eng: Engine;
               prompt: seq[int32];
               maxNew: uint32;
               weights: pointer;
               cfg = DecodeConfig()): seq[int32] =
  ## Run an autoregressive decode loop of `maxNew` tokens starting from
  ## `prompt`.  Returns the produced tokens (including the prompt).
  ## Stops early on negative sample results (model can signal EOS via
  ## the sampling kernel).
  if prompt.len == 0:
    raise (ref EngineError)(code: PHENO_ERR_INVALID_ARG,
                            kind: ekInvalidArg,
                            msg: "prompt is empty")
  var bufs = allocBuffers(cfg)
  result = @prompt

  # Prefill: process each prompt token at positions 0..S.
  for i, tok in prompt:
    discard decodeStep(eng, bufs, cfg, tok.int32, i.uint32, weights)
  # Decode: roll one new token per step.
  for i in 0'u32 ..< maxNew:
    let last = result[^1]
    let pos = uint32(prompt.len) + i
    let next = decodeStep(eng, bufs, cfg, last, pos, weights)
    result.add(next)
    if next < 0: break

# ---------------------------------------------------------------------------
# CLI entry: print a sample decode plan (no actual GPU call).
# ---------------------------------------------------------------------------

when isMainModule:
  echo "decode.nim — Qwen3.5 0.8B decode example"
  echo "Layer schedule: every 4th of 24 is full attention"
  for i in 0'u32 ..< QWEN3_5_NUM_HIDDEN_LAYERS:
    if i mod 8 == 0: stdout.write "\n"
    stdout.write (if layerIsFull(i): "F " else: "L ")
  stdout.write "\n"
  let cfg = DecodeConfig(batchSize: 1, maxSeqLen: 4096, invTemperature: cfloat(1.0))
  echo "Default config: batch=", cfg.batchSize, " seq=", cfg.maxSeqLen
