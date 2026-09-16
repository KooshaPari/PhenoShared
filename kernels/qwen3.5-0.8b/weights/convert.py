"""
convert.py — Bridge between ModelWeightsHF (the raw HF loader schema) and
ModelWeights (the reference-schema dataclass in python/reference.py).

The reference forward pass expects a specific Layout:

* full attention
  - qkv_w: [Q + KV + KV, H]   (packed Q / K / V)
  - q_gate_w: [Q, H]           (the gate = second half of HF q_proj)
  - q_norm_w, k_norm_w: [D]    (per-head RMSNorm weights)
* linear attention
  - qkv_w: [3*Hk*Dk, H]        (packed Q / K / V from in_proj_qkv)
  - in_proj_a_w, in_proj_b_w: [Hv, H]    (delta + beta inputs)
  - in_proj_z_w: [Hv*Dv, H]                (silu gate)
  - A_log, dt_bias: [Hv]                  (per-head decay / bias)
  - lin_norm_w: [Dv]                      (per-head RMSNorm on output)
  - conv_w: [C, K]                        (depthwise conv1d kernel)

ModelWeightsHF stores q_proj as [2*Q, H] where the first Q rows are the
query and the second Q rows are the gate.  This module splits that into
q_w / q_gate_w before constructing the reference's qkv_w.

Returned tensors are MLX arrays in bf16 (the reference's working dtype).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mlx.core as mx

from .hf_loader import (
    ARCH_DEFAULTS,
    LayerWeightsHF,
    ModelWeightsHF,
    _is_full_layer,
)

if TYPE_CHECKING:
    # Forward reference only — the runtime import happens lazily inside
    # hf_to_reference() to avoid pulling in mlx / reference at module
    # import time. Used by the type annotations on line 75 and 165.
    from python.reference import ModelWeights  # noqa: F401


def _ensure_bf16(arr, *, name: str):
    """Cast an MLX array to bf16 (the reference's working dtype)."""
    if arr is None:
        return None
    if isinstance(arr, mx.array):
        if arr.dtype != mx.bfloat16:
            return arr.astype(mx.bfloat16)
        return arr
    # numpy / python scalar — wrap and cast
    a = mx.array(arr)
    if a.dtype != mx.bfloat16:
        a = a.astype(mx.bfloat16)
    return a


def _split_full_attn_q(hf_layer: LayerWeightsHF, H: int, Q: int, KV: int):
    """Split the HF q_proj weight [2Q, H] into the q_w [Q, H] and the
    gate [Q, H] used by the reference."""
    qw = _ensure_bf16(hf_layer.q_w, name="q_w")
    if qw is None:
        raise ValueError("full-attn layer missing q_proj weight")
    if qw.shape[0] != 2 * Q:
        raise ValueError(
            f"expected HF q_proj weight shape [2Q={2 * Q}, H={H}], got {tuple(qw.shape)}"
        )
    if qw.shape[1] != H:
        raise ValueError(
            f"HF q_proj hidden dim mismatch: got {qw.shape[1]}, expected {H}"
        )
    # First Q rows are the query; second Q rows are the gate.
    q_real = qw[:Q, :]
    q_gate = qw[Q : 2 * Q, :]
    return q_real, q_gate


def hf_to_reference(mw_hf: ModelWeightsHF) -> ModelWeights:
    """Convert a :class:`ModelWeightsHF` (raw HF loader schema) into a
    :class:`reference.ModelWeights` (the schema the functional forward
    pass expects)."""
    # Lazy import: the reference module is heavyweight and pulls in
    # arch.yaml / mlx.  Tests for the loader shouldn't have to import it.
    import sys

    # Make sure the kernels/qwen3.5-0.8b/python directory is on sys.path
    _pkg_root = Path(__file__).resolve().parent.parent
    _py_dir = _pkg_root / "python"
    if str(_py_dir) not in sys.path:
        sys.path.insert(0, str(_py_dir))
    from reference import LayerWeights as RefLayerWeights
    from reference import ModelWeights as RefModelWeights

    arch = dict(ARCH_DEFAULTS)
    H = arch["hidden_size"]
    arch["intermediate_size"]
    full_q = arch["full_heads"] * arch["full_head_dim"]  # type: ignore[operator]
    full_kv = arch["full_kv_heads"] * arch["full_head_dim"]  # type: ignore[operator]
    arch["lin_key_heads"]
    arch["lin_key_head_dim"]
    arch["lin_value_heads"]
    arch["lin_value_head_dim"]

    embed = _ensure_bf16(mw_hf.embed, name="embed")

    ref_layers = []
    for i, hf_layer in enumerate(mw_hf.layers):
        attn_norm_w = _ensure_bf16(hf_layer.attn_norm_w, name=f"layers.{i}.attn_norm_w")
        ffn_norm_w = _ensure_bf16(hf_layer.ffn_norm_w, name=f"layers.{i}.ffn_norm_w")

        if _is_full_layer(i):
            # Split q_proj: first Q rows are q, next Q rows are gate.
            q_real, q_gate = _split_full_attn_q(hf_layer, H, full_q, full_kv)  # type: ignore[arg-type]
            k_w = _ensure_bf16(hf_layer.k_w, name=f"layers.{i}.k_w")
            v_w = _ensure_bf16(hf_layer.v_w, name=f"layers.{i}.v_w")
            o_w = _ensure_bf16(hf_layer.o_w, name=f"layers.{i}.o_w")
            q_norm_w = _ensure_bf16(hf_layer.q_norm_w, name=f"layers.{i}.q_norm_w")
            k_norm_w = _ensure_bf16(hf_layer.k_norm_w, name=f"layers.{i}.k_norm_w")
            # Concatenate into the reference's [Q + KV + KV, H] qkv_w.
            qkv_w = mx.concatenate([q_real, k_w, v_w], axis=0)
            ref_layer = RefLayerWeights(
                attn_norm_w=attn_norm_w,
                ffn_norm_w=ffn_norm_w,
                qkv_w=qkv_w,
                o_proj_w=o_w,
                q_gate_w=q_gate,
                q_norm_w=q_norm_w,
                k_norm_w=k_norm_w,
                gate_w=_ensure_bf16(hf_layer.gate_w, name=f"layers.{i}.gate_w"),
                up_w=_ensure_bf16(hf_layer.up_w, name=f"layers.{i}.up_w"),
                down_w=_ensure_bf16(hf_layer.down_w, name=f"layers.{i}.down_w"),
            )
        else:
            qkv_w = _ensure_bf16(hf_layer.in_proj_qkv, name=f"layers.{i}.in_proj_qkv")
            in_proj_a_w = _ensure_bf16(hf_layer.in_proj_a, name=f"layers.{i}.in_proj_a")
            in_proj_b_w = _ensure_bf16(hf_layer.in_proj_b, name=f"layers.{i}.in_proj_b")
            in_proj_z_w = _ensure_bf16(hf_layer.in_proj_z, name=f"layers.{i}.in_proj_z")
            conv_w = _ensure_bf16(hf_layer.conv1d_w, name=f"layers.{i}.conv1d_w")
            A_log = _ensure_bf16(hf_layer.A_log, name=f"layers.{i}.A_log")
            dt_bias = _ensure_bf16(hf_layer.dt_bias, name=f"layers.{i}.dt_bias")
            lin_norm_w = _ensure_bf16(
                hf_layer.lin_norm_w, name=f"layers.{i}.lin_norm_w"
            )
            o_w = _ensure_bf16(hf_layer.o_w, name=f"layers.{i}.o_w")
            ref_layer = RefLayerWeights(
                attn_norm_w=attn_norm_w,
                ffn_norm_w=ffn_norm_w,
                qkv_w=qkv_w,
                o_proj_w=o_w,
                conv_w=conv_w,
                A_log=A_log,
                dt_bias=dt_bias,
                in_proj_a_w=in_proj_a_w,
                in_proj_b_w=in_proj_b_w,
                in_proj_z_w=in_proj_z_w,
                lin_norm_w=lin_norm_w,
                gate_w=_ensure_bf16(hf_layer.gate_w, name=f"layers.{i}.gate_w"),
                up_w=_ensure_bf16(hf_layer.up_w, name=f"layers.{i}.up_w"),
                down_w=_ensure_bf16(hf_layer.down_w, name=f"layers.{i}.down_w"),
            )
        ref_layers.append(ref_layer)

    final_norm_w = _ensure_bf16(mw_hf.final_norm_w, name="final_norm_w")
    return RefModelWeights(embed=embed, layers=ref_layers, final_norm_w=final_norm_w)


def load_reference_weights(
    hf_dir: str | Path,
    *,
    prefer_mlx: bool = True,
    verbose: bool = False,
) -> ModelWeights:
    """Convenience wrapper: load HF weights and immediately convert to the
    reference schema.  Equivalent to
    ``hf_to_reference(load_hf_weights(hf_dir, prefer_mlx=..., verbose=...))``.
    """
    from .hf_loader import load_hf_weights

    mw_hf = load_hf_weights(hf_dir, prefer_mlx=prefer_mlx, verbose=verbose)
    return hf_to_reference(mw_hf)
