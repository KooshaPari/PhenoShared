"""Direct Anthropic-format MiniMax-M3 adapter.

Drop-in replacement for the forge-cp subprocess path (`call_minimax_m3` in
`run_minimax_m3.py`). Activates when the `MINIMAX_API_KEY` env var is set;
falls back to the forge-cp path otherwise.

Performance contract vs forge-cp subprocess:

    forge-cp (current):   3-15s per call (agent scaffolding + TUI/spinner)
    direct (this module):  ~1-3s per call (TCP+TLS+LLM cold-start only)

Wire-in: in `run_minimax_m3.py::call_minimax_m3`, before the subprocess
branch, check `MINIMAX_API_KEY` env var. If present, use this adapter;
else fall back to forge-cp.

Endpoint + auth contract:

    POST https://api.minimax.io/anthropic/v1/messages
    X-Api-Key: $MINIMAX_API_KEY          (~108 char full key, not the
                                          31-char public prefix that
                                          forge displays truncated)
    anthropic-version: 2023-06-01
    Content-Type: application/json
    { "model": "MiniMax-M3",
      "max_tokens": 256,
      "temperature": 0,
      "messages": [{"role": "user", "content": "..."}] }

Response shape (Anthropic Messages API):

    { "content": [{"type": "text", "text": "..."}],
      "usage": {"input_tokens": N, "output_tokens": M},
      "stop_reason": "end_turn",
      "model": "MiniMax-M3",
      "id": "msg_..." }

To use:
    export MINIMAX_API_KEY="sk-cp-...<full-key>..."
    python -m bench.comparison.run_minimax_m3
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

# Default endpoint + model — matches what forge-cp actually dispatches to.
ENDPOINT = "https://api.minimax.io/anthropic/v1/messages"
MODEL = "MiniMax-M3"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class DirectMiniMaxResult:
    """Result of one direct-call round-trip to MiniMax-M3."""

    ok: bool
    reply: str = ""
    raw_status: int = 0
    raw_body: str = ""
    wall_clock_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    model_id: str = ""
    error: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def is_available() -> bool:
    """True if `MINIMAX_API_KEY` is set and non-empty in the current env."""
    return bool(os.environ.get("MINIMAX_API_KEY", "").strip())


def call(
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
    system: str | None = None,
    timeout_s: float = 60.0,
    extra_body: dict[str, Any] | None = None,
) -> DirectMiniMaxResult:
    """Single-turn call to MiniMax-M3 via the Anthropic-format endpoint.

    `prompt` is the user message. `system` is optional system prompt.
    Returns a `DirectMiniMaxResult` with timing + token usage.

    Latency: ~1-3s vs 3-15s for forge-cp subprocess.
    """
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        return DirectMiniMaxResult(
            ok=False,
            error="MINIMAX_API_KEY env var is empty or unset",
        )

    # Lazy-import requests so the module is importable even when the
    # `requests` package isn't installed (e.g. on a slim CI image).
    try:
        import requests
    except ImportError as e:
        return DirectMiniMaxResult(
            ok=False,
            error=f"`requests` package is required: {e}",
        )

    headers = {
        "X-Api-Key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "pheno-harness/1.0 (direct)",
    }
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if extra_body:
        body.update(extra_body)

    started = time.monotonic()
    try:
        resp = requests.post(
            ENDPOINT,
            headers=headers,
            json=body,
            timeout=timeout_s,
        )
    except Exception as e:
        return DirectMiniMaxResult(
            ok=False,
            wall_clock_s=time.monotonic() - started,
            error=f"HTTP transport error: {type(e).__name__}: {e}",
        )

    elapsed = time.monotonic() - started
    raw_body = resp.text or ""
    if resp.status_code != 200:
        return DirectMiniMaxResult(
            ok=False,
            raw_status=resp.status_code,
            raw_body=raw_body,
            wall_clock_s=elapsed,
            error=f"HTTP {resp.status_code} from {ENDPOINT}",
        )

    # Parse Anthropic Messages response shape.
    try:
        data = resp.json()
    except Exception as e:
        return DirectMiniMaxResult(
            ok=False,
            raw_status=resp.status_code,
            raw_body=raw_body,
            wall_clock_s=elapsed,
            error=f"Non-JSON response: {e}",
        )

    # content: list of {type: "text", text: "..."} (or tool_use blocks)
    reply_parts: list[str] = []
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            reply_parts.append(block.get("text", ""))
    reply = "".join(reply_parts).strip()

    usage = data.get("usage") or {}
    return DirectMiniMaxResult(
        ok=True,
        reply=reply,
        raw_status=resp.status_code,
        raw_body=raw_body,
        wall_clock_s=elapsed,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        stop_reason=str(data.get("stop_reason", "")),
        model_id=str(data.get("model", MODEL)),
        extra={"raw": data},
    )


# Back-compat: expose `call_minimax_m3` so the existing run_minimax_m3.py
# harness can swap implementations with a one-line change.
def call_minimax_m3(
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """Adapter for the existing `run_minimax_m3.py::call_minimax_m3` shape.

    Returns a dict compatible with the forge-cp subprocess path:
        {"ok": bool, "reply": str, "wall_clock_s": float, "exit_code": int,
         "raw_stdout": str, "raw_stdout_bytes": int, "model": str,
         "input_tokens": int, "output_tokens": int}
    """
    res = call(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_s=timeout_s,
    )
    return {
        "ok": res.ok,
        "reply": res.reply,
        "wall_clock_s": res.wall_clock_s,
        "exit_code": 0 if res.ok else 1,
        "raw_stdout": res.raw_body,
        "raw_stdout_bytes": len(res.raw_body.encode("utf-8")),
        "model": res.model_id or MODEL,
        "input_tokens": res.input_tokens,
        "output_tokens": res.output_tokens,
        "error": res.error,
    }


if __name__ == "__main__":  # pragma: no cover
    # Smoke probe (only runs if MINIMAX_API_KEY is set).
    if not is_available():
        print(
            "MINIMAX_API_KEY env var is empty.\n"
            "To run a smoke probe, set:\n"
            "  export MINIMAX_API_KEY='sk-cp-...<full-key>...'\n"
            "and retry.",
            flush=True,
        )
    else:
        res = call("Reply with exactly the words: ack-ok-direct", max_tokens=32)
        print(f"ok:        {res.ok}")
        print(f"reply:     {res.reply!r}")
        print(f"status:    {res.raw_status}")
        print(f"wall_s:    {res.wall_clock_s:.3f}")
        print(f"in_tok:    {res.input_tokens}")
        print(f"out_tok:   {res.output_tokens}")
        print(f"stop:      {res.stop_reason}")
        if res.error:
            print(f"error:     {res.error}")
