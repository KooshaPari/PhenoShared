"""
weights/ — HuggingFace weight loading + serialization for Qwen3.5 0.8B.

This package bridges the HF safetensors checkpoint
(``Qwen/Qwen3.5-0.8B`` on HuggingFace Hub) and the kernel suite's internal
:mod:`reference` schema.

Public API
----------

* :func:`load_hf_weights`  — read a safetensors directory, return a
  ``ModelWeights`` populated with the language-model parameters (vision
  tower + MTP modules are skipped; this suite is text-only).
* :func:`load_hf_tokenizer` — load the Qwen3.5 BPE tokenizer via
  ``tokenizers`` (no ``transformers`` dependency).
* :func:`save_blob` / :func:`load_blob` — round-trip the weights through a
  single flat bf16 file, matching the C++ engine's expected
  ``layer_weights`` layout (see :mod:`serialize`).
* :func:`weights_summary` — print per-tensor shape/dtype stats for
  inspection.

CLI
---

The package is also runnable as a script::

    python3 -m weights --hf-dir <DIR> download
    python3 -m weights --hf-dir <DIR> inspect
    python3 -m weights --hf-dir <DIR> dump-blob build/weights.bin
    python3 -m weights --hf-dir <DIR> sample "The capital of France is"

This will populate the standard ``ModelWeights`` structure used by
``reference.ref_end_to_end_forward`` and validate end-to-end with the
real Qwen3.5 0.8B base model.
"""

from __future__ import annotations

from .convert import (
    hf_to_reference,
    load_reference_weights,
)
from .hf_loader import (
    LayerWeightsHF,
    ModelWeightsHF,
    load_hf_tokenizer,
    load_hf_weights,
    weights_summary,
)
from .serialize import (
    BLOB_HEADER_MAGIC,
    BLOB_HEADER_VERSION,
    blob_summary,
    load_blob,
    save_blob,
)

__all__ = [
    "load_hf_weights",
    "load_hf_tokenizer",
    "weights_summary",
    "ModelWeightsHF",
    "LayerWeightsHF",
    "save_blob",
    "load_blob",
    "blob_summary",
    "BLOB_HEADER_MAGIC",
    "BLOB_HEADER_VERSION",
    "hf_to_reference",
    "load_reference_weights",
]
