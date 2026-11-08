"""Tests for the FastAPI/Starlette ASGI middleware.

These tests are collected only when the optional `fastapi` extra (or
dev extras) is installed; otherwise pytest will skip them via the
`requires_fastapi` fixture.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any, AsyncIterator

import pytest

pytest_plugins: tuple[str, ...] = ()


@pytest.fixture(scope="module")
def fastapi_deps() -> Any:
    """Skip the entire module when fastapi/starlette/httpx aren't present."""
    try:
        import fastapi  # noqa: F401
        import httpx  # noqa: F401
        import starlette  # noqa: F401
    except Exception as exc:  # pragma: no cover - depends on env
        pytest.skip(f"fastapi/httpx/starlette not installed: {exc!r}")
    return True


@pytest.fixture
def app(fastapi_deps: Any) -> Any:
    from fastapi import FastAPI

    from phenotype_request_id.fastapi import RequestIdMiddleware

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo")
    async def echo() -> dict[str, str | None]:
        from phenotype_request_id.context import get_request_id

        return {"rid": get_request_id()}

    return app


@pytest.fixture
async def client(app: Any) -> AsyncIterator[Any]:
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_middleware_propagates_inbound_header(client: Any) -> None:
    resp = await client.get("/echo", headers={"X-Request-Id": "caller-supplied-42"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id") == "caller-supplied-42"
    assert resp.json() == {"rid": "caller-supplied-42"}


async def test_middleware_generates_uuid4_when_missing(client: Any) -> None:
    resp = await client.get("/echo")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-Id")
    assert rid is not None
    # uuid4().hex is 32 lowercase hex chars
    assert re.fullmatch(r"[0-9a-f]{32}", rid), f"expected uuid4 hex, got {rid!r}"
    # Round-trip through uuid.UUID to be extra sure
    uuid.UUID(hex=rid, version=4)
    assert resp.json() == {"rid": rid}


async def test_middleware_rejects_empty_header_and_generates(client: Any) -> None:
    resp = await client.get("/echo", headers={"X-Request-Id": "   "})
    rid = resp.headers.get("X-Request-Id")
    assert rid is not None
    assert re.fullmatch(r"[0-9a-f]{32}", rid)


async def test_middleware_isolates_concurrent_requests(app: Any) -> None:
    """Two concurrent in-flight requests must not share a request id."""
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        a, b = await asyncio.gather(
            c.get("/echo", headers={"X-Request-Id": "req-a"}),
            c.get("/echo", headers={"X-Request-Id": "req-b"}),
        )
    assert a.json() == {"rid": "req-a"}
    assert b.json() == {"rid": "req-b"}
    assert a.headers["X-Request-Id"] == "req-a"
    assert b.headers["X-Request-Id"] == "req-b"
