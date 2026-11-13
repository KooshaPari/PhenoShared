// AUTO-GENERATED from arch.yaml — DO NOT EDIT.
// Regenerate with: python3 python/codegen.py --arch arch.yaml
// Verification: tests/test_codegen.py asserts byte-equality.

# Mirror of include/qwen3_5.h for native Nim consumers.

const ModelId* = "Qwen3.5-0.8B"
const HfRepo* = "Qwen/Qwen3.5-0.8B"
const Family* = "qwen3.5"
const Kind* = "hybrid_attention"

# Core dims
const VocabSize* = 248320
const HiddenSize* = 1024
const IntermediateSize* = 3584
const NumHiddenLayers* = 24
const MaxPositionEmbeddings* = 262144
const RmsNormEps*: float32 = 1.0e-6'f32
const TieWordEmbeddings* = true

# Full attention (GQA 4:1)
const FullHeads* = 8
const FullKvHeads* = 2
const FullHeadDim* = 256
const FullHeadsPerKv* = FullHeads div FullKvHeads  # 4
const FullQDim* = FullHeads * FullHeadDim  # 2048
const FullKvDim* = FullKvHeads * FullHeadDim  # 512
const FullQkvDim* = FullQDim + 2 * FullKvDim  # 3072
const FullAttnInterval* = 4
const FullAttnNumLayers* = 6

# Partial rotary
const RopeTheta*: float32 = 10000000.0'f32
const PartialRotaryFactor*: float32 = 0.25'f32
const MRopeInterleaved* = true
const MRopeSectionT* = 11
const MRopeSectionH* = 11
const MRopeSectionW* = 10
const RotDim* = 32

# Linear attention (DeltaNet)
const LinNumLayers* = 18
const LinKeyHeads* = 16
const LinValueHeads* = 16
const LinKeyHeadDim* = 128
const LinValueHeadDim* = 128
const LinConvKernel* = 4
const LinQkvDim* = 3 * LinKeyHeads * LinKeyHeadDim  # 6144
const LinStateElements* = 16 * 16 * 128 * 128  # 4194304
const LinStateBytesF32* = LinStateElements * 4  # 16777216
const LinStateBytesBf16* = LinStateElements * 2  # 8388608

# Layer schedule (true = full attention)
const LayerIsFull*: array[NumHiddenLayers, bool] = [
  False, False, False, True, False, False, False, True,
  False, False, False, True, False, False, False, True,
  False, False, False, True, False, False, False, True
]

# Compile-time sanity (matches _Static_assert in qwen3_5.h)
static:
  doAssert HiddenSize == 1024, "hidden_size mismatch"
  doAssert FullHeadDim == 256, "head_dim mismatch"
  doAssert RotDim == 32, "rot_dim mismatch"
