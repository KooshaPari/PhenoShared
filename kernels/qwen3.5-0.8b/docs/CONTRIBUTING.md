# Contributing to `kernels/qwen3.5-0.8b/`

This document is the **kernel-side** contributor guide.  It covers:

1. How to add a new kernel
2. How to validate it
3. How to extend the suite to other Qwen3.5 sizes (1.7B / 4B / 8B)
4. The kernel-suite conventions you must follow

For top-level repo conventions (release process, secret handling, etc.),
see the parent `AGENTS.md` and `CONTRIBUTING.md` in the repo root.

---

## 1. Adding a new kernel

The kernel suite is single-source-of-truth driven.  Every kernel:

1. Has a **declaration** in `arch.yaml` (only if it needs new shape
   constants).
2. Has an **MLX reference** in `python/reference.py` (the golden path).
3. Has a **Metal implementation** in `metal/*.metal` (or a binding in
   `cpp/`, `rust/`, `zig/`, or `mojo/`).
4. Is **wired into the validator** in `python/validate.py`.
5. Is **wired into the bench** in `python/bench.py`.

### 1.1 The five-step recipe

#### Step 1 — Identify whether you need new constants

Read `arch.yaml` first.  If your kernel needs a new shape constant (a
new head count, a new dimension, a new schedule), add it under the
appropriate top-level section.  Do **not** add a brand-new top-level
section unless you've first checked with the maintainer — most
constants slot into the existing `model`, `full_attention`,
`linear_attention`, or `mtp` blocks.

After editing `arch.yaml`, regenerate the cross-language mirrors:

```bash
cd kernels/qwen3.5-0.8b
python3 python/codegen.py
# → writes iso/qwen3_5.h, iso/arch.rs, iso/qwen3_5.zig, iso/qwen3_5.mojo,
#   iso/qwen3_5.nim, codegen/arch.json
```

The generated `iso/*` files are the **drift targets**; the
hand-written `include/qwen3_5.h`, `rust/src/arch.rs`, and
`zig/engine.zig` are the canonical headers.  When you regenerate,
the diff between `iso/qwen3_5.h` and `include/qwen3_5.h` should be
either zero (if the canonical file was up to date) or a clean
additive change (if you hand-bumped the canonical file at the same
time as `arch.yaml`).

Verify drift in CI:

```bash
python3 python/codegen.py --check          # iso/ matches a fresh emit
python3 python/codegen.py --check-canonical # canonical/ matches a fresh emit
```

#### Step 2 — Implement the reference in `python/reference.py`

The reference is the gold standard.  It must:

