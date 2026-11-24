"""
hf_loader.py — Load Qwen3.5 0.8B from HuggingFace safetensors into the
internal :class:`ModelWeightsHF` schema used by :mod:`reference`.

The HuggingFace parameter naming for the hybrid Qwen3.5 0.8B *text* path
(we ignore vision tower and MTP)::

  # Embeddings + final norm
  model.language_model.embed_tokens.weight           [V, H]   bf16
  model.language_model.norm.weight                   [H]      bf16

  # Per-layer (i = 0..23)
  model.language_model.layers.{i}.input_layernorm.weight            [H]   bf16  (attn pre-norm)
  model.language_model.layers.{i}.post_attention_layernorm.weight   [H]   bf16  (ffn pre-norm)

  # Full-attention layers (i in {3, 7, 11, 15, 19, 23})
  model.language_model.layers.{i}.self_attn.q_proj.weight           [2Q, H]     bf16
    # ^ doubled because attn_output_gate=true: first Q dims are q, next Q dims are gate
  model.language_model.layers.{i}.self_attn.k_proj.weight           [KV, H]    bf16
  model.language_model.layers.{i}.self_attn.v_proj.weight           [KV, H]    bf16
  model.language_model.layers.{i}.self_attn.o_proj.weight           [H, Q]     bf16
  model.language_model.layers.{i}.self_attn.q_norm.weight           [D]        bf16  (per-head)
  model.language_model.layers.{i}.self_attn.k_norm.weight           [D]        bf16

  # Linear-attention (GatedDeltaNet) layers (the other 18)
  model.language_model.layers.{i}.linear_attn.in_proj_qkv.weight    [3*Hk*Dk, H]  bf16
  model.language_model.layers.{i}.linear_attn.in_proj_z.weight      [Hv*Dv, H]    bf16  (gate)
  model.language_model.layers.{i}.linear_attn.in_proj_a.weight      [Hv, H]       bf16  (delta input)
  model.language_model.layers.{i}.linear_attn.in_proj_b.weight      [Hv, H]       bf16  (beta input)
  model.language_model.layers.{i}.linear_attn.conv1d.weight         [C, 1, K]     bf16
  model.language_model.layers.{i}.linear_attn.A_log                 [Hv]          f32   (decay)
  model.language_model.layers.{i}.linear_attn.dt_bias               [Hv]          bf16  (delta bias)
  model.language_model.layers.{i}.linear_attn.out_proj.weight       [H, Hv*Dv]    bf16
  model.language_model.layers.{i}.linear_attn.norm.weight           [Hv*Dv]       f32   (per-head RMSNorm on out)

  # FFN (both kinds of layers)
  model.language_model.layers.{i}.mlp.gate_proj.weight              [I, H]        bf16
  model.language_model.layers.{i}.mlp.up_proj.weight                [I, H]        bf16
  model.language_model.layers.{i}.mlp.down_proj.weight              [H, I]        bf16

Tied embedding: when ``tie_word_embeddings=True`` the embed table is
reused as the LM head (no separate ``lm_head.weight`` in the safetensors).

Design notes
------------

We avoid ``safetensors.safe_open`` because:

* It relies on numpy's bfloat16 dtype, which is only available in numpy
  2.0+; on some Apple-bundled Pythons the dtype is missing or broken.
* It triggers a materialise-then-reinterpret path that loses the bf16
  byte pattern when round-tripping through mlx.core (we hit this in
  practice — see ``reference.py`` notes on the broken ``__array__``
  protocol for bfloat16).

Instead we implement a thin raw-byte reader that:

* Parses the safetensors header (8-byte little-endian length followed
  by a JSON dictionary of ``{name: {dtype, shape, data_offsets}}``).
* For each requested tensor, ``seek`` + ``read`` the exact byte slice
  and convert the dtype by hand.  bf16 raw bytes are mapped to a
  ``np.uint16`` view (memory-exact, no conversion), or to an
  ``mlx.core.bfloat16`` array via the fp32 zero-pad-and-cast trick
  (works on every numpy/mlx version we have shipped on Apple Silicon).

The returned tensors are ``mlx.core.array`` for hot-path consumers
(``reference.py``) and the manifest dict carries shape/dtype metadata
for inspection / serialization.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Architecture constants — must match arch.yaml and reference.QwenArch
# ---------------------------------------------------------------------------

ARCH_DEFAULTS = {
    "vocab_size": 248_320,
    "hidden_size": 1024,
    "intermediate_size": 3584,
    "num_hidden_layers": 24,
    "full_heads": 8,
    "full_kv_heads": 2,
    "full_head_dim": 256,
    "full_attention_interval": 4,
    "lin_key_heads": 16,
    "lin_value_heads": 16,
    "lin_key_head_dim": 128,
    "lin_value_head_dim": 128,
    "lin_conv_kernel": 4,
    "rms_norm_eps": 1.0e-6,
    "rope_theta": 10_000_000.0,
    "mrope_section": (11, 11, 10),
    "tie_word_embeddings": True,
    "attn_output_gate": True,
}


# ---------------------------------------------------------------------------
# Loaded-weight dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LayerWeightsHF:
    """Per-layer weights loaded from HuggingFace safetensors.

    All tensors are ``mlx.core.array`` (bf16 or f32 as appropriate). Shapes
    match the model architecture in :data:`ARCH_DEFAULTS`. The schema is
    the union of parameters needed by ``reference.py`` and the kernel
    engine's ``layer_weights`` blob.
    """

    # Common to every layer
    attn_norm_w: object = None  # [H]       bf16   (input_layernorm)
    ffn_norm_w: object = None  # [H]       bf16   (post_attention_layernorm)

    # Full attention: q is concatenated with the gate in the q_proj output
    # (first Q dims = q, next Q dims = gate; see attn_output_gate).
    q_w: object = None  # [2Q, H]   bf16   full only — already q+gate packed
    k_w: object = None  # [KV, H]   bf16   full only
    v_w: object = None  # [KV, H]   bf16   full only
    o_w: object = None  # [H, Q]    bf16   full: [H, Q]; linear: [H, Hv*Dv]
    q_norm_w: object = None  # [D]       bf16   full only  (per-head RMSNorm)
    k_norm_w: object = None  # [D]       bf16   full only

    # Linear attention (GatedDeltaNet / Qwen3_5Next)
    in_proj_qkv: object = None  # [3*Hk*Dk, H] bf16
    in_proj_z: object = None  # [Hv*Dv, H]   bf16   (silu gate)
    in_proj_a: object = None  # [Hv, H]      bf16   (delta input)
    in_proj_b: object = None  # [Hv, H]      bf16   (beta input)
    conv1d_w: object = None  # [C, 1, K]    bf16   depthwise conv kernel
    A_log: object = None  # [Hv]         f32    (decay parameter)
    dt_bias: object = None  # [Hv]         bf16   (delta bias)
    lin_norm_w: object = None  # [Hv*Dv]      f32    (per-head RMSNorm on out)

    # FFN (SwiGLU) — identical for both layer types
    gate_w: object = None  # [I, H] bf16
    up_w: object = None  # [I, H] bf16
    down_w: object = None  # [H, I] bf16


@dataclass
class ModelWeightsHF:
    """Top-level model weights loaded from HuggingFace safetensors.

    Attributes
    ----------
    embed : [V, H] bf16
        Token embedding table (also used as LM head, since
        tie_word_embeddings=True).
    layers : list[LayerWeightsHF]
        24 layer weight blocks in the canonical order (0..23).
    final_norm_w : [H] bf16
        Final RMSNorm before the LM head.
    arch : dict
        Architecture constants (subset of arch.yaml), for downstream
        consumers.
    manifest : dict
        Per-tensor shape / dtype / source-shard metadata, kept for
        debugging and serialization.
    """

    embed: object
    layers: list
    final_norm_w: object
    arch: dict
    manifest: dict = field(default_factory=dict)

    def __post_init__(self):
        if len(self.layers) != ARCH_DEFAULTS["num_hidden_layers"]:
            raise ValueError(
                f"expected {ARCH_DEFAULTS['num_hidden_layers']} layers, "
                f"got {len(self.layers)}"
            )


# ---------------------------------------------------------------------------
# Schedule helper
# ---------------------------------------------------------------------------


def _is_full_layer(layer_idx: int) -> bool:
    """Schedule: every (full_attention_interval)th layer is full attention.

    Layer indices 3, 7, 11, 15, 19, 23 are full attention; the rest are
    linear (GatedDeltaNet).  This matches both the HF
    ``text_config.layer_types`` array and the kernel-suite arch.yaml.
    """
    return (layer_idx + 1) % ARCH_DEFAULTS["full_attention_interval"] == 0


# ---------------------------------------------------------------------------
# Raw safetensors reader — works on every Python / numpy / mlx version
# ---------------------------------------------------------------------------

_NUMPY_DTYPE_FOR_SAFETENSORS = {
    "BF16": np.uint16,  # bf16 raw bits reinterpreted as uint16
    "F16": np.float16,
    "F32": np.float32,
    "F64": np.float64,
    "I8": np.int8,
    "I16": np.int16,
    "I32": np.int32,
    "I64": np.int64,
    "U8": np.uint8,
    "BOOL": np.bool_,
}


class _SafetensorsRawReader:
    """Open a safetensors shard and yield raw bytes per tensor.

    The returned numpy array for a bf16 tensor is a ``np.uint16`` view of
    the on-disk bf16 bytes — memory-exact, no conversion.  For f32 it is
    a ``np.float32`` view of the f32 bytes.  This avoids the numpy bf16
    dtype (not always available) entirely.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        with open(self.path, "rb") as f:
            header_len_bytes = f.read(8)
            if len(header_len_bytes) != 8:
                raise ValueError(f"{self.path}: not a safetensors file")
            (header_len,) = struct.unpack("<Q", header_len_bytes)
            header_text = f.read(header_len).decode("utf-8")
            self.header = json.loads(header_text)
            self._data_offset = 8 + header_len
        self._fh = None  # lazy

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __del__(self):
        self.close()

    def names(self) -> list:
        """List of all tensor names in the shard."""
        return list(self.header.keys())

    def info(self, name: str) -> dict:
        """Return the header metadata for a single tensor."""
        if name not in self.header:
            raise KeyError(f"{name!r} not in {self.path.name}")
        return self.header[name]

    def read_raw(self, name: str) -> tuple[bytes, dict]:
        """Read raw bytes + metadata for a tensor. Returns ``(bytes, info)``."""
        if self._fh is None:
            self._fh = open(self.path, "rb")
        info = self.info(name)
        offsets = info["data_offsets"]
        nbytes = offsets[1] - offsets[0]
        self._fh.seek(self._data_offset + offsets[0])
        raw = self._fh.read(nbytes)
        return raw, info

    def read_np(self, name: str) -> np.ndarray:
        """Read a tensor as a numpy ndarray with the natural dtype.

        bf16 → ``np.uint16`` (raw bit pattern, no conversion)
        f32  → ``np.float32``
        f16  → ``np.float16``
        etc.

        The returned array is a view of bytes freshly ``read()`` from
        disk; callers must not rely on the bytes after the next
        ``read_np`` call (we work around this by copying on ingest in
        :func:`load_hf_weights`).
        """
        raw, info = self.read_raw(name)
        dtype_str = info["dtype"]
        if dtype_str not in _NUMPY_DTYPE_FOR_SAFETENSORS:
            raise ValueError(
                f"unsupported safetensors dtype {dtype_str!r} for tensor {name!r}"
            )
        np_dtype = _NUMPY_DTYPE_FOR_SAFETENSORS[dtype_str]
        shape = tuple(info["shape"])
        # Make a writable copy so the caller can free the original bytes
        # by letting `raw` go out of scope.
        arr = np.frombuffer(raw, dtype=np_dtype).reshape(shape).copy()
        return arr


