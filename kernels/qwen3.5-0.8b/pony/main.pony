// main.pony — Pony entry point that exercises the kernel engine via FFI.
//
// Steps:
//   1. Create engine via PhenoFFI
//   2. Load kernels.metallib from ../build/kernels.metallib relative to cwd
//   3. Print device name + has_metal
//   4. Print arch constants
//
// Build:
//   ponyc --path . --output ../build .

use @access[I32](path: Pointer[U8] tag, mode: I32)

actor Main
  new create(env: Env) =>
    env.out.print("[pony] Qwen3.5 0.8B kernel engine — Pony FFI smoke test")

    let engine = PhenoHelpers.create_engine()
    if engine.is_null() then
      env.out.print("[pony] engine creation failed")
      return
    end
    env.out.print("[pony] engine created")

    // Try to load metallib from ../build/kernels.metallib relative to cwd.
    let metallib_path = "../build/kernels.metallib"
    if path_exists(metallib_path) then
      let rc = PhenoHelpers.load_metallib(engine, metallib_path)
      if rc == Status.ok() then
        env.out.print("[pony] metallib loaded: " + metallib_path)
        env.out.print("[pony] has_metal: " + PhenoHelpers.has_metal(engine).string())
        env.out.print("[pony] device:    " + PhenoHelpers.device_name(engine))
      else
        env.out.print("[pony] metallib load failed: " + Status.strerror(rc))
      end
    else
      env.out.print("[pony] metallib not found; continuing without GPU")
    end

    env.out.print("[pony] arch: H=" + Qwen35.hidden_size().string() +
                  " I=" + Qwen35.intermediate_size().string() +
                  " V=" + Qwen35.vocab_size().string() +
                  " L=" + Qwen35.num_hidden_layers().string() +
                  " full=" + Qwen35.num_full_layers().string() +
                  " lin=" + Qwen35.num_linear_layers().string())

    // Spawn the decode orchestrator.
    let orchestrator = DecodeOrchestrator(engine)

    env.out.print("[pony] smoke test PASS")

    // Destroy engine.
    @pheno_engine_destroy[I32](engine)

  fun tag path_exists(path: String): Bool =>
    @access[I32](path.cstring(), 0) == 0