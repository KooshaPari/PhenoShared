# AUTO-GENERATED from arch.yaml — DO NOT EDIT.
# Regenerate with: python3 python/codegen.py --arch arch.yaml
# Verification: tests/test_codegen.py asserts byte-equality.

# Mirror of include/qwen3_5.h for native Mojo consumers.

alias ModelId = "Qwen3.5-0.8B"
alias HfRepo = "Qwen/Qwen3.5-0.8B"
alias Family = "qwen3.5"
alias Kind = "hybrid_attention"

# Core dims
alias VocabSize: Int = 248320
alias HiddenSize: Int = 1024
alias IntermediateSize: Int = 3584
alias NumHiddenLayers: Int = 24
alias MaxPositionEmbeddings: Int = 262144
alias RmsNormEps: Float32 = 1.0e-6
alias TieWordEmbeddings: Bool = True

# Full attention (GQA 4:1)
alias FullHeads: Int = 8
alias FullKvHeads: Int = 2
alias FullHeadDim: Int = 256
alias FullHeadsPerKv: Int = FullHeads // FullKvHeads  # 4
alias FullQDim: Int = FullHeads * FullHeadDim  # 2048
alias FullKvDim: Int = FullKvHeads * FullHeadDim  # 512
alias FullQkvDim: Int = FullQDim + 2 * FullKvDim  # 3072
alias FullAttnInterval: Int = 4
alias FullAttnNumLayers: Int = 6

# Partial rotary
alias RopeTheta: Float32 = 1e+07
alias PartialRotaryFactor: Float32 = 0.25
alias MRopeInterleaved: Bool = True
alias MRopeSectionT: Int = 11
alias MRopeSectionH: Int = 11
alias MRopeSectionW: Int = 10
alias RotDim: Int = 32

# Linear attention (DeltaNet)
alias LinNumLayers: Int = 18
alias LinKeyHeads: Int = 16
alias LinValueHeads: Int = 16
alias LinKeyHeadDim: Int = 128
alias LinValueHeadDim: Int = 128
alias LinConvKernel: Int = 4
alias LinQkvDim: Int = 3 * LinKeyHeads * LinKeyHeadDim  # 6144
alias LinStateElements: Int = 16 * 16 * 128 * 128  # 4194304
alias LinStateBytesF32: Int = LinStateElements * 4  # 16777216
alias LinStateBytesBf16: Int = LinStateElements * 2  # 8388608

# Layer schedule (True = full attention, False = DeltaNet)
fn layer_is_full(i: Int) -> Bool:
    return ((i + 1) % FullAttnInterval) == 0

# Compile-time sanity (mirrors _Static_assert in qwen3_5.h)
comptime if HiddenSize != 1024:
    print("ERROR: hidden_size mismatch")
comptime if FullHeadDim != 256:
    print("ERROR: head_dim mismatch")
comptime if RotDim != 32:
    print("ERROR: rot_dim mismatch")