# ---------------------------------------------------------------------------
# bf16/f32 → mlx.core.array conversion
# ---------------------------------------------------------------------------


def _to_mx(np_arr: np.ndarray, *, dtype_hint: str | None = None):
    """Convert a numpy array to an ``mlx.core.array``.

    The safetensors file gives us bf16 raw bits stored as ``np.uint16``.
    We can't pass that to ``mx.array`` directly — it would treat the
    ``uint16`` values as small integers, not as bf16 bit patterns.  The
    portable conversion is to pad the bf16 bits into the high 16 bits
    of an fp32, then ``mx.array().astype(mx.bfloat16)``.  This works on
    every numpy version we ship (numpy 2.0+ is not required).

    For f32 / f16 / i32 tensors we delegate to ``mx.array`` directly.
    """
    try:
        import mlx.core as mx
    except ImportError:
        return np_arr

    if np_arr.dtype == np.uint16 and (dtype_hint in (None, "BF16")):
        # bf16 raw bits → fp32 with bits in the high 16 → mx.bfloat16.
        # fp32 byte layout (LE) is [b0 b1 b2 b3]; the bf16 value lives
        # in b2+b3 so we zero-pad b0+b1.
        n = int(np_arr.size)
        flat = np_arr.reshape(n)
        fp32_u8 = np.zeros((n, 4), dtype=np.uint8)
        bf16_u8 = flat.view(np.uint8).reshape(n, 2)
        fp32_u8[:, 2] = bf16_u8[:, 0]
        fp32_u8[:, 3] = bf16_u8[:, 1]
        fp32 = fp32_u8.view(np.float32).reshape(np_arr.shape)
        arr = mx.array(np.ascontiguousarray(fp32))
        arr = arr.astype(mx.bfloat16)
        return arr

    return mx.array(np.ascontiguousarray(np_arr))


