from __future__ import annotations

import pytest

from cheap_llm_mcp.config import Config, ProviderConfig
from cheap_llm_mcp.providers.base import Completion
from cheap_llm_mcp.router import Router


class _FakeProvider:
    def __init__(self, name: str, fail: bool = False):
        self.name = name
        self.fail = fail

    async def complete(
        self, messages, *, model=None, variant=None, max_tokens=4096, temperature=0.2
    ):
        if self.fail:
            raise RuntimeError(f"{self.name} boom")
        return Completion(
            text=f"hello from {self.name}",
            model=model or "fake-model",
            provider=self.name,
            input_tokens=1,
            output_tokens=2,
        )

    async def aclose(self):
        pass


@pytest.fixture
def router() -> Router:
    cfg = Config(
        providers={
            "minimax": ProviderConfig(
                name="minimax",
                base_url="http://localhost",
                api_key_env="FAKE_KEY",
                default_model="MiniMax-M2",
            ),
            "kimi": ProviderConfig(
                name="kimi",
                base_url="http://localhost",
                api_key_env="FAKE_KEY",
                default_model="kimi",
            ),
        },
        default_provider="minimax",
    )
    r = Router(cfg)
    r._providers["minimax"] = _FakeProvider("minimax")
    r._providers["kimi"] = _FakeProvider("kimi")
    return r


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-001")
async def test_router_direct_provider(router: Router):
    result = await router.complete("hi", provider="kimi")
    assert result.provider == "kimi"
    assert "hello from kimi" in result.text


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-002")
async def test_router_auto_picks_default(router: Router):
    result = await router.complete("hi")
    assert result.provider == "minimax"


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-003")
async def test_router_auto_fallback(router: Router):
    router._providers["minimax"] = _FakeProvider("minimax", fail=True)
    result = await router.complete("hi")
    assert result.provider == "kimi"


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-004")
async def test_router_all_fail(router: Router):
    router._providers["minimax"] = _FakeProvider("minimax", fail=True)
    router._providers["kimi"] = _FakeProvider("kimi", fail=True)
    with pytest.raises(RuntimeError, match="All providers failed"):
        await router.complete("hi")
