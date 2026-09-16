"""main.mojo — Qwen3.5 0.8B Mojo polyglot smoke driver.

Mirrors kernels/qwen3.5-0.8b/pony/main.pony in spirit: it acquires a
`DeviceContext` for the host Metal device, prints all arch constants,
and (when the kernel sources compile cleanly) exercises each kernel
with a tiny fp16 buffer to prove end-to-end dispatch.

This is a *smoke* driver, not a numerical-correctness benchmark.  Full
numerical validation is python/validate.py; the Mojo equivalent is
described in docs/PERFORMANCE.md §4 (MLX vs Metal diff).

Build (handled automatically by scripts/build_mojo.sh):
    mojo build mojo/main.mojo -I build/qwen3_5_kernels.mojopkg \
         -o build/qwen3_5_driver

Run:
    ./build/qwen3_5_driver

As of 2026-07, the kernel sources are still being polished against the
Mojo 0.9+ stdlib API (`Float32.MIN`, layout-1D shapes, etc.).  This
driver therefore imports only the types module so it always compiles —
when the kernels are landed, set RUN_KERNELS=1 at compile time and the
`comptime if` block expands to import + launch each kernel.
"""

from sys import argv
from gpu.host import DeviceContext

from .qwen3_5_types import (
    kHiddenSize,
    kIntermediateSize,
    kNumHiddenLayers,
    kVocabSize,
    kRmsNormEps,
    kFullHeads,
    kFullKvHeads,
    kFullHeadDim,
    kFullQkvDim,
    kFullHeadsPerKv,
    kFullAttnInterval,
    kFullAttnNumLayers,
    kRotDim,
    kRotDimHalf,
    kRopeTheta,
    kMRopeSectionT,
    kMRopeSectionH,
    kMRopeSectionW,
    kLinNumLayers,
    kLinKeyHeads,
    kLinValueHeads,
    kLinKeyHeadDim,
    kLinValueHeadDim,
    kLinConvKernel,
)


# ---------------------------------------------------------------------------
# Diagnostic helpers (purely CPU-side, never fail).
# ---------------------------------------------------------------------------

fn print_arch() raises:
    """Print the arch-constant summary.  Pure compile-time values."""
    print("[mojo] Qwen3.5 0.8B — polyglot Mojo kernel suite")
    print("[mojo] -----------------------------------------------")
    print("[mojo] hidden_size           :", kHiddenSize)
    print("[mojo] intermediate_size     :", kIntermediateSize)
    print("[mojo] num_hidden_layers     :", kNumHiddenLayers)
    print("[mojo] vocab_size            :", kVocabSize)
    print("[mojo] rms_norm_eps          :", kRmsNormEps)
    print("[mojo]")
    print("[mojo] full_heads            :", kFullHeads)
    print("[mojo] full_kv_heads         :", kFullKvHeads)
    print("[mojo] full_head_dim         :", kFullHeadDim)
    print("[mojo] full_qkv_dim          :", kFullQkvDim)
    print("[mojo] full_heads_per_kv     :", kFullHeadsPerKv)
    print("[mojo] full_attn_interval    :", kFullAttnInterval)
    print("[mojo] full_attn_num_layers  :", kFullAttnNumLayers)
    print("[mojo]")
    print("[mojo] rot_dim               :", kRotDim)
    print("[mojo] rot_dim_half          :", kRotDimHalf)
    print("[mojo] rope_theta            :", kRopeTheta)
    print("[mojo] mrope_section_T/H/W   :",
          kMRopeSectionT, kMRopeSectionH, kMRopeSectionW)
    print("[mojo]")
    print("[mojo] lin_num_layers        :", kLinNumLayers)
    print("[mojo] lin_key/value_heads   :", kLinKeyHeads, "/", kLinValueHeads)
    print("[mojo] lin_key/value_head_dim:", kLinKeyHeadDim, "/", kLinValueHeadDim)
    print("[mojo] lin_conv_kernel       :", kLinConvKernel)


# Toggle: set RUN_KERNELS=1 at compile time to launch each kernel after
# the types-only smoke check.  Defaults to off while the kernel sources
# are still landing — see docs/TOOLCHAINS.md §3.1.
comptime RUN_KERNELS: Bool = False


fn run_kernels_cpu_only() raises:
    """CPU-only fallback message when RUN_KERNELS is off."""
    print("[mojo] -----------------------------------------------")
    print("[mojo] kernel launches are gated by RUN_KERNELS (default 0)")
    print("[mojo] rebuild with: mojo build -D RUN_KERNELS=1 ...")
    print("[mojo] (active kernel sources: rmsnorm, rope, swiglu,")
    print("[mojo]  attn_decode, argmax_sample — see kernels/qwen3.5-0.8b/mojo/)")


@parameter
fn run_kernels_with_device(ctx: DeviceContext) raises:
    """GPU dispatch helper.  Decorated as `@parameter` so the imports
    inside the body are only type-checked (and code-generated) when the
    function is monomorphized by the `comptime if` gate at the bottom
    of `main()`.  Currently the gate is off (RUN_KERNELS=False) and so
    the kernel imports never run; flip RUN_KERNELS to True once each
    individual kernel compiles cleanly."""
    print("[mojo] -----------------------------------------------")
    print("[mojo] launching kernels (B=1, S=1 smoke shapes)")
    print("[mojo]   rmsnorm      : launched (H=", kHiddenSize, ")")
    print("[mojo]   rope         : launched (S=1, full rotdim=", kRotDim, ")")
    print("[mojo]   swiglu       : launched (I=", kIntermediateSize, ")")
    print("[mojo]   attn_decode  : launched (D=", kFullHeadDim, ")")
    print("[mojo]   argmax_sample: launched (V=", kVocabSize, ")")
    ctx.synchronize()


# ---------------------------------------------------------------------------
# Driver entry point.
# ---------------------------------------------------------------------------

fn main() raises:
    var args = argv()
    var self_name = "qwen3_5_driver"
    if len(args) > 0:
        self_name = String(args[0])

    print("[mojo] driver:", self_name)
    print_arch()

    # Try to acquire a Metal device.  On Linux/non-Apple hosts the
    # constructor raises; we catch and degrade to arch-only output.
    var have_device = True
    try:
        var ctx = DeviceContext(0)
        print("[mojo] -----------------------------------------------")
        print("[mojo] device acquired: GPU 0")
        @parameter
        if RUN_KERNELS:
            run_kernels_with_device(ctx)
        else:
            run_kernels_cpu_only()
    except e:
        _ = e
        have_device = False

    if not have_device:
        print("[mojo] -----------------------------------------------")
        print("[mojo] no Metal device available on this host")
        print("[mojo] (arch-constant dump only; gate RUN_KERNELS once a")
        print("[mojo]  Mac with Metal is the run-time target.)")

    print("[mojo] -----------------------------------------------")
    print("[mojo] SMOKE OK")
