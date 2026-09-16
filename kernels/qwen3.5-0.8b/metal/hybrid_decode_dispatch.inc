// AUTO-GENERATED from arch.yaml — DO NOT EDIT.
// Regenerate with: python3 python/codegen.py --arch arch.yaml
// Verification: tests/test_codegen.py asserts byte-equality.

//
// This file replaces a hand-coded ``((layer % 4u) == 3u)`` literal
// that lived in ``metal/hybrid_decode.metal``.  Everything is
// derived from ``arch.yaml`` via ``python/codegen.py``.
//
// Schedule invariant: layers {3, 7, 11, 15, 19, 23} (every 4th layer, of which there are 6) are full attention with GQA 8:2 = 4:1.  The rest are DeltaNet linear attention.
//
#ifndef QWEN_HYBRID_DECODE_DISPATCH_INC
#define QWEN_HYBRID_DECODE_DISPATCH_INC

#include <metal_stdlib>
namespace qwen {

constant uint kHybridFullAttnInterval   = 4u;   // arch.yaml: full_attention.full_attention_interval
constant uint kHybridFullAttnOffset     = 0u;                       // predicate remainder (1+layer) % interval == offset
constant uint kHybridFullAttnNumLayers  = 6u;   // arch.yaml: full_attention.full_attention_layer_indices.size()
constant uint kHybridLinearNumLayers    = 18u;          // num_hidden_layers - kHybridFullAttnNumLayers

// Explicit full-attention layer indices, sorted ascending.
// Source: arch.yaml full_attention.full_attention_layer_indices.
// Compiled by the build from this generated constant, so a
// change requires editing arch.yaml + running codegen.
constant uint kHybridFullAttnLayerIndices[kHybridFullAttnNumLayers] = {3, 7, 11, 15, 19, 23};

// Static (compile-time) assertion: the explicit index list and
// the predicate ``((layer + 1) % kHybridFullAttnInterval) == 0`` must
// be equivalent on [0, num_hidden_layers).  The codegen runs
// this check at code-generation time; the kernel additionally
// rebuilds it via static_assert in tests.
// (codegen-time guard satisfied — see codegen.py emit_metal_dispatch)


// Per-layer kind predicate.
//   1u = full attention (flash-attn v2 GQA path)
//   0u = linear attention  (DeltaNet gated recurrent)
// Replaces the literal ``(layer % kHybridFullAttnInterval) == (kHybridFullAttnInterval - 1)u``
// we used to inline in hybrid_decode.metal.  Equivalent under the
// schedule invariant; offset form picks every interval-th layer
// starting at index 0 — the same set as full_attention_layer_indices.
inline uint hybrid_layer_is_full(uint layer) {
    return ((layer + 1u) % kHybridFullAttnInterval) == kHybridFullAttnOffset ? 1u : 0u;
}

inline uint hybrid_layer_is_linear(uint layer) {
    return 1u - hybrid_layer_is_full(layer);
}


// Audit A4: runtime simdgroup_size.  Source of truth is
// arch.yaml kernel_strategy.default_simdgroup_size; the host binds
// this constant via MTLFunctionConstantValues at pipeline-creation
// time (Apple Silicon -> 32u, Intel/AMD -> 16u).
constant uint kArchSimdgroupSize = 32u;
}  // namespace qwen

#endif  // QWEN_HYBRID_DECODE_DISPATCH_INC
