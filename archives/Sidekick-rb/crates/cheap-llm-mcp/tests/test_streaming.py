from __future__ import annotations

import httpx
import pytest
import respx

from cheap_llm_mcp.config import ProviderConfig
from cheap_llm_mcp.providers.base import Message
from cheap_llm_mcp.providers.openai_compat import OpenAICompatProvider


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "fake")
    return ProviderConfig(
        name="test",
        base_url="https://api.example.com/v1",
        api_key_env="TEST_API_KEY",
        default_model="test-model",
    )


SSE_BODY = (
    b'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n'
    b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
    b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
    b"data: [DONE]\n\n"
)


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-042")
async def test_stream_aggregates_chunks(cfg):
    p = OpenAICompatProvider(cfg)
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=SSE_BODY, headers={"content-type": "text/event-stream"}
        )
    )
    chunks = []
    async for c in p.stream([Message(role="user", content="hi")]):
        chunks.append(c)
    assert "".join(chunks) == "hello world"
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-043")
async def test_stream_handles_non_json_lines(cfg):
    p = OpenAICompatProvider(cfg)
    body = (
        b": ping\n\n"  # SSE comment, should be skipped
        b'data: {"choices":[{"delta":{"content":"x"}}]}\n\n'
        b"data: not-json\n\n"
        b"data: [DONE]\n\n"
    )
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=body, headers={"content-type": "text/event-stream"}
        )
    )
    chunks = [c async for c in p.stream([Message(role="user", content="hi")])]
    assert chunks == ["x"]
    await p.aclose()
