"""OpenAI adapter for the model-adapter layer."""

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

openai: Any = None
try:
    import openai as _openai_mod  # noqa: F401

    openai = _openai_mod
except Exception:  # pragma: no cover  # nosec B110
    pass


def _resolve_openai_class() -> Any:
    """Return the (possibly monkey-patched) ``openai.OpenAI`` class.

    Prefers the module-level ``openai.OpenAI`` attribute (monkeypatch target).
    Falls back to a fresh import.
    """
    mod = globals().get("openai")
    if mod is not None and getattr(mod, "OpenAI", None) is not None:
        return mod.OpenAI
    try:
        import openai as _o

        return _o.OpenAI
    except Exception:
        return None


class OpenAIAdapter(ModelAdapter):
    """OpenAI / OpenAI-compatible adapter (Chat Completions API).

    Also used for OmniRoute's ``Main`` combo tier (per AGENTS.md), which exposes
    an OpenAI-compatible endpoint at ``http://127.0.0.1:20128/v1``.
    """

    name: ClassVar[str] = "openai"

    def __init__(
        self,
        *,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(model_id=model_id)
        cls = _resolve_openai_class()
        if cls is None:
            raise MissingDependencyError(
                "openai SDK not installed; `pip install openai`"
            )
        kwargs: dict[str, Any] = {}
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        # OpenAI SDK requires api_key; supply a benign default when absent so
        # callers like OmniRoute's ``Main`` blend can be constructed in tests /
        # dry-runs without a real secret.  The default is overridden if a real
        # key is found in env.
        if resolved_key:
            kwargs["api_key"] = resolved_key
        else:
            kwargs["api_key"] = "sk-bench-runner-no-key"
        resolved_base = base_url or os.environ.get("OPENAI_BASE_URL")
        if resolved_base:
            kwargs["base_url"] = resolved_base
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
        """Call OpenAI Chat Completions and return the Completion."""
        import time as _t

        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs: dict[str, Any] = {
            "model": self._model,
            "temperature": float(temperature),
            "messages": messages,
        }
        if max_tokens > 0:
            kwargs["max_tokens"] = int(max_tokens)
        if extra:
            kwargs.update(dict(extra))
        t0 = _t.monotonic()
        try:
            resp = self._client.chat.completions.create(timeout=timeout_s, **kwargs)
        except Exception:  # noqa: BLE001
            self._record(Completion(text=""), ok=False)
            raise
        dt = (_t.monotonic() - t0) * 1000.0
        text = ""
        choices = getattr(resp, "choices", None) or []
        if choices:
            text = (
                (choices[0].message.content or "")
                if getattr(choices[0], "message", None)
                else ""
            )
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        ct = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        comp = Completion(
            text=text,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=dt,
            extra={
                "id": getattr(resp, "id", None),
                "model": getattr(resp, "model", self._model),
            },
        )
        return self._record(comp, ok=True)