# ---------------------------------------------------------------------------
# Tokenizer (no transformers dep)
# ---------------------------------------------------------------------------


def load_hf_tokenizer(hf_dir: str | Path):
    """Load the Qwen3.5 BPE tokenizer from a HF directory.

    Requires the ``tokenizers`` library (>=0.15). The HF directory must
    contain ``tokenizer.json`` (the fast-tokenizer serialization).

    Returns
    -------
    tokenizers.Tokenizer
    """
    from tokenizers import Tokenizer

    hf_dir = Path(hf_dir)
    tok_path = hf_dir / "tokenizer.json"
    if not tok_path.exists():
        raise FileNotFoundError(f"no tokenizer.json at {tok_path}")
    return Tokenizer.from_file(str(tok_path))


# ---------------------------------------------------------------------------
# Shard discovery
# ---------------------------------------------------------------------------


def _find_safetensors(hf_dir: Path) -> list:
    """Return the list of safetensors shard files for the model.

    Honours ``model.safetensors.index.json`` if present, otherwise globs
    ``model*.safetensors`` in the directory.
    """
    idx = hf_dir / "model.safetensors.index.json"
    if idx.exists():
        try:
            weight_map = json.loads(idx.read_text())["weight_map"]
            shards = sorted(set(weight_map.values()))
            return [hf_dir / s for s in shards]
        except (KeyError, json.JSONDecodeError):
            pass
    return sorted(hf_dir.glob("model*.safetensors"))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

