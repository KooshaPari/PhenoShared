"""Concrete adapter implementations for pheno-mcp-router ports.

Six adapters ship in this module — three I/O-bound (httpx LLM clients and
a JSON-file KV store) and three in-process helpers for tests and the
prompt-regression harness:

* :class:`OpenAIAdapter`         — `api.openai.com/v1/chat/completions`
* :class:`AnthropicAdapter`      — `api.anthropic.com/v1/messages`
* :class:`InMemoryStorageAdapter` — dict-backed KV for tests
* :class:`JsonFileStorageAdapter` — JSON-file-backed KV (persistent)
* :class:`EchoToolAdapter`       — round-trips ``args`` for tool tests
* :class:`PromptTestToolAdapter` — wraps :func:`pheno_prompt_test.run_case`
                                   so MCP servers can run prompt
                                   regression suites through the router.

The HTTP adapters use ``httpx.AsyncClient`` lazily so the module is safe
to import from environments without network access.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

import httpx

from pheno_mcp_router import config as _config
from pheno_mcp_router.ports import LlmAdapter, StorageAdapter, ToolAdapter

try:  # pheno-prompt-test is an optional runtime peer.
    from pheno_prompt_test import LLMResponse, PromptCase, run_case
except ImportError:  # pragma: no cover - allow router to import without peer.
    LLMResponse = None  # type: ignore[assignment]
    PromptCase = None  # type: ignore[assignment]
    run_case = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# LLM adapters
# ---------------------------------------------------------------------------


class OpenAIAdapter(LlmAdapter):
    """Async OpenAI chat completions adapter.

    Targets ``https://api.openai.com/v1/chat/completions``. The API key
    is read from the ``OPENAI_API_KEY`` environment variable at call
    time (not at construction) so test code can monkey-patch it.
    """

    DEFAULT_BASE_URL = _config.OPENAI_BASE_URL
    DEFAULT_TIMEOUT = _config.OPENAI_TIMEOUT

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._explicit_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def _resolve_key(self) -> str:
        key = self._explicit_key or os.environ.get(_config.OPENAI_API_KEY_ENV)
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return key

    async def chat(self, messages: list[Mapping[str, Any]], model: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._resolve_key()}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"model": model, "messages": list(messages)}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("openai: empty choices in response")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("openai: missing assistant content")
        return content


class AnthropicAdapter(LlmAdapter):
    """Async Anthropic messages adapter.

    Targets ``https://api.anthropic.com/v1/messages``. Translates the
    shared ``list[dict]`` message format into Anthropic's
    ``system`` + ``messages`` shape. ``max_tokens`` defaults to 1024.
    """

    DEFAULT_BASE_URL = _config.ANTHROPIC_BASE_URL
    DEFAULT_TIMEOUT = _config.ANTHROPIC_TIMEOUT
    ANTHROPIC_VERSION = _config.ANTHROPIC_VERSION
    DEFAULT_MAX_TOKENS = _config.ANTHROPIC_DEFAULT_MAX_TOKENS

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._explicit_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_tokens = max_tokens

    def _resolve_key(self) -> str:
        key = self._explicit_key or os.environ.get(_config.ANTHROPIC_API_KEY_ENV)
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return key

    @staticmethod
    def _split_messages(
        messages: list[Mapping[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Pull any leading ``system`` message out, return (system, rest)."""
        system_parts: list[str] = []
        rest: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                if isinstance(content, str):
                    system_parts.append(content)
                continue
            rest.append({"role": role or "user", "content": content})
        return "\n\n".join(system_parts), rest

    async def chat(self, messages: list[Mapping[str, Any]], model: str) -> str:
        system, rest = self._split_messages(list(messages))
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": rest,
        }
        if system:
            payload["system"] = system
        headers = {
            "x-api-key": self._resolve_key(),
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content_blocks = data.get("content") or []
        text_parts = [
            block["text"]
            for block in content_blocks
            if isinstance(block, Mapping) and block.get("type") == "text"
        ]
        if not text_parts:
            raise RuntimeError("anthropic: no text blocks in response")
        return "".join(text_parts)


# ---------------------------------------------------------------------------
# Storage adapters
# ---------------------------------------------------------------------------


class InMemoryStorageAdapter(StorageAdapter):
    """Dict-backed async storage adapter. Single-process only.

    Useful for unit tests where the test harness needs deterministic
    state without any filesystem side effects.
    """

    def __init__(self, initial: Mapping[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial or {})

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


class JsonFileStorageAdapter(StorageAdapter):
    """JSON-file-backed async storage adapter.

    The whole file is loaded on construction and rewritten on every
    ``set``/``delete`` via a temp-file rename for crash-safety. Suitable
    for development and single-replica deployments; not concurrent-safe
    across processes.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._data = {}
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._persist()

    def _persist(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._persist()

    async def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._persist()


# ---------------------------------------------------------------------------
# Tool adapters
# ---------------------------------------------------------------------------


class EchoToolAdapter(ToolAdapter):
    """Trivial tool that returns its ``args`` unchanged.

    Handy for router smoke tests where the focus is on the dispatch
    plumbing, not the tool semantics.
    """

    def __init__(self, name: str = "echo", description: str = "Returns args as-is.") -> None:
        self._name = name
        self._description = description

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        return dict(args)


class PromptTestToolAdapter(ToolAdapter):
    """Wraps :func:`pheno_prompt_test.run_case` as an MCP tool.

    Lets a router host regression tests for an LLM-backed MCP tool
    end-to-end. The ``args`` mapping must include ``prompt``; optional
    fields map to :class:`PromptCase` attributes (``expected``,
    ``must_contain``, ``must_match``, ``must_be_json``,
    ``min_similarity``). The ``backend`` callable follows
    :func:`pheno_prompt_test.run_case`'s contract
    ``Callable[[str], LLMResponse]``.
    """

    def __init__(
        self,
        backend: Callable[[str], "LLMResponse"],
        tool_name: str = "prompt_test",
        description: str = "Runs a prompt regression case via pheno-prompt-test.",
    ) -> None:
        if run_case is None or PromptCase is None:  # pragma: no cover
            raise RuntimeError(
                "pheno-prompt-test is not installed; PromptTestToolAdapter requires it"
            )
        self._backend = backend
        self._tool_name = tool_name
        self._description = description

    def name(self) -> str:
        return self._tool_name

    def description(self) -> str:
        return self._description

    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        case = PromptCase(
            name=str(args.get("name", "ad_hoc")),
            prompt=str(args["prompt"]),
            expected=str(args.get("expected", "")),
            min_similarity=float(args.get("min_similarity", 0.8)),
            must_contain=list(args.get("must_contain", [])),
            must_match=list(args.get("must_match", [])),
            must_be_json=bool(args.get("must_be_json", False)),
        )
        response = run_case(case, self._backend)
        return {
            "name": case.name,
            "text": response.text,
            "model": response.model,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "cost_usd": response.cost_usd,
            "min_similarity": case.min_similarity,
        }


__all__ = [
    "AnthropicAdapter",
    "EchoToolAdapter",
    "InMemoryStorageAdapter",
    "JsonFileStorageAdapter",
    "OpenAIAdapter",
    "PromptTestToolAdapter",
]
