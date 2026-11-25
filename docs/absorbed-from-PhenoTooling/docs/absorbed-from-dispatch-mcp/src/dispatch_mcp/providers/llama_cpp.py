"""LlamaCpp provider for local LLM inference via llama-cpp-python.

This provider wraps a local llama.cpp server or directly loads a GGUF
model via the ``llama-cpp-python`` bindings. It implements the
:class:`Provider` protocol so it can be registered in the dispatch-mcp
provider registry and used as a drop-in local inference backend.

Usage
-----
The provider is configured via environment variables:

- ``LLAMA_CPP_MODEL_PATH`` — path to a GGUF model file (required for direct mode).
- ``LLAMA_CPP_SERVER_URL`` — URL of a running llama.cpp server (optional; takes precedence).
- ``LLAMA_CPP_N_CTX`` — context window size (default: 4096).
- ``LLAMA_CPP_N_GPU_LAYERS`` — layers offloaded to GPU (default: 0).

If ``LLAMA_CPP_SERVER_URL`` is set the provider operates in server mode,
issuing HTTP requests to a running llama.cpp server. Otherwise it loads
the model directly via ``llama-cpp-python``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

from dispatch_mcp.providers.base import Completion, Message, Provider

_logger = logging.getLogger("dispatch_mcp.providers.llama_cpp")


class LlamaCppProvider:
    """Provider for local LLM inference via llama-cpp-python.

    Wraps either a direct GGUF model load (``llama-cpp-python``) or an
    HTTP client against a running llama.cpp server.
    """

    def __init__(self) -> None:
        self.name = "llama_cpp"
        self._server_url = os.environ.get("LLAMA_CPP_SERVER_URL", "").strip()
        self._model_path = os.environ.get("LLAMA_CPP_MODEL_PATH", "").strip()
        self._n_ctx = int(os.environ.get("LLAMA_CPP_N_CTX", "4096"))
        self._n_gpu_layers = int(os.environ.get("LLAMA_CPP_N_GPU_LAYERS", "0"))
        self._model: Any = None  # lazy-loaded Llama instance

    # --------------------------------------------------------------- internal

    def _get_model(self) -> Any:
        """Lazy-load the Llama model (direct mode only)."""
        if self._model is not None:
            return self._model
        if not self._model_path:
            raise RuntimeError(
                "LLAMA_CPP_MODEL_PATH is required when LLAMA_CPP_SERVER_URL is not set"
            )
        try:
            from llama_cpp import Llama  # type: ignore[import-untyped]

            self._model = Llama(
                model_path=self._model_path,
                n_ctx=self._n_ctx,
                n_gpu_layers=self._n_gpu_layers,
                verbose=False,
            )
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            ) from None
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self._model_path}: {e}") from e
        return self._model

    def _is_server_mode(self) -> bool:
        return bool(self._server_url)

    def _build_prompt(self, messages: list[Message]) -> str:
        """Convert chat messages into a single prompt string."""
        parts: list[str] = []
        for m in messages:
            if m.role == "system":
                parts.append(f"<|system|>\n{m.content}\n")
            elif m.role == "user":
                parts.append(f"<|user|>\n{m.content}\n")
            elif m.role == "assistant":
                parts.append(f"<|assistant|>\n{m.content}\n")
        parts.append("<|assistant|>\n")
        return "".join(parts)

    # ----------------------------------------------------------- server mode

    async def _server_complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            payload: dict[str, Any] = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            resp = await client.post(
                f"{self._server_url.rstrip('/')}/completion",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("content", "")
            return Completion(
                text=text,
                model=data.get("model", "llama.cpp"),
                provider=self.name,
                input_tokens=data.get("tokens_generated", 0),  # approximate
                output_tokens=len(text.split()),
                finish_reason="stop",
            )

    async def _server_stream(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            payload: dict[str, Any] = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            async with client.stream(
                "POST",
                f"{self._server_url.rstrip('/')}/completion",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    content = obj.get("content", "")
                    if content:
                        yield content

    # ---------------------------------------------------------- direct mode

    async def _direct_complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        import anyio

        def _sync_complete() -> Completion:
            model = self._get_model()
            output = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=None,
                echo=False,
            )
            choice = output.get("choices", [{}])[0]
            text = choice.get("text", "")
            usage = output.get("usage", {})
            return Completion(
                text=text,
                model=os.path.basename(self._model_path),
                provider=self.name,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                finish_reason=choice.get("finish_reason", "stop"),
            )

        return await anyio.to_thread.run_sync(_sync_complete)

    async def _direct_stream(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        import anyio
        from anyio import create_taskinese, open_cancel

        model = self._get_model()
        generator = model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=None,
            echo=False,
            stream=True,
        )

        # Wrap the sync generator in async iteration via trio/anyio.
        # This is the standard pattern for bridging sync iterators.
        async def _iterate() -> AsyncIterator[str]:
            for chunk in generator:
                choice = chunk.get("choices", [{}])[0]
                text = choice.get("text", "")
                if text:
                    yield text

        async for token in _iterate():
            yield token

    # ---------------------------------------------------------------- public

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> Completion:
        prompt = self._build_prompt(messages)
        if self._is_server_mode():
            return await self._server_complete(prompt, max_tokens=max_tokens, temperature=temperature)
        return await self._direct_complete(prompt, max_tokens=max_tokens, temperature=temperature)

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        prompt = self._build_prompt(messages)
        if self._is_server_mode():
            async for token in self._server_stream(prompt, max_tokens=max_tokens, temperature=temperature):
                yield token
        else:
            async for token in self._direct_stream(prompt, max_tokens=max_tokens, temperature=temperature):
                yield token

    async def health(self) -> dict:
        t0 = time.perf_counter()
        try:
            if self._is_server_mode():
                import httpx

                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{self._server_url.rstrip('/')}/health")
                    r.raise_for_status()
                    return {
                        "status": "ok",
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                        "provider": self.name,
                        "mode": "server",
                    }
            else:
                # Direct mode: check if model is loaded
                _ = self._get_model()
                return {
                    "status": "ok",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "provider": self.name,
                    "mode": "direct",
                    "model": os.path.basename(self._model_path),
                }
        except Exception as e:
            return {
                "status": "error",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "provider": self.name,
                "error": f"{type(e).__name__}: {e}",
            }

    async def aclose(self) -> None:
        if self._model is not None:
            self._model = None

    def __repr__(self) -> str:
        mode = "server" if self._is_server_mode() else "direct"
        return f"<LlamaCppProvider mode={mode}>"