# Tensor-name filter: only language-model parameters are loaded.  Vision
# tower and MTP have different prefixes and are skipped.
_LM_PREFIX = "model.language_model."


def load_hf_weights(
    hf_dir: str | Path,
    *,
    prefer_mlx: bool = True,
    verbose: bool = False,
) -> ModelWeightsHF:
    """Load Qwen3.5 0.8B language-model weights from a HF safetensors dir.

    Parameters
    ----------
    hf_dir : str or Path
        Path to a directory containing ``model.safetensors`` (or shard
        index) and the architecture ``config.json``.
    prefer_mlx : bool
        If True, return ``mlx.core.array`` tensors; otherwise return
        ``numpy.ndarray`` (faster load, no Metal device required).
        Numpy bf16 tensors are stored as ``np.uint16`` (raw bits) since
        the numpy bf16 dtype is not portable across all installs we
        support.
    verbose : bool
        Print progress / shape stats as we go.

    Returns
    -------
    ModelWeightsHF
    """
    hf_dir = Path(hf_dir)
    if not hf_dir.is_dir():
        raise FileNotFoundError(f"hf_dir not found: {hf_dir}")
    shards = _find_safetensors(hf_dir)
    if not shards:
        raise FileNotFoundError(f"no model*.safetensors found in {hf_dir}")

    # Optional arch validation against config.json
    cfg_path = hf_dir / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        text_cfg = cfg.get("text_config", cfg)
        mismatches = []
        for k, v in ARCH_DEFAULTS.items():
            if k in ("mrope_section", "tie_word_embeddings"):
                continue  # handled below
            hf_v = text_cfg.get(k)
            if hf_v is not None and hf_v != v:
                mismatches.append(f"{k}: arch={v} hf={hf_v}")
        if text_cfg.get("tie_word_embeddings") != ARCH_DEFAULTS["tie_word_embeddings"]:
            mismatches.append("tie_word_embeddings mismatch")
        hf_section = tuple(text_cfg.get("rope_parameters", {}).get("mrope_section", ()))
        if hf_section and hf_section != ARCH_DEFAULTS["mrope_section"]:
            mismatches.append(
                f"mrope_section: arch={ARCH_DEFAULTS['mrope_section']} hf={hf_section}"
            )
        if mismatches:
            raise ValueError(
                "config.json / arch.yaml mismatch:\n  - " + "\n  - ".join(mismatches)
            )

    # Per-layer dispatch tables: which sub-key on LayerWeightsHF to fill
    full_dispatch = {
        "self_attn.q_proj.weight": "q_w",
        "self_attn.k_proj.weight": "k_w",
        "self_attn.v_proj.weight": "v_w",
        "self_attn.o_proj.weight": "o_w",
        "self_attn.q_norm.weight": "q_norm_w",
        "self_attn.k_norm.weight": "k_norm_w",
    }
    linear_dispatch = {
        "linear_attn.in_proj_qkv.weight": "in_proj_qkv",
        "linear_attn.in_proj_z.weight": "in_proj_z",
        "linear_attn.in_proj_a.weight": "in_proj_a",
        "linear_attn.in_proj_b.weight": "in_proj_b",
        "linear_attn.conv1d.weight": "conv1d_w",
        "linear_attn.A_log": "A_log",
        "linear_attn.dt_bias": "dt_bias",
        "linear_attn.out_proj.weight": "o_w",
        "linear_attn.norm.weight": "lin_norm_w",
    }
    common_dispatch = {
        "input_layernorm.weight": "attn_norm_w",
        "post_attention_layernorm.weight": "ffn_norm_w",
        "mlp.gate_proj.weight": "gate_w",
        "mlp.up_proj.weight": "up_w",
        "mlp.down_proj.weight": "down_w",
    }

    # Pre-allocate the per-layer list with None placeholders.
    layers = [None] * ARCH_DEFAULTS["num_hidden_layers"]
    embed = None
    final_norm_w = None

    manifest = {
        "shards": [str(p) for p in shards],
        "tensors": {},
    }

    seen = 0
    skipped = 0
    for shard_idx, shard_path in enumerate(shards):
        if verbose:
            print(
                f"[hf_loader] opening shard {shard_idx + 1}/{len(shards)}: "
                f"{shard_path.name}",
                flush=True,
            )
        with _SafetensorsRawReader(shard_path) as reader:
            for name in reader.names():
                if not name.startswith(_LM_PREFIX):
                    skipped += 1
                    continue
                tail = name[len(_LM_PREFIX) :]  # e.g. "embed_tokens.weight"
                parts = tail.split(".")

                # Top-level embedding / final norm
                if (
                    len(parts) == 2
                    and parts[0] == "embed_tokens"
                    and parts[1] == "weight"
                ):
                    np_arr = reader.read_np(name)
                    embed = (
                        _to_mx(np_arr, dtype_hint=reader.info(name)["dtype"])
                        if prefer_mlx
                        else np_arr
                    )
                    seen += 1
                    manifest["tensors"][name] = {
                        "shape": list(np_arr.shape),
                        "dtype": reader.info(name)["dtype"],
                        "shard": str(shard_path),
                    }
                    continue
                if len(parts) == 2 and parts[0] == "norm" and parts[1] == "weight":
                    np_arr = reader.read_np(name)
                    final_norm_w = (
                        _to_mx(np_arr, dtype_hint=reader.info(name)["dtype"])
                        if prefer_mlx
                        else np_arr
                    )
                    seen += 1
                    manifest["tensors"][name] = {
                        "shape": list(np_arr.shape),
                        "dtype": reader.info(name)["dtype"],
                        "shard": str(shard_path),
                    }
                    continue

                # Per-layer tensor
                if len(parts) < 4 or parts[0] != "layers":
                    skipped += 1
                    continue
                try:
                    layer_idx = int(parts[1])
                except ValueError:
                    skipped += 1
                    continue
                if not 0 <= layer_idx < ARCH_DEFAULTS["num_hidden_layers"]:
                    skipped += 1
                    continue
                sub = ".".join(parts[2:])  # e.g. "self_attn.q_proj.weight"

                if layers[layer_idx] is None:
                    layers[layer_idx] = LayerWeightsHF()

                np_arr = reader.read_np(name)
                arr = (
                    _to_mx(np_arr, dtype_hint=reader.info(name)["dtype"])
                    if prefer_mlx
                    else np_arr
                )

                slot = (
                    full_dispatch.get(sub)
                    or linear_dispatch.get(sub)
                    or common_dispatch.get(sub)
                )
                if slot is None:
                    skipped += 1
                    if verbose:
                        print(f"  [warn] unknown tensor: {name}", flush=True)
                    continue
                setattr(layers[layer_idx], slot, arr)

                seen += 1
                manifest["tensors"][name] = {
                    "shape": list(np_arr.shape),
                    "dtype": reader.info(name)["dtype"],
                    "shard": str(shard_path),
                }

    if verbose:
        print(
            f"[hf_loader] loaded {seen} language-model tensors, "
            f"skipped {skipped} (vision/mtp/unknown)",
            flush=True,
        )

    # ---- sanity checks ----
    if embed is None:
        raise ValueError("embed_tokens.weight not found in safetensors")
    if final_norm_w is None:
        raise ValueError("model.language_model.norm.weight not found in safetensors")
    for i, lw in enumerate(layers):
        if lw is None:
            raise ValueError(f"layer {i} not found in safetensors")
        if lw.attn_norm_w is None or lw.ffn_norm_w is None:
            raise ValueError(f"layer {i} missing layernorm weights")
        if lw.o_w is None:
            raise ValueError(f"layer {i} missing o_proj / out_proj weights")
        if lw.gate_w is None or lw.up_w is None or lw.down_w is None:
            raise ValueError(f"layer {i} missing FFN weights")
        if _is_full_layer(i):
            for k in ("q_w", "k_w", "v_w", "q_norm_w", "k_norm_w"):
                if getattr(lw, k) is None:
                    raise ValueError(f"full-attn layer {i} missing {k}")
        else:
            for k in (
                "in_proj_qkv",
                "in_proj_z",
                "in_proj_a",
                "in_proj_b",
                "conv1d_w",
                "A_log",
                "dt_bias",
                "lin_norm_w",
            ):
                if getattr(lw, k) is None:
                    raise ValueError(f"linear-attn layer {i} missing {k}")

    return ModelWeightsHF(
        embed=embed,
        layers=layers,
        final_norm_w=final_norm_w,
        arch=dict(ARCH_DEFAULTS),
        manifest=manifest,
    )


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------


