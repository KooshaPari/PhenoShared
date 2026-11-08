"""Centralized configuration for pheno-mcp-router.

All tunable constants in the package are defined *here* so operators
have a single place to inspect, override, or document defaults.
Every module that previously defined hardcoded magic numbers now
imports from this module.

Environment variable overrides
-------------------------------
Non-security-sensitive values can be overridden at import time
through the ``PHENO_*`` environment variables listed below.
Overrides are read once at import time (not on every call), so
they must be set before the router package is loaded.

Security contract
-----------------
Values annotated with **SECURITY-SENSITIVE** in their docstring must
NOT be overridden at runtime without a security review.  They are
the contract between the router and every MCP server it proxies.

    =================================== ===================== ====================================
    Env var                             Default               Description
    =================================== ===================== ====================================
    ``PHENO_TIMEOUT_SECONDS``           60.0                  HTTP client timeout for all backends
    ``PHENO_MAX_MESSAGE_BYTES``         128_000               Max request payload before dispatch
    ``PHENO_MAX_RESPONSE_BYTES``        512_000               Max response payload from backend
    =================================== ===================== ====================================
"""

from __future__ import annotations

import os
from typing import Final

# ---------------------------------------------------------------------------
# Environment variable helpers
# ---------------------------------------------------------------------------


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ[key])
    except (KeyError, TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# McpRouter — payload sanitisation & response allowlisting
# ---------------------------------------------------------------------------

# SECURITY-SENSITIVE: sanitise-keys list — any field NOT in this set is
# stripped from outgoing requests before they reach the backend.  Do
# NOT widen without a security review.  See AGENTS.md §"Do Not Touch".
DEFAULT_SANITIZE_KEYS: Final[set[str]] = frozenset(
    {"model", "messages", "temperature", "max_tokens"}
)

# SECURITY-SENSITIVE: response-keys list — any field NOT in this set is
# stripped from the backend response before it is returned to the
# caller.  Do NOT widen without a security review.
DEFAULT_RESPONSE_KEYS: Final[set[str]] = frozenset(
    {"id", "model", "choices", "usage"}
)

# Max request payload size in bytes before dispatch (DoS protection).
DEFAULT_MAX_MESSAGE_BYTES: Final[int] = 128_000

# Max response payload size in bytes (DoS protection).
DEFAULT_MAX_RESPONSE_BYTES: Final[int] = 512_000

# Default HTTP client timeout in seconds.
DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0


# ---------------------------------------------------------------------------
# McpRouter — env-var overridable values
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS: Final[float] = _env_float(
    "PHENO_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
)
MAX_MESSAGE_BYTES: Final[int] = _env_int(
    "PHENO_MAX_MESSAGE_BYTES", DEFAULT_MAX_MESSAGE_BYTES
)
MAX_RESPONSE_BYTES: Final[int] = _env_int(
    "PHENO_MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES
)


# ---------------------------------------------------------------------------
# LLM adapter settings
# ---------------------------------------------------------------------------

# OpenAI-compatible API defaults.
OPENAI_BASE_URL: Final[str] = "https://api.openai.com/v1/chat/completions"
OPENAI_TIMEOUT: Final[float] = 60.0
OPENAI_API_KEY_ENV: Final[str] = "OPENAI_API_KEY"

# Anthropic API defaults.
ANTHROPIC_BASE_URL: Final[str] = "https://api.anthropic.com/v1/messages"
ANTHROPIC_TIMEOUT: Final[float] = 60.0
ANTHROPIC_VERSION: Final[str] = "2023-06-01"
ANTHROPIC_DEFAULT_MAX_TOKENS: Final[int] = 1024
ANTHROPIC_API_KEY_ENV: Final[str] = "ANTHROPIC_API_KEY"

# Default backend URL used by the CLI ``init`` scaffold.
DEFAULT_BACKEND_URL: Final[str] = "http://localhost:20128/v1/chat/completions"


# ---------------------------------------------------------------------------
# Cost calculator  (pheno_mcp_router.cost)
# ---------------------------------------------------------------------------

# Approximate characters-per-token for English text.  BPE tokenizers
# (cl100k_base, o200k_base, Claude, Kimi) cluster between 3.5 and 4.5
# chars/token; we use 4 as a conservative over-estimate for pre-dispatch
# budget enforcement.  See cost.py for details.
CHARS_PER_TOKEN: Final[int] = 4

# Fallback output-token count when the upstream response does not include
# a usage block.  Conservative so unmeasured dispatches do not silently
# slip under the budget radar.
DEFAULT_OUTPUT_TOKEN_ESTIMATE: Final[int] = 256


# ---------------------------------------------------------------------------
# Budget enforcer  (pheno_mcp_router.budget)
# ---------------------------------------------------------------------------

# Conservative per-dispatch floor rate (USD) for unpriced tiers.  This
# prevents an unregistered tier from bypassing the budget enforcer with
# a cost_usd of zero.  See budget.py for details.
UNPRICED_FLOOR_USD: Final[float] = 1.00


# ---------------------------------------------------------------------------
# Quota tracker  (pheno_mcp_router.quota)
# ---------------------------------------------------------------------------

# Minimum allowed quota window in seconds.  Values below this floor are
# clamped so callers cannot effectively disable the quota gate by setting
# an absurdly short window.
MIN_WINDOW_SECONDS: Final[float] = 1.0

# Default rolling-window length for quota tracking.
DEFAULT_WINDOW_SECONDS: Final[float] = 60.0


__all__ = [
    # McpRouter — security-sensitive (do not override)
    "DEFAULT_SANITIZE_KEYS",
    "DEFAULT_RESPONSE_KEYS",
    # McpRouter — defaults (env-var overridable)
    "DEFAULT_MAX_MESSAGE_BYTES",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "TIMEOUT_SECONDS",
    "MAX_MESSAGE_BYTES",
    "MAX_RESPONSE_BYTES",
    # LLM adapters
    "OPENAI_BASE_URL",
    "OPENAI_TIMEOUT",
    "OPENAI_API_KEY_ENV",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_TIMEOUT",
    "ANTHROPIC_VERSION",
    "ANTHROPIC_DEFAULT_MAX_TOKENS",
    "ANTHROPIC_API_KEY_ENV",
    "DEFAULT_BACKEND_URL",
    # Cost calculator
    "CHARS_PER_TOKEN",
    "DEFAULT_OUTPUT_TOKEN_ESTIMATE",
    # Budget enforcer
    "UNPRICED_FLOOR_USD",
    # Quota tracker
    "MIN_WINDOW_SECONDS",
    "DEFAULT_WINDOW_SECONDS",
]
