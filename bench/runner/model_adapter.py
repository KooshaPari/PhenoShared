"""Model-adapter layer for the runner.

This module defines:

* ``ModelAdapter`` — abstract base class.  Subclasses must implement
  ``complete(prompt, *, temperature, max_tokens)`` returning a ``Completion``
  namedtuple-like record carrying the generated text and token counts.
* ``AnthropicAdapter`` — uses the official ``anthropic`` Python client.
* ``OpenAIAdapter`` — uses the official ``openai`` Python client.
* ``MLXAdapter`` — uses Apple MLX via ``mlx_lm`` (loaded in-process).
* ``VLLMAdapter`` — calls an OpenAI-compatible HTTP endpoint exposed by a vLLM
  server (e.g. ``http://127.0.0.1:8000/v1``).  Implemented in pure ``urllib``
  so it doesn't require the ``openai`` SDK at test time.

The ``--model`` CLI flag selects which adapter to construct via
``build_adapter()``.  The selector is human-friendly by string prefix:

| Prefix                       | Adapter class       |
|------------------------------|---------------------|
| ``claude-*``, ``anthropic-*``| ``AnthropicAdapter``|
| ``gpt-*``, ``o1-*``, ``o3-*``| ``OpenAIAdapter``   |
| ``mlx-*``                    | ``MLXAdapter``      |
| ``mlx-stub``                 | ``MLXStubAdapter``  |
| ``vllm://...``, ``http(s)://*`` | ``VLLMAdapter`` |
| ``Main`` (OmniRoute blend)   | ``OpenAIAdapter``   |

All adapters lazy-import their SDK so the harness can run unit tests without
the SDK installed.  Missing-dependency failures raise ``MissingDependencyError``.

Sub-adapter implementations live in sibling modules for modularity:

* ``model_adapter_anthropic`` — ``AnthropicAdapter``
* ``model_adapter_openai``    — ``OpenAIAdapter``
* ``model_adapter_mlx``       — ``MLXAdapter``
* ``model_adapter_mock``      — ``MLXStubAdapter``

``VLLMAdapter`` stays here because it only uses the stdlib ``urllib``.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from bench.ports.inference import InferencePort
from bench.runner.adapters_typing import TypedAdapter

# The sibling adapters (AnthropicAdapter, OpenAIAdapter, MLXAdapter,
# MLXStubAdapter) live in their own modules to avoid a circular
# import (model_adapter_anthropic.py imports Completion / ModelAdapter
# from this module). Import them lazily inside build_adapter() so the
# public API still works.

# Tokens counts are estimates for MLX (the library doesn't surface them);
# for Anthropic / OpenAI / vLLM the SDK returns authoritative counts.


@dataclass
class Completion:
    """One model completion.

    ``latency_ms`` is wall-clock from ``complete()`` entry to response decoding
    (not including the cache key seek).  ``extra`` carries provider-specific
    fields (e.g. ``stop_reason``, ``id``).
    """

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return asdict(self)


class MissingDependencyError(ImportError):
    """Raised when a model adapter's optional SDK isn't installed."""


class ModelAdapter(InferencePort, ABC):
    """Abstract model adapter interface.

    Inherits from :class:`InferencePort` (hexagonal ports layer) so the
    executor and domain services depend only on the port contract.

    Concrete subclasses must override ``name`` (str property used in cache keys
    and the RunReport) and ``complete()``.  The base class tracks per-call
    counters that are aggregated by the executor.
    """

    #: provider name used in cache keys & RunReport
    name: ClassVar[str] = ""

    def __init__(self, *, model_id: str) -> None:
        self.model_id = model_id
        self._call_count = 0
        self._error_count = 0
        self._total_tokens = 0

    # -- counters -------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Number of completed ``complete()`` invocations on this adapter."""
        return self._call_count

    @property
    def error_count(self) -> int:
        """Number of failed ``complete()`` invocations on this adapter."""
        return self._error_count

    @property
    def total_tokens(self) -> int:
        """Sum of prompt + completion tokens for completed calls."""
        return self._total_tokens

    # -- main API -------------------------------------------------------

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        system: str | None = None,
        timeout_s: float = 120.0,
        extra: Mapping[str, Any] | None = None,
    ) -> Completion:
        """Generate one completion.  Must be safe to call from a thread."""

    async def aclose(self) -> None:
        """Release any held resources (HTTP sessions, SDK clients).  Default: no-op."""

    # -- InferencePort bridge --------------------------------------------

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> Completion:
        """InferencePort adapter: delegates to :meth:`complete`."""
        prompt = messages[-1]["content"] if messages else ""
        system = None
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
                break
        return self.complete(
            prompt,
            temperature=float(kwargs.get("temperature", 0.0)),
            max_tokens=int(kwargs.get("max_tokens", 1024)),
            system=system,
            timeout_s=float(kwargs.get("timeout_s", 120.0)),
            extra=kwargs.get("extra"),
        )

    async def agenerate(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> Completion:
        """InferencePort async adapter: delegates to :meth:`generate` in a thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.generate(messages, **kwargs)
        )

    # -- helpers --------------------------------------------------------

    def _record(self, comp: Completion, *, ok: bool) -> Completion:
        """Internal bookkeeping: bump counters and return the same Completion."""
        if ok:
            self._call_count += 1
            self._total_tokens += int(comp.prompt_tokens) + int(comp.completion_tokens)
        else:
            self._error_count += 1
        return comp


# ---------------------------------------------------------------------------
# vLLM (OpenAI-compatible HTTP) — stdlib-only, stays in the base module
# ---------------------------------------------------------------------------


class VLLMAdapter(ModelAdapter):
    """vLLM via OpenAI-compatible HTTP API (server-side ``vllm serve``)."""

    name: ClassVar[str] = "vllm"

    def __init__(
        self,
        *,
        model_id: str,
        base_url: str = "http://127.0.0.1:8000/v1",
        api_key: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        super().__init__(model_id=model_id)
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.environ.get("VLLM_API_KEY", "EMPTY")
        self._timeout_s = timeout_s

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        system: str | None = None,
        timeout_s: float = 120.0,
        extra: Mapping[str, Any] | None = None,
    ) -> Completion:
        import time as _t

        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        if extra:
            payload.update(dict(extra))
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        t0 = _t.monotonic()
        try:
            with (
                urllib.request.urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError):
            self._record(Completion(text=""), ok=False)
            raise
        except Exception:  # noqa: BLE001
            self._record(Completion(text=""), ok=False)
            raise
        dt = (_t.monotonic() - t0) * 1000.0
        text = ""
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message", {})
                text = msg.get("content", "") or ""
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        pt = int(usage.get("prompt_tokens", 0) or 0)
        ct = int(usage.get("completion_tokens", 0) or 0)
        comp = Completion(
            text=text,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=dt,
            extra={"provider": "vllm", "base_url": self._base_url},
        )
        return self._record(comp, ok=True)


# ---------------------------------------------------------------------------
# Adapter selector (factory)
# ---------------------------------------------------------------------------


def build_adapter(
    model: str, *, api_key: str | None = None, base_url: str | None = None
) -> ModelAdapter:
    """Select an adapter for a ``--model`` string.

    Recognized prefixes (case-insensitive):

    * ``claude-*``, ``anthropic-*``           → ``AnthropicAdapter``
    * ``gpt-*``, ``o1-*``, ``o3-*``, ``Main`` → ``OpenAIAdapter``
    * ``mlx-stub``                            → ``MLXStubAdapter``
    * ``mlx-*``                               → ``MLXAdapter`` (falls back to stub on missing dep)
    * ``vllm://...``, ``http://*``, ``https://*`` → ``VLLMAdapter``
    * anything else                           → ``MLXStubAdapter`` (safe fallback)

    Unknown prefixes deliberately fall back to the stub rather than raising
    so unit tests can pass ``--model foo`` to exercise the rest of the harness.
    Callers that need strictness should explicit-construct themselves.
    """
    # Lazy imports to avoid pulling in optional SDKs at module load time.
    from bench.runner.model_adapter_anthropic import AnthropicAdapter
    from bench.runner.model_adapter_mlx import MLXAdapter
    from bench.runner.model_adapter_mock import MLXStubAdapter
    from bench.runner.model_adapter_openai import OpenAIAdapter

    needle = model.strip()
    lo = needle.lower()
    if lo == "mlx-stub":
        return MLXStubAdapter(model_id=needle)
    if lo.startswith("claude-") or lo.startswith("anthropic-"):
        return AnthropicAdapter(model_id=needle, api_key=api_key, base_url=base_url)
    if (
        lo.startswith("gpt-")
        or lo.startswith("o1-")
        or lo.startswith("o3-")
        or needle == "Main"
    ):
        return OpenAIAdapter(model_id=needle, api_key=api_key, base_url=base_url)
    if lo.startswith("mlx-"):
        try:
            return MLXAdapter(model_id=needle)
        except MissingDependencyError:
            # Spec: missing optional dep shouldn't kill a smoke test.
            return MLXStubAdapter(model_id=needle)
    if lo.startswith("vllm://"):
        base = needle[len("vllm://") :]
        if not base.startswith("http"):
            base = "http://" + base
        return VLLMAdapter(model_id=needle, base_url=base)
    if lo.startswith("http://") or lo.startswith("https://"):
        return VLLMAdapter(
            model_id=needle,
            base_url=needle if needle.endswith("/v1") else needle.rstrip("/") + "/v1",
        )
    # Fallback: stub (lets you run smoke tests with whatever identifier).
    return MLXStubAdapter(model_id=needle)


__all__ = [
    "Completion",
    "ModelAdapter",
    "TypedAdapter",
    "VLLMAdapter",
    "MissingDependencyError",
    "build_adapter",
    # Note: AnthropicAdapter, OpenAIAdapter, MLXAdapter, MLXStubAdapter
    # live in sibling modules (model_adapter_anthropic, _openai, _mlx,
    # _mock) and are NOT re-exported here to avoid a circular import.
    # Import them from their own modules:
    #   from bench.runner.model_adapter_anthropic import AnthropicAdapter
    #   from bench.runner.model_adapter_openai import OpenAIAdapter
    #   from bench.runner.model_adapter_mlx import MLXAdapter
    #   from bench.runner.model_adapter_mock import MLXStubAdapter
]