def _to_fp32_view(arr) -> np.ndarray:
    """Coerce an mlx or numpy tensor to a numpy float32 ndarray.

    bf16 raw bits (np.uint16) are first zero-extended to fp32 (matching
    the bit-level conversion used everywhere else in this package), then
    materialised so we can call ``.min()/.max()`` etc. on the result.
    """
    if hasattr(arr, "tolist") and not isinstance(arr, np.ndarray):
        # mlx bfloat16 → list → fp32 numpy
        return np.array(arr.tolist(), dtype=np.float32)
    if isinstance(arr, np.ndarray):
        if arr.dtype == np.uint16:
            # bf16 raw bits — promote
            return (arr.astype(np.uint32) << 16).view(np.float32).copy()
        return arr.astype(np.float32, copy=False)
    return np.asarray(arr, dtype=np.float32)


def weights_summary(mw: ModelWeightsHF) -> dict:
    """Return a JSON-serialisable summary of the loaded weights.

    Includes per-tensor shapes, dtypes, and a few statistics so that the
    CLI ``inspect`` command can sanity-check a loaded checkpoint.
    """
    embed_f32 = _to_fp32_view(mw.embed)
    summary = {
        "model_id": "Qwen3.5-0.8B",
        "tie_word_embeddings": True,
        "embed": {
            "shape": list(embed_f32.shape),
            "dtype": str(getattr(mw.embed, "dtype", "uint16/raw_bf16")),
            "min": float(embed_f32.min()),
            "max": float(embed_f32.max()),
            "mean": float(embed_f32.mean()),
            "std": float(embed_f32.std()),
            "count": int(embed_f32.size),
        },
        "full_attention_layer_indices": [
            i for i in range(ARCH_DEFAULTS["num_hidden_layers"]) if _is_full_layer(i)
        ],
        "linear_attention_layer_indices": [
            i
            for i in range(ARCH_DEFAULTS["num_hidden_layers"])
            if not _is_full_layer(i)
        ],
        "samples": {},
        "tensors_seen": len(mw.manifest.get("tensors", {})),
    }

    if summary["full_attention_layer_indices"]:
        i = summary["full_attention_layer_indices"][0]
        lw = mw.layers[i]
        summary["samples"][f"full_layer_{i}"] = {
            "q_w": list(_to_fp32_view(lw.q_w).shape),
            "k_w": list(_to_fp32_view(lw.k_w).shape),
            "v_w": list(_to_fp32_view(lw.v_w).shape),
            "o_w": list(_to_fp32_view(lw.o_w).shape),
            "q_norm_w": list(_to_fp32_view(lw.q_norm_w).shape),
            "k_norm_w": list(_to_fp32_view(lw.k_norm_w).shape),
        }
    if summary["linear_attention_layer_indices"]:
        i = summary["linear_attention_layer_indices"][0]
        lw = mw.layers[i]
        A_log_arr = lw.A_log
        summary["samples"][f"linear_layer_{i}"] = {
            "in_proj_qkv": list(_to_fp32_view(lw.in_proj_qkv).shape),
            "in_proj_z": list(_to_fp32_view(lw.in_proj_z).shape),
            "in_proj_a": list(_to_fp32_view(lw.in_proj_a).shape),
            "in_proj_b": list(_to_fp32_view(lw.in_proj_b).shape),
            "conv1d_w": list(_to_fp32_view(lw.conv1d_w).shape),
            "A_log_dtype": str(getattr(A_log_arr, "dtype", "f32")),
            "A_log_first4": _to_fp32_view(A_log_arr).reshape(-1)[:4].tolist(),
            "dt_bias": list(_to_fp32_view(lw.dt_bias).shape),
            "out_proj": list(_to_fp32_view(lw.o_w).shape),
            "lin_norm_w": list(_to_fp32_view(lw.lin_norm_w).shape),
        }
    return summary
