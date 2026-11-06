"""Cheap-LLM MCP: Minimax + Kimi + Fireworks as a Haiku-class reasoner."""

from cheap_llm_mcp.cache import TTLCache
from cheap_llm_mcp.config import Config, ProviderConfig
from cheap_llm_mcp.config import load as load_config
from cheap_llm_mcp.ledger import (
    PRICING,
    Ledger,
    LedgerEntry,
    MonthAggregate,
    estimate_cost_usd,
)
from cheap_llm_mcp.logging_util import request_scope, setup_json_logging
from cheap_llm_mcp.retry import with_retry
from cheap_llm_mcp.router import Router

__version__ = "0.1.0"

__all__ = [
    "PRICING",
    "Config",
    "Ledger",
    "LedgerEntry",
    "MonthAggregate",
    "ProviderConfig",
    "Router",
    "TTLCache",
    "estimate_cost_usd",
    "load_config",
    "request_scope",
    "setup_json_logging",
    "with_retry",
]
