"""Minimal scaffold for SGLang direct adapter.

Provides SGLangDirect class and is_available() for direct SGLang model
execution without the bench.adapters wrapper. Used by stock_vs_ours benchmark
to exercise the matrix's SGLang docker npipe leg.

Usage (host with SGLang runtime + a Qwen3.5-0.8B model loaded):
    adapter = SGLangDirect(base_url="http://127.0.0.1:30000/v1",
                            model="Qwen/Qwen3.5-0.8B")
    text = adapter.generate("Explain quantization in one sentence.")

Docker npipe preconditions:
    docker run --rm -p 30000:30000 -v /path/to/models:/models \\
        lmsysorg/sglang:latest \\
        python -m sglang.launch_server \\
        --model-path /models/Qwen3.5-0.8B \\
        --host 0.0.0.0 --port 30000 \\
        --chat-template qwen2

The adapter uses the OpenAI-compatible HTTP endpoint exposed by sglang's
launch_server. It does NOT use named pipes (npipe) directly because
sglang's IPC is HTTP/JSON; the "npipe leg" in the matrix refers to the
sglang engine's intra-process named-pipe channel between scheduler and
detokenizer (only available when the engine runs in-process, e.g. via
sglang.Runtime(model_path=...)). For cross-process comparison we use the
HTTP endpoint.

This module is intentionally a scaffold: it only imports requests when
SGLangDirect.generate() is actually called. The bench harness detects
is_available() at module load to decide whether to include this leg in
the matrix; we report available iff the env var PHENO_SGLANG_URL is set.
"""

from __future__ import annotations

import os
from typing import Any


def is_available() -> bool:
    """SGLang is reachable iff PHENO_SGLANG_URL is set AND responds 200 to /v1/models."""
    url = os.environ.get("PHENO_SGLANG_URL")
    if not url:
        return False
    try:
        import requests  # noqa: F401

        r = requests.get(f"{url.rstrip('/')}/models", timeout=2.0)
        return bool(r.ok)
    except Exception:
        return False


class SGLangDirect:
    """Direct SGLang HTTP adapter (OpenAI-compatible)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int = 512,
    ) -> None:
        self._base_url = (base_url or os.environ.get("PHENO_SGLANG_URL") or "").rstrip("/")
        self._model = model or os.environ.get("PHENO_SGLANG_MODEL") or "default"
        self._max_tokens = max_tokens
        if not self._base_url:
            raise RuntimeError(
                "SGLangDirect needs PHENO_SGLANG_URL env var or explicit base_url."
            )

    @property
    def model_id(self) -> str:
        """Public alias used by the matrix to match against the harness's model registry."""
        return self._model

    def generate(
        self, prompt: str, *, max_tokens: int | None = None, **kwargs: Any
    ) -> str:
        """Send a prompt to the SGLang /v1/chat/completions endpoint and return text."""
        import requests

        mt = max_tokens or self._max_tokens
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": mt,
            "temperature": kwargs.get("temperature", 0.0),
        }
        r = requests.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            timeout=kwargs.get("timeout", 60.0),
        )
        r.raise_for_status()
        data = r.json()
        # OpenAI-compatible: choices[0].message.content
        return str(data["choices"][0]["message"]["content"])

    def close(self) -> None:
        """SGLang is a managed subprocess / docker container — no per-call teardown needed."""
        return None
