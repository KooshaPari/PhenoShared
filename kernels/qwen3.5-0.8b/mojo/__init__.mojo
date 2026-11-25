"""Mojo polyglot bindings for Qwen3.5 0.8B kernels.

These files mirror the corresponding files in ../metal/ so the host can
dispatch either Metal or Mojo transparently (same buffer order, same dtype,
same kernel semantics).

Public API (importable as `from qwen3_5_kernels import ...`):

    qwen3_5_types.mojo  — arch constants, SIMD helpers, layout aliases,
                           shared warp reductions (`warp_reduce_sum`,
                           `warp_reduce_argmax`).
    rmsnorm.mojo        — RMSNorm (per-row reduction).
    rope.mojo           — M-RoPE (partial rotary, sections T/H/W).
    swiglu.mojo         — SwiGLU activation (silu(gate) * up).
    attn_decode.mojo    — Full-attention decode (S=1) with KV paging.
    argmax_sample.mojo  — Fused argmax + Gumbel sampling.

Driver (built to `build/qwen3_5_driver` by scripts/build_mojo.sh):

    main.mojo           — smoke driver: prints arch constants and
                          (gated by RUN_KERNELS=1) launches each kernel.

Buffer-arg contract
-------------------

Each kernel module documents its own argument order in its top-level
docstring (every kernel mirrors the corresponding metal signature in
../metal/).  A common pattern across the suite:

    [0..k-1]  input / output buffers (fp16 / fp32 / int32)
    [k..n-1]  scalar args  (UInt dims, Float32 scales, etc.)

There is no single "in1/out/w/aux" convention; each kernel takes the
minimum set of buffers needed for its semantics.  In particular, RoPE
takes Q and K as separate buffers with separate output buffers (Q_out,
K_out) so a follow-up layer can read the rotated activations without
aliasing the inputs.

Activations / weights: DType.float16.
Accumulation: DType.float32.

Numerical helpers (in qwen3_5_types.mojo) preserve the fast-math
patterns from metal/types.metal — they are designed to map to MSL's
`metal::fast::*` intrinsics on Apple Silicon.  Numerical results are
expected to match the Metal port bit-for-bit for inputs that fit in
fp16's dynamic range.
"""
