"""Typed Protocol for ``bench`` model adapters.

This module provides a runtime-checkable ``TypedAdapter`` Protocol that
documents the structural contract every concrete adapter (MockModel,
MLXStubAdapter, HttpGemini, HttpOpenAI, HttpAnthropic, LocalPhenoAdapter)
must satisfy. The Protocol is intentionally narrow:

  - ``name``: registry key (str)
  - ``generate(messages, **kw) -> ModelResponse``: synchronous entrypoint
  - ``agenerate(messages, **kw) -> ModelResponse``: async entrypoint
  - ``aclose() -> None``: cleanup (no-op for non-network adapters)

Why a Protocol here?
  - The ``bench.executor`` and ``bench.parallel`` modules need to
    accept either a real adapter or a stub without runtime dispatch.
  - Structural typing lets us add new adapters in separate modules
    without touching the executor.

Use ``isinstance(adapter, TypedAdapter)`` in tests to assert conformance.

This module corresponds to WBS v0.10 Phase 6 (task 93 — typed Adapter
protocol).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TypedAdapter(Protocol):
    """Structural contract for any bench model adapter.

    Concrete adapters: MockModel, MLXStubAdapter, HttpGemini,
    HttpOpenAI, HttpAnthropic, LocalPhenoAdapter.

    The Protocol captures the synchronous + asynchronous entrypoints
    that ``bench.executor`` and ``bench.parallel`` rely on.
    """

    name: str

    def generate(
        self,
        messages: list[dict[str, str]],
        **kw: Any,
    ) -> Any: ...  # returns ModelResponse

    async def agenerate(
        self,
        messages: list[dict[str, str]],
        **kw: Any,
    ) -> Any: ...  # returns ModelResponse

    async def aclose(self) -> None: ...


__all__ = ["TypedAdapter"]
