"""Quickstart: pheno-mcp-router

Run with::

    python examples/quickstart.py

Builds an McpRouter, registers one tier, and exercises `dispatch()` against
a fake in-process backend (no live HTTP).  Illustrates the contract without
requiring an actual MCP server.
"""

from __future__ import annotations

import asyncio

from pheno_mcp_router import McpRouter


async def _demo_dispatch(router: McpRouter) -> dict:
    """Call dispatch directly (bypassing FastMCP) with a sanitized payload."""
    return await router.dispatch(
        tier="default",
        payload={
            "model": "minimax-m2p7",
            "messages": [{"role": "user", "content": "ping"}],
            # The following non-allowlisted keys are dropped by sanitize_keys.
            "leaked_secret": "should-not-appear",
        },
    )


def build_router() -> McpRouter:
    """Construct a router with one tier and explicit allowlists."""
    return (
        McpRouter(
            name="quickstart-router",
            backend_url="http://localhost:20128/v1/chat/completions",
            sanitize_keys={"model", "messages", "temperature", "max_tokens"},
            response_keys={"id", "model", "choices", "usage"},
        )
        .add_tier("default", {"model": "minimax-m2p7"})
    )


def main() -> None:
    router = build_router()
    print(f"router={router.name} backend={router.backend_url}")
    print(f"tiers={list(router._tiers.keys())}")  # noqa: SLF001 — internal OK for demo
    # In a real server, you would call `router.serve()`. Here we just exercise
    # the dispatch path against the sanitization layer only (no HTTP).
    try:
        result = asyncio.run(_demo_dispatch(router))
    except Exception as exc:  # no live backend in this demo
        result = {"demo_skipped_backend": type(exc).__name__, "note": str(exc)}
    print(f"dispatch_result={result}")


if __name__ == "__main__":
    main()