"""Back-compat alias for bench.adapters (some files import model_adapter)."""

from bench.adapters import (
    AnthropicAdapter,
    Completion,
    GeminiAdapter,
    HttpAnthropic,
    HttpGemini,
    HttpOpenAI,
    LocalPhenoAdapter,
    ModelAdapter,
    OpenAIAdapter,
    build_adapter,
    list_adapters,
    make_adapter,
    register_adapter,
)
from bench.adapters_mock import MockModel
from bench.adapters_typing import TypedAdapter

__all__ = [
    "AnthropicAdapter",
    "Completion",
    "GeminiAdapter",
    "HttpAnthropic",
    "HttpGemini",
    "HttpOpenAI",
    "LocalPhenoAdapter",
    "MockModel",
    "ModelAdapter",
    "OpenAIAdapter",
    "TypedAdapter",
    "build_adapter",
    "list_adapters",
    "make_adapter",
    "register_adapter",
]
