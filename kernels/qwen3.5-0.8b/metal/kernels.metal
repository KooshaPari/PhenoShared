// kernels.metal — top-level entry that includes all kernel sources.
//
// Compiled to a single .metallib via:
//   xcrun -sdk macosx metal -c kernels.metal -o kernels.air
//   xcrun -sdk macosx metallib kernels.air -o kernels.metallib
//
// All .metal files in this directory are #included here.  Order matters only
// for namespace resolution; types.metal must come first.
//
// Buffer-arg contract (per task spec, applies to every kernel in this lib):
//   [[buffer(0)]]  in1   (input, fp16 unless noted)
//   [[buffer(1)]]  out   (output)
//   [[buffer(2)]]  w     (weight/bias; may be null)
//   [[buffer(3)]]  aux   (auxiliary: state, cache, mask, etc.)
//   [[buffer(4..N)]] dims / scalars (uint, float)

#include "types.metal"
#include "norm.metal"
#include "rope.metal"
#include "activation.metal"
#include "attention.metal"
#include "linear_attention.metal"
#include "sampling.metal"
#include "gemm.metal"
#include "fused_l2norm.metal"
#include "fused_mla_decode.metal"
#include "hybrid_decode.metal"
