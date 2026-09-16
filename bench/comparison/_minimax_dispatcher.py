"""Auto-switching MiniMax-M3 dispatcher.

Two adapters wired, selected by env at call time:

- Direct mode (`requests.post` to https://api.minimax.io/anthropic/v1/messages,
  ms-level overhead, ~1-3s vs 3-15s for forge-cp). Requires `MINIMAX_API_KEY`
  in env (read directly by the adapter).
- Forge mode (subprocess: `forge -p "<prompt>"`, ~10-120s per call due to
  forge agent scaffolding). No key required; forge manages auth via its
  encrypted keychain store.

Selection rule: if `MINIMAX_API_KEY` is in env, use direct. Otherwise use
forge. Override with `PHENO_MINIMAX_BACKEND=direct|forge`.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import time
from typing import Any

from bench.comparison._direct_minimax_adapter import (
    ENDPOINT,
)
from bench.comparison._direct_minimax_adapter import (
    call as _direct_call,
)
from bench.comparison._direct_minimax_adapter import (
    is_available as _direct_available,
)
from bench.comparison._forge_reply_parser import _extract_reply

FORGE_BIN = "/Users/kooshapari/.local/bin/forge"
DIRECT_TIMEOUT_CAP_S = 60.0
DEFAULT_BACKEND = "auto"  # auto | direct | forge


def _selected_backend() -> str:
    """Return the backend selected for this call."""
    override = os.environ.get("PHENO_MINIMAX_BACKEND", DEFAULT_BACKEND).strip().lower()
    if override in ("direct", "forge"):
        return override
    if os.environ.get("MINIMAX_API_KEY"):
        return "direct"
    return "forge"


def _call_direct(prompt: str, timeout_s: int) -> dict[str, Any]:
    """Make a direct API call to api.minimax.io and return the structured result."""
    started = time.monotonic()
    eff_timeout = min(float(timeout_s), DIRECT_TIMEOUT_CAP_S)
    try:
        result = _direct_call(prompt, timeout_s=eff_timeout)
        wall = time.monotonic() - started
        return {
            "ok": result.ok,
            "exit_code": 0 if result.ok else -2,
            "wall_clock_s": wall,
            "reply": (result.reply or "").strip(),
            "raw_stdout": result.reply or "",
            "raw_stderr": result.error or "",
            "backend": "direct",
            "endpoint": ENDPOINT,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "raw_status": result.raw_status,
        }
    except Exception as e:
        return {
            "ok": False,
            "exit_code": -2,
            "wall_clock_s": time.monotonic() - started,
            "reply": "",
            "raw_stdout": "",
            "raw_stderr": f"DIRECT_ERROR {type(e).__name__}: {e}",
            "backend": "direct",
            "endpoint": ENDPOINT,
            "error": type(e).__name__,
        }


def _call_forge(prompt: str, timeout_s: int) -> dict[str, Any]:
    """Run forge -p as a subprocess and parse the spinner-stuffed reply."""
    started = time.monotonic()
    env = {
        **os.environ,
        "PATH": "/usr/bin:/bin:/usr/local/bin:/Users/kooshapari/.local/bin",
    }
    try:
        proc = subprocess.run(  # nosec B603
            [FORGE_BIN, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        wall = time.monotonic() - started
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "wall_clock_s": wall,
            "reply": _extract_reply(stdout),
            "raw_stdout": stdout,
            "raw_stderr": stderr,
            "backend": "forge",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": -1,
            "wall_clock_s": time.monotonic() - started,
            "reply": "",
            "raw_stdout": "",
            "raw_stderr": f"TIMEOUT after {timeout_s}s",
            "backend": "forge",
            "error": "timeout",
        }
    except Exception as e:
        return {
            "ok": False,
            "exit_code": -2,
            "wall_clock_s": time.monotonic() - started,
            "reply": "",
            "raw_stdout": "",
            "raw_stderr": str(e),
            "backend": "forge",
            "error": type(e).__name__,
        }


def call_minimax_m3(prompt: str, *, timeout_s: int = 90) -> dict[str, Any]:
    """Auto-switching dispatch.

    Selection (per `_selected_backend`):
      - `MINIMAX_API_KEY` in env → direct HTTP (ms-level)
      - else                    → forge -p subprocess (agent overhead)
    Override with `PHENO_MINIMAX_BACKEND=direct|forge`.

    `timeout_s` is the upper bound per call; direct mode caps at
    `min(timeout_s, DIRECT_TIMEOUT_CAP_S)`.
    """
    backend = _selected_backend()
    if backend == "direct":
        return _call_direct(prompt, timeout_s)
    return _call_forge(prompt, timeout_s)


def backend_status() -> dict[str, Any]:
    """Diagnostic helper: which backend is selected and is it functional?"""
    be = _selected_backend()
    info: dict[str, Any] = {
        "backend": be,
        "override": os.environ.get("PHENO_MINIMAX_BACKEND", "(unset)"),
        "minimax_api_key_set": bool(os.environ.get("MINIMAX_API_KEY")),
        "endpoint": ENDPOINT,
        "forge_bin": FORGE_BIN,
        "direct_timeout_cap_s": DIRECT_TIMEOUT_CAP_S,
    }
    if be == "direct":
        info["direct_available"] = _direct_available()
    return info


__all__ = [
    "FORGE_BIN",
    "DEFAULT_BACKEND",
    "DIRECT_TIMEOUT_CAP_S",
    "call_minimax_m3",
    "backend_status",
    "_selected_backend",
]
