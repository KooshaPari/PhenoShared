from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from .cache import TTLCache
from .config import Config
from .providers import Completion, Message, OpenAICompatProvider

log = logging.getLogger(__name__)


class Router:
    """Dispatches completion requests to the right provider with fallback."""

    def __init__(self, cfg: Config, cache_ttl: float = 0.0):
        self.cfg = cfg
        self._providers: dict[str, OpenAICompatProvider] = {}
        self._cache = TTLCache(ttl_seconds=cache_ttl) if cache_ttl > 0 else None

    def _get(self, name: str) -> OpenAICompatProvider:
        if name not in self._providers:
            if name not in self.cfg.providers:
                raise KeyError(f"Unknown provider: {name!r}")
            self._providers[name] = OpenAICompatProvider(self.cfg.providers[name])
        return self._providers[name]

    def _resolve_order(self, provider: str | None) -> list[str]:
        if provider and provider != "auto":
            return [provider]
        return [
            self.cfg.default_provider,
            *(p for p in self.cfg.providers if p != self.cfg.default_provider),
        ]

    async def complete(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> Completion:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        variant = variant or self.cfg.default_variant
        order = self._resolve_order(provider)

        cache_key = None
        if self._cache is not None and temperature == 0.0:
            cache_key = TTLCache.key(
                "complete",
                prompt,
                system,
                provider,
                variant,
                model,
                max_tokens,
                temperature,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        last_error: Exception | None = None
        for name in order:
            try:
                p = self._get(name)
                result = await p.complete(
                    messages,
                    model=model,
                    variant=variant,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if cache_key is not None and self._cache is not None:
                    self._cache.set(cache_key, result)
                return result
            except Exception as e:
                log.warning("provider %s failed: %s", name, e)
                last_error = e
        raise RuntimeError(f"All providers failed; last: {last_error!r}")

    async def stream(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        variant = variant or self.cfg.default_variant
        name = (self._resolve_order(provider))[0]
        p = self._get(name)
        async for chunk in p.stream(
            messages,
            model=model,
            variant=variant,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk

    async def aclose(self) -> None:
        for p in self._providers.values():
            await p.aclose()
