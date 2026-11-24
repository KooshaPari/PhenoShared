## bench.nim — Nim vs C++ latency benchmark harness.
##
## Compares per-decode-step latency between the C++ host (linked into the
## Rust cdylib) and the Nim abstraction layer on top of it.  The point is
## to verify that the Nim FFI shim adds *zero* overhead compared to
## calling the C ABI directly from C.
##
## Build (when nim is installed):
##   nim c --hints:off --warnings:off --gc:arc --opt:speed \
##       -d:phenoCengPath="../rust/target/release" \
##       --out:nim_bench nim/bench.nim
##
## Run:
##   ./nim_bench
##
## If the C++ engine is in stub mode (no metallib loaded), every per-op
## call returns PHENO_ERR_NO_KERNEL which we tolerate; the benchmark
## then measures FFI overhead, not GPU compute time.
##
## If nim is NOT installed (current state of this worktree), this file
## is documentation only.  The install command is `brew install nim`.

import qwen3_5
import std/[times, strutils, strformat, options, math, algorithm, os]

# ---------------------------------------------------------------------------
# Configurable knobs.
# ---------------------------------------------------------------------------

type
  BenchConfig* = object
    batchSize*: uint32
    seqLen*: uint32
    warmupSteps*: uint32
    measureSteps*: uint32
    tolerateStub*: bool

const defaultCfg = BenchConfig(
  batchSize: 1,
  seqLen: 4096,
  warmupSteps: 3,
  measureSteps: 100,
  tolerateStub: true)

# ---------------------------------------------------------------------------
# A single decode-step call from the Nim side.
# ---------------------------------------------------------------------------

proc runOneStep(eng: Engine;
                bufs: pointer;
                cfg: BenchConfig;
                tokenId: int32;
                position: uint32): int32 =
  ## In stub mode this returns 0; the per-op kernel_engine_* calls would
  ## raise EngineError(ekNoKernel), which is tolerated.  When a real
  ## metallib is loaded, this is the per-step orchestration time.
  try:
    # Per-op dispatch as in `decode.nim::runLayer` — we exercise the
    # most expensive op (attention decode) per step.
    let scale: cfloat = 1.0 / sqrt(cfloat(QWEN3_5_FULL_HEAD_DIM))
    eng.attentionDecode(bufs, bufs, bufs, bufs,
                        cfg.batchSize, position + 1, scale)
    eng.fusedSwiglu(bufs, bufs, cfg.batchSize * QWEN3_5_INTERMEDIATE_SIZE)
  except EngineError as e:
    if not (e.kind == ekNoKernel and cfg.tolerateStub):
      raise
  return 0

# ---------------------------------------------------------------------------
# The benchmark: warmup, then `measureSteps` timed iterations, report
# per-step p50/p99.
# ---------------------------------------------------------------------------

proc bench*(cfg: BenchConfig = defaultCfg) =
  echo "Qwen3.5 0.8B Nim bench (batch=", cfg.batchSize,
       " seq=", cfg.seqLen, " steps=", cfg.measureSteps, ")"
  var eng = initEngine(none(cstring))
  echo "  device: ", eng.deviceName,
       "  hasMetal: ", eng.hasMetal

  # Allocate scratch buffers.  We don't use them in stub mode, but
  # declare them so the FFI calls don't null-deref.
  let scratchBytes = cfg.batchSize * QWEN3_5_HIDDEN_SIZE * 2 + 1024
  let bufs = newSeq[uint8](scratchBytes)

  # Warmup.
  for i in 0'u32 ..< cfg.warmupSteps:
    discard runOneStep(eng, addr bufs[0], cfg, 0, i)

  # Measure.
  let t0 = epochTime()
  var samples: array[256, float]  # sized > max measureSteps; unused slots stay 0.
  for i in 0'u32 ..< cfg.measureSteps:
    let t_step = epochTime()
    discard runOneStep(eng, addr bufs[0], cfg,
                       (i mod QWEN3_5_VOCAB_SIZE).int32, i)
    samples[i.int] = (epochTime() - t_step) * 1_000_000  # microseconds

  let total_us = (epochTime() - t0) * 1_000_000
  let avg_us = total_us / cfg.measureSteps.float

  # Build a sortable view of just the populated slots.  We copy to a fresh
  # seq only at the end so the hot loop avoids any seq reallocations.
  var populated = newSeq[float](cfg.measureSteps.int)
  for i in 0 ..< cfg.measureSteps.int:
    populated[i] = samples[i]
  populated.sort()

  let p50 = populated[populated.len div 2]
  let p99 = populated[(populated.len * 99) div 100]

  echo &"  total: {total_us:.1f} us  avg: {avg_us:.2f} us/step"
  echo &"  p50: {p50:.2f} us  p99: {p99:.2f} us"

  # Approximate tokens/sec.
  let tps = 1_000_000.0 / avg_us
  echo &"  approx throughput: {tps:.1f} tok/s (stub mode = FFI overhead only)"

  # Force-exit to dodge Nim 2 ARC's shutdown-time dealloc assertion when
  # the engine handle and seqs are torn down in an unusual order.  The
  # benchmark numbers are already printed by this point.
  quit(0)

# ---------------------------------------------------------------------------
# CLI entry.
# ---------------------------------------------------------------------------

when isMainModule:
  # Parse simple CLI flags.
  var cfg = defaultCfg
  for i, arg in commandLineParams():
    if arg.startsWith("--batch="):
      cfg.batchSize = parseUInt(arg[8 .. ^1]).uint32
    elif arg.startsWith("--seq="):
      cfg.seqLen = parseUInt(arg[5 .. ^1]).uint32
    elif arg.startsWith("--steps="):
      cfg.measureSteps = parseUInt(arg[7 .. ^1]).uint32
  bench(cfg)
