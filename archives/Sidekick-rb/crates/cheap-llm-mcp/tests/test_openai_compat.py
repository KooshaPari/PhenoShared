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
        variants={"fast": "test-model-fast"},
    )


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-040")
async def test_complete_happy_path(cfg):
    p = OpenAICompatProvider(cfg)
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "message": {"content": "hello world"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )
    )
    result = await p.complete([Message(role="user", content="hi")])
    assert result.text == "hello world"
    assert result.provider == "test"
    assert result.input_tokens == 5
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-041")
async def test_complete_variant_resolution(cfg):
    p = OpenAICompatProvider(cfg)
    captured = {}

    def handler(request):
        import json

        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    respx.post("https://api.example.com/v1/chat/completions").mock(side_effect=handler)
    await p.complete([Message(role="user", content="hi")], variant="fast")
    assert captured["payload"]["model"] == "test-model-fast"
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-050")
async def test_complete_retries_on_503(cfg):
    p = OpenAICompatProvider(cfg)
    respx.post("https://api.example.com/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {},
                },
            ),
        ]
    )
    result = await p.complete([Message(role="user", content="hi")])
    assert result.text == "ok"
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-051")
async def test_complete_does_not_retry_on_400(cfg):
    p = OpenAICompatProvider(cfg)
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(400, json={"error": "bad request"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        await p.complete([Message(role="user", content="hi")])
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-044")
async def test_health_ok(cfg):
    p = OpenAICompatProvider(cfg)
    respx.get("https://api.example.com/v1/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    out = await p.health()
    assert out["status"] == "ok"
    assert "latency_ms" in out
    await p.aclose()


@pytest.mark.asyncio
@respx.mock
@pytest.mark.requirement("FR-LLM-044")
async def test_health_error(cfg):
    p = OpenAICompatProvider(cfg)
    respx.get("https://api.example.com/v1/models").mock(return_value=httpx.Response(500))
    out = await p.health()
    # 500 triggers retries in with_retry, but health() doesn't use with_retry — it raises.
    # Note: health() swallows to return error dict.
    assert out["status"] == "error"
    await p.aclose()
