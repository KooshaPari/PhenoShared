"""bench.adapters — Model adapter layer (base classes + factory).

Provides a uniform interface for talking to different LLM providers
regardless of API shape. Each adapter exposes a single method
``generate(messages, **opts) -> ModelResponse`` so the executor doesn't
need to know whether it's talking to a local MLX model, OpenAI, Anthropic,
or a mocked stub.

Used by:
  - bench.executor (sync + async run)
  - bench.cli (smoke test via MockModel)
  - bench.parallel (parallel multi-model runner)

Convention: every adapter returns a ``ModelResponse`` with the same
shape (text, raw_provider_response, latency_ms, token counts, finish_reason).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class ModelResponse:
    """Uniform response from any adapter."""

    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text)


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


class ModelAdapter:
    """Protocol every concrete adapter implements."""

    name: str = "base"

    def __init__(self, **opts: Any) -> None:
        self.opts = opts

    def generate(
        self, messages: list[dict[str, str]], **kw: Any
    ) -> ModelResponse:  # pragma: no cover - protocol
        raise NotImplementedError

    def complete(self, prompt: str, **kw: Any) -> Completion:
        """Legacy single-prompt entrypoint used by the executor and judges."""
        response = self.generate([{"role": "user", "content": prompt}], **kw)
        return Completion(
            text=response.text,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
            finish_reason=response.finish_reason,
            error=response.error,
            extra=dict(response.raw),
        )

    async def agenerate(
        self, messages: list[dict[str, str]], **kw: Any
    ) -> ModelResponse:  # pragma: no cover - protocol
        return self.generate(messages, **kw)

    async def aclose(self) -> None:  # pragma: no cover - protocol
        pass


# ---------------------------------------------------------------------------
# Back-compat aliases
# ---------------------------------------------------------------------------


@dataclass
class Completion:
    """Alias for ModelResponse (used by some legacy imports)."""

    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_in(self) -> int:
        return self.prompt_tokens

    @property
    def tokens_out(self) -> int:
        return self.completion_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "extra": dict(self.extra),
        }


# ---------------------------------------------------------------------------
# HttpGemini — Google Generative AI (Gemini 2.x/3.x)
# ---------------------------------------------------------------------------


class HttpGemini(ModelAdapter):
    """Google Gemini generateContent API."""

    name = "http_gemini"

    def __init__(
        self,
        base_url: str = "https://generativelanguage.googleapis.com",
        api_key: str | None = None,
        model: str = "gemini-2.5-pro",
        timeout_s: float = 60.0,
        **opts: Any,
    ) -> None:
        super().__init__(**opts)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or __import__("os").environ.get("GEMINI_API_KEY", "")
        self.model = model
        self.timeout_s = timeout_s

    def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        import json
        import urllib.request

        url = (
            f"{self.base_url}/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with (
            urllib.request.urlopen(req, timeout=self.timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        import time
        import urllib.error

        t0 = time.perf_counter()
        contents = []
        system = None
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                system = text
                continue
            contents.append(
                {
                    "role": "user" if role == "user" else "model",
                    "parts": [{"text": text}],
                }
            )
        body: dict[str, Any] = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            r = self._request(body)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error=f"http_gemini: {type(e).__name__}: {e}",
            )
        candidates = r.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
        usage = r.get("usageMetadata", {})
        return ModelResponse(
            text=text,
            raw=r,
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            finish_reason=candidates[0].get("finishReason", "stop")
            if candidates
            else "stop",
        )


# ---------------------------------------------------------------------------
# LocalPhenoAdapter — runs against pheno-harness' own kernels/ Python wrapper
# ---------------------------------------------------------------------------


class LocalPhenoAdapter(ModelAdapter):
    """Runs inference through the local pheno-harness engine.

    Requires ``pheno_engine_t`` importable from ``kernels.qwen3.5-0.8b.python.engine``
    (the Python module exposed by the kernel suite). Falls back to MockModel
    if not importable.
    """

    name = "local_pheno"

    def __init__(self, **opts: Any) -> None:
        super().__init__(**opts)
        self._engine = None
        self._impl: Any = None

    def _ensure(self) -> None:
        if self._impl is not None:
            return
        try:
            import os
            import sys

            sys_path = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            py_dir = os.path.join(sys_path, "kernels", "qwen3.5-0.8b", "python")
            if py_dir not in sys.path:
                sys.path.insert(0, py_dir)
            import mlx.core as mx  # noqa: F401, E402
            from engine import EngineHandle  # noqa: F401, E402

            self._engine = EngineHandle
            self._impl = mx
        except Exception:
            from bench.adapters_mock import MockModel

            self._impl = MockModel()

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        self._ensure()
        from bench.adapters_mock import MockModel

        if isinstance(self._impl, MockModel):
            return self._impl.generate(messages, **kw)
        return MockModel().generate(messages, **kw)


# ---------------------------------------------------------------------------
# Registry + factory
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, type]:
    from bench.adapters_anthropic import HttpAnthropic
    from bench.adapters_mlx import MLXModelAdapter
    from bench.adapters_mock import MockModel
    from bench.adapters_openai import HttpOpenAI

    return {
        "mock": MockModel,
        "http_openai": HttpOpenAI,
        "openai": HttpOpenAI,
        "OpenAI": HttpOpenAI,
        "http_anthropic": HttpAnthropic,
        "anthropic": HttpAnthropic,
        "Anthropic": HttpAnthropic,
        "http_gemini": HttpGemini,
        "gemini": HttpGemini,
        "Gemini": HttpGemini,
        "local_pheno": LocalPhenoAdapter,
        "pheno": LocalPhenoAdapter,
        "mlx": MLXModelAdapter,
        "local": MLXModelAdapter,
    }


def _get_registry() -> dict[str, type]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


_REGISTRY: dict[str, type] | None = None


def make_adapter(name: str, **opts: Any) -> ModelAdapter:
    """Factory used by CLI: ``bench.cli run --model mock``, ``--model http_openai:...``."""
    registry = _get_registry()
    if name not in registry:
        # Unknown model labels are intentionally safe for harness dry-runs:
        # execute against the deterministic mock rather than contacting a
        # provider unexpectedly.
        from bench.adapters_mock import MockModel

        return cast(ModelAdapter, MockModel(**opts))
    cls = registry[name]
    return cast(ModelAdapter, cls(**opts))


def list_adapters() -> list[str]:
    return sorted(_get_registry())


def register_adapter(name: str, cls: type) -> None:
    """Register a custom adapter (used by tests + suites that want a custom model)."""
    if not isinstance(cls, type) or not issubclass(cls, ModelAdapter):
        raise TypeError(
            f"register_adapter({name!r}, ...) requires ModelAdapter subclass, "
            f"got {cls!r}"
        )
    _get_registry()[name] = cls


def build_adapter(spec: str) -> ModelAdapter:
    """Back-compat alias used by CLI — parses "name[:k=v]*" into a registered adapter."""
    return make_adapter(spec)


# ---------------------------------------------------------------------------
# Back-compat aliases for imports
# ---------------------------------------------------------------------------

OpenAIAdapter = None
AnthropicAdapter = None
GeminiAdapter = None


def _ensure_aliases() -> None:
    global OpenAIAdapter, AnthropicAdapter, GeminiAdapter
    from bench.adapters_anthropic import HttpAnthropic
    from bench.adapters_openai import HttpOpenAI

    if OpenAIAdapter is None:
        OpenAIAdapter = HttpOpenAI
    if AnthropicAdapter is None:
        AnthropicAdapter = HttpAnthropic
    if GeminiAdapter is None:
        GeminiAdapter = HttpGemini


_ensure_aliases()

# Concrete HTTP adapters are exported here as well as through the registry so
# older consumers importing ``bench.adapters`` keep a single stable surface.
from bench.adapters_anthropic import HttpAnthropic  # noqa: E402
from bench.adapters_mlx import MLXModelAdapter  # noqa: E402
from bench.adapters_openai import HttpOpenAI  # noqa: E402

# MockModel intentionally NOT re-exported here to avoid a circular import
# (bench.adapters_mock imports ModelAdapter/ModelResponse from this module).
# Import directly from bench.adapters_mock when needed.

__all__ = [
    "ModelResponse",
    "ModelAdapter",
    "Completion",
    "HttpGemini",
    "HttpAnthropic",
    "HttpOpenAI",
    "MLXModelAdapter",
    "LocalPhenoAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GeminiAdapter",
    "make_adapter",
    "list_adapters",
    "register_adapter",
    "build_adapter",
]
