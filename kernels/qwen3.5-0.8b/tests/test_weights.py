#!/usr/bin/env python3
"""
test_weights.py — End-to-end test suite for the weights/ package.

Run with::

    python3 -m pytest tests/test_weights.py -v
    # or
    python3 tests/test_weights.py

The tests need the HF safetensors snapshot to be present; they auto-skip
if not.  Tests cover:

  * shape and dtype sanity (load_hf_weights, load_hf_tokenizer)
  * full ↔ linear attention layer-type detection
  * converter: HF schema → reference schema
  * end-to-end forward pass produces finite, confident logits
  * blob serialization round-trip (bit-exact for every tensor)
  * per-tensor dtype policy (A_log / lin_norm_w stay f32)
  * blob header magic + version check
  * CLI subcommands work (download/inspect/dump-blob/sample)
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

pytest.importorskip("numpy", reason="numpy not installed in test venv")

import numpy as np

# Make the package importable when run as a script
HERE = Path(__file__).resolve().parent
KERNEL_ROOT = HERE.parent
sys.path.insert(0, str(KERNEL_ROOT))

from weights import (  # noqa: E402
    BLOB_HEADER_MAGIC,
    BLOB_HEADER_VERSION,
    blob_summary,
    load_blob,
    load_hf_tokenizer,
    load_hf_weights,
    save_blob,
    weights_summary,
)
from weights.hf_loader import ARCH_DEFAULTS, _is_full_layer  # noqa: E402
from weights.serialize import (  # noqa: E402
    _is_bf16_dtype,
    _pack_tensor,
    _safe_bf16_dtype,
)

# ---------------------------------------------------------------------------
# Locate the HF safetensors snapshot.  Skip all data-dependent tests if
# the snapshot is missing.
# ---------------------------------------------------------------------------

DEFAULT_HF_DIR = (
    KERNEL_ROOT
    / "weights"
    / "build"
    / "hf-cache"
    / "models--Qwen--Qwen3.5-0.8B"
    / "snapshots"
    / "2fc06364715b967f1860aea9cf38778875588b17"
)


def _find_hf_dir() -> Path | None:
    candidates = []
    env = os.environ.get("QWEN35_HF_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(DEFAULT_HF_DIR)
    for c in candidates:
        if c.is_dir() and any(c.glob("model.safetensors*")):
            return c
    return None


HF_DIR = _find_hf_dir()


def _bf16_to_f32(arr) -> np.ndarray:
    """Lift a uint16/bf16 array (numpy or mlx) to f32 (lossless).

    Handles the on-disk/native representations that show up across numpy
    versions and across the numpy/MLX split in this repo:

    * ``np.dtype("bfloat16")`` (numpy 2.5+) — view as uint16.
    * ``np.uint16`` carrying bf16 bit patterns — view as uint16.
    * ``np.float32`` — already fine.
    * ``mlx.core.array`` — round-trip through ``.tolist()`` and lift to f32.

    The unified path avoids the broken ``np.asarray(...).view(...)`` chain
    that fails on native bf16 numpy builds (PEP 3118 buffer format
    mismatch) and on MLX arrays (no ``view(uint16)``).
    """
    # MLX path: go through Python float (lossless for bf16 → f32).
    if not isinstance(arr, np.ndarray):
        try:
            import mlx.core as mx

            if isinstance(arr, mx.array):
                f32 = np.array(arr.astype(mx.float32).tolist(), dtype=np.float32)
                return f32
        except ImportError:
            pass
    if arr.dtype == np.float32:
        return arr.copy()
    if arr.dtype == np.uint16:
        bits = arr
    else:
        bits = arr.view(np.uint16)
    bits32 = bits.astype(np.uint32) << 16
    return bits32.view(np.float32)


# ---------------------------------------------------------------------------
# Pure-Python unit tests (no HF data needed)
# ---------------------------------------------------------------------------


class TestArchConstants(unittest.TestCase):
    """Architecture constants must match arch.yaml and the reference impl."""

    def test_layer_count_is_24(self):
        self.assertEqual(ARCH_DEFAULTS["num_hidden_layers"], 24)

    def test_full_attention_indices(self):
        full = [i for i in range(24) if _is_full_layer(i)]
        self.assertEqual(full, [3, 7, 11, 15, 19, 23])

    def test_hidden_size(self):
        self.assertEqual(ARCH_DEFAULTS["hidden_size"], 1024)
        self.assertEqual(ARCH_DEFAULTS["vocab_size"], 248_320)
        self.assertEqual(ARCH_DEFAULTS["intermediate_size"], 3584)

    def test_full_attention_dims(self):
        # GQA 4:1: 8 heads, 2 KV heads, head_dim 256
        self.assertEqual(ARCH_DEFAULTS["full_heads"], 8)
        self.assertEqual(ARCH_DEFAULTS["full_kv_heads"], 2)
        self.assertEqual(ARCH_DEFAULTS["full_head_dim"], 256)

    def test_linear_attention_dims(self):
        # 16 K heads × 128 = 16 V heads × 128
        self.assertEqual(ARCH_DEFAULTS["lin_key_heads"], 16)
        self.assertEqual(ARCH_DEFAULTS["lin_value_heads"], 16)
        self.assertEqual(ARCH_DEFAULTS["lin_key_head_dim"], 128)
        self.assertEqual(ARCH_DEFAULTS["lin_value_head_dim"], 128)
        self.assertEqual(ARCH_DEFAULTS["lin_conv_kernel"], 4)

    def test_tied_embeddings(self):
        self.assertTrue(ARCH_DEFAULTS["tie_word_embeddings"])

    def test_attn_output_gate_enabled(self):
        # Q-projection output is doubled [q | gate] only when this is on.
        self.assertTrue(ARCH_DEFAULTS["attn_output_gate"])


class TestDtypeHelpers(unittest.TestCase):
    """Tests for the bf16/f32 dtype helpers (used by serialize.py)."""

    def test_safe_bf16_returns_2_bytes(self):
        dt = _safe_bf16_dtype()
        self.assertEqual(dt.itemsize, 2)

    def test_is_bf16_dtype_accepts_uint16(self):
        a = np.zeros(8, dtype=np.uint16)
        self.assertTrue(_is_bf16_dtype(a.dtype))

    def test_is_bf16_dtype_rejects_f32(self):
        a = np.zeros(8, dtype=np.float32)
        self.assertFalse(_is_bf16_dtype(a.dtype))

    def test_pack_tensor_bf16_default(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        raw, dtype_str, kind = _pack_tensor(a, name="embed")
        self.assertEqual(dtype_str, "bfloat16")
        self.assertEqual(kind, "bf16")
        self.assertEqual(len(raw), 6)  # 2 bytes/elem

    def test_pack_tensor_a_log_f32(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        raw, dtype_str, kind = _pack_tensor(a, name="A_log")
        self.assertEqual(dtype_str, "float32")
        self.assertEqual(kind, "fp32")
        self.assertEqual(len(raw), 12)  # 4 bytes/elem

    def test_pack_tensor_lin_norm_w_f32(self):
        a = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        raw, dtype_str, kind = _pack_tensor(a, name="lin_norm_w")
        self.assertEqual(dtype_str, "float32")
        self.assertEqual(kind, "fp32")
        self.assertEqual(len(raw), 12)


class TestBlobHeader(unittest.TestCase):
    """Header constants and file-format invariants."""

    def test_magic_is_8_bytes(self):
        self.assertEqual(len(BLOB_HEADER_MAGIC), 8)

    def test_version_is_int(self):
        self.assertIsInstance(BLOB_HEADER_VERSION, int)
        self.assertEqual(BLOB_HEADER_VERSION, 1)


# ---------------------------------------------------------------------------
# Data-dependent tests (skipped when HF snapshot is missing)
# ---------------------------------------------------------------------------


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestHFLoad(unittest.TestCase):
    """End-to-end HF loader tests using the real Qwen3.5 0.8B checkpoint."""

    @classmethod
    def setUpClass(cls):
        cls.mw = load_hf_weights(str(HF_DIR), verbose=False)

    def test_layer_count(self):
        self.assertEqual(len(self.mw.layers), 24)

    def test_full_attention_layer_count(self):
        full = [i for i, layer in enumerate(self.mw.layers) if layer.q_w is not None]
        self.assertEqual(full, [3, 7, 11, 15, 19, 23])

    def test_linear_attention_layer_count(self):
        linear = [
            i for i, layer in enumerate(self.mw.layers) if layer.in_proj_qkv is not None
        ]
        self.assertEqual(len(linear), 18)

    def test_embed_shape(self):
        self.assertEqual(self.mw.embed.shape, (248_320, 1024))

    def test_final_norm_shape(self):
        self.assertEqual(self.mw.final_norm_w.shape, (1024,))

    def test_full_layer_qkv_shapes(self):
        # Layer 3 (full): q [2*Q, H], k [KV, H], v [KV, H]
        # Q = 8*256 = 2048, KV = 2*256 = 512, so q is [4096, 1024].
        fl = self.mw.layers[3]
        self.assertEqual(fl.q_w.shape, (4096, 1024))
        self.assertEqual(fl.k_w.shape, (512, 1024))
        self.assertEqual(fl.v_w.shape, (512, 1024))
        self.assertEqual(fl.o_w.shape, (1024, 2048))
        self.assertEqual(fl.q_norm_w.shape, (256,))
        self.assertEqual(fl.k_norm_w.shape, (256,))

    def test_linear_layer_shapes(self):
        ll = self.mw.layers[0]
        # in_proj_qkv: [3*Hk*Dk, H] = [3*16*128, 1024] = [6144, 1024]
        self.assertEqual(ll.in_proj_qkv.shape, (6144, 1024))
        # in_proj_z: [Hv*Dv, H] = [2048, 1024]
        self.assertEqual(ll.in_proj_z.shape, (2048, 1024))
        # in_proj_a, in_proj_b: [Hv, H] = [16, 1024]
        self.assertEqual(ll.in_proj_a.shape, (16, 1024))
        self.assertEqual(ll.in_proj_b.shape, (16, 1024))
        # conv1d: [C, 1, K] = [6144, 1, 4]
        self.assertEqual(ll.conv1d_w.shape, (6144, 1, 4))
        # A_log, dt_bias: [Hv] = [16]
        self.assertEqual(ll.A_log.shape, (16,))
        self.assertEqual(ll.dt_bias.shape, (16,))
        # lin_norm_w: [Dk] = [128] (HF stores per-head RMSNorm over the
        # K-dim of the recurrent state; the kernel applies it to the
        # value-head output dimension).
        self.assertEqual(ll.lin_norm_w.shape, (128,))
        # o_w: [H, Hv*Dv] = [1024, 2048]
        self.assertEqual(ll.o_w.shape, (1024, 2048))

    def test_ffn_shapes(self):
        # SwiGLU: gate [I, H] = [3584, 1024], up [3584, 1024], down [1024, 3584]
        for i in (0, 3, 23):
            layer = self.mw.layers[i]
            self.assertEqual(layer.gate_w.shape, (3584, 1024), f"layer {i} gate")
            self.assertEqual(layer.up_w.shape, (3584, 1024), f"layer {i} up")
            self.assertEqual(layer.down_w.shape, (1024, 3584), f"layer {i} down")

    def test_summary_keys(self):
        s = weights_summary(self.mw)
        for key in (
            "embed",
            "full_attention_layer_indices",
            "linear_attention_layer_indices",
            "tensors_seen",
            "samples",
        ):
            self.assertIn(key, s)


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestTokenizer(unittest.TestCase):
    """Qwen3.5 BPE tokenizer tests."""

    @classmethod
    def setUpClass(cls):
        cls.tok = load_hf_tokenizer(str(HF_DIR))

    def test_round_trip_ascii(self):
        for s in ["hello", "the cat", "Qwen3.5 0.8B"]:
            ids = self.tok.encode(s).ids
            back = self.tok.decode(ids)
            self.assertEqual(back, s)

    def test_vocab_size(self):
        # The Qwen3.5 tokenizer reserves 250 special tokens (e.g. image/
        # video placeholders, control tokens, padding).  The effective
        # vocab is 248070 but the embed table is sized to 248320 so any
        # future token additions don't require re-embedding.
        vocab = self.tok.get_vocab_size()
        self.assertEqual(vocab, 248_070)
        # The model embed table is what matters for downstream kernels.
        # We cross-check this against the HF weights if they're loaded.
        mw = load_hf_weights(str(HF_DIR), verbose=False)
        self.assertEqual(mw.embed.shape[0], 248_320)


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestBlobRoundTrip(unittest.TestCase):
    """save_blob → load_blob round-trip is bit-exact for every tensor."""

    @classmethod
    def setUpClass(cls):
        cls.mw = load_hf_weights(str(HF_DIR), verbose=False)
        cls.tmpdir = tempfile.mkdtemp(prefix="pheno-blob-test-")
        cls.blob_path = Path(cls.tmpdir) / "weights.bin"
        cls.manifest = save_blob(cls.mw, cls.blob_path, verbose=False)

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_manifest_arch_matches(self):
        arch = self.manifest["arch"]
        self.assertEqual(arch["num_hidden_layers"], 24)
        self.assertEqual(arch["vocab_size"], 248_320)
        self.assertEqual(arch["hidden_size"], 1024)
        self.assertEqual(arch["intermediate_size"], 3584)

    def test_manifest_total_params(self):
        # Qwen3.5 0.8B should be ~800M params; the loader reports 752M
        # (text-only, vision tower and MTP are skipped).
        self.assertGreater(self.manifest["total_params"], 750_000_000)
        self.assertLess(self.manifest["total_params"], 760_000_000)

    def test_tensor_count(self):
        # 2 top-level + 24 layers × (3 full-attn tensors per linear
        # branch varies; 13 for full, 14 for linear — exact count
        # depends on the schema, just check we have 24 layers worth)
        n_full = sum(
            1
            for t in self.manifest["tensors"]
            if t["name"].startswith("layers.") and "q_w" in t["name"]
        )
        n_linear = sum(
            1
            for t in self.manifest["tensors"]
            if t["name"].startswith("layers.") and "in_proj_qkv" in t["name"]
        )
        self.assertEqual(n_full, 6)
        self.assertEqual(n_linear, 18)

    def test_f32_tensors_are_a_log_and_lin_norm_w(self):
        f32_names = sorted(
            t["name"].split(".")[-1]
            for t in self.manifest["tensors"]
            if t["dtype"] == "float32"
        )
        # Should be exactly A_log and lin_norm_w (one per linear layer)
        self.assertEqual(set(f32_names), {"A_log", "lin_norm_w"})
        self.assertEqual(len(f32_names), 2 * 18)

    def test_header(self):
        with open(self.blob_path, "rb") as f:
            head = f.read(32)
        magic, version, _flags, _mo, _ml, _po, _ = struct.unpack("<8sIIIIII", head)
        self.assertEqual(magic, BLOB_HEADER_MAGIC)
        self.assertEqual(version, BLOB_HEADER_VERSION)

    def test_round_trip_bit_exact(self):
        # Round-trip equivalence is verified by saving the in-memory
        # weights to a *fresh* blob and byte-comparing its payload to
        # the payload of the test blob.  This is the actual on-disk
        # invariant we care about (the kernel engine reads the bytes
        # directly via mmap).  The alternative — comparing each
        # tensor element-by-element via f32 lift — is correct but
        # wastes 100+ seconds on a 254M-element embed table.
        mw2 = load_blob(self.blob_path)
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            blob2_path = Path(f2.name)
        try:
            save_blob(mw2, blob2_path, verbose=False)
            with open(self.blob_path, "rb") as f:
                bytes1 = f.read()
            with open(blob2_path, "rb") as f:
                bytes2 = f.read()
            self.assertEqual(
                len(bytes1),
                len(bytes2),
                f"blob size mismatch: {len(bytes1)} vs {len(bytes2)}",
            )
            self.assertEqual(
                bytes1,
                bytes2,
                "blob byte-mismatch after save→load→save round-trip",
            )
        finally:
            blob2_path.unlink(missing_ok=True)

    def test_blob_summary(self):
        s = blob_summary(self.blob_path)
        self.assertEqual(s["magic"], BLOB_HEADER_MAGIC.decode())
        self.assertEqual(s["version"], BLOB_HEADER_VERSION)
        self.assertGreater(s["n_tensors"], 0)
        self.assertEqual(s["total_params"], self.manifest["total_params"])


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestEndToEndForward(unittest.TestCase):
    """One forward pass through all 24 layers with the real weights."""

    @classmethod
    def setUpClass(cls):
        # Lazy-import MLX to keep CI-fast on machines without it.
        import mlx.core as mx
        from python.reference import ref_end_to_end_forward
        from weights import hf_to_reference, load_hf_tokenizer

        cls.mx = mx
        mw = load_hf_weights(str(HF_DIR), prefer_mlx=True, verbose=False)
        cls.ref = hf_to_reference(mw)
        cls.tok = load_hf_tokenizer(str(HF_DIR))
        # Bind to a local closure so ``self._fwd(...)`` doesn't trigger
        # Python's descriptor protocol (which would make ``self`` the
        # first arg).
        cls._fwd = staticmethod(ref_end_to_end_forward)

        prompt = "The capital of France is"
        ids = cls.tok.encode(prompt).ids
        cls.S = len(ids)
        cls.ids = mx.array([ids], dtype=mx.int32)
        cls.pos = mx.array(
            np.broadcast_to(np.arange(cls.S)[:, None], (1, cls.S, 3)).astype(np.int32)
        )

    def test_logits_shape(self):
        out = self._fwd(self.ids, self.pos, self.ref)
        self.mx.eval(out)
        self.assertEqual(tuple(out.shape), (1, self.S, 248_320))

    def test_logits_finite(self):
        out = self._fwd(self.ids, self.pos, self.ref)
        self.mx.eval(out)
        self.assertTrue(bool(self.mx.all(self.mx.isfinite(out)).item()))

    def test_top1_confident(self):
        out = self._fwd(self.ids, self.pos, self.ref)
        self.mx.eval(out)
        last = out[0, -1, :].astype(self.mx.float32)
        self.mx.eval(last)
        arr = np.array(last.tolist())
        top1_id = int(arr.argmax())
        top1_logit = float(arr[top1_id])
        self.assertGreater(
            top1_logit, 5.0, f"top-1 logit={top1_logit} (model is uncertain)"
        )
        top1_text = self.tok.decode([top1_id])
        self.assertTrue(
            len(top1_text) > 0, f"top-1 token {top1_id} decoded to empty string"
        )


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestCLIInspect(unittest.TestCase):
    """The `weights inspect` CLI subcommand must work end-to-end."""

    def test_inspect_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(KERNEL_ROOT)
        out = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "weights",
                "--hf-dir",
                str(HF_DIR),
                "inspect",
                "--json",
            ],
            env=env,
            text=True,
        )
        data = json.loads(out)
        # The embed table's shape encodes vocab_size / hidden_size.
        self.assertEqual(data["embed"]["shape"], [248_320, 1024])
        self.assertEqual(
            data["full_attention_layer_indices"],
            [3, 7, 11, 15, 19, 23],
        )
        self.assertEqual(len(data["linear_attention_layer_indices"]), 18)
        # Spot-check that we sampled a full-attention layer's tensors.
        self.assertIn("full_layer_3", data["samples"])
        self.assertEqual(data["samples"]["full_layer_3"]["q_w"], [4096, 1024])


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestCLIDumpBlob(unittest.TestCase):
    """The `weights dump-blob` CLI subcommand produces a valid blob."""

    def test_dump_blob(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(KERNEL_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "weights.bin"
            # Need ~1.5 GiB free to write the full Qwen3.5 0.8B blob.
            # Skip rather than fail on disk-full CI machines.
            free = shutil.disk_usage(tmp).free
            if free < 2 * 1024**3:
                self.skipTest(
                    f"not enough free space ({free // 1024**3} GiB) "
                    "to dump-blob; skipping",
                )
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "weights",
                    "--hf-dir",
                    str(HF_DIR),
                    "dump-blob",
                    str(out_path),
                ],
                env=env,
            )
            # Read the header
            with open(out_path, "rb") as f:
                head = f.read(32)
            magic, version, _, _, _, _, _ = struct.unpack("<8sIIIIII", head)
            self.assertEqual(magic, BLOB_HEADER_MAGIC)
            self.assertEqual(version, BLOB_HEADER_VERSION)
            # Should be roughly 1.4 GiB (24 layers × ~60 MiB each + 0.5 GiB embed)
            size = out_path.stat().st_size
            self.assertGreater(size, 1_000_000_000)
            self.assertLess(size, 2_000_000_000)


@unittest.skipUnless(
    HF_DIR is not None, f"HF safetensors snapshot not found at {DEFAULT_HF_DIR}"
)
class TestCLISample(unittest.TestCase):
    """The `weights sample` CLI subcommand produces sensible text."""

    def test_sample_runs(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(KERNEL_ROOT)
        out = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "weights",
                "--hf-dir",
                str(HF_DIR),
                "sample",
                "The capital of France is",
                "--max-new-tokens",
                "3",
                "--temperature",
                "0.0",
            ],
            env=env,
            text=True,
            stderr=subprocess.STDOUT,
        )
        # Must contain prefill + top-5 + at least one decode step.
        self.assertIn("Top-5 next-token predictions", out)
        self.assertIn("step", out)


if __name__ == "__main__":
    # Allow running as a plain script too (not just via pytest).
    unittest.main(verbosity=2)