* Be **pure-MLX** (Apple's `mlx.core` / `mlx.nn`).
* Use the **same dtype conventions** as the rest of the suite: bf16 for
  activations and weights, fp32 for accumulators and the linear-attn
  recurrent state.
* Be **self-contained** — accept its inputs as plain `mx.array`s, return
  a single `mx.array` (or a tuple where the first element is the
  "primary" output and the rest are side-channels like the new state).
* Have a `ref_*` alias matching the kernel name if the validate harness
  uses a different name (see existing aliases at
  `python/reference.py:773-777`).

A minimal template:

```python
def ref_my_new_kernel(x: mx.array, w: mx.array, eps: float = ARCH.rms_norm_eps) -> mx.array:
    """Pure-MLX <description> matching my_new_kernel.metal.

    x:  [B, D] bf16
    w:  [D]  bf16
    """
    fp = x.astype(mx.float32)
    # ... math ...
    return out.astype(x.dtype)
```

Add a small smoke test inside `run_self_test()` at the bottom of the
file.  **The full reference must run in < 5 s on a M-series Mac** — if
yours is slower, you probably have a Python loop where a vmap would
suffice; see the linear-attention step (`python/reference.py:278`) for
an example where a loop is *intentionally* kept (the per-token
recurrent update is inherently sequential).

#### Step 3 — Implement the Metal kernel

Hand-tune the Metal MSL in `metal/<op>.metal`.  The conventions:

* Use the constants from `include/qwen3_5.h` directly — **never**
  hardcode shape values; they will silently drift if `arch.yaml`
  changes.
* Accumulate in fp32, store in bf16.
* Each kernel must be **multi-batch safe** (B is a runtime arg).
* For decode-path kernels (S=1), optimize for **latency**; for
  prefill-path kernels (S>1), optimize for **throughput**.
* The first argument of every kernel is `device const uint* args` —
  this is a small struct (≤ 64 B) carrying dynamic dims the constants
  header doesn't (e.g. current `seq_len`, `kv_cache_offset`).

A minimal kernel skeleton (see `metal/rmsnorm.metal` for a complete
example):

```metal
#include <metal_stdlib>
#include "qwen3_5.h"
using namespace metal;

kernel void my_new_kernel(
    const device half*  x       [[buffer(0)]],
    const device half*  w       [[buffer(1)]],
    device       half*  out     [[buffer(2)]],
    constant     uint&  D       [[buffer(3)]],
    uint                  tgid   [[threadgroup_position_in_grid]]
) {
    // ... hand-tuned math ...
}
```

Bind it in the engine's dispatch table.  The exact binding site
depends on the language (Rust/Zig/C++), but they all look up the
kernel by string name — pick a unique `<op>_<variant>` name.

#### Step 4 — Wire into `python/validate.py`

Open `python/validate.py:521` and find the per-kernel closure list.
Add a new closure in the same style:

```python
def _my_new_kernel():
    return ref_my_new_kernel(inputs["mnk_x"], inputs["mnk_w"])

cases = [
    # ... existing entries ...
    ("my_new_kernel", _my_new_kernel, fp16_tol),
]
```

Then add the input tensors to `gen_inputs()` at
`python/validate.py:365`.  Pick the smallest representative shape
that still exercises the kernel — the validator runs each kernel 25
times, so 1× bigger inputs = 1× more test time per run.

When the Metal ABI is wired up (see
`python/validate.py:560-565` for the hook point), the per-kernel
`metal_runners` dict is what connects the Python name to the C ABI
function.  Until then, the harness degrades to MLX-vs-MLX
self-consistency and still PASSes.

#### Step 5 — Wire into `python/bench.py`

Add a row to the bench sweep that measures your kernel at the
**decode shape** (S=1) and at **three prefill shapes** (S=128,
S=512, S=1024).  The current bench sweeps
`python/bench.py:1` — extend the `seq_lens` list and add a per-kernel
dispatch entry to the dispatch table in `python/bench.py`
(`KERNEL_DISPATCH` dict; see existing rows for the shape of the entry).

### 1.2 Acceptance gates

A new kernel is "shippable" when:

* `python3 python/validate.py --quick` reports PASS for the new
  kernel name.
* `python3 python/codegen.py --check` and `--check-canonical` both
  pass.
* `python3 -m pytest tests/ -v` is green (25 tests, < 2 s).
* `python3 python/bench.py --quick` produces a fresh
  `bench/results/qwen3.5-0.8b-ref.json` with your kernel in the
  throughput table.

If you only changed `arch.yaml` (and not the kernel suite), the gates
are:

* `python3 python/codegen.py` regenerates `iso/*`.
* `python3 python/codegen.py --check-canonical` reports any drift
  between `iso/*` and the canonical hand-written files.

---

## 2. Validating your work

The three validation harnesses in this directory are independent.  Run
them in this order for a clean check:

```bash
# 1. Pure-Python / in-process tests (no MLX, no Metal).
#    Asserts codegen is idempotent and cross-language round-trips.
python3 -m pytest tests/ -v            # 25 tests, ~1.4 s

# 2. Per-kernel numerical harness (MLX gold standard).
#    Reports PASS/FAIL per kernel with timing + max-abs diff.
cd kernels/qwen3.5-0.8b
python3 python/validate.py --quick     # ~30 s, 11 kernels

# 3. End-to-end throughput benchmark.
#    Writes bench/results/qwen3.5-0.8b-ref.json.
python3 python/bench.py --quick        # ~2 min, sweeps seq_lens
```

If you only want to check a single kernel during development:

```bash
# Run just one kernel at a time in the validator (current impl does
# all 10 in one pass; for a single kernel, edit the `cases` list in
# python/validate.py:570 to keep just the one you care about).
```

The validator's JSON report lands in
`kernels/qwen3.5-0.8b/bench/results/validate_latest.json`.  The
benchmark's JSON lands in
`kernels/qwen3.5-0.8b/bench/results/qwen3.5-0.8b-ref.json`.  Both
files are gitignored.

---

## 3. Extending to other Qwen3.5 sizes (1.7B / 4B / 8B)

The kernel suite is **per-size** — there is a `kernels/qwen3.5-0.8b/`
directory and a separate `kernels/qwen3.5-1.7b/` (etc.) would live
alongside it.  We do not have a single multi-size suite because the
delta-rules, head counts, and conv-kernel dimensions all differ
between sizes, and consolidating them adds more abstraction than it
saves.

To create a new size:

1. **Copy the directory.**

   ```bash
   cp -r kernels/qwen3.5-0.8b/ kernels/qwen3.5-1.7b/
   cd kernels/qwen3.5-1.7b
   ```

2. **Update `arch.yaml`.**  The constants that differ between sizes
   are (and only these — leave the rest alone):

   ```yaml
   model:
     vocab_size: 152064             # 1.7B uses 152064
     hidden_size: 2048              # 1.7B doubles hidden
     intermediate_size: 6144        # 1.7B intermediate scales
     num_hidden_layers: 28          # 1.7B has 28 layers
     # ... etc.
     mrope:
       section: [16, 24, 24]        # 1.7B uses different M-RoPE split
   full_attention:
     num_attention_heads: 16
     num_key_value_heads: 8         # 1.7B may have 16/8 or 8/4
     head_dim: 128                  # 1.7B has smaller head_dim
     full_attention_interval: 4
   linear_attention:                # 1.7B may use different K/V head counts
     num_key_heads: 16
     num_value_heads: 32
     key_head_dim: 128
     value_head_dim: 128
   ```

   The exact Qwen3.5-1.7B values are published in the
   `Qwen/Qwen3.5-1.7B/config.json` on Hugging Face.  **Do not guess** —
   read the source.

3. **Regenerate everything.**

   ```bash
   python3 python/codegen.py                # iso/* (drift targets)
   python3 python/codegen.py --canonical    # overwrites hand-written
                                          # include/qwen3_5.h, etc.
   ```

4. **Update the MLX constants in `python/reference.py`.**  The
   `QwenArch` dataclass at `python/reference.py:61` has a hand-written
   default that must match `arch.yaml`.  Either keep the dataclass
   defaults in sync manually, or refactor to read `arch.yaml` once at
   import (a future improvement).

5. **Run the validation suite.**  All three validators must PASS
   before the new size is shippable.

   ```bash
   python3 -m pytest tests/ -v
   python3 python/validate.py --quick
   python3 python/bench.py --quick
   ```

6. **Check the C header canonicalization.**  If the new size is
   intended for **release**, regenerate the canonical headers with
   `python3 python/codegen.py --canonical` and commit them.  Otherwise
   the canonical files drift from `arch.yaml` and CI will fail.

### 3.1 What *not* to do

* Do **not** add `--size {0.8b,1.7b,4b,8b}` flags to the existing
  `python/reference.py`.  The suites are intentionally separate so
  per-kernel perf and correctness can be optimized in isolation.
* Do **not** parameterize the validate/bench harnesses to load a
  different `arch.yaml` at runtime.  If you want a different size,
  copy the directory.
* Do **not** add a new top-level `arch.yaml` section without
  coordinating with the maintainer — most constants belong in one of
  the existing blocks.

---

## 4. Conventions

### 4.1 Naming

* Files: `camelCase` for Python, `snake_case` for everything else.
* C macros: `QWEN3_5_<DOMAIN>_<FIELD>` — e.g. `QWEN3_5_HIDDEN_SIZE`.
* Rust constants: `UpperCamelCase` inside the `arch` module — e.g.
  `arch::HIDDEN_SIZE`.
* Zig constants: `UpperCamelCase` — e.g. `HiddenSize`.
* Mojo aliases: `UpperCamelCase` — e.g. `HiddenSize`.

### 4.2 Dtype discipline

* **bf16**: all weights, all activations, all inputs/outputs of
  per-kernel Metal calls.
* **fp32**: all accumulators, all matmul reductions, the linear-attn
  recurrent state, the M-RoPE trig intermediate.
* **fp32 → bf16** at the very end of each kernel (one cast).
* **Never** accumulate in bf16; the rounding error compounds across 24
  layers and breaks the validator.

### 4.3 What belongs in `arch.yaml`

Shape constants and per-size tunables.  Does **not** belong:

* Code-style settings (those go in `.clang-format` / `rustfmt.toml`).
* Build flags (those go in `Justfile` / `CMakeLists.txt`).
* Kernel-strategy tunables that aren't shape-related (those go in
  `kernel_strategy` inside `arch.yaml` — see `arch.yaml:77-96` for
  examples).

### 4.4 Commit hygiene

* One logical change per commit.  If your PR touches `arch.yaml`,
  every emitted header in `iso/*` will also change — that's expected
  and **not** a sign of bloat.
* The CI script `python3 python/codegen.py --check-canonical` must
  pass on every PR.  If it fails, either regenerate the canonical
  files (`python3 python/codegen.py --canonical`) or fix the drift
  in your kernel source.
* Bench JSON files (`bench/results/qwen3.5-0.8b-ref.json`,
  `validate_latest.json`) are gitignored.  Do not commit them.
