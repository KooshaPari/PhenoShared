"""bench.adapters_anthropic — HttpAnthropic adapter.

Anthropic Messages API (Claude Opus 4.x / Sonnet 4.x / 5.x).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, cast

from bench.adapters import ModelAdapter, ModelResponse


class HttpAnthropic(ModelAdapter):
    """Anthropic Messages API (Claude Opus 4.x / Sonnet 4.x / 5.x)."""

    name = "http_anthropic"

    def __init__(
        self,
        base_url: str = "https://api.anthropic.com",
        api_key: str | None = None,
        model: str = "claude-sonnet-5-20251008",
        timeout_s: float = 60.0,
        max_tokens: int = 1024,
        **opts: Any,
    ) -> None:
        super().__init__(**opts)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens

    def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/messages"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with (
            urllib.request.urlopen(req, timeout=self.timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        t0 = time.perf_counter()
        system = None
        anthropic_msgs = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                anthropic_msgs.append(m)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_msgs,
            "max_tokens": self.max_tokens,
        }
        if system:
            body["system"] = system
        body.update({k: v for k, v in kw.items() if k not in {"messages", "model"}})
        try:
            r = self._request(body)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error=f"http_anthropic: {type(e).__name__}: {e}",
            )
        text = "".join(
            blk.get("text", "")
            for blk in r.get("content", [])
            if blk.get("type") == "text"
        )
        usage = r.get("usage", {})
        return ModelResponse(
            text=text,
            raw=r,
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            finish_reason=r.get("stop_reason", "stop") or "stop",
        )


__all__ = ["HttpAnthropic"]
