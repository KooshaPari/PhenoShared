## main.nim — Nim smoke-test entry for the Qwen3.5 0.8B kernel engine.
##
## Mirrors `pony/main.pony`: creates an engine, prints the device name,
## tries to load `../build/kernels.metallib` (if present), then exits.
##
## Build:
##   nim c --hints:off --warnings:off --gc:arc --opt:speed \
##       -d:phenoCengPath="../rust/target/release" \
##       --out:nim_main nim/main.nim
##
## Run:
##   ./nim_main
##
## Expected output (with no metallib): prints device name, "metallib not
## found; continuing without GPU", and "smoke test PASS".  With a valid
## metallib on disk it additionally prints `has_metal: true`.

import qwen3_5
import std/[os, strutils, options]

proc pathExists(path: string): bool =
  ## Cheap `access(path, 0)`-style check via `fileExists`.  We don't pull
  ## in `<unistd.h>` because the build is portable to non-POSIX targets
  ## (in theory) and `fileExists` covers the common case.
  try:
    result = fileExists(path)
  except IOError:
    result = false

proc main() =
  echo "[nim] Qwen3.5 0.8B kernel engine — Nim FFI smoke test"

  # 1. Construct the engine.  In stub mode (no metallib), the C ABI still
  # returns OK and the engine object is usable for non-GPU calls.
  let eng = initEngine(none(cstring))
  echo "[nim] engine created"
  echo "[nim] device:    ", eng.deviceName
  echo "[nim] hasMetal:  ", eng.hasMetal

  # 2. Try to load kernels.metallib relative to cwd.
  let metallibPath = "../build/kernels.metallib"
  if pathExists(metallibPath):
    try:
      eng.loadMetallib(metallibPath)
      echo "[nim] metallib loaded: ", metallibPath
    except EngineError as e:
      echo "[nim] metallib load failed: ", e.msg
  else:
    echo "[nim] metallib not found; continuing without GPU"

  # 3. Architecture constants — surface them so we can spot-check that the
  # header-derived constants match the model config.  `QWEN3_5_NUM_FULL_LAYERS`
  # is implicit (total minus linear).
  let fullLayers = QWEN3_5_NUM_HIDDEN_LAYERS - QWEN3_5_LIN_NUM_LAYERS
  echo "[nim] arch: H=", QWEN3_5_HIDDEN_SIZE,
       " I=", QWEN3_5_INTERMEDIATE_SIZE,
       " V=", QWEN3_5_VOCAB_SIZE,
       " L=", QWEN3_5_NUM_HIDDEN_LAYERS,
       " full=", fullLayers,
       " lin=", QWEN3_5_LIN_NUM_LAYERS

  echo "[nim] smoke test PASS"

when isMainModule:
  main()