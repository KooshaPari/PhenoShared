#!/usr/bin/env python3
"""OpenAI-compatible local proxy for pheno-serve-dev.

Milestone 1 intentionally proxies existing local OpenAI-compatible engines
instead of launching them. Engine lifecycle management lands in later adapters.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pheno.serve.config import ServeConfig, load_config
from pheno.serve.events import EventLog
from pheno.serve.metrics import Metrics
from pheno.serve.registry import ProfileRegistry, ServingProfile


class ServeState:
    def __init__(self, config: ServeConfig):
        self.config = config
        self.registry = ProfileRegistry(config)
        self.events = EventLog(config.events_path)
        self.metrics = Metrics()
        self.upstream_timeout_s = float(config.server.get("upstream_timeout_s", 60))

    def readiness(self) -> tuple[bool, dict[str, Any]]:
        active = [profile for profile in self.registry.list() if profile.active]
        if not active:
            return False, {"active_profiles": 0, "reason": "no active serving profiles"}
        checks: dict[str, Any] = {}
        for profile in active:
            if not profile.base_url:
                checks[profile.alias] = {
                    "ready": False,
                    "reason": "no upstream base_url",
                }
                continue
            try:
                req = Request(profile.upstream_models_url, method="GET")
                with (
                    urlopen(req, timeout=min(self.upstream_timeout_s, 3)) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
                ):
                    checks[profile.alias] = {
                        "ready": 200 <= response.status < 300,
                        "status": response.status,
                    }
            except (HTTPError, URLError, OSError, TimeoutError) as exc:
                checks[profile.alias] = {"ready": False, "reason": str(exc)}
        return all(item.get("ready") for item in checks.values()), checks


def _json_response(
    handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]
) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _text_response(
    handler: BaseHTTPRequestHandler,
    code: int,
    payload: str,
    content_type: str = "text/plain",
) -> None:
    data = payload.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class PhenoServeHandler(BaseHTTPRequestHandler):
    server_version = "pheno-serve-dev/0.1"
    state: ServeState

    def log_message(self, fmt: str, *args: Any) -> None:
        # Request events are written as JSONL; keep stderr quiet for eval runs.
        return

    def do_GET(self) -> None:
        if self.path == "/healthz":
            _json_response(self, 200, {"ok": True, "service": "pheno-serve-dev"})
            return
        if self.path == "/readyz":
            ready, checks = self.state.readiness()
            _json_response(
                self,
                200 if ready else 503,
                {
                    "ok": ready,
                    "service": "pheno-serve-dev",
                    "checks": checks,
                },
            )
            return
        if self.path == "/v1/models":
            _json_response(self, 200, self.state.registry.openai_models())
            return
        if self.path == "/admin/models":
            _json_response(
                self,
                200,
                {
                    "profiles": [
                        p.raw
                        | {"alias": p.alias, "engine": p.engine, "status": p.status}
                        for p in self.state.registry.list()
                    ]
                },
            )
            return
        if self.path == "/metrics":
            _text_response(
                self, 200, self.state.metrics.prometheus(), "text/plain; version=0.0.4"
            )
            return
        _json_response(self, 404, {"error": {"message": f"unknown path: {self.path}"}})

    def do_POST(self) -> None:
        if self.path == "/admin/routes/resolve":
            body = self._read_json()
            alias = str(body.get("model", ""))
            try:
                profile = self.state.registry.get(alias)
                _json_response(
                    self,
                    200,
                    {
                        "model": alias,
                        "resolved": profile.alias,
                        "engine": profile.engine,
                        "base_url": profile.base_url,
                    },
                )
            except KeyError as exc:
                _json_response(self, 404, {"error": {"message": str(exc)}})
            return
        if self.path in ("/v1/chat/completions", "/v1/completions"):
            self._proxy_completion()
            return
        _json_response(self, 404, {"error": {"message": f"unknown path: {self.path}"}})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(length) if length else b"{}"
        decoded = json.loads(data.decode("utf-8") or "{}")
        return cast(dict[str, Any], decoded)

    def _captured_headers(self) -> dict[str, str]:
        out = {}
        for name in self.state.config.capture_headers:
            value = self.headers.get(name)
            if value:
                out[name] = value
        return out

    def _proxy_completion(self) -> None:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        body = self._read_json()
        alias = str(body.get("model") or "")
        try:
            profile = self.state.registry.get(alias)
        except KeyError as exc:
            _json_response(
                self, 404, {"error": {"message": str(exc), "type": "unknown_model"}}
            )
            return

        upstream_body = dict(body)
        upstream_body["model"] = (
            profile.raw.get("api_model_name")
            or profile.raw.get("upstream_model")
            or alias
        )

        event_base = self._event_base(request_id, alias, profile, body)
        try:
            if bool(body.get("stream")) and profile.backend_mode in (
                "openai_chat",
                "auto",
            ):
                self._proxy_stream(
                    profile, upstream_body, event_base, request_id, started
                )
                return
            status, headers, payload = self._call_upstream(profile, upstream_body)
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.state.metrics.observe(profile.engine, elapsed_ms, error=status >= 400)
            self.state.events.append(
                {
                    **event_base,
                    "status": status,
                    "latency_ms": round(elapsed_ms, 3),
                    "ttft_ms": None,
                    "itl_ms_p50": None,
                    "itl_ms_p95": None,
                    "engine_error": None
                    if status < 400
                    else payload.decode("utf-8", errors="replace")[:500],
                }
            )
            self.send_response(status)
            self.send_header(
                "Content-Type", headers.get("Content-Type", "application/json")
            )
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Pheno-Request-Id", request_id)
            self.send_header("X-Pheno-Engine", profile.engine)
            self.end_headers()
            self.wfile.write(payload)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.state.metrics.observe(profile.engine, elapsed_ms, error=True)
            self.state.events.append(
                {
                    **event_base,
                    "status": 502,
                    "latency_ms": round(elapsed_ms, 3),
                    "ttft_ms": None,
                    "itl_ms_p50": None,
                    "itl_ms_p95": None,
                    "engine_error": str(exc),
                }
            )
            _json_response(
                self,
                502,
                {
                    "error": {
                        "message": str(exc),
                        "type": "upstream_error",
                        "request_id": request_id,
                    }
                },
            )

    def _proxy_stream(
        self,
        profile: ServingProfile,
        body: dict[str, Any],
        event_base: dict[str, Any],
        request_id: str,
        started: float,
    ) -> None:
        """Forward SSE incrementally so TTFT and ITL remain observable downstream."""
        req = Request(
            profile.upstream_chat_url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Authorization": self.headers.get(
                    "Authorization", "Bearer local-no-key"
                ),
            },
        )
        first_ms = None
        chunk_times: list[float] = []
        status = 502
        try:
            with (
                urlopen(req, timeout=self.state.upstream_timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                status = resp.status
                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    resp.headers.get("Content-Type", "text/event-stream"),
                )
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("X-Pheno-Request-Id", request_id)
                self.send_header("X-Pheno-Engine", profile.engine)
                self.end_headers()
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    now = time.perf_counter()
                    if b'"content":"' in chunk or b'"content": "' in chunk:
                        first_ms = (
                            first_ms if first_ms is not None else (now - started) * 1000
                        )
                        chunk_times.append(now)
                    self.wfile.write(chunk)
                    self.wfile.flush()
            elapsed_ms = (time.perf_counter() - started) * 1000
            intervals = [(b - a) * 1000 for a, b in zip(chunk_times, chunk_times[1:])]
            self.state.metrics.observe(profile.engine, elapsed_ms, error=status >= 400)
            self.state.events.append(
                {
                    **event_base,
                    "status": status,
                    "latency_ms": round(elapsed_ms, 3),
                    "ttft_ms": round(first_ms, 3) if first_ms is not None else None,
                    "itl_ms_p50": self._percentile(intervals, 0.5),
                    "itl_ms_p95": self._percentile(intervals, 0.95),
                    "engine_error": None,
                }
            )
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.state.metrics.observe(profile.engine, elapsed_ms, error=True)
            self.state.events.append(
                {
                    **event_base,
                    "status": getattr(exc, "code", 502),
                    "latency_ms": round(elapsed_ms, 3),
                    "ttft_ms": round(first_ms, 3) if first_ms is not None else None,
                    "itl_ms_p50": self._percentile(
                        [(b - a) * 1000 for a, b in zip(chunk_times, chunk_times[1:])],
                        0.5,
                    ),
                    "itl_ms_p95": self._percentile(
                        [(b - a) * 1000 for a, b in zip(chunk_times, chunk_times[1:])],
                        0.95,
                    ),
                    "engine_error": str(exc),
                }
            )

    @staticmethod
    def _percentile(values: list[float], quantile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        return round(
            ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * quantile)))], 3
        )

    def _event_base(
        self, request_id: str, alias: str, profile: ServingProfile, body: dict[str, Any]
    ) -> dict[str, Any]:
        captured = self._captured_headers()
        return {
            "request_id": request_id,
            "run_id": captured.get("X-Pheno-Run-Id"),
            "lane": captured.get("X-Pheno-Lane"),
            "role": captured.get("X-Pheno-Role"),
            "route_kind": captured.get("X-Pheno-Route-Kind"),
            "eval_suite": captured.get("X-Pheno-Eval-Suite"),
            "bypass_reason": captured.get("X-Pheno-Bypass-Reason"),
            "model_alias": alias,
            "resolved_alias": profile.alias,
            "engine": profile.engine,
            "backend_mode": profile.backend_mode,
            "decode_method": (profile.raw.get("decode") or {}).get("method"),
            "stream": bool(body.get("stream")),
        }

    def _call_upstream(
        self, profile: ServingProfile, body: dict[str, Any]
    ) -> tuple[int, dict[str, str], bytes]:
        mode = profile.backend_mode
        if mode == "openai_chat":
            return self._call_openai_chat(profile, body)
        if mode == "openai_completion":
            completion = self._call_openai_completion_fallback(profile, body)
            if completion is None:
                raise ValueError(
                    f"profile {profile.alias} has no OpenAI completion endpoint"
                )
            return completion
        if mode == "llama_cpp_legacy":
            if not profile.raw.get("legacy_completion_url"):
                raise ValueError(
                    f"profile {profile.alias} has no legacy_completion_url"
                )
            return self._call_llamacpp_legacy(profile, body)
        if mode != "auto":
            raise ValueError(f"unsupported backend_mode for {profile.alias}: {mode}")

        status, headers, payload = self._call_openai_chat(profile, body)
        if status not in (404, 405):
            return status, headers, payload
        completion = self._call_openai_completion_fallback(profile, body)
        if completion is not None:
            return completion
        if profile.raw.get("legacy_completion_url"):
            return self._call_llamacpp_legacy(profile, body)
        return status, headers, payload

    def _call_openai_chat(
        self, profile: ServingProfile, body: dict[str, Any]
    ) -> tuple[int, dict[str, str], bytes]:
        data = json.dumps(body).encode("utf-8")
        req = Request(
            profile.upstream_chat_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": self.headers.get(
                    "Authorization", "Bearer local-no-key"
                ),
            },
        )
        try:
            with (
                urlopen(req, timeout=self.state.upstream_timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                return resp.status, dict(resp.headers.items()), resp.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()

    def _call_openai_completion_fallback(
        self, profile: ServingProfile, body: dict[str, Any]
    ) -> tuple[int, dict[str, str], bytes] | None:
        if not profile.base_url:
            return None
        prompt = self._messages_to_prompt(body.get("messages") or [])
        completion_body = {
            "model": profile.raw.get("api_model_name")
            or profile.raw.get("upstream_model")
            or body.get("model"),
            "prompt": prompt,
            "temperature": body.get("temperature", 0),
            "max_tokens": body.get("max_tokens", 256),
            "stream": False,
        }
        req = Request(
            profile.base_url.rstrip("/") + "/completions",
            data=json.dumps(completion_body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": self.headers.get(
                    "Authorization", "Bearer local-no-key"
                ),
            },
        )
        try:
            with (
                urlopen(req, timeout=self.state.upstream_timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                raw = json.loads(resp.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            if exc.code in (404, 405):
                return None
            return exc.code, dict(exc.headers.items()), exc.read()
        content = ""
        choices = raw.get("choices") or []
        if choices:
            first = choices[0]
            content = (
                first.get("text") or (first.get("message") or {}).get("content") or ""
            )
        wrapped = {
            "id": raw.get("id", f"chatcmpl-pheno-{uuid.uuid4().hex[:12]}"),
            "object": "chat.completion",
            "created": raw.get("created", int(time.time())),
            "model": body.get("model"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": choices[0].get("finish_reason", "stop")
                    if choices
                    else "stop",
                }
            ],
            "usage": raw.get("usage", {}),
            "pheno_serve": {"openai_completions_fallback": True},
        }
        return (
            200,
            {"Content-Type": "application/json"},
            json.dumps(wrapped).encode("utf-8"),
        )

    def _call_llamacpp_legacy(
        self, profile: ServingProfile, body: dict[str, Any]
    ) -> tuple[int, dict[str, str], bytes]:
        prompt = self._messages_to_prompt(body.get("messages") or [])
        legacy_body = {
            "prompt": prompt,
            "temperature": body.get("temperature", 0),
            "n_predict": body.get("max_tokens", 256),
            "stream": False,
        }
        req = Request(
            str(profile.raw["legacy_completion_url"]),
            data=json.dumps(legacy_body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with (
            urlopen(req, timeout=self.state.upstream_timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            legacy = json.loads(resp.read().decode("utf-8") or "{}")
        content = (
            legacy.get("content") or legacy.get("response") or legacy.get("text") or ""
        )
        created = int(time.time())
        wrapped = {
            "id": f"chatcmpl-pheno-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": created,
            "model": body.get("model"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": legacy.get("stop_type")
                    or legacy.get("finish_reason")
                    or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": legacy.get("tokens_evaluated"),
                "completion_tokens": legacy.get("tokens_predicted"),
                "total_tokens": None,
            },
            "pheno_serve": {"legacy_llamacpp": True},
        }
        return (
            200,
            {"Content-Type": "application/json"},
            json.dumps(wrapped).encode("utf-8"),
        )

    def _messages_to_prompt(self, messages: list[dict[str, Any]]) -> str:
        parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("assistant:")
        return "\n".join(parts)


def run(config_path: str | None = None) -> None:
    config = load_config(config_path)
    host = str(config.server.get("host", "127.0.0.1"))
    port = int(config.server.get("port", 21080))
    state = ServeState(config)
    handler = type(
        "ConfiguredPhenoServeHandler", (PhenoServeHandler,), {"state": state}
    )
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"pheno-serve-dev listening on http://{host}:{port}")
    httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pheno-serve-dev")
    parser.add_argument("--config", help="Path to pheno_serve.yaml")
    args = parser.parse_args()
    run(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
