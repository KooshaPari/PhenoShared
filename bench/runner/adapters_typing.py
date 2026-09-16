"""Typed Protocol for ``bench.runner`` model adapters.

This module provides a runtime-checkable ``TypedAdapter`` Protocol that
documents the structural contract every concrete runner adapter
(MLXStubAdapter, MLXAdapter, OpenAIAdapter, AnthropicAdapter, VLLMAdapter)
must satisfy. The Protocol is intentionally narrow:

  - ``name``: registry key (str)
  - ``complete(prompt, *, temperature, max_tokens, system, timeout_s, extra) -> Completion``

Why a Protocol here?
  - The ``bench.runner.executor`` module needs to accept either a real
    adapter or a stub without runtime dispatch.
  - Structural typing lets us add new adapters in separate modules
    without touching the executor.

Use ``isinstance(adapter, TypedAdapter)`` in tests to assert conformance.

This module corresponds to WBS v0.10 Phase 6 (task 93 — typed Adapter
protocol). The sibling ``bench.adapters_typing`` covers the top-level
``bench.adapters`` layer (which uses ``generate(messages) -> ModelResponse``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TypedAdapter(Protocol):
    """Structural contract for any bench.runner model adapter.

    Concrete adapters: MLXStubAdapter, MLXAdapter, OpenAIAdapter,
    AnthropicAdapter, VLLMAdapter.

    The Protocol captures the synchronous entrypoint that
    ``bench.runner.executor`` relies on.
    """

    name: str

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = ...,
        max_tokens: int = ...,
        system: str | None = ...,
        timeout_s: float = ...,
        extra: Mapping[str, Any] | None = ...,
    ) -> Any: ...  # returns Completion


__all__ = ["TypedAdapter"]
