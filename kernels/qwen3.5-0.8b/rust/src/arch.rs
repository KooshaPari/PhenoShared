// AUTO-GENERATED from arch.yaml — DO NOT EDIT.
// Regenerate with: python3 python/codegen.py --arch arch.yaml
// Verification: tests/test_codegen.py asserts byte-equality.

// Generated python/codegen.py — regenerate to keep in sync.

// Mirrors include/qwen3_5.h byte-for-byte.

#![allow(dead_code)]

pub mod arch {
    // Identity (informational; match qwen3_5.h string literals).
    pub const MODEL_ID: &str = "Qwen3.5-0.8B";
    pub const HF_REPO: &str = "Qwen/Qwen3.5-0.8B";
    pub const FAMILY: &str = "qwen3.5";
    pub const KIND: &str = "hybrid_attention";

    // Core dims
    pub const VOCAB_SIZE: usize = 248320;
    pub const HIDDEN_SIZE: usize = 1024;
    pub const INTERMEDIATE_SIZE: usize = 3584;
    pub const NUM_HIDDEN_LAYERS: usize = 24;
    pub const MAX_POSITION_EMBEDDINGS: usize = 262144;
    pub const RMS_NORM_EPS: f32 = 1.0e-06;
    pub const TIE_WORD_EMBEDDINGS: bool = true;

    // Full attention (GQA 4:1)
    pub const FULL_HEADS: usize = 8;
    pub const FULL_KV_HEADS: usize = 2;
    pub const FULL_HEAD_DIM: usize = 256;
    pub const FULL_HEADS_PER_KV: usize = FULL_HEADS / FULL_KV_HEADS; // 4
    pub const FULL_Q_DIM: usize = FULL_HEADS * FULL_HEAD_DIM;          // 2048
    pub const FULL_KV_DIM: usize = FULL_KV_HEADS * FULL_HEAD_DIM;      // 512
    pub const FULL_QKV_DIM: usize = FULL_Q_DIM + 2 * FULL_KV_DIM;       // 3072
    pub const FULL_ATTN_INTERVAL: usize = 4;
    pub const FULL_ATTN_NUM_LAYERS: usize = 6;
    pub const FULL_ATTN_LAYER_INDICES: [usize; FULL_ATTN_NUM_LAYERS] = [3, 7, 11, 15, 19, 23];

    // Partial rotary
    pub const ROPE_THETA: f32 = 1e+07;
    pub const PARTIAL_ROTARY_FACTOR: f32 = 0.25;
    pub const MROPE_INTERLEAVED: bool = true;
    pub const MROPE_SECTION: [usize; 3] = [11, 11, 10];
    pub const ROT_DIM: usize = 32;       // partial_rotary_factor * head_dim

    // Linear attention (DeltaNet)
    pub const LIN_NUM_LAYERS: usize = 18;        // = NUM_HIDDEN_LAYERS - FULL_ATTN_NUM_LAYERS
    pub const LIN_KEY_HEADS: usize = 16;
    pub const LIN_VALUE_HEADS: usize = 16;
    pub const LIN_KEY_HEAD_DIM: usize = 128;
    pub const LIN_VALUE_HEAD_DIM: usize = 128;
    pub const LIN_CONV_KERNEL: usize = 4;
    pub const LIN_QKV_DIM: usize = 3 * LIN_KEY_HEADS * LIN_KEY_HEAD_DIM; // 6144
    pub const LIN_STATE_ELEMENTS: usize = 16 * 16 * 128 * 128; // 4194304
    pub const LIN_STATE_BYTES_F32: usize = LIN_STATE_ELEMENTS * 4;   // 16777216
    pub const LIN_STATE_BYTES_BF16: usize = LIN_STATE_ELEMENTS * 2;  // 8388608

    /// Kernel dispatch (DAG-41 — audit-A4 extended to Rust).
    pub const DEFAULT_SIMDGROUP_SIZE: u32 = 32; // Metal simdgroup
    pub const THREADGROUP_SIZE_DEFAULT: u32 = 256; // = 8 * DEFAULT_SIMDGROUP_SIZE

    /// Layer schedule: 6 full, 18 linear (every 4th is full).
    pub const LAYER_IS_FULL: [bool; NUM_HIDDEN_LAYERS] = {
        let mut arr = [false; NUM_HIDDEN_LAYERS];
        let mut i = 0;
        while i < NUM_HIDDEN_LAYERS {
            arr[i] = (i + 1) % FULL_ATTN_INTERVAL == 0;
            i += 1;
        }
        arr
    };

    /// Sanity assertions matching _Static_assert in qwen3_5.h.
    const _: () = {
        assert!(HIDDEN_SIZE == 1024, "hidden_size mismatch");
        assert!(FULL_HEAD_DIM == 256, "head_dim mismatch");
        assert!(ROT_DIM == 32, "rot_dim mismatch");
    };
}
