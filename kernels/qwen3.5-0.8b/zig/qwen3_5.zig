// AUTO-GENERATED from arch.yaml — DO NOT EDIT.
// Regenerate with: python3 python/codegen.py --arch arch.yaml
// Verification: tests/test_codegen.py asserts byte-equality.

// Mirror of include/qwen3_5.h for native Zig consumers.

pub const ModelId = "Qwen3.5-0.8B";
pub const HfRepo = "Qwen/Qwen3.5-0.8B";
pub const Family = "qwen3.5";
pub const Kind = "hybrid_attention";

pub const VocabSize: usize = 248320;
pub const HiddenSize: usize = 1024;
pub const IntermediateSize: usize = 3584;
pub const NumHiddenLayers: usize = 24;
pub const MaxPositionEmbeddings: usize = 262144;
pub const RmsNormEps: f32 = 1.0e-6f;
pub const TieWordEmbeddings: bool = true;

// Full attention (GQA 4:1)
pub const FullHeads: usize = 8;
pub const FullKvHeads: usize = 2;
pub const FullHeadDim: usize = 256;
pub const FullHeadsPerKv: usize = FullHeads / FullKvHeads; // 4
pub const FullQDim: usize = FullHeads * FullHeadDim; // 2048
pub const FullKvDim: usize = FullKvHeads * FullHeadDim; // 512
pub const FullQkvDim: usize = FullQDim + 2 * FullKvDim; // 3072
pub const FullAttnInterval: usize = 4;
pub const FullAttnNumLayers: usize = 6;

// Partial rotary
pub const RopeTheta: f32 = 10000000.0;
pub const PartialRotaryFactor: f32 = 0.25;
pub const MRopeInterleaved: bool = true;
pub const MRopeSection = .{11, 11, 10}; // T, H, W
pub const RotDim: usize = 32;  // partial_rotary_factor * FullHeadDim

// Linear attention (DeltaNet)
pub const LinNumLayers: usize = 18;
pub const LinKeyHeads: usize = 16;
pub const LinValueHeads: usize = 16;
pub const LinKeyHeadDim: usize = 128;
pub const LinValueHeadDim: usize = 128;
pub const LinConvKernel: usize = 4;
pub const LinQkvDim: usize = 3 * LinKeyHeads * LinKeyHeadDim; // 6144
pub const LinStateElements: usize = 16 * 16 * 128 * 128; // 4194304
pub const LinStateBytesF32: usize = LinStateElements * 4; // 16777216
pub const LinStateBytesBf16: usize = LinStateElements * 2; // 8388608

/// Layer schedule. true = full attention, false = DeltaNet.
pub const LayerIsFull: [NumHiddenLayers]bool = blk: {
    var arr: [NumHiddenLayers]bool = undefined;
    for (0..NumHiddenLayers) |i| { arr[i] = ((i + 1) % FullAttnInterval == 0); }
    break :blk arr;
};

/// Convenience: pretty-print the layer schedule.
pub fn printLayerSchedule(writer: anytype) !void {
    try writer.writeAll("Qwen3.5 0.8B layer schedule (F = full, L = linear):\n");
    for (0..NumHiddenLayers) |i| {
        try writer.writeAll(if (LayerIsFull[i]) "F " else "L ");
        if ((i + 1) % 8 == 0) try writer.writeAll("\n");
    }
    try writer.writeAll("\n");
}

// ----- Compile-time sanity (matches _Static_assert in qwen3_5.h) -----
comptime {
    _ = HiddenSize;
    if (HiddenSize != 1024) @compileError("hidden_size mismatch");
    if (FullHeadDim != 256) @compileError("head_dim mismatch");
    if (RotDim != 32) @compileError("rot_dim mismatch");
}
