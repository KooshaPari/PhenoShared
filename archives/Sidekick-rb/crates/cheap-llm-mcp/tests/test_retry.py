from __future__ import annotations

import httpx
import pytest

from cheap_llm_mcp.retry import with_retry


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-050")
async def test_retry_succeeds_eventually():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            req = httpx.Request("GET", "http://x")
            raise httpx.HTTPStatusError(
                "boom", request=req, response=httpx.Response(503, request=req)
            )
        return "ok"

    result = await with_retry(flaky, attempts=4, base_delay=0.01)
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-051")
async def test_retry_gives_up_on_non_retryable():
    async def bad():
        req = httpx.Request("GET", "http://x")
        raise httpx.HTTPStatusError("boom", request=req, response=httpx.Response(400, request=req))

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(bad, attempts=3, base_delay=0.01)


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-052")
async def test_retry_exhausts_attempts():
    calls = {"n": 0}

    async def always_fail():
        calls["n"] += 1
        req = httpx.Request("GET", "http://x")
        raise httpx.HTTPStatusError("boom", request=req, response=httpx.Response(503, request=req))

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(always_fail, attempts=3, base_delay=0.01)
    assert calls["n"] == 3
