"""Adapter layer: vLLM / TensorRT / SGLang / llama.cpp / MLX / Metal.

Each backend exposes a uniform `generate(prompt, **kw) -> str` interface that
the OMLX server / CLI / GUI can call without committing to a specific engine.
"""

from .base import BackendBase, BackendCapabilities, GenerateRequest, GenerateResponse
from .llamacpp_backend import LlamaCppBackend
from .metal_backend import MetalKernelBackend
from .mlx_backend import MlxBackend
from .sglang_backend import SglangBackend
from .tensorrt_backend import TensorrtBackend
from .vllm_backend import VllmBackend

__all__ = [
    "BackendBase",
    "BackendCapabilities",
    "GenerateRequest",
    "GenerateResponse",
    "LlamaCppBackend",
    "MetalKernelBackend",
    "MlxBackend",
    "SglangBackend",
    "TensorrtBackend",
    "VllmBackend",
]
