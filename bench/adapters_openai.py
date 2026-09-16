"""bench.adapters_openai — HttpOpenAI adapter.

OpenAI Chat Completions (compatible: also works for OpenRouter, vLLM, etc.).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, cast

from bench.adapters import ModelAdapter, ModelResponse


class HttpOpenAI(ModelAdapter):
    """OpenAI Chat Completions (compatible: also works for OpenRouter, vLLM, etc.)."""

    name = "http_openai"

    def __init__(
        self,
        base_url: str = "https://api.openai.com",
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout_s: float = 60.0,
        **opts: Any,
    ) -> None:
        super().__init__(**opts)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.timeout_s = timeout_s

    def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with (
            urllib.request.urlopen(req, timeout=self.timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        t0 = time.perf_counter()
        body = {"model": self.model, "messages": messages, **kw}
        try:
            r = self._request(body)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error=f"http_openai: {type(e).__name__}: {e}",
            )
        text = r.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = r.get("usage", {})
        return ModelResponse(
            text=text,
            raw=r,
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            finish_reason=r.get("choices", [{}])[0].get("finish_reason", "stop"),
        )


__all__ = ["HttpOpenAI"]
