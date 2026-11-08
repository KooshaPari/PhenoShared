from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastmcp import FastMCP

from pheno_mcp_router import config as _config

logger = logging.getLogger("pheno_mcp_router")

ToolFn = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]


@dataclass(frozen=True)
class TierRoute:
    """Backend route configuration for an allowed tier."""

    name: str
    route: Mapping[str, Any]


@dataclass
class McpRouter:
    """Small FastMCP router for backend HTTP dispatch wrappers."""

    name: str
    backend_url: str
    sanitize_keys: set[str] = field(
        default_factory=lambda: set(_config.DEFAULT_SANITIZE_KEYS)  # type: ignore[arg-type]
    )
    response_keys: set[str] = field(
        default_factory=lambda: set(_config.DEFAULT_RESPONSE_KEYS)  # type: ignore[arg-type]
    )
    max_message_bytes: int = _config.MAX_MESSAGE_BYTES
    max_response_bytes: int = _config.MAX_RESPONSE_BYTES
    timeout_seconds: float = _config.TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        self._tiers: dict[str, TierRoute] = {}
        self._tools: dict[str, list[ToolFn]] = {}
        self.mcp = FastMCP(self.name)
        self._register_default_tool()

    def add_tier(self, name: str, route: Mapping[str, Any]) -> "McpRouter":
        """Allow a tier and bind default backend route data to it."""
        if not name:
            raise ValueError("tier name is required")
        self._tiers[name] = TierRoute(name=name, route=dict(route))
        self._tools.setdefault(name, [])
        return self

    def add_tool(self, tier: str, fn: ToolFn) -> "McpRouter":
        """Register a local tool callback allowed for a tier."""
        if tier not in self._tiers:
            raise ValueError(f"unknown tier: {tier}")
        self._tools.setdefault(tier, []).append(fn)
        return self

    def _register_default_tool(self) -> None:
        @self.mcp.tool
        async def dispatch(tier: str, payload: dict[str, Any]) -> dict[str, Any]:
            """Dispatch a sanitized payload to the configured backend."""
            return await self.dispatch(tier=tier, payload=payload)

    async def dispatch(self, tier: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Validate tier, sanitize payload, call backend, and allowlist response."""
        if tier not in self._tiers:
            raise ValueError(f"tier is not allowed: {tier}")

        clean_payload = self._sanitize_payload(payload)
        merged_payload = {**self._tiers[tier].route, **clean_payload}
        message_bytes = len(json.dumps(merged_payload, separators=(",", ":")).encode("utf-8"))
        if message_bytes > self.max_message_bytes:
            raise ValueError("payload exceeds max_message_bytes")

        logger.info("mcp_dispatch_started", extra={"router": self.name, "tier": tier, "bytes": message_bytes})
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.backend_url, json=merged_payload)
            response.raise_for_status()
            raw = response.content

        if len(raw) > self.max_response_bytes:
            raise ValueError("response exceeds max_response_bytes")

        data = json.loads(raw.decode("utf-8"))
        allowed = self._allowlist_response(data)
        logger.info("mcp_dispatch_completed", extra={"router": self.name, "tier": tier})
        return allowed

    def _sanitize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key in self.sanitize_keys}

    def _allowlist_response(self, response: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in response.items() if key in self.response_keys}

    def serve(self) -> None:
        """Run the underlying FastMCP server."""
        self.mcp.run()


# Re-export L4 hexagonal ports and concrete adapters so callers can
# `from pheno_mcp_router import LlmPort, OpenAIAdapter, ...` without
# reaching into the sub-modules.
from pheno_mcp_router.adapters import (  # noqa: E402
    AnthropicAdapter,
    EchoToolAdapter,
    InMemoryStorageAdapter,
    JsonFileStorageAdapter,
    OpenAIAdapter,
    PromptTestToolAdapter,
)
from pheno_mcp_router.ports import (  # noqa: E402
    LlmAdapter,
    LlmPort,
    StorageAdapter,
    StoragePort,
    ToolAdapter,
    ToolPort,
)


__all__ = [
    "AnthropicAdapter",
    "EchoToolAdapter",
    "InMemoryStorageAdapter",
    "JsonFileStorageAdapter",
    "LlmAdapter",
    "LlmPort",
    "McpRouter",
    "OpenAIAdapter",
    "PromptTestToolAdapter",
    "StorageAdapter",
    "StoragePort",
    "TierRoute",
    "ToolAdapter",
    "ToolFn",
    "ToolPort",
]
