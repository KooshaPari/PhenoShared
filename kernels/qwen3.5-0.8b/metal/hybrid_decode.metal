// hybrid_decode.metal — per-layer dispatch orchestrator for decode (S=1).
//
// Qwen3.5 0.8B is a hybrid model: 24 layers, every 4th layer (3, 7, 11, 15,
// 19, 23) is full attention with GQA 4:1; the remaining 18 layers are
// DeltaNet-style linear attention.
//
// This file hosts the orchestration kernel that, given a layer index,
// dispatches to either `fused_mla_decode` (full attn) or a fused linear-
// attention decode path, in a single launch using tgid.z as the layer
// index.  The host encodes the layer index in the grid, so the kernel
// branch is just a switch on `layer`.
//
// Args (per task contract — fixed order input/output/aux/dims):
//   buffer(0)  hidden_in     [B, H]  half   (input to the layer)
//   buffer(1)  hidden_out    [B, H]  half   (output of the layer)
//   buffer(2)  qkv_cache     [L_full, ...]  half   (K/V cache for full layers)
//   buffer(3)  state_cache   [L_lin, ...]   float  (delta-net state for lin layers)
//   buffer(4)  weight_bufs   [..]    half   (packed QKV/MLP/etc.)
//   buffer(5)  B             (uint)
//   buffer(6)  S_k           (uint)         (current seq length)
//   buffer(7)  layer         (uint)         (0..23)
//   buffer(8)  layer_kind    (uint)         (0 = linear, 1 = full, derived in-kernel)
//
// The kernel performs a minimal-norm-normalize + dispatch — the actual GEMM,
// attention, and MLP are out of scope here.  The orchestrator is the layer
// entry point: it sets up the per-layer sub-grid and routes work.
//
// The "per-layer kind" is computed in-kernel as `((layer % 4) == 3) ? full : linear`
// to mirror the Qwen3.5 pattern: the 0th, 4th, 8th, 12th, 16th, 20th layers
// are linear (so layers 3, 7, 11, 15, 19, 23 are full).

#include <metal_stdlib>
#include <metal_simdgroup>
#include "types.metal"
using namespace metal;

namespace {
constant int kHybridMaxLayers = qwen::kNumHiddenLayers;   // 24
constant int kHybridTgSize    = 128;
}  // namespace

// Full-attn layers (3, 7, 11, 15, 19, 23) use the standard fused-mla path
// (the implementation lives in fused_mla_decode.metal; we re-declare the
// same argument contract here so a host-level linker can call either).  The
// actual work is done by `fused_mla_decode`; this orchestrator just
// identifies which path applies and emits a token identifying the layer
// kind to the host (via the `layer_kind_out` buffer) so the host can
// dispatch the right kernel in a subsequent launch.
//
// For the "all-in-one" demo path, we just compute a tiny attribute buffer
// describing what the host should do.

kernel void hybrid_decode_orchestrator(
    const device half* hidden_in   [[buffer(0)]],
    device half* hidden_out        [[buffer(1)]],
    const device half* qkv_cache    [[buffer(2)]],
    const device float* state_cache [[buffer(3)]],
    const device half* weight_bufs  [[buffer(4)]],
    device uint* layer_kind_out     [[buffer(5)]],
    constant uint& B               [[buffer(6)]],
    constant uint& S_k             [[buffer(7)]],
    constant uint& layer           [[buffer(8)]],
    uint tgid                      [[threadgroup_position_in_grid]],
    uint tid                       [[thread_index_in_threadgroup]]) {
    // 1 TG per (b, layer).  Inside the TG: tiny work (just bookkeeping +
    // a minimal copy of hidden_in -> hidden_out so the kernel can be smoke-
    // tested in isolation).  Real work is dispatched host-side after reading
    // layer_kind_out.
    uint b = tgid;
    if (b >= B) return;
    if (layer >= uint(kHybridMaxLayers)) return;

    // Compute layer kind in-kernel (mirrors Qwen3.5's every-4th convention).
    uint is_full = ((layer % 4u) == 3u) ? 1u : 0u;

    // Smoke-test pass-through: copy the first 1024 hidden elements from
    // hidden_in to hidden_out.  This makes the kernel runnable end-to-end
    // without the host's pre/post processing.
    if (tid < 128u) {
        // 128 threads copy 1024 elements (8/thread) from hidden_in to hidden_out.
        for (int i = 0; i < 8; ++i) {
            uint e = tid + i * 128u;
            if (e < uint(qwen::kHiddenSize)) {
                hidden_out[b * qwen::kHiddenSize + e] =
                    hidden_in[b * qwen::kHiddenSize + e];
            }
        }
    }

    // Emit the layer kind to the host.  This is a 1-shot write.
    if (tid == 0 && b == 0u) {
        layer_kind_out[layer] = is_full;
    }
}
