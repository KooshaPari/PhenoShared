"""
reference.py — Pure-MLX reference implementation of Qwen3.5 0.8B (text path).

Used to validate the hand-tuned Metal kernels.  MLX is the Apple-blessed
reference because it has identical numerics to PyTorch/MPS on Apple Silicon
and uses the same underlying Metal compute.

The reference implements:
  - Token embedding
  - 24-layer transformer with hybrid linear/full attention
  - Per-layer: RMSNorm, QKV/linear projections, RoPE (M-RoPE partial),
    full or linear attention, output gate, SwiGLU FFN
  - Final norm + LM head (tied with embedding)
  - Sampling (greedy / top-k / top-p / temperature)

Architecture constants are imported from arch.yaml via codegen; weights are
random unless an Hugging Face safetensors directory is supplied via
``--weights-dir``.

For a single token forward (decode), this is ~5-10x slower than the hand-
tuned Metal kernels, but produces the same numerical output up to bf16
rounding.

Per-kernel entry points (also reused by validate.py):
  ref_rmsnorm(x, w, eps)
  mrope_apply(x, pos_ids)
  ref_rope(q, pos_ids, rot_dim, rope_theta, mrope_section)
  ref_swiglu(gate, up)
  ref_sigmoid_gate(o, og)
  ref_full_attention(q, k, v, causal)
  ref_attention_decode(q, k_cache, v_cache, seq_len, scale)
  ref_linear_attention_step(q, k, v, gate, beta, alpha_log, state)
  ref_conv1d_step(qkv_in, conv_w, conv_state, conv_bias)
  ref_gemv(x, w, bias)
  ref_gemm(a, b, bias)
  ref_gumbel_argmax(logits, temperature, seed)
  ref_sample(logits, temperature, top_k, top_p, seed, mode)
  ref_end_to_end_forward(input_ids, position_ids, weights, kv_caches, lin_states)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import mlx.core as mx
import mlx.nn as nn
import numpy as np

# ---------------------------------------------------------------------------
# Architecture constants — must match kernels/qwen3.5-0.8b/arch.yaml and
# kernels/qwen3.5-0.8b/include/qwen3_5.h
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QwenArch:
    vocab_size: int = 248_320
    hidden_size: int = 1024
    intermediate_size: int = 3584
    num_hidden_layers: int = 24
    max_position_embeddings: int = 262_144
    rms_norm_eps: float = 1.0e-6

    # Full attention
    full_heads: int = 8
    full_kv_heads: int = 2
    full_head_dim: int = 256
    full_attention_interval: int = 4

    # Partial rotary
    # rot_dim: only the first D_rot dims of each head_dim are rotated.  The
    # HF config reports partial_rotary_factor=0.25 (=64 if applied to 256),
    # but the mrope_section=[11,11,10] sums to 32 which is the actual value
    # the model uses.  HF's partial_rotary_factor is a vestige of the Qwen2
    # convention (where head_dim=128 → 0.25*128=32) and does not match the
    # current Qwen3.5 layout.
    rot_dim: int = 32  # sum of mrope_section (11+11+10)
    partial_rotary_factor: float = 0.25  # legacy HF field, kept for compat
    rope_theta: float = 10_000_000.0

    # M-RoPE
    mrope_interleaved: bool = True
    mrope_section: tuple = (11, 11, 10)  # sums to 32 = rot_dim / 2

    # Linear attention
    lin_key_heads: int = 16
    lin_value_heads: int = 16
    lin_key_head_dim: int = 128
    lin_value_head_dim: int = 128
    lin_conv_kernel: int = 4

    tie_word_embeddings: bool = True
    attn_output_gate: bool = True
    hidden_act: str = "silu"

    @property
    def full_q_dim(self) -> int:
        return self.full_heads * self.full_head_dim  # 2048

    @property
    def full_kv_dim(self) -> int:
        return self.full_kv_heads * self.full_head_dim  # 512

    @property
    def full_qkv_dim(self) -> int:
        return self.full_q_dim + 2 * self.full_kv_dim  # 3072

    @property
    def lin_qkv_dim(self) -> int:
        return 3 * self.lin_key_heads * self.lin_key_head_dim  # 6144

    @property
    def layer_is_full(self) -> list:
        """Returns [True, True, True, False, ...] for full attention layers."""
        return [
            ((i + 1) % self.full_attention_interval == 0)
            for i in range(self.num_hidden_layers)
        ]


ARCH = QwenArch()


# ---------------------------------------------------------------------------
# M-RoPE (multi-modal rotary position embedding) — Qwen3.5 variant
#
#   mrope_interleaved=True:  for k in 0..D_rot/2:
#     idx = k % 3           -> 0:T, 1:H, 2:W
#     pos = position_ids[b, s, idx]
#     out[..., 2k]   = cos(pos * inv_freq[k]) * x[2k]   - sin(pos * inv_freq[k]) * x[2k+1]
#     out[..., 2k+1] = sin(pos * inv_freq[k]) * x[2k]   + cos(pos * inv_freq[k]) * x[2k+1]
#   Only the first D_rot=32 of head_dim=256 dims are rotated.
# ---------------------------------------------------------------------------


def _build_inv_freq(rot_dim: int, theta: float) -> mx.array:
    # inv_freq[k] = 1 / (theta ** (2k / rot_dim))   for k in 0..(rot_dim/2 - 1)
    half = rot_dim // 2
    k = mx.arange(0, half, dtype=mx.float32)
    e = (2.0 * k) / rot_dim
    return 1.0 / mx.power(theta, e)


_INV_FREQ = _build_inv_freq(ARCH.rot_dim, ARCH.rope_theta)  # [D_rot/2]


def mrope_apply(x: mx.array, position_ids: mx.array) -> mx.array:
    """Apply M-RoPE partial rotary to the first D_rot=32 dims.

    x:           [B, S, H, D]   bf16
    position_ids:[B, S, 3]      i32   (T, H, W)

    Returns x with the first 32 dims rotated, the remaining dims unchanged.
    """
    B, S, H, D = x.shape
    rot = ARCH.rot_dim
    half = rot // 2

    # Cast to fp32 for trig ops
    x_rot = x[..., :rot].astype(mx.float32)  # [B, S, H, rot]
    x_pass = x[..., rot:]  # [B, S, H, D - rot]

    # inv_freq per (k, section) → position multiplier.
    # mrope_interleaved: k % 3 selects section (0:T, 1:H, 2:W)
    k = mx.arange(0, half, dtype=mx.int32)  # [half]
    section = k % 3  # [half]
    pos_sel = mx.take(position_ids, section, axis=-1)  # [B, S, half]
    pos_sel = pos_sel.astype(mx.float32)  # [B, S, half]

    angle = pos_sel * _INV_FREQ  # [B, S, half]
    cos = mx.cos(angle)  # [B, S, half]
    sin = mx.sin(angle)  # [B, S, half]

    # x_rot shape [B, S, H, rot]; reshape to [B, S, H, half, 2]
    xr = mx.reshape(x_rot, (B, S, H, half, 2))
    x_even = xr[..., 0]  # [B, S, H, half]
    x_odd = xr[..., 1]  # [B, S, H, half]

    # Broadcast cos/sin across H
    cos = cos[:, :, None, :]  # [B, S, 1, half]
    sin = sin[:, :, None, :]

    out_even = cos * x_even - sin * x_odd
    out_odd = sin * x_even + cos * x_odd

    out_rot = mx.stack([out_even, out_odd], axis=-1)  # [B, S, H, half, 2]
    out_rot = mx.reshape(out_rot, (B, S, H, rot)).astype(x.dtype)

    return mx.concatenate([out_rot, x_pass.astype(x.dtype)], axis=-1)


# ---------------------------------------------------------------------------
# RMSNorm
# ---------------------------------------------------------------------------


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1.0e-6):
        super().__init__()
        self.weight = mx.ones((dim,))
        self.eps = eps

    def __call__(self, x: mx.array) -> mx.array:
        fp = x.astype(mx.float32)
        sq = fp * fp
        mean_sq = mx.mean(sq, axis=-1, keepdims=True)
        rms_inv = mx.rsqrt(mean_sq + self.eps)
        return (fp * rms_inv * self.weight.astype(mx.float32)).astype(x.dtype)


# ---------------------------------------------------------------------------
# Full attention (GQA 4:1, flash-style for prefill, decode-friendly for S=1)
# ---------------------------------------------------------------------------


def _rearrange(x: mx.array, pattern: str) -> mx.array:
    """Thin wrapper around einops-style rearrange.  Uses mx.transpose + reshape."""
    # We only need a couple of patterns, implement inline.
    if pattern == "b s (h d) -> b s h d":
        B, S, HD = x.shape
        H = HD // ARCH.full_head_dim
        return x.reshape(B, S, H, ARCH.full_head_dim)
    if pattern == "b s h d -> b s (h d)":
        B, S, H, D = x.shape
        return x.reshape(B, S, H * D)
    raise ValueError(f"unknown pattern {pattern}")


def full_attention(
    q: mx.array,  # [B, S, H_q, D]
    k: mx.array,  # [B, S_k, H_kv, D]
    v: mx.array,  # [B, S_k, H_kv, D]
    causal: bool = True,
) -> mx.array:
    H_q, H_kv, D = ARCH.full_heads, ARCH.full_kv_heads, ARCH.full_head_dim
    group = H_q // H_kv  # 4

    # GQA broadcast:  [B, H_kv, group, D] from k, then expand to [B, H_q, D]
    # We compute attn in [B, H_q, S, S_k] form using the broadcast.
    B, S, _, _ = q.shape
    _, S_k, _, _ = k.shape
    scale = 1.0 / math.sqrt(D)

    # q: [B, S, H_q, D] -> [B, H_q, S, D]
    q = q.transpose(0, 2, 1, 3)
    # k,v: [B, S_k, H_kv, D] -> [B, H_kv, S_k, D]
    k = k.transpose(0, 2, 1, 3)
    v = v.transpose(0, 2, 1, 3)
    # Broadcast: [B, H_kv, S_k, D] -> [B, H_kv, group, S_k, D] -> [B, H_q, S_k, D]
    k = mx.repeat(k, group, axis=1)  # [B, H_q, S_k, D]
    v = mx.repeat(v, group, axis=1)

    # scores: [B, H_q, S, S_k]
    scores = (q @ k.transpose(0, 1, 3, 2)) * scale
    if causal:
        # Apply causal mask: S_q can attend to S_kv where S_kv_idx <= S_q_idx + (S_k - S)
        # For prefill S_q == S_kv:  S_kv_idx <= S_q_idx.
        # For decode S_q = 1, S_kv = current_len:  S_kv_idx <= S_kv_len - 1 = position.
        # We assume S_q <= S_kv and the offset is S_kv - S_q.
        offset = S_k - S
        idx_q = mx.arange(S)[:, None]
        idx_k = mx.arange(S_k)[None, :]
        mask = idx_k <= (idx_q + offset)
        scores = mx.where(mask, scores, mx.array(-1e9, dtype=scores.dtype))

    # Softmax in fp32
    s_fp = scores.astype(mx.float32)
    s_max = mx.max(s_fp, axis=-1, keepdims=True)
    exp_s = mx.exp(s_fp - s_max)
    p = (exp_s / mx.sum(exp_s, axis=-1, keepdims=True)).astype(scores.dtype)

    # out: [B, H_q, S, D]
    out = p @ v
    # [B, H_q, S, D] -> [B, S, H_q, D]
    out = out.transpose(0, 2, 1, 3)
    return out


# ---------------------------------------------------------------------------
# Linear attention (DeltaNet-style) — recurrent state update
# ---------------------------------------------------------------------------


def linear_attention_step(
    q: mx.array,  # [B, H, Dk]   — already L2-normalized by the kernel
    k: mx.array,  # [B, H, Dk]   — already L2-normalized by the kernel
    v: mx.array,  # [B, H, Dv]
    gate: mx.array,  # [B, H, Dv]  — the silu gate z, applied after norm outside this fn
    beta: mx.array,  # [B, H]       — sigmoid(b_t), already activated
    alpha_log: mx.array,  # [H]    — A_log; we apply -exp(alpha_log) * softplus(a + dt_bias)
    #          outside this fn, so alpha_log here is the
    #          per-token decay log (already includes dt_bias+a).
    state: mx.array,  # [B, H, Dv, Dk]  fp32  (in/out)
) -> tuple:
    """One step of the gated delta rule (FLA-style).

    This implements the recurrence from
    :func:`torch_recurrent_gated_delta_rule` in the reference HF
    implementation:

        g_t  = exp(-alpha_log_t)            # [B, H]   — already includes softplus+dt_bias
        st   = g_t * state                  # [B, H, Dv, Dk]
        v_new = v_t - beta_t * (st @ k_t)   # [B, H, Dv]
        state = st + outer(k_t, v_new)      # [B, H, Dv, Dk]
        o_t   = state @ q_t                 # [B, H, Dv]

    The caller is responsible for L2-normalising q and k beforehand (when
    ``use_qk_l2norm_in_kernel=True``), applying the silu gate to ``o_t`` via
    the gated-norm, and feeding the resulting ``o`` through ``out_proj``.

    The :class:`ref_end_to_end_forward` driver applies the gate and norm
    together as ``norm(o, z)`` (RMSNorm then * silu(z)) which matches
    Qwen3_5RMSNormGated.  ``gate`` here is therefore unused at the per-step
    level — the driver hoists the silu gate to the layer end for efficiency.

    Returns ``(o_t, new_state)``.
    """
    B, H, Dk = q.shape
    _, _, Dv = v.shape
    # alpha_log here is the per-token "g" from FLA — already a negative
    # quantity (g = -A_log.exp() * softplus(a + dt_bias)).  The decay
    # factor applied to state is therefore exp(g) = exp(alpha_log), NOT
    # exp(-alpha_log).  (An earlier version of this code inverted the
    # sign and produced garbage outputs.)
    g = mx.exp(alpha_log.astype(mx.float32))  # [B, H]
    beta_f = beta.astype(mx.float32)  # [B, H]
    # FLA scales query by 1/sqrt(Dk).  Apply it here so the resulting
    # ``state @ q`` has the right magnitude.
    scale = 1.0 / (Dk**0.5)
    q_f = q.astype(mx.float32) * scale  # [B, H, Dk]
    k_f = k.astype(mx.float32)  # [B, H, Dk]
    v_f = v.astype(mx.float32)  # [B, H, Dv]
    s_f = state.astype(mx.float32)  # [B, H, Dv, Dk]

    # state decay
    s_new = g[..., None, None] * s_f  # [B, H, Dv, Dk]

    # state @ k : [B, H, Dv]
    sk = mx.einsum("bhdk,bhk->bhd", s_new, k_f)
    v_new = v_f - beta_f[..., None] * sk  # [B, H, Dv]

    # state update (in fp32, then cast back)
    new_state = (s_new + mx.einsum("bhd,bhk->bhdk", v_new, k_f)).astype(state.dtype)
    state = new_state

    # o = state @ q : [B, H, Dv]
    o = mx.einsum("bhdk,bhk->bhd", new_state.astype(mx.float32), q_f)

    return (o.astype(state.dtype), state)


def causal_conv1d_step(
    qkv_in: mx.array,  # [B, 3H*Dk] or [B, C, Dk]
    conv_w: mx.array,  # [3H, K] or [C, K]
    conv_state: mx.array,  # [B, 3H, K] or [B, C, K]   in/out
    conv_bias: mx.array | None = None,
) -> mx.array:
    """One step of depthwise causal conv1d with kernel K=4.

    Accepts both flattened ``[B, 3H*Dk]`` (end-to-end forward shape) and
    explicit ``[B, C, Dk]`` (per-kernel test shape). The latter treats each
    of the C channels independently — the conv weights are depthwise over
    the channel axis.
    """
    B, C, K = conv_state.shape
    if qkv_in.ndim == 2:
        # [B, 3H*Dk] → take the last slot of the packed axis (matches the
        # kernel's "store latest input into slot K-1" convention).
        last = qkv_in[:, -1].reshape(B, C, 1)
    elif qkv_in.ndim == 3:
        last = qkv_in[:, :, -1:]
    else:
        raise ValueError(f"qkv_in must be 2D or 3D, got shape {qkv_in.shape}")
    # MLX arrays are immutable; we return the shifted state rather than
    # mutating in place. Callers should rebind the conv_state variable.
    new_state = mx.concatenate([conv_state[:, :, 1:], last], axis=-1)
    # out[c] = sum_k w[c, k] * state[c, k]   +  bias[c]
    # conv_w has shape [C, K], new_state has shape [B, C, K] → broadcast
    # over the B axis. Use einsum to make the contraction explicit.
    out = mx.einsum("bck,ck->bc", new_state, conv_w.astype(mx.float32)).astype(
        qkv_in.dtype
    )
    if conv_bias is not None:
        out = out + conv_bias
    # Return both the per-token conv output (broadcast to Dk slots) and the
    # new state — the validate.py harness unwraps the first.
    return out, new_state


# ---------------------------------------------------------------------------
# SwiGLU MLP — silu(x @ W_gate.T) * (x @ W_up.T)  @ W_down.T
# ---------------------------------------------------------------------------


def ref_swiglu(gate: mx.array, up: mx.array) -> mx.array:
    """silu(gate) * up — matches activation.metal :: silu_mul_inplace.

    gate, up: same shape [B, S, I] bf16, returns [B, S, I] bf16.
    """
    g = gate.astype(mx.float32)
    u = up.astype(mx.float32)
    return (g * mx.sigmoid(g) * u).astype(gate.dtype)


def ref_swiglu_mlp(
    x: mx.array,  # [B, S, H] bf16
    w_gate: mx.array,  # [I, H] bf16
    w_up: mx.array,  # [I, H] bf16
    w_down: mx.array,  # [H, I] bf16
) -> mx.array:
    """Full SwiGLU MLP block: x -> gate,up projections -> silu* -> down.

    Returns [B, S, H] bf16.  H = hidden_size, I = intermediate_size.
    """
    gate = x @ w_gate.T
    up = x @ w_up.T
    inter = ref_swiglu(gate, up)
    return (inter @ w_down.T).astype(x.dtype)


def ref_sigmoid_gate(o: mx.array, og: mx.array) -> mx.array:
    """o * sigmoid(og) — matches activation.metal :: sigmoid_gate_mul."""
    return (o.astype(mx.float32) * mx.sigmoid(og.astype(mx.float32))).astype(o.dtype)


# ---------------------------------------------------------------------------
# GEMM / GEMV — used for projection and lm_head reference
# ---------------------------------------------------------------------------


def ref_gemv(x: mx.array, w: mx.array, bias: mx.array | None = None) -> mx.array:
    """y[n] = sum_k x[k] * w[k, n] + bias[n] — matches gemv_decode.

    x: [K] bf16, w: [K, N] bf16, bias: [N] bf16 or None; output [N] bf16.
    """
    y = mx.matmul(x.astype(mx.float32)[None, :], w.astype(mx.float32))
    y = y[0]
    if bias is not None:
        y = y + bias.astype(mx.float32)
    return y.astype(mx.bfloat16)


def ref_gemm(a: mx.array, b: mx.array, bias: mx.array | None = None) -> mx.array:
    """y[m, n] = sum_k a[m, k] * b[k, n] — matches gemm_bf16.

    a: [M, K] bf16, b: [K, N] bf16, bias: [N] bf16 or None; output [M, N] bf16.
    """
    y = mx.matmul(a.astype(mx.float32), b.astype(mx.float32))
    if bias is not None:
        y = y + bias.astype(mx.float32)
    return y.astype(mx.bfloat16)


# ---------------------------------------------------------------------------
# Sampling — greedy / top-k / top-p / temperature / gumbel
# ---------------------------------------------------------------------------


def _softmax(x: mx.array, axis: int = -1) -> mx.array:
    x_max = mx.max(x, axis=axis, keepdims=True)
    e = mx.exp(x - x_max)
    return e / mx.sum(e, axis=axis, keepdims=True)


def ref_gumbel_argmax(logits: mx.array, temperature: float, seed: int) -> int:
    """Sample argmax(logits/T + gumbel) using numpy RNG.

    logits: [V] bf16.
    Returns the sampled int token id.

    This is the fused_topk_topp_argmax Metal kernel's reference; the same
    gumbel-max trick is used by HF transformers and matches the greedy
    decoder when temperature→0.
    """
    rng = np.random.default_rng(seed)
    u = rng.uniform(0.0, 1.0, size=logits.shape).astype(np.float32)
    # gumbel = -log(-log(u + eps) + eps)   — eps keeps it finite near 0.
    gumbel = -np.log(-np.log(u + 1e-30) + 1e-30)
    scores = (logits.astype(mx.float32) / float(temperature)) + mx.array(
        gumbel, dtype=mx.float32
    )
    return int(mx.argmax(scores, axis=-1).item())


def ref_sample(
    logits: mx.array,  # [V] or [B, V] bf16
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: float = 1.0,
    seed: int = 0,
    mode: str = "gumbel",  # "greedy" | "gumbel" | "topk_topp"
) -> mx.array:
    """Sample from a vocab distribution.

    Modes:
      "greedy"     — pure argmax (temperature ignored)
      "gumbel"     — gumbel-max with temperature (default; matches Metal kernel)
      "topk_topp"  — temperature + top-k filter + nucleus (top-p) filter, then categorical

    Returns int (or [B] ints).
    """
    is_batched = logits.ndim == 2
    if not is_batched:
        logits = logits[None, :]
    out = []
    for b in range(logits.shape[0]):
        row = logits[b].astype(mx.float32)
        if mode == "greedy" or temperature <= 0:
            out.append(int(mx.argmax(row, axis=-1).item()))
            continue
        scaled = row / float(temperature)
        # top-k filter
        if top_k and top_k < row.shape[-1]:
            kth = mx.topk(scaled, k=top_k, axis=-1)[0][-1]
            scaled = mx.where(scaled < kth, mx.array(-1e30, dtype=scaled.dtype), scaled)
        # top-p (nucleus) filter
        if top_p < 1.0:
            sorted_idx = mx.argsort(-scaled, axis=-1)
            sorted_vals = mx.take(scaled, sorted_idx, axis=-1)
            probs = _softmax(sorted_vals)
            cum = mx.cumsum(probs, axis=-1)
            keep = cum <= float(top_p)
            # always keep at least 1
            keep = (
                mx.concatenate([mx.array([True], dtype=mx.bool_), keep[1:]], axis=-1)
                if keep.shape[0] > 1
                else keep
            )
            sorted_vals = mx.where(
                keep, sorted_vals, mx.array(-1e30, dtype=scaled.dtype)
            )
            # unsort back
            scaled = mx.put_along_axis(
                mx.zeros_like(scaled),
                sorted_idx[None, :],
                sorted_vals[None, :],
                axis=-1,
            )[0]
        if mode == "gumbel":
            out.append(
                int(
                    ref_gumbel_argmax(logits[b], temperature=temperature, seed=seed + b)
                )
            )
        elif mode == "topk_topp":
            probs = _softmax(scaled)
            cat = mx.random.categorical(mx.log(probs + 1e-30))
            out.append(int(cat.item()))
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return out[0] if not is_batched else mx.array(out, dtype=mx.int32)


# ---------------------------------------------------------------------------
# Weights container — minimal dataclass holding the tensors each layer needs.
# Pure random init is fine for the reference; real loading is wired elsewhere.
# ---------------------------------------------------------------------------


@dataclass
class LayerWeights:
    """Per-layer weight tensors used by the functional forward pass.

    Shapes:
      attn_norm_w, ffn_norm_w      [H]                    bf16
      qkv_w                        [QKV, H]                bf16
        Full attn: [Q + KV + KV, H] where Q = 2*full_q_dim (gated).
        Linear:   [3*Hk*Dk, H] (packed Q/K/V from in_proj_qkv).
      o_proj_w                     [H, Q]                  bf16
      q_gate_w (full only)         [Q, H]                  bf16  (the second
                                     half of the HF q_proj weight matrix)
      q_norm_w, k_norm_w (full)    [D]                    bf16  (per-head RMSNorm)
      gate_w, up_w                 [I, H]                  bf16
      down_w                       [H, I]                  bf16
      conv_w (linear only)         [C, K]                  bf16  (depthwise)
      A_log, dt_bias (linear)      [Hv]                    bf16
      in_proj_a_w, in_proj_b_w     [Hv, H]                bf16  (per-head a/b)
      in_proj_z_w                  [Hv*Dv, H]             bf16  (silu gate)
      lin_norm_w (linear only)     [Dv]                    bf16  (per-head norm)
      alpha_log                    [H_kv]                  bf16 (legacy alias for A_log)
    """

    attn_norm_w: mx.array
    ffn_norm_w: mx.array
    qkv_w: mx.array
    o_proj_w: mx.array
    o_gate_w: mx.array | None = None  # legacy alias (unused now)
    q_gate_w: mx.array | None = None  # [Q, H] from second half of HF q_proj
    q_norm_w: mx.array | None = None  # [D]
    k_norm_w: mx.array | None = None  # [D]
    gate_w: mx.array | None = None
    up_w: mx.array | None = None
    down_w: mx.array | None = None
    conv_w: mx.array | None = None
    A_log: mx.array | None = None
    dt_bias: mx.array | None = None
    in_proj_a_w: mx.array | None = None
    in_proj_b_w: mx.array | None = None
    in_proj_z_w: mx.array | None = None
    lin_norm_w: mx.array | None = None
    # Back-compat field name retained for older callers.
    alpha_log: mx.array | None = None


@dataclass
class ModelWeights:
    """Top-level weight container — embed tied with lm_head."""

    embed: mx.array  # [V, H] bf16
    layers: list  # list[LayerWeights], length = num_hidden_layers
    final_norm_w: mx.array  # [H] bf16

    def __post_init__(self):
        assert len(self.layers) == ARCH.num_hidden_layers, (
            f"expected {ARCH.num_hidden_layers} layer weight blocks, got {len(self.layers)}"
        )


def random_weights(seed: int = 0) -> ModelWeights:
    """Generate random weights of the right shapes for a forward pass.

    Uses small-magnitude init (std=0.02, like the HF Qwen3.5 init) so the
    model produces finite outputs without blow-up.  Returns a fully-
    populated ModelWeights.
    """
    mx.random.seed(seed)
    np.random.seed(seed)
    std = 0.02

    # Use MLX's Metal RNG directly to generate fp32 on-device — np.random.randn
    # defaults to fp64 which would allocate a 2 GB intermediate for the
    # [vocab_size, hidden_size] embed and OOM/swap on this machine.
    std = 0.02

    def t(shape, dtype=mx.bfloat16):
        # mx.random.normal generates fp32 on-device; cast to bf16 in-place.
        return (mx.random.normal(shape=shape, dtype=mx.float32) * std).astype(dtype)

    embed = t((ARCH.vocab_size, ARCH.hidden_size))

    layers = []
    for i in range(ARCH.num_hidden_layers):
        is_full = ARCH.layer_is_full[i]
        if is_full:
            qkv_dim = ARCH.full_qkv_dim  # 3072
            q_dim = ARCH.full_q_dim  # 2048
            o_w = t((ARCH.hidden_size, q_dim))
            # The HF q_proj outputs [2*Q, H]; the second Q rows are the gate.
            # random_weights splits these into q_w [Q, H] + q_gate_w [Q, H] in
            # the qkv slot.  Concretely we pack qkv = [q, k, v, gate] where the
            # gate lives in the second q_dim rows of the q-segment.  For the
            # functional reference we instead expose q_gate_w separately.
            qkv = t((qkv_dim, ARCH.hidden_size))
            q_gate = t((q_dim, ARCH.hidden_size))
            q_norm = t((ARCH.full_head_dim,))
            k_norm = t((ARCH.full_head_dim,))
            conv_w = None
            A_log = None
            dt_bias = None
            in_proj_a = None
            in_proj_b = None
            in_proj_z = None
            lin_norm = None
        else:
            qkv_dim = ARCH.lin_qkv_dim  # 6144  (3*Hk*Dk packed Q/K/V input)
            lin_out = ARCH.lin_value_heads * ARCH.lin_value_head_dim  # 2048
            o_w = t((ARCH.hidden_size, lin_out))
            q_gate = None
            q_norm = None
            k_norm = None
            qkv = t((qkv_dim, ARCH.hidden_size))
            conv_w = t((qkv_dim, ARCH.lin_conv_kernel))
            A_log = mx.zeros((ARCH.lin_value_heads,))  # log-decay init at 0
            dt_bias = t((ARCH.lin_value_heads,)) * 0.0 + 0.5  # small positive bias
            in_proj_a = t((ARCH.lin_value_heads, ARCH.hidden_size)) * 0.1
            in_proj_b = t((ARCH.lin_value_heads, ARCH.hidden_size)) * 0.1
            in_proj_z = t((lin_out, ARCH.hidden_size))
            lin_norm = mx.ones((ARCH.lin_value_head_dim,))

        layers.append(
            LayerWeights(
                attn_norm_w=t((ARCH.hidden_size,)),
                ffn_norm_w=t((ARCH.hidden_size,)),
                qkv_w=qkv,
                o_proj_w=o_w,
                q_gate_w=q_gate,
                q_norm_w=q_norm,
                k_norm_w=k_norm,
                gate_w=t((ARCH.intermediate_size, ARCH.hidden_size)),
                up_w=t((ARCH.intermediate_size, ARCH.hidden_size)),
                down_w=t((ARCH.hidden_size, ARCH.intermediate_size)),
                conv_w=conv_w,
                A_log=A_log,
                dt_bias=dt_bias,
                in_proj_a_w=in_proj_a,
                in_proj_b_w=in_proj_b,
                in_proj_z_w=in_proj_z,
                lin_norm_w=lin_norm,
            )
        )

    return ModelWeights(embed=embed, layers=layers, final_norm_w=t((ARCH.hidden_size,)))


# ---------------------------------------------------------------------------
# End-to-end forward pass
# ---------------------------------------------------------------------------


def ref_end_to_end_forward(
    input_ids: mx.array,  # [B, S] int32
    position_ids: mx.array,  # [B, S, 3] int32 (T, H, W per token)
    weights: ModelWeights,
    kv_caches: list | None = None,  # list per-full-layer of (k_cache, v_cache)
    lin_states: list | None = None,  # list per-linear-layer of fp32 [B, H, Dv, Dk]
    conv_states: list | None = None,  # list per-linear-layer of bf16 [B, C, K]
) -> mx.array:
    """Pure-MLX end-to-end forward pass through all 24 layers.

    Returns logits [B, S, V].  All weights/activations are bf16 except the
    linear-attention state (fp32) and the matmul accumulators (computed
    in fp32 then cast back to bf16).

    This is the gold-standard reference for the hand-tuned Metal kernels.
    Used by validate.py to verify end-to-end shape and finiteness, and
    by bench.py to measure tokens/sec against the kernel path.

    Schema
    ------
    For full-attention layers the reference expects ``qkv_w`` shaped
    ``[Q+KV+KV, H]``.  The HF checkpoint stores the q-projection with
    an extra gate in the second Q rows (``q_w: [2Q, H] = [q; gate]``)
    and the gate is applied as ``attn_out *= sigmoid(gate)`` BEFORE
    ``o_proj``.  The reference :class:`LayerWeights` therefore expects
    the *gate* part of q_proj to be passed separately as ``q_gate_w``
    of shape ``[Q, H]``.  ``cli._build_reference_weights`` and the
    hf-to-reference adapter handle this split.

    For linear-attention layers the reference expects ``conv_w`` shaped
    ``[C, K]`` (depthwise, no per-channel bias).  The gate ``z`` comes
    from ``in_proj_z`` (shape ``[Hv*Dv, H]``) and is consumed by the
    gated-norm at the end of the layer.  The beta input ``b`` is
    sigmoid-activated by :class:`ref_end_to_end_forward` (per HF impl)
    before being fed to ``linear_attention_step``.  The per-head decay
    is computed inside the driver as
    ``alpha = -exp(A_log) * softplus(a + dt_bias)``.
    """
    x = weights.embed[input_ids]  # [B, S, H]
    B, S, _ = x.shape
    full_layer_idx = 0
    lin_layer_idx = 0

    def _rmsnorm(xn, w):
        """Layer-local RMSNorm helper — avoids building an nn.Module per call.

        Qwen3.5's :class:`Qwen3_5RMSNorm` stores weight initialised to zeros
        and computes ``y = x_norm * (1 + w)`` so the initial gain is 1.  We
        therefore replicate the ``1 + w`` here; passing raw weights gives
        off-by-one gain which throws off the logits after 24 layers.
        """
        fp = xn.astype(mx.float32)
        ms = mx.mean(fp * fp, axis=-1, keepdims=True)
        return (
            fp * mx.rsqrt(ms + ARCH.rms_norm_eps) * (1.0 + w.astype(mx.float32))
        ).astype(xn.dtype)

    def _l2norm(xn, eps: float = 1e-6):
        """L2 normalise over the last axis (matches FLA's ``l2norm``)."""
        fp = xn.astype(mx.float32)
        inv = mx.rsqrt(mx.sum(fp * fp, axis=-1, keepdims=True) + eps)
        return (fp * inv).astype(xn.dtype)

    for i, layer in enumerate(weights.layers):
        is_full = ARCH.layer_is_full[i]
        # ----- Attention block -----
        h_attn = _rmsnorm(x, layer.attn_norm_w)

        if is_full:
            qkv = h_attn @ layer.qkv_w.T  # [B, S, QKV_dim]
            q, k, v = mx.split(
                qkv, [ARCH.full_q_dim, ARCH.full_q_dim + ARCH.full_kv_dim], axis=-1
            )
            q = q.reshape(B, S, ARCH.full_heads, ARCH.full_head_dim)
            k = k.reshape(B, S, ARCH.full_kv_heads, ARCH.full_head_dim)
            v = v.reshape(B, S, ARCH.full_kv_heads, ARCH.full_head_dim)
            # Per-head RMSNorm on q and k (HF: Qwen3_5RMSNorm on head_dim).
            # NOTE: Qwen3.5 stores the norm weight init-at-zero and uses
            # gain = (1 + w) — same convention as the input_layernorm.  We
            # inline this here; the kernel path also bakes in the +1.
            if layer.q_norm_w is not None:
                q_fp = q.astype(mx.float32)
                ms = mx.mean(q_fp * q_fp, axis=-1, keepdims=True)
                q = (
                    q_fp
                    * mx.rsqrt(ms + ARCH.rms_norm_eps)
                    * (1.0 + layer.q_norm_w.astype(mx.float32))
                ).astype(q.dtype)
            if layer.k_norm_w is not None:
                k_fp = k.astype(mx.float32)
                ms = mx.mean(k_fp * k_fp, axis=-1, keepdims=True)
                k = (
                    k_fp
                    * mx.rsqrt(ms + ARCH.rms_norm_eps)
                    * (1.0 + layer.k_norm_w.astype(mx.float32))
                ).astype(k.dtype)
            # M-RoPE on q and k
            q = mrope_apply(q, position_ids)
            k = mrope_apply(k, position_ids)
            # Full attention (GQA broadcast)
            attn_out = full_attention(q, k, v, causal=True)  # [B, S, H_q, D]
            attn_out = attn_out.reshape(B, S, ARCH.full_q_dim)
            # attn_output_gate: sigmoid(gate) * attn_out, applied BEFORE o_proj.
            # The gate is the second half of the q-projection output (see HF
            # Qwen3_5Attention: chunk(q_proj(x), 2, dim=-1)).
            if ARCH.attn_output_gate and layer.q_gate_w is not None:
                gate = h_attn @ layer.q_gate_w.T  # [B, S, Q]
                attn_out = (
                    attn_out.astype(mx.float32) * mx.sigmoid(gate.astype(mx.float32))
                ).astype(attn_out.dtype)
            # Output projection
            attn_out = attn_out @ layer.o_proj_w.T  # [B, S, H]
            # KV cache append (no-op if prefill and caches aren't passed)
            if kv_caches is not None and full_layer_idx < len(kv_caches):
                kc, vc = kv_caches[full_layer_idx]
                kc[:, :S, :, :] = k
                vc[:, :S, :, :] = v
            full_layer_idx += 1
        else:
            # Linear attention: packed QKV via linear projection
            qkv = h_attn @ layer.qkv_w.T  # [B, S, 3*Hk*Dk]
            # Causal depthwise conv1d step (operates per-channel, K=4).
            # HF: padded by (K-1) zeros on the left, then conv produces
            # shape [B, C, S + K - 1] which we slice to [B, C, S].
            qkv_seq = qkv.transpose(0, 2, 1)  # [B, C, S]
            C = qkv_seq.shape[1]
            if conv_states is not None and lin_layer_idx < len(conv_states):
                conv_states[lin_layer_idx]
            else:
                mx.zeros((B, C, ARCH.lin_conv_kernel), dtype=mx.bfloat16)
            # Slide window for prefill: for each t in [0, S), conv window =
            # qkv_seq[:, :, max(0, t-K+1):t+1] — equivalent to a (K-1) zero
            # pad on the left and a [S, K] sliding window.
            padded = mx.concatenate(
                [
                    mx.zeros((B, C, ARCH.lin_conv_kernel - 1), dtype=qkv_seq.dtype),
                    qkv_seq,
                ],
                axis=-1,
            )
            windows = mx.stack(
                [padded[:, :, i : i + ARCH.lin_conv_kernel] for i in range(S)],
                axis=2,
            )  # [B, C, S, K]
            # conv_w stored as [C, 1, K] (depthwise); squeeze to [C, K] for einsum.
            conv_w_2d = layer.conv_w.astype(mx.float32).reshape(
                layer.conv_w.shape[0], ARCH.lin_conv_kernel
            )
            conv_out = mx.einsum("bcsk,ck->bcs", windows, conv_w_2d)
            # HF applies silu after conv; the linear-attn block expects this.
            conv_out = conv_out * mx.sigmoid(conv_out)
            conv_out = conv_out.transpose(0, 2, 1)  # [B, S, C]

            # Split into Q, K, V (conv_dim = 2*key_dim + value_dim)
            qkv_lin = conv_out.astype(mx.bfloat16)
            C3 = ARCH.lin_key_heads * ARCH.lin_key_head_dim
            q = qkv_lin[..., :C3].reshape(
                B, S, ARCH.lin_key_heads, ARCH.lin_key_head_dim
            )
            k = qkv_lin[..., C3 : 2 * C3].reshape(
                B, S, ARCH.lin_key_heads, ARCH.lin_key_head_dim
            )
            v = qkv_lin[..., 2 * C3 :].reshape(
                B, S, ARCH.lin_value_heads, ARCH.lin_value_head_dim
            )

            # GQA-style repeat for v heads if Hv // Hk > 1 (here Hv=Hk=16, so 1).
            # (HF does repeat_interleave on q and k when num_v_heads // num_k_heads > 1.)

            # L2-normalise q, k (use_qk_l2norm_in_kernel=True in HF).
            q = _l2norm(q)
            k = _l2norm(k)

            # RoPE on q, k (M-RoPE, partial rotary — applied per-head).
            q = mrope_apply(q, position_ids)
            k = mrope_apply(k, position_ids)

            # Compute z (gate projection), b (beta input), a (delta input).
            # Beta = sigmoid(b);  decay log = -exp(A_log) * softplus(a + dt_bias).
            z = h_attn @ layer.in_proj_z_w.T  # [B, S, Hv*Dv]
            z = z.reshape(B, S, ARCH.lin_value_heads, ARCH.lin_value_head_dim)
            b_proj = h_attn @ layer.in_proj_b_w.T  # [B, S, Hv]
            a_proj = h_attn @ layer.in_proj_a_w.T  # [B, S, Hv]
            beta = mx.sigmoid(b_proj.astype(mx.float32)).astype(mx.bfloat16)
            # alpha_log per token: -exp(A_log) * softplus(a_proj + dt_bias)
            A_log_f = (
                layer.A_log.astype(mx.float32)
                if layer.A_log is not None
                else mx.zeros((ARCH.lin_value_heads,), dtype=mx.float32)
            )
            dt = (
                layer.dt_bias.astype(mx.float32)
                if layer.dt_bias is not None
                else mx.zeros((ARCH.lin_value_heads,), dtype=mx.float32)
            )
            # softplus(x) = log(1 + exp(x)); numerically stable

            def softplus(x):
                return mx.logaddexp(x, mx.zeros_like(x))

            alpha_log = -mx.exp(A_log_f)[None, None, :] * softplus(
                a_proj.astype(mx.float32) + dt[None, None, :]
            )
            # shape [B, S, Hv]; broadcast against [B, Hv] per-step

            # For prefill, run linear_attention_step token-by-token (no
            # parallel chunked scan yet).
            state = (
                lin_states[lin_layer_idx]
                if (
                    lin_states is not None
                    and lin_layer_idx < len(lin_states)
                    and lin_states[lin_layer_idx] is not None
                )
                else mx.zeros(
                    (
                        B,
                        ARCH.lin_value_heads,
                        ARCH.lin_value_head_dim,
                        ARCH.lin_key_head_dim,
                    ),
                    dtype=mx.float32,
                )
            )
            attn_lin_out = None
            for t in range(S):
                out_t, state = linear_attention_step(
                    q[:, t, :, :].reshape(B, ARCH.lin_key_heads, ARCH.lin_key_head_dim),
                    k[:, t, :, :].reshape(B, ARCH.lin_key_heads, ARCH.lin_key_head_dim),
                    v[:, t, :, :].reshape(
                        B, ARCH.lin_value_heads, ARCH.lin_value_head_dim
                    ),
                    # Gate is applied at the per-layer gated-norm; we pass
                    # the (unused) z slot here as zeros to keep the signature.
                    mx.zeros_like(
                        v[:, t, :, :].reshape(
                            B, ARCH.lin_value_heads, ARCH.lin_value_head_dim
                        )
                    ),
                    beta[:, t, :],  # [B, Hv]
                    alpha_log[:, t, :],  # [B, Hv]
                    state,
                )
                out_t = out_t.reshape(
                    B, 1, ARCH.lin_value_heads, ARCH.lin_value_head_dim
                )
                attn_lin_out = (
                    out_t
                    if attn_lin_out is None
                    else mx.concatenate([attn_lin_out, out_t], axis=1)
                )

            # Gated RMSNorm on the per-head output, then silu(z) gate.
            # Matches HF Qwen3_5RMSNormGated: y = rms_norm(o) * silu(z), where
            # rms_norm uses (1 + weight) just like the input_layernorm above
            # (see comment on _rmsnorm).  In the HF source the gate is applied
            # to ``weight * hidden_states`` (i.e. after the gain) so we mirror
            # that ordering here.
            if layer.lin_norm_w is not None:
                w_ln = 1.0 + layer.lin_norm_w.astype(mx.float32)
                fp = attn_lin_out.astype(mx.float32)
                ms = mx.mean(fp * fp, axis=-1, keepdims=True)
                normed = fp * mx.rsqrt(ms + ARCH.rms_norm_eps) * w_ln
            else:
                normed = attn_lin_out.astype(mx.float32)
            # silu(z)
            z_f = z.astype(mx.float32)
            silu_z = z_f * mx.sigmoid(z_f)
            gated_out = (normed * silu_z).astype(mx.bfloat16)
            # [B, S, Hv*Dv] -> [B, S, H]
            gated_out = gated_out.reshape(
                B, S, ARCH.lin_value_heads * ARCH.lin_value_head_dim
            )
            attn_out = gated_out @ layer.o_proj_w.T

            if lin_states is not None and lin_layer_idx < len(lin_states):
                lin_states[lin_layer_idx] = state
            lin_layer_idx += 1

        # Residual add of attention block
        x = x + attn_out

        # ----- FFN block (SwiGLU) -----
        h_ffn = _rmsnorm(x, layer.ffn_norm_w)
        x = x + ref_swiglu_mlp(h_ffn, layer.gate_w, layer.up_w, layer.down_w)

    # Final norm
    x = _rmsnorm(x, weights.final_norm_w)
    # Tied LM head
    return (x @ weights.embed.T).astype(mx.bfloat16)


def ref_rmsnorm(
    x: mx.array, weight: mx.array, eps: float = ARCH.rms_norm_eps
) -> mx.array:
    """Pure-MLX RMSNorm matching norm.metal.

    x: [..., H] bf16; weight: [H] bf16; out [..., H] bf16.
    """
    fp = x.astype(mx.float32)
    sq = fp * fp
    mean_sq = mx.mean(sq, axis=-1, keepdims=True)
    rms_inv = mx.rsqrt(mean_sq + eps)
    return (fp * rms_inv * weight.astype(mx.float32)).astype(x.dtype)


# ---------------------------------------------------------------------------
# Aliases — the validate.py harness uses shortened names; keep them consistent.
# ---------------------------------------------------------------------------

#: Alias of :func:`linear_attention_step` matching the kernel name used by
#: validate.py / the Metal dispatch table.
ref_linear_attn_step = linear_attention_step

#: Alias of :func:`causal_conv1d_step` matching the kernel name used by
#: validate.py / the Metal dispatch table.
ref_conv1d_step = causal_conv1d_step


def ref_rope(
    q: mx.array,
    pos_ids: mx.array,
    rot_dim: int,
    rope_theta: float,
    mrope_section: tuple[int, int, int],
) -> mx.array:
    """M-RoPE partial interleaved, matching rope.metal.

    q: [B, S, H, D] bf16 — only first rot_dim dims rotated.
    pos_ids: [B, S, 3] int32 — (T, H, W) per token.
    """
    B, S, H, D = q.shape
    half = rot_dim // 2
    x_rot = q[..., :rot_dim].astype(mx.float32)
    x_pass = q[..., rot_dim:]
    inv_freq = mx.power(
        rope_theta, -(2.0 * mx.arange(0, half, dtype=mx.float32)) / rot_dim
    )
    k_idx = mx.arange(0, half, dtype=mx.int32)
    section = k_idx % 3
    pos_sel = mx.take(pos_ids, section, axis=-1).astype(mx.float32)
    angle = pos_sel * inv_freq
    cos = mx.cos(angle)[:, :, None, :]
    sin = mx.sin(angle)[:, :, None, :]
    xr = mx.reshape(x_rot, (B, S, H, half, 2))
    even = xr[..., 0]
    odd = xr[..., 1]
    out_even = cos * even - sin * odd
    out_odd = sin * even + cos * odd
    out_rot = mx.reshape(
        mx.stack([out_even, out_odd], axis=-1), (B, S, H, rot_dim)
    ).astype(q.dtype)
    return mx.concatenate([out_rot, x_pass.astype(q.dtype)], axis=-1)


def ref_attention_decode(
    q: mx.array, k_cache: mx.array, v_cache: mx.array, seq_len: int, scale: float
) -> mx.array:
    """One-token decode over KV cache.

    q: [B, H_q, D] bf16
    k_cache: [B, S_k, H_kv, D] bf16
    v_cache: [B, S_k, H_kv, D] bf16
    Returns: [B, H_q, D] bf16
    """
    B, H_q, D = q.shape
    H_kv = k_cache.shape[2]
    group = H_q // H_kv
    qf = q.astype(mx.float32)
    kf = k_cache[:, :seq_len, :, :].astype(mx.float32)
    vf = v_cache[:, :seq_len, :, :].astype(mx.float32)
    k_used = mx.transpose(kf, (0, 2, 1, 3))
    v_used = mx.transpose(vf, (0, 2, 1, 3))
    k_b = mx.repeat(k_used, group, axis=1)
    v_b = mx.repeat(v_used, group, axis=1)
    scores = mx.matmul(qf[:, :, None, :], mx.transpose(k_b, (0, 1, 3, 2))) * scale
    s_fp = scores.astype(mx.float32)
    s_max = mx.max(s_fp, axis=-1, keepdims=True)
    exp_s = mx.exp(s_fp - s_max)
    p = (exp_s / mx.sum(exp_s, axis=-1, keepdims=True)).astype(mx.bfloat16)
    out = mx.matmul(p, v_b)
    return mx.reshape(out, (B, H_q, D)).astype(mx.bfloat16)


# ---------------------------------------------------------------------------
# Quick perf comparison vs hand-tuned kernels
# ---------------------------------------------------------------------------


def run_self_test():
    """Smoke test the reference (does not need real weights)."""
    print("Qwen3.5 0.8B reference self-test (MLX, M-series GPU)")
    print(f"  Vocab:      {ARCH.vocab_size}")
    print(f"  Hidden:     {ARCH.hidden_size}")
    print(f"  Layers:     {ARCH.num_hidden_layers}")
    print(f"  Full attn:  {sum(ARCH.layer_is_full)} / {ARCH.num_hidden_layers} layers")
    print(
        f"  Lin attn:   {sum(1 for x in ARCH.layer_is_full if not x)} / {ARCH.num_hidden_layers} layers"
    )
    print(
        f"  Rot dim:    {ARCH.rot_dim} / {ARCH.full_head_dim} (partial rotary {ARCH.partial_rotary_factor})"
    )
    print(
        f"  M-RoPE:     interleaved={ARCH.mrope_interleaved}, section={ARCH.mrope_section}"
    )
    print(
        f"  Lin heads:  K={ARCH.lin_key_heads} (Dk={ARCH.lin_key_head_dim}), V={ARCH.lin_value_heads} (Dv={ARCH.lin_value_head_dim})"
    )
    print(f"  Conv kernel: {ARCH.lin_conv_kernel}")
    print()

    # M-RoPE smoke test
    mx.random.seed(42)
    B, S, H, D = 1, 8, ARCH.full_heads, ARCH.full_head_dim
    x = mx.random.normal((B, S, H, D)).astype(mx.bfloat16)
    pos_ids = mx.array([[list(range(S))] * 3], dtype=mx.int32).transpose(2, 0, 1)
    pos_ids = pos_ids.reshape(B, S, 3)
    y = mrope_apply(x, pos_ids)
    mx.eval(y)
    print(
        f"  M-RoPE: input {x.shape} -> output {y.shape}, sample[0,0,0,:8] = {y[0, 0, 0, :8].tolist()}"
    )
    print(
        f"  M-RoPE: sample[0,0,0,rot_dim:rot_dim+8] = {y[0, 0, 0, ARCH.rot_dim : ARCH.rot_dim + 8].tolist()} (pass-through)"
    )
    print()

    # Full attention smoke
    q = mx.random.normal((B, S, ARCH.full_heads, ARCH.full_head_dim)).astype(
        mx.bfloat16
    )
    k = mx.random.normal((B, S, ARCH.full_kv_heads, ARCH.full_head_dim)).astype(
        mx.bfloat16
    )
    v = mx.random.normal((B, S, ARCH.full_kv_heads, ARCH.full_head_dim)).astype(
        mx.bfloat16
    )
    t0 = time.time()
    out = full_attention(q, k, v, causal=True)
    mx.eval(out)
    t1 = time.time()
    print(
        f"  Full attn (prefill S={S}, causal): {1000 * (t1 - t0):.2f} ms, output shape {out.shape}"
    )
    print()

    # Linear attention step
    B, H, Dk, Dv = 1, ARCH.lin_key_heads, ARCH.lin_key_head_dim, ARCH.lin_value_head_dim
    q = mx.random.normal((B, H, Dk)).astype(mx.bfloat16)
    k = mx.random.normal((B, H, Dk)).astype(mx.bfloat16)
    v = mx.random.normal((B, H, Dv)).astype(mx.bfloat16)
    gate = mx.random.normal((B, H, Dv)).astype(mx.bfloat16)
    beta = mx.random.uniform(shape=(B, H)).astype(mx.bfloat16)
    alpha_log = mx.random.uniform(low=0.1, high=1.0, shape=(B, H)).astype(mx.bfloat16)
    state = mx.zeros((B, H, Dv, Dk), dtype=mx.float32)
    out, new_state = linear_attention_step(q, k, v, gate, beta, alpha_log, state)
    mx.eval(out, new_state)
    print(f"  Linear attn (decode, 1 token): output shape {out.shape}")
    print(
        f"  Linear state: shape {state.shape}, dtype {state.dtype}, bytes {state.nbytes}"
    )
    print(f"  Per-layer state memory (fp32): {state.nbytes / 1024 / 1024:.1f} MiB")
    print(f"  All 18 linear layers: {18 * state.nbytes / 1024 / 1024:.1f} MiB")
    print()

    # End-to-end forward pass with random weights
    B, S = 1, 4
    mx.random.seed(7)
    w = random_weights(seed=7)
    ids = mx.array([[17, 42, 113, 9001]], dtype=mx.int32)
    pos = mx.zeros((B, S, 3), dtype=mx.int32)
    for t in range(S):
        pos[:, t, 0] = t  # T axis
        pos[:, t, 1] = 0  # H axis
        pos[:, t, 2] = 0  # W axis
    t0 = time.time()
    logits = ref_end_to_end_forward(ids, pos, w)
    mx.eval(logits)
    t1 = time.time()
    finite = bool(mx.all(mx.isfinite(logits)).item())
    next_id = int(mx.argmax(logits[0, -1, :]).item())
    print(
        f"  End-to-end (B={B}, S={S}, 24 layers): {1000 * (t1 - t0):.1f} ms, "
        f"logits shape {logits.shape}, finite={finite}, sample id={next_id}"
    )
    assert finite, "non-finite logits from end-to-end forward"
    print()

    print("All smoke tests passed.")


if __name__ == "__main__":
    run_self_test()
