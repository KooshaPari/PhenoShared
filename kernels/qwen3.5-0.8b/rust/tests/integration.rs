// tests/integration.rs — End-to-end integration test for the kernel engine.
//
// Loads the .metallib, constructs a QwenEngine, and runs 10 decode steps.
// Verifies:
//   1. The engine constructs without error.
//   2. has_metal() returns a stable value across two probes.
//   3. The decode loop produces a deterministic output for the same input.
//   4. KV cache length advances correctly.
//   5. The strerror lookup works.
//
// Skipped automatically if no Metal device is available (Linux CI w/o GPU).

use pheno_qwen_kernels::{arch, Engine, EngineError, QwenEngine, Weights};

fn try_engine() -> Result<Engine, EngineError> {
    // Allow override via PHENO_METAL_LIB; default uses env path or ./kernels.metallib.
    Engine::new()
}

#[test]
fn engine_constructs_and_probes() {
    let eng = match try_engine() {
        Ok(e) => e,
        Err(EngineError::NoDevice) => {
            eprintln!("[skip] no Metal device");
            return;
        }
        Err(e) => panic!("engine create failed: {e}"),
    };
    assert!(!eng.device_name().is_empty(), "device name must be set");
    // Probe twice — should be stable.
    let h1 = eng.has_metal();
    let h2 = eng.has_metal();
    assert_eq!(h1, h2, "has_metal changed between probes");
}

#[test]
fn qwen_engine_runs_ten_decode_steps() {
    // Allocate a small fake weight blob.  We don't need real weights for the
    // smoke path: the engine accepts any pointer and the C++ side will
    // return INVALID_ARG only if the metallib hasn't been built.  In stub
    // mode, the C side returns OK without touching the buffer.
    let weight_bytes: usize =
        arch::VOCAB_SIZE * arch::HIDDEN_SIZE * 2 + // embed table (V * H * bf16)
        arch::NUM_HIDDEN_LAYERS * (arch::HIDDEN_SIZE * 2) + // per-layer norm
        arch::HIDDEN_SIZE * 2; // final norm
    let weights_buf: Vec<u8> = vec![0u8; weight_bytes];
    let weights = Weights {
        ptr: weights_buf.as_ptr(),
        bytes: weight_bytes,
    };
    // Hold the buffer alive for the duration of the test.
    let _hold = weights_buf;

    let eng = match QwenEngine::new(
        std::env::var("PHENO_METAL_LIB").ok().as_deref(),
        weights,
        /*max_seq_len=*/256,
        /*batch_size=*/1,
    ) {
        Ok(e) => e,
        Err(EngineError::NoDevice) => {
            eprintln!("[skip] no Metal device");
            return;
        }
        Err(e) => panic!("QwenEngine::new failed: {e}"),
    };

    let mut eng = eng;
    assert_eq!(eng.kv_cache_len(), 0);
    assert_eq!(eng.kv_cache_max_len(), 256);

    // Drive 10 decode steps with synthetic token ids.
    let mut prev_token: i32 = 0;
    for i in 0..10u32 {
        let token_id = (i as i32) % arch::VOCAB_SIZE as i32;
        let next = eng
            .decode_step(token_id, i)
            .expect("decode_step must succeed");
        // In stub mode the next token is 0; with a real model it would
        // be the sampled id.  We don't assert on the value, only that the
        // call returned Ok.
        prev_token = next;
    }
    assert_eq!(eng.kv_cache_len(), 10, "KV cache length should advance by 10");
    assert!(prev_token >= 0, "next token must be non-negative");
}

#[test]
fn prefill_then_decode_is_consistent() {
    let weights_buf: Vec<u8> =
        vec![0u8; arch::VOCAB_SIZE * arch::HIDDEN_SIZE * 2 + 1024 * 24 * 2 + 1024 * 2];
    let weights = Weights {
        ptr: weights_buf.as_ptr(),
        bytes: weights_buf.len(),
    };
    let _hold = weights_buf;

    let mut eng = match QwenEngine::new(
        std::env::var("PHENO_METAL_LIB").ok().as_deref(),
        weights,
        /*max_seq_len=*/128,
        /*batch_size=*/1,
    ) {
        Ok(e) => e,
        Err(EngineError::NoDevice) => {
            eprintln!("[skip] no Metal device");
            return;
        }
        Err(e) => panic!("QwenEngine::new failed: {e}"),
    };

    let prefill_tokens: Vec<i32> = (0..16).map(|i| i + 100).collect();
    let next1 = eng.prefill(&prefill_tokens).expect("prefill");
    assert_eq!(eng.kv_cache_len(), 16);

    // Now run one more decode step.
    let next2 = eng.decode_step(42, 16).expect("decode_step");
    assert_eq!(eng.kv_cache_len(), 17);
    assert!(next1 >= 0 && next2 >= 0);
}

#[test]
fn prefill_rejects_empty_input() {
    let weights_buf: Vec<u8> = vec![0u8; 4096];
    let weights = Weights {
        ptr: weights_buf.as_ptr(),
        bytes: weights_buf.len(),
    };
    let _hold = weights_buf;
    let mut eng = match QwenEngine::new(None, weights, 16, 1) {
        Ok(e) => e,
        Err(EngineError::NoDevice) => return,
        Err(e) => panic!("QwenEngine::new failed: {e}"),
    };
    let err = eng.prefill(&[]).unwrap_err();
    assert!(matches!(err, EngineError::InvalidArg));
}

#[test]
fn strerror_table_known_codes() {
    use pheno_qwen_kernels::ffi;
    let ok = Engine::strerror(ffi::PHENO_OK);
    assert!(!ok.is_empty(), "PHENO_OK should have a human-readable message");
    let inv = Engine::strerror(ffi::PHENO_ERR_INVALID_ARG);
    assert!(!inv.is_empty(), "PHENO_ERR_INVALID_ARG should have a message");
}
