"""OpenAI-compatible SSE timing with explicit measurement caveats."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any


def _token_fallback(text: str) -> int:
    return len(text.split())


def parse_sse(lines: Iterable[bytes], started: float | None = None) -> dict[str, Any]:
    """Parse chat-completion SSE lines, recording nonempty content chunks.

    Chunk timing is a proxy for token timing: servers may place multiple tokens
    in one SSE event. Usage is preferred when the server sends it.
    """
    start = time.perf_counter() if started is None else started
    first_ms: float | None = None
    chunk_times: list[float] = []
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    usage: dict[str, Any] = {}
    for raw in lines:
        line = (
            raw.decode("utf-8", errors="replace")
            if isinstance(raw, bytes)
            else str(raw)
        )
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(event.get("usage"), dict):
            usage.update(event["usage"])
        choices = event.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content") or ""
        reasoning = delta.get("reasoning_content") or ""
        if reasoning:
            reasoning_parts.append(reasoning)
        if content:
            now = time.perf_counter()
            first_ms = first_ms if first_ms is not None else (now - start) * 1000.0
            chunk_times.append(now)
            text_parts.append(content)
    intervals = [(b - a) * 1000.0 for a, b in zip(chunk_times, chunk_times[1:])]
    completion = "".join(text_parts)
    completion_tokens = usage.get("completion_tokens")
    if not isinstance(completion_tokens, int):
        completion_tokens = _token_fallback(completion)
    return {
        "ttft_ms": first_ms,
        "itl_ms": intervals,
        "itl_ms_p50": percentile(intervals, 0.50),
        "itl_ms_p95": percentile(intervals, 0.95),
        "completion": completion,
        "reasoning": "".join(reasoning_parts),
        "reasoning_tokens": _token_fallback("".join(reasoning_parts)),
        "completion_tokens": completion_tokens,
        "prompt_tokens": usage.get("prompt_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "raw_usage": usage,
        "measurement_quality": "stream_chunk_proxy",
    }


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return ordered[index]


def stream_chat(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
    api_key: str | None = None,
    enable_thinking: bool = False,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
    }
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        # Avoid a Windows HTTPServer half-close race after the final SSE event.
        "Connection": "close",
    }
    token = api_key or os.environ.get("PHENO_API_KEY")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        endpoint + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            received: list[bytes] = []
            stream_warning: str | None = None
            try:
                for line in response:
                    received.append(line)
            except (OSError, TimeoutError) as exc:
                # Some Windows HTTP servers abort the half-closed socket after
                # sending the final SSE frame. Preserve a valid partial stream;
                # an abort before any frame remains a hard request failure.
                if not received:
                    raise
                stream_warning = f"stream terminated after received events: {exc}"
            result = parse_sse(received, started)
            if stream_warning:
                result["stream_warning"] = stream_warning
            result["status"] = response.status
    except urllib.error.HTTPError as exc:
        return {
            "error": f"HTTP {exc.code}: {exc.read(512).decode('utf-8', errors='replace')}"
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"error": f"request failed: {exc}"}
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    result["elapsed_ms"] = elapsed_ms
    result["decode_tok_s"] = (
        result["completion_tokens"] / (elapsed_ms / 1000.0) if elapsed_ms else 0.0
    )
    return result


def nonstream_chat(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
    api_key: str | None = None,
    enable_thinking: bool = False,
) -> dict[str, Any]:
    """Call an OpenAI-compatible endpoint without SSE streaming.

    This is required for single-flight runtimes that reject ``stream=true``.
    Latency is total request time, so TTFT/ITL are intentionally unavailable.
    """
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
    }
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close",
    }
    token = api_key or os.environ.get("PHENO_API_KEY")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        endpoint + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as exc:
        return {
            "error": f"HTTP {exc.code}: {exc.read(512).decode('utf-8', errors='replace')}"
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"error": f"request failed: {exc}"}
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    choices = payload.get("choices") or []
    message = choices[0].get("message") or {} if choices else {}
    completion = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    completion_tokens = usage.get("completion_tokens")
    if not isinstance(completion_tokens, int):
        completion_tokens = _token_fallback(completion)
    return {
        "status": status,
        "elapsed_ms": elapsed_ms,
        "ttft_ms": None,
        "itl_ms": [],
        "itl_ms_p50": None,
        "itl_ms_p95": None,
        "completion": completion,
        "reasoning": reasoning,
        "reasoning_tokens": _token_fallback(reasoning),
        "completion_tokens": completion_tokens,
        "prompt_tokens": usage.get("prompt_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "raw_usage": usage,
        "measurement_quality": "non_streaming_total_latency_proxy",
        "decode_tok_s": completion_tokens / (elapsed_ms / 1000.0)
        if elapsed_ms
        else 0.0,
    }


__all__ = ["nonstream_chat", "parse_sse", "percentile", "stream_chat"]
