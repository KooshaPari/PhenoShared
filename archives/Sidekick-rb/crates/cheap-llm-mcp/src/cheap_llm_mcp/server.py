from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

from .config import load as load_config
from .ledger import Ledger
from .logging_util import request_scope, setup_json_logging
from .router import Router

log = logging.getLogger("cheap-llm-mcp")

mcp = FastMCP("cheap-llm")
_router: Router | None = None
_ledger: Ledger | None = None


def _router_get() -> Router:
    global _router
    if _router is None:
        cfg = load_config()
        _router = Router(cfg, cache_ttl=cfg.cache_ttl_seconds)
    return _router


def _ledger_get() -> Ledger:
    global _ledger
    if _ledger is None:
        cfg = _router_get().cfg
        _ledger = Ledger(
            path=Path.home() / ".cheap-llm" / "ledger.jsonl",
            cap_usd=cfg.monthly_cost_cap_usd,
        )
    return _ledger


@mcp.tool(
    name="cheapllm_complete_prompt",
    description=(
        "Complete a prompt using a cheap LLM (Minimax, Kimi, or Fireworks-hosted). "
        "Use for bulk/cheap reasoning subtasks where Haiku-class quality is acceptable: "
        "summarization, extraction, simple codegen, test-case generation, doc polishing."
    )
)
async def complete(
    prompt: str,
    system: str | None = None,
    provider: Literal["auto", "minimax", "kimi", "fireworks"] = "auto",
    variant: str = "highspeed",
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict:
    with request_scope() as rid:
        log.info(
            "complete.start",
            extra={"provider": provider, "variant": variant, "prompt_len": len(prompt)},
        )
        ledger = _ledger_get()
        ledger.check_cap()
        r = _router_get()
        result = await r.complete(
            prompt,
            provider=None if provider == "auto" else provider,
            variant=variant,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        entry = ledger.record(
            result.provider, result.model, result.input_tokens, result.output_tokens
        )
        log.info(
            "complete.done",
            extra={
                "provider": result.provider,
                "model": result.model,
                "cost_usd": entry.cost_usd,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        )
        return {
            "text": result.text,
            "model": result.model,
            "provider": result.provider,
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
            "cost_usd": entry.cost_usd,
            "finish_reason": result.finish_reason,
            "request_id": rid,
        }


@mcp.tool(
    name="cheapllm_stream_completion",
    description=(
        "Stream-complete a prompt. Returns full aggregated text (MCP tools don't "
        "stream chunks to clients, but streaming reduces time-to-first-byte on "
        "the provider side for long completions)."
    )
)
async def stream_complete(
    prompt: str,
    system: str | None = None,
    provider: Literal["auto", "minimax", "kimi", "fireworks"] = "auto",
    variant: str = "highspeed",
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict:
    _ledger_get().check_cap()
    r = _router_get()
    chunks: list[str] = []
    async for c in r.stream(
        prompt,
        provider=None if provider == "auto" else provider,
        variant=variant,
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    ):
        chunks.append(c)
    text = "".join(chunks)
    # Streaming API typically does not return usage; estimate.
    approx_in = len(prompt) // 4
    approx_out = len(text) // 4
    return {"text": text, "approx_input_tokens": approx_in, "approx_output_tokens": approx_out}


@mcp.tool(name="cheapllm_check_health", description="Probe health of all configured providers.")
async def health() -> dict:
    r = _router_get()
    out = {}
    for name in r.cfg.providers:
        p = r._get(name)
        out[name] = await p.health()
    return out


@mcp.tool(name="cheapllm_get_cost", description="Get month-to-date cost summary from the ledger.")
async def cost_summary(month: str | None = None) -> dict:
    agg = _ledger_get().month_total(month)
    cfg = _router_get().cfg
    return {
        "month": agg.month,
        "total_usd": agg.total_usd,
        "calls": agg.calls,
        "by_provider": agg.by_provider,
        "cap_usd": cfg.monthly_cost_cap_usd,
        "remaining_usd": (
            round(cfg.monthly_cost_cap_usd - agg.total_usd, 4)
            if cfg.monthly_cost_cap_usd is not None
            else None
        ),
    }


@mcp.tool(name="cheapllm_list_providers", description="List known provider names and their default models.")
async def providers() -> dict:
    cfg = _router_get().cfg
    return {
        "default_provider": cfg.default_provider,
        "default_variant": cfg.default_variant,
        "providers": {
            name: {
                "base_url": p.base_url,
                "default_model": p.default_model,
                "variants": p.variants,
            }
            for name, p in cfg.providers.items()
        },
    }


@mcp.tool(
    name="cheapllm_list_models",
    description=(
        "Query a provider's live /models endpoint to discover available model IDs. "
        "Use when you don't know the exact model name a provider currently serves."
    )
)
async def list_live_models(
    provider: Literal["minimax", "kimi", "fireworks"],
) -> list[dict]:
    r = _router_get()
    p = r._get(provider)
    return await p.list_models()


def main() -> None:
    setup_json_logging("INFO")
    try:
        mcp.run()
    finally:
        if _router is not None:
            asyncio.run(_router.aclose())


if __name__ == "__main__":
    main()
