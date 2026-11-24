"""
serialize.py — Flat bf16 blob layout for the Qwen3.5 0.8B weight set.

The C++ ``kernel_engine.mm`` consumes ``layer_weights`` as a single flat
bf16 blob per layer; this module is the Python counterpart that turns a
:class:`hf_loader.ModelWeightsHF` into the exact byte layout the engine
expects.

Blob format
-----------

The file starts with a fixed-size header (16 bytes magic + 4 bytes
version + 4 bytes reserved + 4 bytes reserved = 28 bytes), then a JSON
manifest describing the per-tensor offsets, then the raw bf16 payload.

Header::

    offset 0   : "PHENOQWE"  (8 bytes, ASCII)
    offset 8   : uint32  version (little-endian, currently 1)
    offset 12  : uint32  flags  (0 = bf16 LE, 1 = reserved)
    offset 16  : uint32  manifest_offset  (byte offset of the JSON manifest)
    offset 20  : uint32  manifest_length  (byte length of the JSON manifest)
    offset 24  : uint32  payload_offset   (byte offset of the bf16 payload)
    offset 28  : uint32  reserved

After the header, the JSON manifest is a UTF-8 text blob (null-padded
to 8-byte alignment).  It contains::

    {
      "version": 1,
      "dtype": "bfloat16",
      "byte_order": "little",
      "tensors": [
         {"name": "embed",                  "shape": [248320, 1024], "dtype": "bfloat16", "offset": 0, "nbytes": 509607680},
         {"name": "layers.0.attn_norm_w",   "shape": [1024],         "dtype": "bfloat16", "offset": 509607680, "nbytes": 2048},
         ...
      ],
      "total_bytes": 1707080704
    }

After the manifest, the raw bf16 payload is laid out in the order
declared by ``tensors``.  All tensors are dense and contiguous in the
declared dtype.

Per-layer layout
----------------

For each of the 24 layers we emit, in order:

* full attention layer (i in {3, 7, 11, 15, 19, 23})::

    attn_norm_w       [H]                          bf16
    ffn_norm_w        [H]                          bf16
    q_w               [Q, H]                       bf16
    k_w               [KV, H]                      bf16
    v_w               [KV, H]                      bf16
    o_w               [H, Q]                       bf16
    q_norm_w          [D]                          bf16
    k_norm_w          [D]                          bf16
    gate_w            [I, H]                       bf16
    up_w              [I, H]                       bf16
    down_w            [H, I]                       bf16

* linear attention layer (i in {0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22})::

    attn_norm_w       [H]                          bf16
    ffn_norm_w        [H]                          bf16
    in_proj_qkv       [3*Hk*Dk, H]                 bf16
    in_proj_z         [Hv*Dv, H]                   bf16
    in_proj_a         [Hv, H]                      bf16
    in_proj_b         [Hv, H]                      bf16
    conv1d_w          [C, 1, K]                    bf16
    A_log             [Hv]                         bf16
    dt_bias           [Hv]                         bf16
    lin_norm_w        [Hv*Dv]                      bf16
    o_w               [H, Hv*Dv]                   bf16
    gate_w            [I, H]                       bf16
    up_w              [I, H]                       bf16
    down_w            [H, I]                       bf16

The ``offset`` recorded in the manifest is the byte offset into the
*payload section* (i.e. relative to ``payload_offset`` from the header).
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

from .hf_loader import (
    ARCH_DEFAULTS,
    ModelWeightsHF,
    _is_full_layer,
)

# ---------------------------------------------------------------------------
# File format constants
# ---------------------------------------------------------------------------

BLOB_HEADER_MAGIC = b"PHENOQWE"  # 8 bytes — matches the on-disk header struct
BLOB_HEADER_VERSION = 1
BLOB_HEADER_SIZE = 32  # bytes


# ---------------------------------------------------------------------------
# Portable bfloat16 dtype helpers
#
# The numpy bf16 dtype is *not* portable: ``np.dtype("bfloat16")`` raises
# ``TypeError: data type 'bfloat16' not understood`` on the numpy 2.4.x
# builds we ship on Apple Silicon, and on older numpy (<2.0) it works but
# uses a different equality semantics.  Our blob format stores bf16 as
# raw 2-byte little-endian bit patterns, so consumers don't actually need
# a real numpy bf16 dtype — ``np.uint16`` with the convention "the high 16
# bits of the corresponding IEEE-754 float32 are the bf16 bit pattern" is
# equivalent.  ``_safe_bf16_dtype`` returns whichever representation numpy
# supports, defaulting to uint16 if bf16 isn't recognised.
# ---------------------------------------------------------------------------


def _safe_bf16_dtype() -> np.dtype:
    """Return a numpy dtype suitable for storing bf16 bit patterns.

    Returns ``np.dtype("bfloat16")`` when numpy recognises the name
    (numpy 1.25 ≤ v < 2.4 mostly), otherwise ``np.uint16``.  In both
    cases the on-disk byte layout is identical: little-endian IEEE-754
    bf16 bits packed into 2 bytes per element.
    """
    try:
        return np.dtype("bfloat16")
    except TypeError:
        return np.dtype("uint16")


def _is_bf16_dtype(dt: np.dtype) -> bool:
    """True if ``dt`` is the numpy bf16 dtype (or its uint16 alias).

    Uses ``dtype.itemsize == 2`` and a kind-based check rather than
    ``==`` comparison, which raises ``TypeError`` on numpy 2.4.x.
    """
    if not isinstance(dt, np.dtype):
        return False
    if dt.itemsize != 2:
        return False
    name = dt.name
    return name in ("bfloat16", "uint16")


def _arch_dims() -> dict:
    return dict(ARCH_DEFAULTS)


# ---------------------------------------------------------------------------
# MLX → numpy adapter (avoid the broken PEP 3118 buffer protocol for bf16)
# ---------------------------------------------------------------------------


def _to_numpy(arr) -> np.ndarray:
    """Convert an MLX array, numpy array, or scalar to a numpy ndarray.

    The ``mlx.core.array`` ``__array__`` protocol is broken on Apple Silicon
    for bfloat16 — it raises
    ``RuntimeError: Item size 2 for PEP 3118 buffer format string B does
    not match the dtype B item size 1.``
    on numpy 2.4.x.  We sidestep it via ``.tolist()`` which always works
    (preserves dtype), then cast to the correct numpy dtype.  For numpy
    inputs this is a no-op copy.

    Output dtypes:
      * ``mlx.core.bfloat16`` → ``np.uint16`` (raw bf16 bit pattern)
      * ``mlx.core.float32``  → ``np.float32``
      * ``mlx.core.int32``    → ``np.int32``
    """
    if arr is None:
        return None
    if isinstance(arr, np.ndarray):
        return arr
    # MLX array path.  The dtype attribute uses ``mlx.core.<dtype>`` names.
    try:
        import mlx.core as mx  # local import to keep this module MLX-free

        if isinstance(arr, mx.array):
            dt_name = str(arr.dtype)
            if dt_name == "mlx.core.bfloat16":
                # Lift bf16 to f32 via tolist(), then take the high 16
                # bits of the IEEE-754 representation.  This is the
                # bf16 bit pattern, packed into uint16.
                f32 = np.array(arr.astype(mx.float32).tolist(), dtype=np.float32)
                return np.ascontiguousarray(f32.view(np.uint32) >> 16, dtype=np.uint16)
            if dt_name == "mlx.core.float32":
                return np.array(arr.tolist(), dtype=np.float32)
            if dt_name == "mlx.core.int32":
                return np.array(arr.tolist(), dtype=np.int32)
            if dt_name == "mlx.core.float16":
                return np.array(arr.tolist(), dtype=np.float16)
            # Generic fallback
            return np.array(arr.tolist())
    except ImportError:
        pass
    # Last resort — assume array-like.
    return np.asarray(arr)


# ---------------------------------------------------------------------------
# Per-layer tensor list (the single source of truth for ordering)
# ---------------------------------------------------------------------------


def _layer_tensors(layer, layer_idx: int) -> list:
    """Return a list of (name, np.ndarray) tuples for the given layer.

    For full-attention layers the list contains Q/K/V/O + per-head norms.
    For linear-attention layers the list contains the GatedDeltaNet
    parameters in Mamba-2 order: qkv, z, a, b, conv1d, A_log, dt_bias,
    norm, out_proj.

    The numpy conversion goes through :func:`_to_numpy` so we accept
    ``mlx.core.array`` inputs (the default on Apple Silicon) and
    sidestep the broken ``__array__`` protocol for bfloat16.
    """
    out = []
    # Common
    out.append(("attn_norm_w", _to_numpy(layer.attn_norm_w)))
    out.append(("ffn_norm_w", _to_numpy(layer.ffn_norm_w)))

    if _is_full_layer(layer_idx):
        out += [
            ("q_w", _to_numpy(layer.q_w)),
            ("k_w", _to_numpy(layer.k_w)),
            ("v_w", _to_numpy(layer.v_w)),
            ("o_w", _to_numpy(layer.o_w)),
            ("q_norm_w", _to_numpy(layer.q_norm_w)),
            ("k_norm_w", _to_numpy(layer.k_norm_w)),
        ]
    else:
        out += [
            ("in_proj_qkv", _to_numpy(layer.in_proj_qkv)),
            ("in_proj_z", _to_numpy(layer.in_proj_z)),
            ("in_proj_a", _to_numpy(layer.in_proj_a)),
            ("in_proj_b", _to_numpy(layer.in_proj_b)),
            ("conv1d_w", _to_numpy(layer.conv1d_w)),
            ("A_log", _to_numpy(layer.A_log)),
            ("dt_bias", _to_numpy(layer.dt_bias)),
            ("lin_norm_w", _to_numpy(layer.lin_norm_w)),
            ("o_w", _to_numpy(layer.o_w)),
        ]

    # FFN
    out += [
        ("gate_w", _to_numpy(layer.gate_w)),
        ("up_w", _to_numpy(layer.up_w)),
        ("down_w", _to_numpy(layer.down_w)),
    ]
    return out


def _to_bf16(arr: np.ndarray) -> np.ndarray:
    """Cast a numpy array to bf16 (machine-native byte order, contiguous).

    The on-disk layout is always the bf16 IEEE-754 bit pattern (2 bytes per
    element).  We accept three input dtypes:

    * ``np.dtype("bfloat16")`` (numpy 1.25 ≤ v < 2.4 / v ≥ 2.5 with native bf16)
      — passed through unchanged (after a contiguous copy).
    * ``np.uint16`` carrying bf16 bit patterns (the convention used by
      :mod:`hf_loader` on numpy builds without bf16 support) — also passed
      through unchanged.
    * ``np.float32`` / float64 / int — converted to bf16 via fp32 → high-16
      truncation.  This is the same round-trip the MLX path uses
      (bf16 → fp32 → bf16 round-trip is identity, so converting via fp32 is
      lossless from bf16's perspective).
    """
    a = np.ascontiguousarray(arr)
    if _is_bf16_dtype(a.dtype):
        return a
    bf_dt = _safe_bf16_dtype()
    if bf_dt.itemsize != 2:
        # Shouldn't happen, but guard against future numpy variants.
        return a.astype(bf_dt)
    if a.dtype == np.float32:
        # Take the high 16 bits of the IEEE-754 float32 representation.
        return (
            np.ascontiguousarray(a.view(np.uint32) >> 16).view(bf_dt)
            if bf_dt.name == "bfloat16"
            else np.ascontiguousarray(a.view(np.uint32) >> 16, dtype=np.uint16)
        )
    if a.dtype == np.float64:
        a32 = a.astype(np.float32)
        return (
            np.ascontiguousarray(a32.view(np.uint32) >> 16).view(bf_dt)
            if bf_dt.name == "bfloat16"
            else np.ascontiguousarray(a32.view(np.uint32) >> 16, dtype=np.uint16)
        )
    # Last resort: cast directly (works on numpy builds with native bf16)
    try:
        return a.astype(bf_dt)
    except TypeError:
        # Fall back to uint16 raw bits via fp32
        a32 = a.astype(np.float32)
        return np.ascontiguousarray(a32.view(np.uint32) >> 16, dtype=np.uint16)


# Per-tensor dtype policy.  Some tensors come from the HF safetensors as
# f32 (A_log, lin_norm_w) and need to keep their full precision on disk
# because the linear-attention decay is sensitive to small A_log errors
# (it feeds ``exp(A_log)`` into a state-update recurrence that runs
# once per token).  Storing them as bf16 introduces ~3% relative error
# per element which compounds across the recurrence.
#
# The rest of the model is bf16 throughout, both in HF and in the kernel
# engine, so we keep the existing bf16 layout for everything else.
_F32_PRECISION_TENSORS = frozenset({"A_log", "lin_norm_w"})


def _pack_tensor(arr: np.ndarray, *, name: str):
    """Convert a numpy array to its on-disk representation.

    Returns a tuple ``(raw_bytes, dtype_str, dtype_kind)``:

    * ``raw_bytes``  — the contiguous payload bytes to be appended to the
      payload section of the blob.
    * ``dtype_str``   — string for the manifest entry (e.g. ``"bfloat16"``,
      ``"float32"``).
    * ``dtype_kind``  — "bf16" (2 bytes/elem, raw bit pattern = bf16) or
      "fp32" (4 bytes/elem, native float32).  Used by ``load_blob`` to
      pick the correct numpy dtype on read-back.
    """
    a = np.ascontiguousarray(arr)
    # Per-tensor dtype policy: A_log / lin_norm_w live inside ``layers.{i}.*``
    # but the bare-name membership is sufficient for the rule.
    bare = name.split(".")[-1]
    if bare in _F32_PRECISION_TENSORS:
        # Preserve full f32 precision.  If the input is already f32 (the
        # normal HF path) or f64 (rare), cast to native f32.
        if a.dtype != np.float32:
            a = a.astype(np.float32)
        return a.tobytes(), "float32", "fp32"
    bf = _to_bf16(a)
    return bf.tobytes(), "bfloat16", "bf16"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_blob(
    mw: ModelWeightsHF,
    path: str | Path,
    *,
    verbose: bool = False,
) -> dict:
    """Serialize a ModelWeightsHF to the flat-blob format.

    Returns the manifest dict that was written (for callers that want to
    inspect the tensor offsets).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    arch = _arch_dims()
    n_layers = arch["num_hidden_layers"]

    # Build the manifest and accumulate the payload in memory.
    tensors = []
    payload_parts = []
    cursor = 0
    total_params = 0

    def _add(full_name, arr, scope=""):
        nonlocal cursor, total_params
        arr_np = _to_numpy(arr)
        nbytes = arr_np.nbytes
        raw, dtype_str, _kind = _pack_tensor(arr_np, name=full_name)
        tensors.append(
            {
                "name": (scope + full_name) if scope else full_name,
                "shape": list(arr_np.shape),
                "dtype": dtype_str,
                "offset": cursor,
                "nbytes": nbytes,
            }
        )
        payload_parts.append(raw)
        cursor += nbytes
        total_params += int(np.prod(arr_np.shape))
        if verbose:
            print(
                f"  + {full_name:<28} shape={list(arr_np.shape)} "
                f"dtype={dtype_str} nbytes={nbytes}",
                flush=True,
            )

    _add("embed", mw.embed)
    for i, layer in enumerate(mw.layers):
        if verbose:
            print(
                f"[layer {i}] {'full' if _is_full_layer(i) else 'linear'}", flush=True
            )
        for name, arr in _layer_tensors(layer, i):
            _add(name, arr, scope=f"layers.{i}.")
    _add("final_norm_w", mw.final_norm_w)

    manifest = {
        "version": BLOB_HEADER_VERSION,
        # Note: this is the *default* dtype.  Each tensor entry carries its
        # own ``dtype`` field which may override this.  See _pack_tensor
        # for the per-tensor policy (A_log / lin_norm_w are stored as f32
        # to preserve precision; everything else is bf16).
        "dtype": "bfloat16",
        "byte_order": "little",
        "model_id": "Qwen3.5-0.8B",
        "arch": {
            "vocab_size": arch["vocab_size"],
            "hidden_size": arch["hidden_size"],
            "intermediate_size": arch["intermediate_size"],
            "num_hidden_layers": n_layers,
            "full_attention_interval": arch["full_attention_interval"],
        },
        "tensors": tensors,
        "total_params": total_params,
    }
    manifest_text = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
    # Pad manifest to 8-byte alignment so the payload is 8-byte aligned.
    if len(manifest_text) % 8 != 0:
        manifest_text += b" " * (8 - (len(manifest_text) % 8))

    payload = b"".join(payload_parts)

    header = struct.pack(
        "<8sIIIIII",
        BLOB_HEADER_MAGIC,
        BLOB_HEADER_VERSION,
        0,  # flags
        BLOB_HEADER_SIZE,
        len(manifest_text),
        BLOB_HEADER_SIZE + len(manifest_text),
        0,  # reserved
    )

    with open(path, "wb") as f:
        f.write(header)
        f.write(manifest_text)
        f.write(payload)

    if verbose:
        print(
            f"[serialize] wrote {path}  "
            f"manifest={len(manifest_text)}  payload={len(payload)}  "
            f"total={BLOB_HEADER_SIZE + len(manifest_text) + len(payload)}",
            flush=True,
        )
    return manifest


def load_blob(path: str | Path) -> ModelWeightsHF:
    """Reverse of :func:`save_blob`: read the flat-blob file and rebuild
    a :class:`ModelWeightsHF`."""
    path = Path(path)
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < BLOB_HEADER_SIZE:
        raise ValueError(f"file too small: {len(data)} bytes")
    magic, version, flags, manifest_offset, manifest_len, payload_offset, _ = (
        struct.unpack("<8sIIIIII", data[:BLOB_HEADER_SIZE])
    )
    if magic != BLOB_HEADER_MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    if version != BLOB_HEADER_VERSION:
        raise ValueError(f"unsupported blob version: {version}")
    manifest_text = data[manifest_offset : manifest_offset + manifest_len]
    manifest = json.loads(manifest_text)
    payload = data[payload_offset:]

    # Group tensors by layer / top-level scope
    embed_arr = None
    final_norm_arr = None
    layers_tensors = {}  # i -> dict[name] -> np.ndarray
    for t in manifest["tensors"]:
        name = t["name"]
        chunk = payload[t["offset"] : t["offset"] + t["nbytes"]]
        # Per-tensor dtype.  Most tensors are stored as bf16 (lossless via
        # the high 16 bits of an fp32 cast).  A_log and lin_norm_w are
        # stored as f32 because the kernel expects fp32 alpha_log / RMS
        # weights and we don't want to quantize them.
        dt_name = t.get("dtype", "bfloat16")
        if dt_name == "float32":
            arr = np.frombuffer(chunk, dtype=np.float32).reshape(t["shape"])
        elif dt_name == "bfloat16":
            # Read raw bf16 bits as uint16.  The on-disk byte order is
            # little-endian IEEE-754 bf16 — taking the high 16 bits of an
            # fp32 cast recovers the original bf16 bit pattern losslessly.
            # We use uint16 (not np.dtype("bfloat16")) for portability
            # across numpy versions that lack native bf16 support
            # (e.g. numpy 2.4.x on Apple Silicon).
            arr = np.frombuffer(chunk, dtype=np.uint16).reshape(t["shape"])
        else:
            raise ValueError(
                f"unsupported tensor dtype in blob: {dt_name!r} (tensor={name})"
            )
        if name == "embed":
            embed_arr = arr
        elif name == "final_norm_w":
            final_norm_arr = arr
        elif name.startswith("layers."):
            head, _, rest = name.partition(".")
            i_str, _, sub = rest.partition(".")
            i = int(i_str)
            d = layers_tensors.setdefault(i, {})
            d[sub] = arr

    # Reconstruct LayerWeightsHF
    from .hf_loader import LayerWeightsHF

    arch = _arch_dims()
    layers = [None] * arch["num_hidden_layers"]
    for i, d in layers_tensors.items():
        lw = LayerWeightsHF(attn_norm_w=d["attn_norm_w"], ffn_norm_w=d["ffn_norm_w"])
        if _is_full_layer(i):
            lw.q_w = d["q_w"]
            lw.k_w = d["k_w"]
            lw.v_w = d["v_w"]
            lw.o_w = d["o_w"]
            lw.q_norm_w = d["q_norm_w"]
            lw.k_norm_w = d["k_norm_w"]
        else:
            lw.in_proj_qkv = d["in_proj_qkv"]
            lw.in_proj_z = d["in_proj_z"]
            lw.in_proj_a = d["in_proj_a"]
            lw.in_proj_b = d["in_proj_b"]
            lw.conv1d_w = d["conv1d_w"]
            lw.A_log = d["A_log"]
            lw.dt_bias = d["dt_bias"]
            lw.lin_norm_w = d["lin_norm_w"]
            lw.o_w = d["o_w"]
        lw.gate_w = d["gate_w"]
        lw.up_w = d["up_w"]
        lw.down_w = d["down_w"]
        layers[i] = lw

    return ModelWeightsHF(
        embed=embed_arr,
        layers=layers,
        final_norm_w=final_norm_arr,
        arch=_arch_dims(),
    )


def blob_summary(path: str | Path) -> dict:
    """Return a summary of a blob file (header + tensor list, no payload)."""
    path = Path(path)
    with open(path, "rb") as f:
        data = f.read(BLOB_HEADER_SIZE)
    magic, version, flags, mo, ml, po, _ = struct.unpack("<8sIIIIII", data)
    if magic != BLOB_HEADER_MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    with open(path, "rb") as f:
        f.seek(mo)
        manifest = json.loads(f.read(ml).decode("utf-8").strip())
    return {
        "magic": magic.decode(),
        "version": version,
        "manifest_offset": mo,
        "manifest_length": ml,
        "payload_offset": po,
        "n_tensors": len(manifest["tensors"]),
        "total_params": manifest.get("total_params"),
        "model_id": manifest.get("model_id"),
        "arch": manifest.get("arch"),
        "first_5_tensors": manifest["tensors"][:5],
        "last_5_tensors": manifest["tensors"][-5:],
    }
