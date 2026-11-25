"""InferencePort — abstract interface for model inference.

Concrete adapters (OpenAI, Anthropic, MLX, vLLM, Mock) implement this port
so the executor and domain services depend only on the interface, never on
a specific provider SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InferencePort(ABC):
    """Port for model inference.  Adapters implement this."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        """Generate a response from a list of chat messages."""
        ...

    @abstractmethod
    async def agenerate(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        """Async variant of :meth:`generate`."""
        ...

    @abstractmethod
    async def aclose(self) -> None:
        """Release any held resources (HTTP sessions, SDK clients)."""
        ...
