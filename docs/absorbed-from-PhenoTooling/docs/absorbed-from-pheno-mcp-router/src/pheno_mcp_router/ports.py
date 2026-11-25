"""Hexagonal port abstractions for pheno-mcp-router.

L4 ports define the *outward-facing* surface of the router substrate: any
collaborator (LLM provider, KV store, MCP tool) is reachable through one of
three small protocols. Concrete adapters — see :mod:`pheno_mcp_router.adapters` —
implement the matching abstract base classes.

Design notes
------------
* Protocols express *structural* (duck-typed) contracts, so tests and
  third-party code can satisfy the surface without inheriting anything.
* ABCs are provided for authors who prefer nominal subtyping and want
  free ``isinstance`` checks via :func:`register`.
* All methods are async because every real adapter we ship is I/O bound
  (HTTP, filesystem, tool dispatch). The Protocol signatures are the
  source of truth — the ABCs delegate to ``NotImplementedError``.
* No runtime imports of heavyweight SDKs happen here. The LLM/Storage
  ABCs do not pull httpx; only concrete adapters do.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Protocol surfaces (structural typing — duck-typed)
# ---------------------------------------------------------------------------


@runtime_checkable
class LlmPort(Protocol):
    """Anything that can answer a chat completion in one round trip.

    Implementations MUST be safe to call concurrently from multiple
    tasks. The ``messages`` argument follows the OpenAI/Anthropic
    ``list[dict]`` convention; ``model`` is the provider-specific
    model identifier. The return value is the assistant text only —
    callers wanting token accounting or logprobs should depend on a
    richer adapter, not this substrate-level port.
    """

    async def chat(self, messages: list[Mapping[str, Any]], model: str) -> str:
        """Return the assistant's reply text for ``messages``/``model``."""
        ...


@runtime_checkable
class StoragePort(Protocol):
    """Async key/value contract used by router middleware.

    Keys are short, filesystem-safe strings. Values are JSON-serialisable
    scalars or mappings. Implementations are expected to be eventually
    consistent across replicas when running in a multi-process setting.
    """

    async def get(self, key: str) -> Any | None:
        """Return the stored value for ``key`` or ``None`` if absent."""
        ...

    async def set(self, key: str, value: Any) -> None:
        """Persist ``value`` under ``key`` (overwrite is allowed)."""
        ...

    async def delete(self, key: str) -> None:
        """Remove ``key``; missing keys are silently ignored."""
        ...


@runtime_checkable
class ToolPort(Protocol):
    """An MCP-style tool that can be invoked by name.

    Tools expose a stable ``name`` and human-readable ``description`` so
    routers can list them, and an ``invoke`` coroutine that accepts a
    free-form ``args`` mapping and returns a JSON-serialisable result.
    """

    def name(self) -> str:
        """Stable, dotted tool name (e.g. ``"phenotype.fetch_user"``)."""
        ...

    def description(self) -> str:
        """One-line human description suitable for LLM tool prompts."""
        ...

    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run the tool with ``args`` and return a JSON-safe result."""
        ...


# ---------------------------------------------------------------------------
# Abstract base classes (nominal typing — for adapter authors)
# ---------------------------------------------------------------------------


class LlmAdapter(ABC):
    """Abstract base for LLM providers.

    Subclasses must implement :meth:`chat`. The base class is intentionally
    minimal so that future LLM-specific helpers (token counting, streaming,
    tool calls) can be added without breaking the public Protocol.
    """

    @abstractmethod
    async def chat(self, messages: list[Mapping[str, Any]], model: str) -> str:
        """Return the assistant's reply text for ``messages``/``model``."""
        raise NotImplementedError


class StorageAdapter(ABC):
    """Abstract base for KV stores used by router middleware."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError


class ToolAdapter(ABC):
    """Abstract base for MCP tools exposed through the router."""

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


__all__ = [
    "LlmAdapter",
    "LlmPort",
    "StorageAdapter",
    "StoragePort",
    "ToolAdapter",
    "ToolPort",
]
