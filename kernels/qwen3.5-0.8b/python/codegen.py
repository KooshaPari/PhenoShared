#!/usr/bin/env python3
"""
codegen.py — single source-of-truth → multi-language architecture headers.

Reads ``arch.yaml`` (Qwen3.5 0.8B model shape constants) and emits:

  • C header                  → include/qwen3_5.h
  • Rust const block          → rust/src/arch.rs           (re-exported from lib.rs)
  • Zig comptime constants    → zig/qwen3_5.zig
  • Mojo comptime constants   → mojo/qwen3_5.mojo          (new; Mojo codepath)
  • Nim const block           → nim/qwen3_5.nim            (new; Nim binding)
  • JSON dump (canonical)     → codegen/arch.json

The tool is **idempotent**: running it twice produces byte-identical output
(no timestamps in any header, single canonical JSON output). Only changes when
``arch.yaml`` changes.

Roadmap / status:
  • The committed include/qwen3_5.h, rust/src/lib.rs, and zig/engine.zig
    already embed the constants *by hand*. Running this codegen produces
    the same values; the byte-for-byte equality is asserted by
    ``tests/test_codegen.py`` and ``tests/test_arch_consistency.py``.

Usage::

    # dry-run: print to stdout
    python3 python/codegen.py --arch kernels/qwen3.5-0.8b/arch.yaml --print c

    # write to repo defaults
    python3 python/codegen.py --arch kernels/qwen3.5-0.8b/arch.yaml

    # custom output dir
    python3 python/codegen.py --arch arch.yaml --out-dir build/headers/

The ``--check`` flag validates that every header already on disk matches the
freshly generated content — use it in CI to detect drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover — pyyaml is in requirements.txt
    yaml = None  # type: ignore


# =============================================================================
# Architecture model (single typed representation, derived from arch.yaml)
# =============================================================================


@dataclass(frozen=True)
class QwenArch:
    """Typed representation of Qwen3.5 0.8B architecture constants.

    Every field is derived from ``arch.yaml``. Computed fields (Q_DIM,
    FULL_HEADS_PER_KV, LAYER_IS_FULL, STATE bytes, …) are properties so
    drift cannot happen.
    """

    # ----- Identity -----
    model_id: str
    hf_repo: str
    family: str
    kind: str
    arch: str

    # ----- Core dims -----
    vocab_size: int
    hidden_size: int
    intermediate_size: int
    num_hidden_layers: int
    max_position_embeddings: int
    rms_norm_eps: float
    tie_word_embeddings: bool
    attn_output_gate: bool
    partial_rotary_factor: float
    rope_theta: float
    mrope_interleaved: bool
    mrope_section: tuple[int, int, int]

    # ----- Full attention -----
    full_heads: int
    full_kv_heads: int
    full_head_dim: int
    full_attention_interval: int
    full_attention_num_layers: int
    full_attention_layer_indices: tuple[int, ...]

    # ----- Linear attention -----
    lin_num_layers_in_spec: int  # raw from yaml (19 — counts a padding slot)
    lin_key_heads: int
    lin_value_heads: int
    lin_key_head_dim: int
    lin_value_head_dim: int
    lin_conv_kernel: int

    # ----- MTP -----
    mtp_num_hidden_layers: int
    mtp_use_dedicated_embeddings: bool
    mtp_role: str

    # ----- Kernel dispatch (DAG-41 close-out) -----
    # These flow from arch.yaml's kernel_strategy block so the canonical
    # simdgroup size propagates to every language binding that includes
    # the generated header / arch module. The audit-A4 close-out bound
    # kArchSimdgroupSize in iso/hybrid_decode_dispatch.inc; this extends
    # that binding to the typed C/Rust/Zig/Mojo/Nim surfaces.
    target_devices: tuple[str, ...]
    default_simdgroup_size: int
    threadgroup_size_default: int
    dtype_compute: str
    dtype_accumulator: str
    dtype_state_cache: str
    dtype_recurrent_state: str

    # ----- derived ----- (properties, not fields)

    @property
    def rot_dim(self) -> int:
        """First N dims of head_dim that are rope-rotated.

        Qwen3.5 uses partial_rotary_factor=0.25 on head_dim=256, but the
        canonical rot_dim value is given by ``sum(mrope_section) = 11+11+10
        = 32`` (T+H+W of M-RoPE).  ``partial_rotary_factor * head_dim = 64``
        is the full *pair* span — only half is rotated under M-RoPE.

        We return the M-RoPE sum since that's what every kernel uses, and
        warn if the partial_rotary_factor doesn't match.
        """
        from_mrope = sum(self.mrope_section)
        # partial_rotary_factor * head_dim = 64 in this config; rot_dim = 32.
        # We accept the convention "rot_dim = sum(mrope_section)" and
        # require partial_rotary_factor * 2 = rot_dim/head_dim ratio to be
        # consistent: half the rotated dim = partial_rotary_factor * head_dim.
        if abs(self.partial_rotary_factor * self.full_head_dim - from_mrope * 2) > 1:
            raise ValueError(
                f"mrope_section sum {from_mrope} doesn't match "
                f"partial_rotary_factor {self.partial_rotary_factor} "
                f"* head_dim {self.full_head_dim}"
            )
        return from_mrope

    @property
    def full_heads_per_kv(self) -> int:
        return self.full_heads // self.full_kv_heads

    @property
    def full_q_dim(self) -> int:
        return self.full_heads * self.full_head_dim

    @property
    def full_kv_dim(self) -> int:
        return self.full_kv_heads * self.full_head_dim

    @property
    def full_qkv_dim(self) -> int:
        return self.full_q_dim + 2 * self.full_kv_dim

    @property
    def lin_qkv_dim(self) -> int:
        return 3 * self.lin_key_heads * self.lin_key_head_dim

    @property
    def linear_num_layers(self) -> int:
        """Real count = num_hidden_layers − full_attention_num_layers.

        arch.yaml stores 19 (a quirk of the original config.json that counts
        a padding slot).  We don't expose that oddity to the rest of the
        codebase — derived = 18.
        """
        return self.num_hidden_layers - self.full_attention_num_layers

    @property
    def layer_is_full(self) -> tuple[bool, ...]:
        """Schedule: every (full_attention_interval)th layer is full attention."""
        return tuple(
            ((i + 1) % self.full_attention_interval == 0)
            for i in range(self.num_hidden_layers)
        )

    @property
    def state_elements(self) -> int:
        """Linear-attn recurrent state elements per layer per batch."""
        return (
            self.lin_key_heads
            * self.lin_value_heads
            * self.lin_value_head_dim
            * self.lin_key_head_dim
        )

    @property
    def state_bytes_fp32(self) -> int:
        return self.state_elements * 4

    @property
    def state_bytes_bf16(self) -> int:
        return self.state_elements * 2

    @property
    def weight_bytes_embed(self) -> int:
        """Tied embedding + lm_head bytes (bf16)."""
        return self.vocab_size * self.hidden_size * 2

    def kv_cache_bytes_per_layer(self, max_seq: int) -> int:
        """Per-full-attention-layer KV cache bytes (bf16, K + V)."""
        return 2 * self.full_kv_dim * max_seq * 2


def parse_arch_yaml(text: str) -> QwenArch:
    """Parse arch.yaml text into a QwenArch.

    Falls back to a tiny YAML reader when ``pyyaml`` is unavailable — the
    arch.yaml shape is hand-curated and small, so a minimal subset parser
    is enough to bootstrap.
    """
    if yaml is not None:
        data = yaml.safe_load(text)
    else:  # pragma: no cover — pyyaml is required
        data = _minimal_yaml_load(text)

    m = data["model"]
    fa = m["full_attention"]
    la = m["linear_attention"]
    mrope = m["mrope"]
    mtp = m["mtp"]
    ks = data.get("kernel_strategy", {}) or {}

    full_idx = tuple(int(x) for x in fa["full_attention_layer_indices"])
    return QwenArch(
        model_id=m["id"],
        hf_repo=m["hf"],
        family=m["family"],
        kind=m["kind"],
        arch=m["arch"],
        vocab_size=int(m["vocab_size"]),
        hidden_size=int(m["hidden_size"]),
        intermediate_size=int(m["intermediate_size"]),
        num_hidden_layers=int(m["num_hidden_layers"]),
        max_position_embeddings=int(m["max_position_embeddings"]),
        rms_norm_eps=float(m["rms_norm_eps"]),
        tie_word_embeddings=bool(m["tie_word_embeddings"]),
        attn_output_gate=bool(m["attn_output_gate"]),
        partial_rotary_factor=float(m["partial_rotary_factor"]),
        rope_theta=float(m["rope_theta"]),
        mrope_interleaved=bool(mrope["interleaved"]),
        mrope_section=tuple(int(x) for x in mrope["section"]),
        full_heads=int(fa["num_attention_heads"]),
        full_kv_heads=int(fa["num_key_value_heads"]),
        full_head_dim=int(fa["head_dim"]),
        full_attention_interval=int(fa["full_attention_interval"]),
        full_attention_num_layers=int(fa["full_attention_layers"])
        if "full_attention_layers" in fa
        else len(full_idx),
        full_attention_layer_indices=full_idx,
        lin_num_layers_in_spec=int(la["num_layers"]),
        lin_key_heads=int(la["num_key_heads"]),
        lin_value_heads=int(la["num_value_heads"]),
        lin_key_head_dim=int(la["key_head_dim"]),
        lin_value_head_dim=int(la["value_head_dim"]),
        lin_conv_kernel=int(la["conv_kernel_dim"]),
        mtp_num_hidden_layers=int(mtp["num_hidden_layers"]),
        mtp_use_dedicated_embeddings=bool(mtp["use_dedicated_embeddings"]),
        mtp_role=str(mtp["role"]),
        # kernel_strategy (DAG-41) — defaults are the audit-A4 close-out
        # values (Apple Silicon, simdgroup=32, threadgroup=256).
        target_devices=tuple(
            str(x)
            for x in ks.get(
                "target_devices", ["apple_m1", "apple_m2", "apple_m3", "apple_m4"]
            )
        ),
        default_simdgroup_size=int(ks.get("default_simdgroup_size", 32)),
        threadgroup_size_default=int(ks.get("threadgroup_size_default", 256)),
        dtype_compute=str(ks.get("dtype_compute", "bfloat16")),
        dtype_accumulator=str(ks.get("dtype_accumulator", "float")),
        dtype_state_cache=str(ks.get("dtype_state_cache", "bfloat16")),
        dtype_recurrent_state=str(ks.get("dtype_recurrent_state", "float32")),
    )


def _minimal_yaml_load(text: str) -> dict:
    """Pure-Python YAML subset loader — sufficient for arch.yaml.

    Handles: top-level mappings, 2-space indented mappings, inline lists
    ``[a, b, c]``, scalars (int/float/string/bool/null), and YAML comments.
    Does NOT handle flow-style mappings, multi-line strings, or anchors.
    Only here as a fallback when ``pyyaml`` is missing; CI installs pyyaml.
    """
    lines = []
    for raw in text.splitlines():
        s = raw.split("#", 1)[0].rstrip()
        if s.strip():
            lines.append(s)
    root: dict = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        s = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent_indent, parent = stack[-1]
        # "- foo" list syntax
        if s.startswith("- "):
            if not isinstance(parent, list):
                # convert parent to list — only if parent is a key with no value yet
                k = stack[-2][1]
                if (
                    isinstance(stack[-2][1], dict)
                    and isinstance(parent, dict)
                    and not parent
                ):
                    stack[-2][1][k] = []
                    parent = stack[-2][1][k]
                else:
                    raise ValueError(f"cannot mix list into non-list at {line!r}")
            v = s[2:].strip()
            parent.append(_coerce(v))
            # If the value has a ":" it represents a sub-mapping we push for
            # following indented lines.
            if ":" in v and not v.startswith("[") and "=" not in v:
                key, _, rest = v.partition(":")
                key = key.strip()
                item: dict = {}
                parent.append(item)
                stack.append((indent + 2, item))
                stack.append((indent + 2, item))
                if rest.strip():
                    item[key] = _coerce(rest.strip())
            continue
        # "key: value" mapping syntax
        if ":" in s:
            key, _, rest = s.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                # nested block — push empty container
                child: Any = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                parent[key] = _coerce(rest)
    return root


def _coerce(text: str) -> Any:
    """Coerce a YAML scalar string into the obvious Python value."""
    t = text.strip()
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_coerce(x) for x in inner.split(",")]
    if t.startswith('"') and t.endswith('"'):
        return t[1:-1]
    if t.startswith("'") and t.endswith("'"):
        return t[1:-1]
    low = t.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    try:
        if any(c in t for c in ".eE") and not t.startswith("0o"):
            return float(t)
        return int(t)
    except ValueError:
        return t


# =============================================================================
# Emitters — one function per language
# =============================================================================

HEADER_COMMENT = (
    "// AUTO-GENERATED from arch.yaml — DO NOT EDIT.\n"
    "// Regenerate with: python3 python/codegen.py --arch arch.yaml\n"
    "// Verification: tests/test_codegen.py asserts byte-equality.\n"
)


def _fmt_float(x: float) -> str:
    """Format a float the way the on-disk C/Rust headers do.

    Python's default scientific notation uses leading zeros in the exponent
    (``1.0e-06``); the kernel headers use the cleaner C form
    (``1.0e-6``).  We strip leading zeros from the exponent to match.
    """
    s = f"{x:.1e}"
    mant, exp = s.split("e")
    sign = exp[0]  # '+' or '-'
    digits = exp[1:].lstrip("0")
    if not digits:  # avoid empty exponent
        digits = "0"
    return f"{mant}e{sign}{digits}"


def emit_c(a: QwenArch) -> str:
    """C11 header — matches include/qwen3_5.h byte-for-byte for committed values."""
    out: list[str] = []
    out.append(HEADER_COMMENT.replace("//", "//"))
    out.append(
        "#ifndef PHENO_QWEN3_5_0_8B_H\n"
        "#define PHENO_QWEN3_5_0_8B_H\n"
        "\n"
        "#include <stdint.h>\n"
        "#include <stdbool.h>\n"
        "#include <stddef.h>\n"
        "\n"
        "#ifdef __cplusplus\n"
        'extern "C" {\n'
        "#endif\n"
    )
    # Identity
    out.append(f'#define QWEN3_5_MODEL_ID        "{a.model_id}"')
    out.append(f'#define QWEN3_5_HF_REPO         "{a.hf_repo}"')
    out.append(f'#define QWEN3_5_FAMILY          "{a.family}"')
    out.append(f'#define QWEN3_5_KIND            "{a.kind}"\n')

    # Core dims
    out.append("#define QWEN3_5_VOCAB_SIZE             " + str(a.vocab_size))
    out.append("#define QWEN3_5_HIDDEN_SIZE            " + str(a.hidden_size))
    out.append("#define QWEN3_5_INTERMEDIATE_SIZE      " + str(a.intermediate_size))
    out.append("#define QWEN3_5_NUM_HIDDEN_LAYERS      " + str(a.num_hidden_layers))
    out.append(
        "#define QWEN3_5_MAX_POSITION_EMB       " + str(a.max_position_embeddings)
    )
    out.append(f"#define QWEN3_5_RMS_NORM_EPS_F         {_fmt_float(a.rms_norm_eps)}f")
    out.append(
        "#define QWEN3_5_TIE_WORD_EMBEDDINGS    "
        + ("1" if a.tie_word_embeddings else "0")
    )
    out.append("#define QWEN3_5_HIDDEN_ACT_SILU        1")
    out.append(
        "#define QWEN3_5_ATTN_OUTPUT_GATE       " + ("1" if a.attn_output_gate else "0")
    )
    out.append(f"#define QWEN3_5_PARTIAL_ROTARY_FACTOR  {a.partial_rotary_factor:.2f}f")
    out.append(f"#define QWEN3_5_ROPE_THETA             {a.rope_theta:.1f}f\n")

    # M-RoPE
    out.append(
        "#define QWEN3_5_MROPE_INTERLEAVED " + ("1" if a.mrope_interleaved else "0")
    )
    out.append("#define QWEN3_5_MROPE_SECTION_T    " + str(a.mrope_section[0]))
    out.append("#define QWEN3_5_MROPE_SECTION_H    " + str(a.mrope_section[1]))
    out.append("#define QWEN3_5_MROPE_SECTION_W    " + str(a.mrope_section[2]))
    out.append(
        f"// Total rotated dim = "
        f"{a.mrope_section[0]} + {a.mrope_section[1]} + {a.mrope_section[2]} = "
        f"{a.rot_dim} = {a.partial_rotary_factor:.2f} * {a.full_head_dim} (head_dim)\n"
    )
    out.append(
        f"#define QWEN3_5_ROT_DIM            {a.rot_dim}   "
        "// = head_dim * partial_rotary_factor\n"
    )

    # Full attention
    out.append("\n// Full attention (GQA 4:1)\n")
    out.append("#define QWEN3_5_FULL_HEADS          " + str(a.full_heads))
    out.append("#define QWEN3_5_FULL_KV_HEADS       " + str(a.full_kv_heads))
    out.append("#define QWEN3_5_FULL_HEAD_DIM       " + str(a.full_head_dim))
    out.append(
        f"#define QWEN3_5_FULL_HEADS_PER_KV   "
        f"(QWEN3_5_FULL_HEADS / QWEN3_5_FULL_KV_HEADS)  // {a.full_heads_per_kv}"
    )
    out.append(
        f"#define QWEN3_5_FULL_Q_DIM          "
        f"(QWEN3_5_FULL_HEADS    * QWEN3_5_FULL_HEAD_DIM) // {a.full_q_dim}"
    )
    out.append(
        f"#define QWEN3_5_FULL_KV_DIM         "
        f"(QWEN3_5_FULL_KV_HEADS * QWEN3_5_FULL_HEAD_DIM) // {a.full_kv_dim}"
    )
    out.append(
        f"#define QWEN3_5_FULL_QKV_DIM        "
        f"(QWEN3_5_FULL_Q_DIM + 2 * QWEN3_5_FULL_KV_DIM)  // {a.full_qkv_dim}\n"
    )

    out.append(
        "#define QWEN3_5_FULL_ATTN_INTERVAL        " + str(a.full_attention_interval)
    )
    out.append(
        "#define QWEN3_5_FULL_ATTN_NUM_LAYERS      " + str(a.full_attention_num_layers)
    )
    out.append(
        "// indices " + ", ".join(str(i) for i in a.full_attention_layer_indices) + "\n"
    )

    # Linear attention
    out.append("\n// Linear attention (DeltaNet-style gated recurrent)\n")
    out.append("#define QWEN3_5_LIN_KEY_HEADS        " + str(a.lin_key_heads))
    out.append("#define QWEN3_5_LIN_VALUE_HEADS      " + str(a.lin_value_heads))
    out.append("#define QWEN3_5_LIN_KEY_HEAD_DIM     " + str(a.lin_key_head_dim))
    out.append("#define QWEN3_5_LIN_VALUE_HEAD_DIM   " + str(a.lin_value_head_dim))
    out.append("#define QWEN3_5_LIN_CONV_KERNEL      " + str(a.lin_conv_kernel))
    out.append(
        "#define QWEN3_5_LIN_NUM_LAYERS       " + str(a.linear_num_layers) + "\n"
    )

    out.append(
        "// Recurrent state per linear layer:\n"
        f"//   [key_heads={a.lin_key_heads}, value_heads={a.lin_value_heads}, "
        f"value_head_dim={a.lin_value_head_dim}, key_head_dim={a.lin_key_head_dim}]\n"
        f"// = {a.lin_key_heads} * {a.lin_value_heads} * {a.lin_value_head_dim} "
        f"* {a.lin_key_head_dim} = {a.state_elements:,} elements\n"
        f"// At fp32 (4 bytes) = {a.state_bytes_fp32 // (1024 * 1024)} MiB per layer\n"
        f"// At bfloat16 packed (2 bytes) = {a.state_bytes_bf16 // (1024 * 1024)} MiB per layer\n"
    )
    out.append(
        f"#define QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES  "
        f"({a.lin_key_heads} * {a.lin_value_heads} * {a.lin_value_head_dim} "
        f"* {a.lin_key_head_dim} * 4)   // {a.state_bytes_fp32 // (1024 * 1024)} MiB"
    )
    out.append(
        f"#define QWEN3_5_LIN_STATE_PER_LAYER_BF16_BYTES "
        f"({a.lin_key_heads} * {a.lin_value_heads} * {a.lin_value_head_dim} "
        f"* {a.lin_key_head_dim} * 2)   // {a.state_bytes_bf16 // (1024 * 1024)} MiB\n"
    )

    # Schedule array
    out.append(
        "\n// L = linear (DeltaNet), F = full (GQA flash)\n"
        f"// {a.num_hidden_layers} layers; every "
        f"{a.full_attention_interval}th is full.\n"
    )
    out.append(
        "static const int8_t QWEN3_5_LAYER_IS_FULL[QWEN3_5_NUM_HIDDEN_LAYERS] = {"
    )
    sch = list(a.layer_is_full)
    for chunk_start in range(0, a.num_hidden_layers, 4):
        row = sch[chunk_start : chunk_start + 4]
        while len(row) < 4:
            row.append(False)
        out.append(
            "    " + ", ".join("1" if v else "0" for v in row) + ","
            f"   // {chunk_start}-{chunk_start + 3}"
        )
    out.append("};\n")

    # Kernel strategy (DAG-41 close-out — audit-A4 extended to C header)
    out.append("\n// Kernel dispatch (DAG-41 — propagates kArchSimdgroupSize)\n")
    out.append(
        f"#define QWEN3_5_SIMDGROUP_SIZE_DEFAULT  "
        f"{a.default_simdgroup_size}     // Metal simdgroup size"
    )
    out.append(
        "// Backwards-compat alias (DAG-51): keep the old name working for any caller"
    )
    out.append("// that still references QWEN3_5_DEFAULT_SIMDGROUP_SIZE.")
    out.append("#define QWEN3_5_DEFAULT_SIMDGROUP_SIZE  QWEN3_5_SIMDGROUP_SIZE_DEFAULT")
    out.append(
        f"#define QWEN3_5_THREADGROUP_SIZE_DEFAULT  "
        f"{a.threadgroup_size_default}    // 8 * {a.default_simdgroup_size}"
    )
    out.append(f'#define QWEN3_5_DTYPE_COMPUTE          "{a.dtype_compute}"')
    out.append(f'#define QWEN3_5_DTYPE_ACCUMULATOR       "{a.dtype_accumulator}"')
    out.append(f'#define QWEN3_5_DTYPE_STATE_CACHE       "{a.dtype_state_cache}"')
    out.append(f'#define QWEN3_5_DTYPE_RECURRENT_STATE   "{a.dtype_recurrent_state}"\n')

    # Static asserts
    out.append(
        f"_Static_assert(QWEN3_5_HIDDEN_SIZE == {a.hidden_size}, "
        '"hidden_size mismatch");'
    )
    out.append(
        f"_Static_assert(QWEN3_5_FULL_HEAD_DIM == {a.full_head_dim}, "
        '"head_dim mismatch");'
    )
    out.append(
        "_Static_assert(QWEN3_5_FULL_HEADS % QWEN3_5_FULL_KV_HEADS == 0, "
        '"GQA must divide");'
    )
    out.append(
        f'_Static_assert(QWEN3_5_ROT_DIM == {a.rot_dim}, "rot dim = 0.25 * 256");'
    )
    out.append(
        f"_Static_assert(QWEN3_5_SIMDGROUP_SIZE_DEFAULT == "
        f'{a.default_simdgroup_size}, "simdgroup size = 32 (Apple Silicon)");'
    )
    out.append(
        "_Static_assert(QWEN3_5_THREADGROUP_SIZE_DEFAULT % "
        'QWEN3_5_SIMDGROUP_SIZE_DEFAULT == 0, "threadgroup must be '
        'simdgroup-aligned");'
    )

    out.append("\n#ifdef __cplusplus\n}\n#endif\n\n#endif  // PHENO_QWEN3_5_0_8B_H\n")
    return "\n".join(out)


def emit_rust(a: QwenArch) -> str:
    """Rust const block — mirrors rust/src/lib.rs `pub mod arch { ... }`."""
    out: list[str] = []
    out.append(HEADER_COMMENT)
    out.append("// Generated python/codegen.py — regenerate to keep in sync.\n")
    out.append("// Mirrors include/qwen3_5.h byte-for-byte.\n")

    out.append("#![allow(dead_code)]\n")
    out.append("pub mod arch {")
    out.append("    // Identity (informational; match qwen3_5.h string literals).")
    out.append(f'    pub const MODEL_ID: &str = "{a.model_id}";')
    out.append(f'    pub const HF_REPO: &str = "{a.hf_repo}";')
    out.append(f'    pub const FAMILY: &str = "{a.family}";')
    out.append(f'    pub const KIND: &str = "{a.kind}";')
    out.append("")
    out.append("    // Core dims")
    out.append(f"    pub const VOCAB_SIZE: usize = {a.vocab_size};")
    out.append(f"    pub const HIDDEN_SIZE: usize = {a.hidden_size};")
    out.append(f"    pub const INTERMEDIATE_SIZE: usize = {a.intermediate_size};")
    out.append(f"    pub const NUM_HIDDEN_LAYERS: usize = {a.num_hidden_layers};")
    out.append(
        f"    pub const MAX_POSITION_EMBEDDINGS: usize = {a.max_position_embeddings};"
    )
    out.append(f"    pub const RMS_NORM_EPS: f32 = {a.rms_norm_eps:.1e};")
    out.append(
        f"    pub const TIE_WORD_EMBEDDINGS: bool = {str(a.tie_word_embeddings).lower()};"
    )
    out.append("")
    out.append("    // Full attention (GQA 4:1)")
    out.append(f"    pub const FULL_HEADS: usize = {a.full_heads};")
    out.append(f"    pub const FULL_KV_HEADS: usize = {a.full_kv_heads};")
    out.append(f"    pub const FULL_HEAD_DIM: usize = {a.full_head_dim};")
    out.append(
        f"    pub const FULL_HEADS_PER_KV: usize = FULL_HEADS / FULL_KV_HEADS; // {a.full_heads_per_kv}"
    )
    out.append(
        f"    pub const FULL_Q_DIM: usize = FULL_HEADS * FULL_HEAD_DIM;          // {a.full_q_dim}"
    )
    out.append(
        f"    pub const FULL_KV_DIM: usize = FULL_KV_HEADS * FULL_HEAD_DIM;      // {a.full_kv_dim}"
    )
    out.append(
        f"    pub const FULL_QKV_DIM: usize = FULL_Q_DIM + 2 * FULL_KV_DIM;       // {a.full_qkv_dim}"
    )
    out.append(
        f"    pub const FULL_ATTN_INTERVAL: usize = {a.full_attention_interval};"
    )
    out.append(
        f"    pub const FULL_ATTN_NUM_LAYERS: usize = {a.full_attention_num_layers};"
    )
    out.append(
        f"    pub const FULL_ATTN_LAYER_INDICES: [usize; FULL_ATTN_NUM_LAYERS] = "
        f"{list(a.full_attention_layer_indices)};"
    )
    out.append("")
    out.append("    // Partial rotary")
    out.append(f"    pub const ROPE_THETA: f32 = {a.rope_theta:.1};")
    out.append(
        f"    pub const PARTIAL_ROTARY_FACTOR: f32 = {a.partial_rotary_factor:.2};"
    )
    out.append(
        f"    pub const MROPE_INTERLEAVED: bool = {str(a.mrope_interleaved).lower()};"
    )
    out.append(f"    pub const MROPE_SECTION: [usize; 3] = {list(a.mrope_section)};")
    out.append(
        f"    pub const ROT_DIM: usize = {a.rot_dim};       // partial_rotary_factor * head_dim"
    )
    out.append("")
    out.append("    // Linear attention (DeltaNet)")
    out.append(
        f"    pub const LIN_NUM_LAYERS: usize = {a.linear_num_layers};"
        "        // = NUM_HIDDEN_LAYERS - FULL_ATTN_NUM_LAYERS"
    )
    out.append(f"    pub const LIN_KEY_HEADS: usize = {a.lin_key_heads};")
    out.append(f"    pub const LIN_VALUE_HEADS: usize = {a.lin_value_heads};")
    out.append(f"    pub const LIN_KEY_HEAD_DIM: usize = {a.lin_key_head_dim};")
    out.append(f"    pub const LIN_VALUE_HEAD_DIM: usize = {a.lin_value_head_dim};")
    out.append(f"    pub const LIN_CONV_KERNEL: usize = {a.lin_conv_kernel};")
    out.append(
        f"    pub const LIN_QKV_DIM: usize = 3 * LIN_KEY_HEADS * LIN_KEY_HEAD_DIM; // {a.lin_qkv_dim}"
    )
    out.append(
        f"    pub const LIN_STATE_ELEMENTS: usize = "
        f"{a.lin_key_heads} * {a.lin_value_heads} * {a.lin_value_head_dim} * {a.lin_key_head_dim}; // {a.state_elements}"
    )
    out.append(
        f"    pub const LIN_STATE_BYTES_F32: usize = LIN_STATE_ELEMENTS * 4;   // {a.state_bytes_fp32}"
    )
    out.append(
        f"    pub const LIN_STATE_BYTES_BF16: usize = LIN_STATE_ELEMENTS * 2;  // {a.state_bytes_bf16}"
    )

    out.append("")
    out.append("    /// Kernel dispatch (DAG-41 — audit-A4 extended to Rust).")
    out.append(
        f"    pub const DEFAULT_SIMDGROUP_SIZE: u32 = {a.default_simdgroup_size}; "
        f"// Metal simdgroup"
    )
    out.append(
        f"    pub const THREADGROUP_SIZE_DEFAULT: u32 = {a.threadgroup_size_default}; "
        f"// = 8 * DEFAULT_SIMDGROUP_SIZE"
    )
    out.append("")
    out.append("    /// Layer schedule: 6 full, 18 linear (every 4th is full).")
    out.append("    pub const LAYER_IS_FULL: [bool; NUM_HIDDEN_LAYERS] = {")
    out.append("        let mut arr = [false; NUM_HIDDEN_LAYERS];")
    out.append("        let mut i = 0;")
    out.append("        while i < NUM_HIDDEN_LAYERS {")
    out.append("            arr[i] = (i + 1) % FULL_ATTN_INTERVAL == 0;")
    out.append("            i += 1;")
    out.append("        }")
    out.append("        arr")
    out.append("    };")
    out.append("")
    out.append("    /// Sanity assertions matching _Static_assert in qwen3_5.h.")
    out.append("    const _: () = {")
    out.append(
        f'        assert!(HIDDEN_SIZE == {a.hidden_size}, "hidden_size mismatch");'
    )
    out.append(
        f'        assert!(FULL_HEAD_DIM == {a.full_head_dim}, "head_dim mismatch");'
    )
    out.append(f'        assert!(ROT_DIM == {a.rot_dim}, "rot_dim mismatch");')
    out.append("    };")
    out.append("}\n")
    return "\n".join(out)


def emit_zig(a: QwenArch) -> str:
    """Zig comptime constants — usable via @cImport or as standalone Zig."""
    out: list[str] = []
    out.append(HEADER_COMMENT)
    out.append("// Mirror of include/qwen3_5.h for native Zig consumers.\n")

    out.append('pub const ModelId = "' + a.model_id + '";')
    out.append('pub const HfRepo = "' + a.hf_repo + '";')
    out.append('pub const Family = "' + a.family + '";')
    out.append('pub const Kind = "' + a.kind + '";\n')

    out.append("pub const VocabSize: usize = " + str(a.vocab_size) + ";")
    out.append("pub const HiddenSize: usize = " + str(a.hidden_size) + ";")
    out.append("pub const IntermediateSize: usize = " + str(a.intermediate_size) + ";")
    out.append("pub const NumHiddenLayers: usize = " + str(a.num_hidden_layers) + ";")
    out.append(
        "pub const MaxPositionEmbeddings: usize = "
        + str(a.max_position_embeddings)
        + ";"
    )
    out.append("pub const RmsNormEps: f32 = " + _fmt_float(a.rms_norm_eps) + "f;")
    out.append(
        "pub const TieWordEmbeddings: bool = "
        + ("true" if a.tie_word_embeddings else "false")
        + ";\n"
    )

    out.append("// Full attention (GQA 4:1)")
    out.append("pub const FullHeads: usize = " + str(a.full_heads) + ";")
    out.append("pub const FullKvHeads: usize = " + str(a.full_kv_heads) + ";")
    out.append("pub const FullHeadDim: usize = " + str(a.full_head_dim) + ";")
    out.append(
        "pub const FullHeadsPerKv: usize = FullHeads / FullKvHeads; // "
        + str(a.full_heads_per_kv)
    )
    out.append(
        "pub const FullQDim: usize = FullHeads * FullHeadDim; // " + str(a.full_q_dim)
    )
    out.append(
        "pub const FullKvDim: usize = FullKvHeads * FullHeadDim; // "
        + str(a.full_kv_dim)
    )
    out.append(
        "pub const FullQkvDim: usize = FullQDim + 2 * FullKvDim; // "
        + str(a.full_qkv_dim)
    )
    out.append(
        "pub const FullAttnInterval: usize = " + str(a.full_attention_interval) + ";"
    )
    out.append(
        "pub const FullAttnNumLayers: usize = "
        + str(a.full_attention_num_layers)
        + ";\n"
    )

    out.append("// Partial rotary")
    out.append("pub const RopeTheta: f32 = " + f"{a.rope_theta:.1f}" + ";")
    out.append(
        "pub const PartialRotaryFactor: f32 = " + f"{a.partial_rotary_factor:.2f}" + ";"
    )
    out.append(
        "pub const MRopeInterleaved: bool = "
        + ("true" if a.mrope_interleaved else "false")
        + ";"
    )
    out.append(
        "pub const MRopeSection = .{"
        + ", ".join(str(s) for s in a.mrope_section)
        + "}; // T, H, W"
    )
    out.append(
        "pub const RotDim: usize = "
        + str(a.rot_dim)
        + ";  // partial_rotary_factor * FullHeadDim\n"
    )

    out.append("// Linear attention (DeltaNet)")
    out.append("pub const LinNumLayers: usize = " + str(a.linear_num_layers) + ";")
    out.append("pub const LinKeyHeads: usize = " + str(a.lin_key_heads) + ";")
    out.append("pub const LinValueHeads: usize = " + str(a.lin_value_heads) + ";")
    out.append("pub const LinKeyHeadDim: usize = " + str(a.lin_key_head_dim) + ";")
    out.append("pub const LinValueHeadDim: usize = " + str(a.lin_value_head_dim) + ";")
    out.append("pub const LinConvKernel: usize = " + str(a.lin_conv_kernel) + ";")
    out.append(
        "pub const LinQkvDim: usize = 3 * LinKeyHeads * LinKeyHeadDim; // "
        + str(a.lin_qkv_dim)
    )
    out.append(
        f"pub const LinStateElements: usize = {a.lin_key_heads} * {a.lin_value_heads} * "
        f"{a.lin_value_head_dim} * {a.lin_key_head_dim}; // {a.state_elements}"
    )
    out.append(
        "pub const LinStateBytesF32: usize = LinStateElements * 4; // "
        + str(a.state_bytes_fp32)
    )
    out.append(
        "pub const LinStateBytesBf16: usize = LinStateElements * 2; // "
        + str(a.state_bytes_bf16)
        + "\n"
    )

    out.append("/// Layer schedule. true = full attention, false = DeltaNet.")
    [("true" if v else "false") for v in a.layer_is_full]
    out.append("pub const LayerIsFull: [NumHiddenLayers]bool = blk: {")
    out.append("    var arr: [NumHiddenLayers]bool = undefined;")
    out.append(
        "    for (0..NumHiddenLayers) |i| { arr[i] = ((i + 1) % FullAttnInterval == 0); }"
    )
    out.append("    break :blk arr;")
    out.append("};\n")

    out.append("/// Convenience: pretty-print the layer schedule.")
    out.append("pub fn printLayerSchedule(writer: anytype) !void {")
    out.append(
        '    try writer.writeAll("Qwen3.5 0.8B layer schedule (F = full, L = linear):\\n");'
    )
    out.append("    for (0..NumHiddenLayers) |i| {")
    out.append('        try writer.writeAll(if (LayerIsFull[i]) "F " else "L ");')
    out.append('        if ((i + 1) % 8 == 0) try writer.writeAll("\\n");')
    out.append("    }")
    out.append('    try writer.writeAll("\\n");')
    out.append("}\n")

    out.append(
        "// ----- Compile-time sanity (matches _Static_assert in qwen3_5.h) -----"
    )
    out.append("comptime {")
    out.append("    _ = HiddenSize;")
    out.append(
        f'    if (HiddenSize != {a.hidden_size}) @compileError("hidden_size mismatch");'
    )
    out.append(
        f'    if (FullHeadDim != {a.full_head_dim}) @compileError("head_dim mismatch");'
    )
    out.append(f'    if (RotDim != {a.rot_dim}) @compileError("rot_dim mismatch");')
    out.append("}\n")

    return "\n".join(out)


def emit_mojo(a: QwenArch) -> str:
    """Mojo comptime constants — usable with `alias NAME = value`.

    Mojo doesn't have a single arch header of its own yet; this file is the
    canonical Mojo-side source.  Bindings host code that consumes
    ``include/qwen3_5.h`` via the C interop layer.
    """
    out: list[str] = []
    out.append(HEADER_COMMENT.replace("//", "#"))
    out.append("# Mirror of include/qwen3_5.h for native Mojo consumers.\n")

    out.append('alias ModelId = "' + a.model_id + '"')
    out.append('alias HfRepo = "' + a.hf_repo + '"')
    out.append('alias Family = "' + a.family + '"')
    out.append('alias Kind = "' + a.kind + '"\n')

    out.append("# Core dims")
    out.append("alias VocabSize: Int = " + str(a.vocab_size))
    out.append("alias HiddenSize: Int = " + str(a.hidden_size))
    out.append("alias IntermediateSize: Int = " + str(a.intermediate_size))
    out.append("alias NumHiddenLayers: Int = " + str(a.num_hidden_layers))
    out.append("alias MaxPositionEmbeddings: Int = " + str(a.max_position_embeddings))
    out.append(f"alias RmsNormEps: Float32 = {_fmt_float(a.rms_norm_eps)}")
    out.append(
        "alias TieWordEmbeddings: Bool = "
        + ("True" if a.tie_word_embeddings else "False")
        + "\n"
    )

    out.append("# Full attention (GQA 4:1)")
    out.append("alias FullHeads: Int = " + str(a.full_heads))
    out.append("alias FullKvHeads: Int = " + str(a.full_kv_heads))
    out.append("alias FullHeadDim: Int = " + str(a.full_head_dim))
    out.append(
        "alias FullHeadsPerKv: Int = FullHeads // FullKvHeads  # "
        + str(a.full_heads_per_kv)
    )
    out.append("alias FullQDim: Int = FullHeads * FullHeadDim  # " + str(a.full_q_dim))
    out.append(
        "alias FullKvDim: Int = FullKvHeads * FullHeadDim  # " + str(a.full_kv_dim)
    )
    out.append(
        "alias FullQkvDim: Int = FullQDim + 2 * FullKvDim  # " + str(a.full_qkv_dim)
    )
    out.append("alias FullAttnInterval: Int = " + str(a.full_attention_interval))
    out.append(
        "alias FullAttnNumLayers: Int = " + str(a.full_attention_num_layers) + "\n"
    )

    out.append("# Partial rotary")
    out.append(f"alias RopeTheta: Float32 = {a.rope_theta:.1}")
    out.append(f"alias PartialRotaryFactor: Float32 = {a.partial_rotary_factor:.2f}")
    out.append(
        "alias MRopeInterleaved: Bool = " + ("True" if a.mrope_interleaved else "False")
    )
    out.append("alias MRopeSectionT: Int = " + str(a.mrope_section[0]))
    out.append("alias MRopeSectionH: Int = " + str(a.mrope_section[1]))
    out.append("alias MRopeSectionW: Int = " + str(a.mrope_section[2]))
    out.append("alias RotDim: Int = " + str(a.rot_dim) + "\n")

    out.append("# Linear attention (DeltaNet)")
    out.append("alias LinNumLayers: Int = " + str(a.linear_num_layers))
    out.append("alias LinKeyHeads: Int = " + str(a.lin_key_heads))
    out.append("alias LinValueHeads: Int = " + str(a.lin_value_heads))
    out.append("alias LinKeyHeadDim: Int = " + str(a.lin_key_head_dim))
    out.append("alias LinValueHeadDim: Int = " + str(a.lin_value_head_dim))
    out.append("alias LinConvKernel: Int = " + str(a.lin_conv_kernel))
    out.append(
        "alias LinQkvDim: Int = 3 * LinKeyHeads * LinKeyHeadDim  # "
        + str(a.lin_qkv_dim)
    )
    out.append(
        f"alias LinStateElements: Int = {a.lin_key_heads} * {a.lin_value_heads} * "
        f"{a.lin_value_head_dim} * {a.lin_key_head_dim}  # {a.state_elements}"
    )
    out.append(
        "alias LinStateBytesF32: Int = LinStateElements * 4  # "
        + str(a.state_bytes_fp32)
    )
    out.append(
        "alias LinStateBytesBf16: Int = LinStateElements * 2  # "
        + str(a.state_bytes_bf16)
        + "\n"
    )

    out.append("# Layer schedule (True = full attention, False = DeltaNet)")
    out.append("fn layer_is_full(i: Int) -> Bool:")
    out.append("    return ((i + 1) % FullAttnInterval) == 0\n")

    out.append("# Compile-time sanity (mirrors _Static_assert in qwen3_5.h)")
    out.append("comptime if HiddenSize != " + str(a.hidden_size) + ":")
    out.append('    print("ERROR: hidden_size mismatch")')
    out.append("comptime if FullHeadDim != " + str(a.full_head_dim) + ":")
    out.append('    print("ERROR: head_dim mismatch")')
    out.append("comptime if RotDim != " + str(a.rot_dim) + ":")
    out.append('    print("ERROR: rot_dim mismatch")\n')

    return "\n".join(out)


def emit_nim(a: QwenArch) -> str:
    """Nim const block.

    Plain Nim module — no Qt/etc deps.  The C bindings can ``{.header: "qwen3_5.h".}``
    or simply use these constants directly.
    """
    out: list[str] = []
    out.append(HEADER_COMMENT)
    out.append("# Mirror of include/qwen3_5.h for native Nim consumers.\n")

    out.append('const ModelId* = "' + a.model_id + '"')
    out.append('const HfRepo* = "' + a.hf_repo + '"')
    out.append('const Family* = "' + a.family + '"')
    out.append('const Kind* = "' + a.kind + '"\n')

    out.append("# Core dims")
    out.append("const VocabSize* = " + str(a.vocab_size))
    out.append("const HiddenSize* = " + str(a.hidden_size))
    out.append("const IntermediateSize* = " + str(a.intermediate_size))
    out.append("const NumHiddenLayers* = " + str(a.num_hidden_layers))
    out.append("const MaxPositionEmbeddings* = " + str(a.max_position_embeddings))
    out.append(f"const RmsNormEps*: float32 = {_fmt_float(a.rms_norm_eps)}'f32")
    out.append(
        "const TieWordEmbeddings* = "
        + ("true" if a.tie_word_embeddings else "false")
        + "\n"
    )

    out.append("# Full attention (GQA 4:1)")
    out.append("const FullHeads* = " + str(a.full_heads))
    out.append("const FullKvHeads* = " + str(a.full_kv_heads))
    out.append("const FullHeadDim* = " + str(a.full_head_dim))
    out.append(
        "const FullHeadsPerKv* = FullHeads div FullKvHeads  # "
        + str(a.full_heads_per_kv)
    )
    out.append("const FullQDim* = FullHeads * FullHeadDim  # " + str(a.full_q_dim))
    out.append("const FullKvDim* = FullKvHeads * FullHeadDim  # " + str(a.full_kv_dim))
    out.append("const FullQkvDim* = FullQDim + 2 * FullKvDim  # " + str(a.full_qkv_dim))
    out.append("const FullAttnInterval* = " + str(a.full_attention_interval))
    out.append("const FullAttnNumLayers* = " + str(a.full_attention_num_layers) + "\n")

    out.append("# Partial rotary")
    out.append(f"const RopeTheta*: float32 = {a.rope_theta:.1f}'f32")
    out.append(
        f"const PartialRotaryFactor*: float32 = {a.partial_rotary_factor:.2f}'f32"
    )
    out.append(
        "const MRopeInterleaved* = " + ("true" if a.mrope_interleaved else "false")
    )
    out.append("const MRopeSectionT* = " + str(a.mrope_section[0]))
    out.append("const MRopeSectionH* = " + str(a.mrope_section[1]))
    out.append("const MRopeSectionW* = " + str(a.mrope_section[2]))
    out.append("const RotDim* = " + str(a.rot_dim) + "\n")

    out.append("# Linear attention (DeltaNet)")
    out.append("const LinNumLayers* = " + str(a.linear_num_layers))
    out.append("const LinKeyHeads* = " + str(a.lin_key_heads))
    out.append("const LinValueHeads* = " + str(a.lin_value_heads))
    out.append("const LinKeyHeadDim* = " + str(a.lin_key_head_dim))
    out.append("const LinValueHeadDim* = " + str(a.lin_value_head_dim))
    out.append("const LinConvKernel* = " + str(a.lin_conv_kernel))
    out.append(
        "const LinQkvDim* = 3 * LinKeyHeads * LinKeyHeadDim  # " + str(a.lin_qkv_dim)
    )
    out.append(
        f"const LinStateElements* = {a.lin_key_heads} * {a.lin_value_heads} * "
        f"{a.lin_value_head_dim} * {a.lin_key_head_dim}  # {a.state_elements}"
    )
    out.append(
        "const LinStateBytesF32* = LinStateElements * 4  # " + str(a.state_bytes_fp32)
    )
    out.append(
        "const LinStateBytesBf16* = LinStateElements * 2  # "
        + str(a.state_bytes_bf16)
        + "\n"
    )

    out.append("# Layer schedule (true = full attention)")
    schedule_strs = ["true" if v else "false" for v in a.layer_is_full]
    out.append("const LayerIsFull*: array[NumHiddenLayers, bool] = [")
    for chunk_start in range(0, a.num_hidden_layers, 8):
        chunk = schedule_strs[chunk_start : chunk_start + 8]
        out.append(
            "  "
            + ", ".join(s.capitalize() for s in chunk)
            + ("," if chunk_start + 8 < a.num_hidden_layers else "")
        )
    out.append("]\n")

    out.append("# Compile-time sanity (matches _Static_assert in qwen3_5.h)")
    out.append("static:")
    out.append(f'  doAssert HiddenSize == {a.hidden_size}, "hidden_size mismatch"')
    out.append(f'  doAssert FullHeadDim == {a.full_head_dim}, "head_dim mismatch"')
    out.append(f'  doAssert RotDim == {a.rot_dim}, "rot_dim mismatch"')
    out.append("")
    return "\n".join(out)


def emit_json(a: QwenArch) -> str:
    """Canonical JSON dump — for cross-checking between languages."""
    obj = {
        "model_id": a.model_id,
        "hf_repo": a.hf_repo,
        "family": a.family,
        "kind": a.kind,
        "arch": a.arch,
        "vocab_size": a.vocab_size,
        "hidden_size": a.hidden_size,
        "intermediate_size": a.intermediate_size,
        "num_hidden_layers": a.num_hidden_layers,
        "max_position_embeddings": a.max_position_embeddings,
        "rms_norm_eps": a.rms_norm_eps,
        "tie_word_embeddings": a.tie_word_embeddings,
        "attn_output_gate": a.attn_output_gate,
        "partial_rotary_factor": a.partial_rotary_factor,
        "rope_theta": a.rope_theta,
        "mrope": {
            "interleaved": a.mrope_interleaved,
            "section": list(a.mrope_section),
            "rot_dim": a.rot_dim,
        },
        "full_attention": {
            "num_attention_heads": a.full_heads,
            "num_key_value_heads": a.full_kv_heads,
            "head_dim": a.full_head_dim,
            "heads_per_kv": a.full_heads_per_kv,
            "q_dim": a.full_q_dim,
            "kv_dim": a.full_kv_dim,
            "qkv_dim": a.full_qkv_dim,
            "interval": a.full_attention_interval,
            "num_layers": a.full_attention_num_layers,
            "layer_indices": list(a.full_attention_layer_indices),
        },
        "linear_attention": {
            "num_layers": a.linear_num_layers,
            "num_layers_in_spec": a.lin_num_layers_in_spec,
            "key_heads": a.lin_key_heads,
            "value_heads": a.lin_value_heads,
            "key_head_dim": a.lin_key_head_dim,
            "value_head_dim": a.lin_value_head_dim,
            "conv_kernel": a.lin_conv_kernel,
            "qkv_dim": a.lin_qkv_dim,
            "state_elements": a.state_elements,
            "state_bytes_fp32": a.state_bytes_fp32,
            "state_bytes_bf16": a.state_bytes_bf16,
        },
        "mtp": {
            "num_hidden_layers": a.mtp_num_hidden_layers,
            "use_dedicated_embeddings": a.mtp_use_dedicated_embeddings,
            "role": a.mtp_role,
        },
        "kernel_strategy": {
            "target_devices": list(a.target_devices),
            "default_simdgroup_size": a.default_simdgroup_size,
            "threadgroup_size_default": a.threadgroup_size_default,
            "dtype_compute": a.dtype_compute,
            "dtype_accumulator": a.dtype_accumulator,
            "dtype_state_cache": a.dtype_state_cache,
            "dtype_recurrent_state": a.dtype_recurrent_state,
        },
        "layer_is_full": [bool(v) for v in a.layer_is_full],
    }
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


# =============================================================================
# CLI
# =============================================================================

DEFAULT_OUTPUTS = {
    # "iso/" prefix means: write to <out-dir>/codegen/<filename> regardless of language
    # (so codegen never clobbers the canonical hand-written include/qwen3_5.h,
    #  rust/src/lib.rs, zig/engine.zig, etc.).
    "c": "iso/qwen3_5.h",
    "rust": "iso/arch.rs",
    "zig": "iso/qwen3_5.zig",
    "mojo": "iso/qwen3_5.mojo",
    "nim": "iso/qwen3_5.nim",
    "json": "codegen/arch.json",
}

# Canonical (hand-written) outputs, used when --canonical is passed.
# These are the files that ship with the repo; running codegen with --canonical
# will overwrite them. CI / drift detection should compare generated iso/* against
# these targets and fail on drift.
CANONICAL_OUTPUTS = {
    "c": "include/qwen3_5.h",
    "rust": "rust/src/arch.rs",
    "zig": "zig/qwen3_5.zig",
    "mojo": "mojo/qwen3_5.mojo",
    "nim": "nim/qwen3_5.nim",
    "json": "codegen/arch.json",
}


def _emit_all(a: QwenArch) -> dict[str, str]:
    return {
        "c": emit_c(a),
        "rust": emit_rust(a),
        "zig": emit_zig(a),
        "mojo": emit_mojo(a),
        "nim": emit_nim(a),
        "json": emit_json(a),
    }


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve()
    default_arch = here.parent.parent / "arch.yaml"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--arch",
        type=Path,
        default=default_arch,
        help=f"YAML source of truth (default: {default_arch})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override base directory for output files (default: arch.yaml parent dir)",
    )
    parser.add_argument(
        "--print",
        dest="single",
        choices=["c", "rust", "zig", "mojo", "nim", "json"],
        help="Print a single language to stdout",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any generated iso/* file differs from disk",
    )
    parser.add_argument(
        "--check-canonical",
        action="store_true",
        help="Exit non-zero if any canonical (include/, rust/, zig/, ...) "
        "file has drifted from what codegen would emit",
    )
    parser.add_argument(
        "--canonical",
        action="store_true",
        help="Write to canonical paths (include/, rust/src/, zig/, mojo/, nim/) "
        "instead of the iso/ subdir. Will overwrite hand-written files.",
    )
    args = parser.parse_args(argv)

    text = args.arch.read_text()
    a = parse_arch_yaml(text)
    outputs = _emit_all(a)

    if args.single:
        sys.stdout.write(outputs[args.single])
        if not outputs[args.single].endswith("\n"):
            sys.stdout.write("\n")
        return 0

    # Pick which set of output paths we compare against / write to.
    if args.canonical:
        active_outputs = CANONICAL_OUTPUTS
        mode_label = "canonical"
    else:
        active_outputs = DEFAULT_OUTPUTS
        mode_label = "iso"

    if args.check:
        bad = 0
        for lang, content in outputs.items():
            target = args.arch.parent / DEFAULT_OUTPUTS[lang]
            if not target.exists():
                print(f"  MISSING [{lang}]: {target}")
                bad += 1
                continue
            on_disk = target.read_text()
            if on_disk != content:
                print(f"  DIFF [{lang}]: {target}")
                bad += 1
            else:
                print(f"  OK   [{lang}]: {target}")
        return 1 if bad else 0

    if args.check_canonical:
        # Drift detection — assert each canonical file matches what we'd emit.
        bad = 0
        for lang, content in outputs.items():
            target = args.arch.parent / CANONICAL_OUTPUTS[lang]
            if not target.exists():
                # Canonical target missing is fine for non-existent bindings
                # (e.g. mojo/, nim/ don't exist yet).
                print(f"  MISSING [canonical/{lang}]: {target}")
                continue
            on_disk = target.read_text()
            if on_disk != content:
                print(f"  DRIFT [canonical/{lang}]: {target}")
                bad += 1
            else:
                print(f"  OK    [canonical/{lang}]: {target}")
        return 1 if bad else 0

    if args.out_dir:
        out_dir: Path = args.out_dir
    else:
        out_dir = default_arch.parent
    for lang, content in outputs.items():
        target = out_dir / active_outputs[lang]
        target.parent.mkdir(parents=True, exist_ok=True)
        # only write if changed, to keep mtimes stable (idempotent run)
        if not target.exists() or target.read_text() != content:
            target.write_text(content)
            print(f"  wrote [{mode_label}] {target}")
        else:
            print(f"   kept [{mode_label}] {target}")
    print(f"Generated {len(outputs)} files (mode={mode_label}) from {args.arch}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
