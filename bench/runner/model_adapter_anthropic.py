"""Anthropic adapter for the model-adapter layer."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, ClassVar

from bench.runner.model_adapter import (
    Completion,
    MissingDependencyError,
    ModelAdapter,
)

# ---------------------------------------------------------------------------
# Guarded import — keeps the harness runnable when the SDK is absent.
# ---------------------------------------------------------------------------

try:
    import anthropic as _anthropic_mod  # noqa: F401

    Anthropic = _anthropic_mod.Anthropic
except Exception:  # pragma: no cover
    _anthropic_mod = None
    Anthropic = None


def _resolve_anthropic_class() -> Any:
    """Return the (possibly monkey-patched) ``anthropic.Anthropic`` class.

    Prefers the module-level ``Anthropic`` symbol (so tests can monkeypatch
    ``bench.runner.model_adapter.Anthropic`` directly).  Falls back to a fresh
    import so production code without an explicit patch still works.
    """
    cls = globals().get("Anthropic")
    if cls is not None:
        return cls
    try:
        import anthropic as _a

        return _a.Anthropic
    except Exception:
        return None


class AnthropicAdapter(ModelAdapter):
    """Anthropic adapter (Messages API)."""

    name: ClassVar[str] = "anthropic"

    def __init__(
        self,
        *,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(model_id=model_id)
        cls = _resolve_anthropic_class()
        if cls is None:
            raise MissingDependencyError(
                "anthropic SDK not installed; `pip install anthropic`"
            )
        kwargs: dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        elif os.environ.get("ANTHROPIC_API_KEY"):
            kwargs["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        if base_url:
            kwargs["base_url"] = base_url
        self._client = cls(**kwargs)
        self._model = model_id

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
        """Call the Anthropic Messages API and return the Completion."""
        import time as _t

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max(1, int(max_tokens)),
            "temperature": float(temperature),
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if extra:
            kwargs.update(dict(extra))
        t0 = _t.monotonic()
        try:
            resp = self._client.messages.create(timeout=timeout_s, **kwargs)
        except Exception:  # noqa: BLE001
            self._record(Completion(text=""), ok=False)
            raise
        dt = (_t.monotonic() - t0) * 1000.0
        text_parts: list[str] = []
        for block in getattr(resp, "content", []) or []:
            t = getattr(block, "text", None)
            if t:
                text_parts.append(t)
        text = "\n".join(text_parts) or ""
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "input_tokens", 0) or 0)
        ct = int(getattr(usage, "output_tokens", 0) or 0)
        comp = Completion(
            text=text,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=dt,
            extra={
                "stop_reason": getattr(resp, "stop_reason", None),
                "id": getattr(resp, "id", None),
                "model": getattr(resp, "model", self._model),
            },
        )
        return self._record(comp, ok=True)
