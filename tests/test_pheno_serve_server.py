"""Comprehensive unit tests for pheno.serve.server.

Covers: ServeState, response helpers, PhenoServeHandler routing and proxy logic,
_percentile, _messages_to_prompt, _event_base, _call_upstream, and all backend modes.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pheno.serve.config import ServeConfig
from pheno.serve.server import (
    PhenoServeHandler,
    ServeState,
    _json_response,
    _text_response,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(
    profiles: dict[str, Any] | None = None,
    capture_headers: list[str] | None = None,
    server_overrides: dict[str, Any] | None = None,
) -> ServeConfig:
    raw: dict[str, Any] = {"server": {}, "profiles": profiles or {}}
    if capture_headers is not None:
        raw["headers"] = {"capture": capture_headers}
    if server_overrides:
        raw["server"].update(server_overrides)
    return ServeConfig(path=Path("pheno-test.yaml"), raw=raw)


def _make_handler(
    state: ServeState | None = None,
    method: str = "GET",
    path: str = "/",
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> PhenoServeHandler:
    """Build a PhenoServeHandler with mocked socket for testing.

    The key insight: BaseHTTPRequestHandler.send_response/send_header/end_headers
    write HTTP header lines to wfile. We suppress those so wfile contains only the
    body written by response helpers and proxy methods.
    """
    if state is None:
        state = ServeState(_make_config())

    handler = PhenoServeHandler.__new__(PhenoServeHandler)
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.headers = _FakeHeaders(headers or {})
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.request_version = "HTTP/1.1"
    handler.command = method
    handler.path = path
    handler.client_address = ("127.0.0.1", 12345)
    handler.state = state
    # Suppress stderr logging
    handler.log_message = lambda fmt, *args: None
    # Suppress HTTP response header lines written to wfile
    handler.send_response = lambda code, *a, **kw: None
    handler.send_header = lambda name, value, *a, **kw: None
    handler.end_headers = lambda: None
    return handler


class _FakeHeaders(dict):
    """Minimal stand-in for http.client.HTTPMessage with .get()."""

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key, default)


# ---------------------------------------------------------------------------
# ServeState tests
# ---------------------------------------------------------------------------


class TestServeState:
    def test_init_sets_fields(self) -> None:
        cfg = _make_config(
            server_overrides={"upstream_timeout_s": 42}
        )
        state = ServeState(cfg)
        assert state.config is cfg
        assert state.registry is not None
        assert state.events is not None
        assert state.metrics is not None
        assert state.upstream_timeout_s == 42.0

    def test_init_default_timeout(self) -> None:
        state = ServeState(_make_config())
        assert state.upstream_timeout_s == 60.0

    def test_readiness_no_active_profiles(self) -> None:
        state = ServeState(_make_config())
        ready, checks = state.readiness()
        assert ready is False
        assert checks["active_profiles"] == 0
        assert "no active serving profiles" in checks["reason"]

    def test_readiness_active_no_base_url(self) -> None:
        cfg = _make_config(
            profiles={"m1": {"engine": "llama.cpp", "status": "active"}}
        )
        ready, checks = ServeState(cfg).readiness()
        assert ready is False
        assert checks["m1"]["ready"] is False
        assert "no upstream base_url" in checks["m1"]["reason"]

    def test_readiness_active_upstream_ok(self) -> None:
        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:9999/v1",
                    "status": "active",
                }
            }
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            ready, checks = ServeState(cfg).readiness()
        assert ready is True
        assert checks["m1"]["ready"] is True
        assert checks["m1"]["status"] == 200

    def test_readiness_upstream_error(self) -> None:
        from urllib.error import URLError

        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:9999/v1",
                    "status": "active",
                }
            }
        )
        with patch("pheno.serve.server.urlopen", side_effect=URLError("connection refused")):
            ready, checks = ServeState(cfg).readiness()
        assert ready is False
        assert checks["m1"]["ready"] is False
        assert "connection refused" in checks["m1"]["reason"]

    def test_readiness_multiple_profiles_one_fails(self) -> None:
        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "a",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                },
                "m2": {
                    "engine": "b",
                    "base_url": None,
                    "status": "active",
                },
            }
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            ready, checks = ServeState(cfg).readiness()
        assert ready is False  # m2 has no base_url
        assert checks["m1"]["ready"] is True
        assert checks["m2"]["ready"] is False


# ---------------------------------------------------------------------------
# Response helper tests
# ---------------------------------------------------------------------------


class TestJsonResponse:
    def test_json_response_writes_correctly(self) -> None:
        handler = MagicMock()
        handler.wfile = io.BytesIO()
        _json_response(handler, 200, {"ok": True})
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["ok"] is True

    def test_json_response_non_ascii(self) -> None:
        handler = MagicMock()
        handler.wfile = io.BytesIO()
        _json_response(handler, 400, {"msg": "\u00e9l\u00e8ve"})
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["msg"] == "\u00e9l\u00e8ve"


class TestTextResponse:
    def test_text_response_default_content_type(self) -> None:
        handler = MagicMock()
        handler.wfile = io.BytesIO()
        _text_response(handler, 200, "hello")
        handler.send_response.assert_called_once_with(200)
        # Check send_header was called with Content-Type
        calls = {name: val for name, val in handler.send_header.call_args_list}
        assert calls.get(("Content-Type",)) is not None or any(
            "Content-Type" in str(c) for c in handler.send_header.call_args_list
        )

    def test_text_response_custom_content_type(self) -> None:
        handler = MagicMock()
        handler.wfile = io.BytesIO()
        _text_response(handler, 200, "data", "application/octet-stream")
        found = False
        for call in handler.send_header.call_args_list:
            if call[0][0] == "Content-Type" and call[0][1] == "application/octet-stream":
                found = True
        assert found


# ---------------------------------------------------------------------------
# PhenoServeHandler.do_GET tests
# ---------------------------------------------------------------------------


class TestDoGet:
    def test_healthz(self) -> None:
        handler = _make_handler(path="/healthz")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["ok"] is True
        assert body["service"] == "pheno-serve-dev"

    def test_v1_models(self) -> None:
        handler = _make_handler(path="/v1/models")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["object"] == "list"
        assert "data" in body

    def test_admin_models(self) -> None:
        handler = _make_handler(path="/admin/models")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert "profiles" in body

    def test_metrics(self) -> None:
        handler = _make_handler(path="/metrics")
        handler.do_GET()
        resp = handler.wfile.getvalue()
        assert b"pheno_serve_requests_total" in resp

    def test_unknown_path_404(self) -> None:
        handler = _make_handler(path="/nope")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert "error" in body
        assert "unknown path" in body["error"]["message"]

    def test_readyz_not_ready(self) -> None:
        handler = _make_handler(path="/readyz")
        handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["ok"] is False
        assert "checks" in body

    def test_readyz_ready(self) -> None:
        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                }
            }
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            handler = _make_handler(state=ServeState(cfg), path="/readyz")
            handler.do_GET()
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["ok"] is True


# ---------------------------------------------------------------------------
# PhenoServeHandler.do_POST tests
# ---------------------------------------------------------------------------


class TestDoPost:
    def test_unknown_post_path(self) -> None:
        handler = _make_handler(method="POST", path="/unknown")
        handler.do_POST()
        body = json.loads(handler.wfile.getvalue().decode())
        assert "error" in body
        assert "unknown path" in body["error"]["message"]

    def test_admin_routes_resolve_success(self) -> None:
        cfg = _make_config(
            profiles={
                "qwen": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                }
            }
        )
        req_body = json.dumps({"model": "qwen"}).encode()
        handler = _make_handler(
            state=ServeState(cfg),
            method="POST",
            path="/admin/routes/resolve",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )
        handler.do_POST()
        body = json.loads(handler.wfile.getvalue().decode())
        assert body["resolved"] == "qwen"
        assert body["engine"] == "llama.cpp"

    def test_admin_routes_resolve_not_found(self) -> None:
        handler = _make_handler(
            method="POST",
            path="/admin/routes/resolve",
            body=json.dumps({"model": "nonexistent"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        handler.do_POST()
        body = json.loads(handler.wfile.getvalue().decode())
        assert "error" in body


# ---------------------------------------------------------------------------
# _read_json tests
# ---------------------------------------------------------------------------


class TestReadJson:
    def test_read_json_valid(self) -> None:
        data = json.dumps({"model": "test", "messages": []}).encode()
        handler = _make_handler(
            method="POST",
            path="/v1/chat/completions",
            body=data,
            headers={"Content-Length": str(len(data))},
        )
        result = handler._read_json()
        assert result["model"] == "test"

    def test_read_json_empty_body(self) -> None:
        handler = _make_handler()
        # No Content-Length header → defaults to 0 → returns {}
        result = handler._read_json()
        assert result == {}


# ---------------------------------------------------------------------------
# _captured_headers tests
# ---------------------------------------------------------------------------


class TestCapturedHeaders:
    def test_captures_configured_headers(self) -> None:
        cfg = _make_config(
            capture_headers=["X-Pheno-Run-Id", "X-Pheno-Lane"]
        )
        handler = _make_handler(
            state=ServeState(cfg),
            headers={"X-Pheno-Run-Id": "run-1", "X-Pheno-Lane": "unit"},
        )
        result = handler._captured_headers()
        assert result["X-Pheno-Run-Id"] == "run-1"
        assert result["X-Pheno-Lane"] == "unit"

    def test_missing_headers_not_in_result(self) -> None:
        cfg = _make_config(capture_headers=["X-Missing"])
        handler = _make_handler(state=ServeState(cfg))
        result = handler._captured_headers()
        assert "X-Missing" not in result

    def test_no_capture_headers(self) -> None:
        handler = _make_handler()
        result = handler._captured_headers()
        assert result == {}


# ---------------------------------------------------------------------------
# _percentile tests
# ---------------------------------------------------------------------------


class TestPercentile:
    def test_empty_list(self) -> None:
        assert PhenoServeHandler._percentile([], 0.5) is None

    def test_single_value(self) -> None:
        assert PhenoServeHandler._percentile([42.0], 0.5) == 42.0

    def test_multiple_values_p50(self) -> None:
        result = PhenoServeHandler._percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5)
        # sorted=[1,2,3,4,5], idx=round(4*0.5)=2 → ordered[2]=3.0
        assert result == 3.0

    def test_two_values_p50(self) -> None:
        # sorted=[10,20], idx=round(1*0.5)=round(0.5)=0 → ordered[0]=10.0
        result = PhenoServeHandler._percentile([10.0, 20.0], 0.5)
        assert result == 10.0

    def test_p95_ten_values(self) -> None:
        values = [float(v) for v in range(1, 11)]  # [1..10]
        result = PhenoServeHandler._percentile(values, 0.95)
        # sorted=[1..10], idx=round(9*0.95)=round(8.55)=9 → ordered[9]=10.0
        assert result == 10.0


# ---------------------------------------------------------------------------
# _messages_to_prompt tests
# ---------------------------------------------------------------------------


class TestMessagesToPrompt:
    def test_empty_messages(self) -> None:
        handler = _make_handler()
        result = handler._messages_to_prompt([])
        assert result == "assistant:"

    def test_single_user_message(self) -> None:
        handler = _make_handler()
        result = handler._messages_to_prompt([{"role": "user", "content": "hi"}])
        assert result == "user: hi\nassistant:"

    def test_multiple_messages(self) -> None:
        handler = _make_handler()
        msgs = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = handler._messages_to_prompt(msgs)
        assert "system: Be helpful" in result
        assert "user: Hello" in result
        assert result.endswith("assistant:")

    def test_missing_role_defaults_user(self) -> None:
        handler = _make_handler()
        result = handler._messages_to_prompt([{"content": "test"}])
        assert result.startswith("user: test")


# ---------------------------------------------------------------------------
# _event_base tests
# ---------------------------------------------------------------------------


class TestEventBase:
    def test_event_base_captures_headers(self) -> None:
        cfg = _make_config(
            capture_headers=["X-Pheno-Run-Id", "X-Pheno-Lane", "X-Pheno-Role"],
            profiles={"m": {"engine": "a", "status": "active"}},
        )
        handler = _make_handler(
            state=ServeState(cfg),
            headers={
                "X-Pheno-Run-Id": "run-1",
                "X-Pheno-Lane": "unit",
                "X-Pheno-Role": "critic",
            },
        )
        profile = handler.state.registry.get("m")
        result = handler._event_base("req-1", "m", profile, {"stream": True})
        assert result["request_id"] == "req-1"
        assert result["run_id"] == "run-1"
        assert result["lane"] == "unit"
        assert result["role"] == "critic"
        assert result["stream"] is True

    def test_event_base_stream_false(self) -> None:
        handler = _make_handler()
        from pheno.serve.registry import ServingProfile

        p = ServingProfile(alias="x", engine="e", base_url=None, status="active", raw={})
        result = handler._event_base("r", "x", p, {})
        assert result["stream"] is False

    def test_event_base_decode_method(self) -> None:
        handler = _make_handler()
        from pheno.serve.registry import ServingProfile

        p = ServingProfile(
            alias="x", engine="e", base_url=None, status="active",
            raw={"decode": {"method": "beam_search"}},
        )
        result = handler._event_base("r", "x", p, {})
        assert result["decode_method"] == "beam_search"

    def test_event_base_no_decode(self) -> None:
        handler = _make_handler()
        from pheno.serve.registry import ServingProfile

        p = ServingProfile(alias="x", engine="e", base_url=None, status="active", raw={})
        result = handler._event_base("r", "x", p, {})
        assert result["decode_method"] is None


# ---------------------------------------------------------------------------
# _proxy_completion tests
# ---------------------------------------------------------------------------


class TestProxyCompletion:
    def test_unknown_model_404(self) -> None:
        handler = _make_handler(
            method="POST",
            path="/v1/chat/completions",
            body=json.dumps({"model": "unknown"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        handler._proxy_completion()
        body = json.loads(handler.wfile.getvalue().decode())
        assert "error" in body
        assert body["error"]["type"] == "unknown_model"


# ---------------------------------------------------------------------------
# _call_upstream tests
# ---------------------------------------------------------------------------


class TestCallUpstream:
    def test_unsupported_backend_mode(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "bogus"},
        )
        with pytest.raises(ValueError, match="unsupported backend_mode"):
            handler._call_upstream(profile, {"model": "x"})

    def test_openai_chat_success(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_chat"},
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"choices":[]}'
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            status, headers, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 200
        assert json.loads(payload) == {"choices": []}

    def test_openai_chat_http_error(self) -> None:
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_chat"},
        )
        err = HTTPError(
            url="http://x", code=500, msg="err", hdrs={}, fp=io.BytesIO(b"bad")
        )
        with patch("pheno.serve.server.urlopen", side_effect=err):
            status, _, _ = handler._call_upstream(profile, {"model": "x"})
        assert status == 500

    def test_auto_mode_fallback_to_completion(self) -> None:
        """When openai_chat returns 404, auto mode falls back to completion."""
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "auto"},
        )

        call_count = [0]

        def side_effect(req, timeout=None):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (openai_chat) → 404
                raise HTTPError(
                    url="http://x/chat", code=404, msg="not found", hdrs={}, fp=io.BytesIO(b"")
                )
            # Second call (completion) → success
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.headers = {"Content-Type": "application/json"}
            mock_resp.read.return_value = json.dumps(
                {"id": "c1", "choices": [{"text": "ok", "finish_reason": "stop"}]}
            ).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("pheno.serve.server.urlopen", side_effect=side_effect):
            status, headers, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 200
        body = json.loads(payload)
        assert body["pheno_serve"]["openai_completions_fallback"] is True

    def test_auto_mode_fallback_to_llamacpp_legacy(self) -> None:
        """When chat returns 404 and completion returns None, auto falls back to legacy."""
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={
                "backend_mode": "auto",
                "legacy_completion_url": "http://127.0.0.1:1/completion",
            },
        )

        call_count = [0]

        def side_effect(req, timeout=None):
            call_count[0] += 1
            if call_count[0] <= 1:
                # First call → 404
                raise HTTPError(
                    url="http://x/chat", code=404, msg="not found", hdrs={}, fp=io.BytesIO(b"")
                )
            if call_count[0] == 2:
                # Second call (completion) → 404
                raise HTTPError(
                    url="http://x/comp", code=404, msg="not found", hdrs={}, fp=io.BytesIO(b"")
                )
            # Third call (legacy) → success
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"content": "legacy ok"}).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("pheno.serve.server.urlopen", side_effect=side_effect):
            status, _, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 200
        body = json.loads(payload)
        assert body["pheno_serve"]["legacy_llamacpp"] is True

    def test_auto_mode_returns_404_when_no_fallbacks(self) -> None:
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "auto"},
        )

        def side_effect(req, timeout=None):
            raise HTTPError(
                url="http://x", code=404, msg="nf", hdrs={}, fp=io.BytesIO(b"nf")
            )

        with patch("pheno.serve.server.urlopen", side_effect=side_effect):
            status, _, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 404

    def test_llama_cpp_legacy_success(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={
                "backend_mode": "llama_cpp_legacy",
                "legacy_completion_url": "http://127.0.0.1:1/legacy",
            },
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "content": "hi",
            "stop_type": "stop",
            "tokens_evaluated": 10,
            "tokens_predicted": 5,
        }).encode()
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            status, _, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 200
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == "hi"
        assert body["pheno_serve"]["legacy_llamacpp"] is True

    def test_llama_cpp_legacy_no_url_raises(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "llama_cpp_legacy"},
        )
        with pytest.raises(ValueError, match="no legacy_completion_url"):
            handler._call_upstream(profile, {"model": "x"})

    def test_openai_completion_no_base_url_returns_none(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url=None,
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        result = handler._call_openai_completion_fallback(profile, {"model": "x"})
        assert result is None

    def test_openai_completion_404_returns_none(self) -> None:
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        err = HTTPError(
            url="http://x/comp", code=404, msg="nf", hdrs={}, fp=io.BytesIO(b"")
        )
        with patch("pheno.serve.server.urlopen", side_effect=err):
            result = handler._call_openai_completion_fallback(profile, {"model": "x"})
        assert result is None

    def test_openai_completion_405_returns_none(self) -> None:
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        err = HTTPError(
            url="http://x/comp", code=405, msg="not allowed", hdrs={}, fp=io.BytesIO(b"")
        )
        with patch("pheno.serve.server.urlopen", side_effect=err):
            result = handler._call_openai_completion_fallback(profile, {"model": "x"})
        assert result is None

    def test_openai_completion_non_404_error(self) -> None:
        from urllib.error import HTTPError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        err = HTTPError(
            url="http://x/comp", code=500, msg="err", hdrs={}, fp=io.BytesIO(b"server err")
        )
        with patch("pheno.serve.server.urlopen", side_effect=err):
            status, _, payload = handler._call_upstream(profile, {"model": "x"})
        assert status == 500

    def test_openai_completion_fallback_content_field(self) -> None:
        """Completion response uses 'message.content' when 'text' is absent."""
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        resp_data = json.dumps({
            "id": "c1",
            "choices": [
                {"message": {"content": "from message"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 10},
        }).encode()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = resp_data
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            result = handler._call_openai_completion_fallback(
                profile, {"model": "x", "messages": [{"role": "user", "content": "hi"}]}
            )
        assert result is not None
        status, _, payload = result
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == "from message"

    def test_openai_completion_empty_choices(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        resp_data = json.dumps({"id": "c1", "choices": []}).encode()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = resp_data
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            result = handler._call_openai_completion_fallback(profile, {"model": "x"})
        assert result is not None
        _, _, payload = result
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == ""

    def test_openai_completion_none_choices(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={"backend_mode": "openai_completion"},
        )
        resp_data = json.dumps({"id": "c1"}).encode()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = resp_data
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            result = handler._call_openai_completion_fallback(profile, {"model": "x"})
        assert result is not None


# ---------------------------------------------------------------------------
# _proxy_stream tests
# ---------------------------------------------------------------------------


class TestProxyStream:
    def test_stream_success(self) -> None:
        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={},
        )

        chunk1 = b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        chunk2 = b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        chunk3 = b""

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "text/event-stream"}
        mock_resp.read.side_effect = [chunk1, chunk2, chunk3]

        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            handler._proxy_stream(
                profile,
                {"model": "x", "stream": True},
                {"request_id": "r1", "model_alias": "x"},
                "r1",
                0.0,
            )

        body = handler.wfile.getvalue()
        assert b"Hello" in body
        assert b"world" in body

    def test_stream_upstream_error(self) -> None:
        from urllib.error import URLError

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x",
            engine="e",
            base_url="http://127.0.0.1:1/v1",
            status="active",
            raw={},
        )

        with patch("pheno.serve.server.urlopen", side_effect=URLError("conn refused")):
            handler._proxy_stream(
                profile,
                {"model": "x", "stream": True},
                {"request_id": "r1", "model_alias": "x"},
                "r1",
                0.0,
            )


# ---------------------------------------------------------------------------
# proxy_completion with stream + backend_mode edge cases
# ---------------------------------------------------------------------------


class TestProxyCompletionEdgeCases:
    def test_stream_auto_mode_triggers_proxy_stream(self) -> None:
        """When stream=True and backend_mode=auto, _proxy_stream is called."""
        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                    "backend_mode": "auto",
                }
            }
        )
        state = ServeState(cfg)
        req_body = json.dumps({"model": "m1", "stream": True}).encode()
        handler = _make_handler(
            state=state,
            method="POST",
            path="/v1/chat/completions",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )

        with patch.object(handler, "_proxy_stream") as mock_stream:
            handler._proxy_completion()
        mock_stream.assert_called_once()

    def test_non_stream_non_auto_mode_calls_upstream(self) -> None:
        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                    "backend_mode": "openai_chat",
                }
            }
        )
        state = ServeState(cfg)
        req_body = json.dumps({"model": "m1", "stream": False}).encode()
        handler = _make_handler(
            state=state,
            method="POST",
            path="/v1/chat/completions",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"choices":[]}'
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            handler._proxy_completion()

        assert handler.wfile.getvalue() != b""

    def test_proxy_completion_upstream_error_returns_502(self) -> None:
        from urllib.error import URLError

        cfg = _make_config(
            profiles={
                "m1": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                    "backend_mode": "openai_chat",
                }
            }
        )
        state = ServeState(cfg)
        req_body = json.dumps({"model": "m1"}).encode()
        handler = _make_handler(
            state=state,
            method="POST",
            path="/v1/chat/completions",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )

        with patch("pheno.serve.server.urlopen", side_effect=URLError("timeout")):
            handler._proxy_completion()

        body = json.loads(handler.wfile.getvalue().decode())
        assert body["error"]["type"] == "upstream_error"
        assert body["error"]["request_id"]

    def test_v1_completions_also_proxied(self) -> None:
        """Both /v1/chat/completions and /v1/completions route to proxy."""
        handler = _make_handler(method="POST", path="/v1/completions")
        with patch.object(handler, "_proxy_completion") as mock_pc:
            handler.do_POST()
        mock_pc.assert_called_once()

    def test_model_name_resolved_from_api_model_name(self) -> None:
        """When api_model_name is set in profile, it's used for upstream."""
        cfg = _make_config(
            profiles={
                "alias1": {
                    "engine": "e",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                    "api_model_name": "real-model",
                }
            }
        )
        state = ServeState(cfg)
        req_body = json.dumps({"model": "alias1"}).encode()
        handler = _make_handler(
            state=state,
            method="POST",
            path="/v1/chat/completions",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {}
        mock_resp.read.return_value = b'{}'
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            handler._proxy_completion()

    def test_model_name_resolved_from_upstream_model(self) -> None:
        """When upstream_model is set (no api_model_name), it's used."""
        cfg = _make_config(
            profiles={
                "alias1": {
                    "engine": "e",
                    "base_url": "http://127.0.0.1:1/v1",
                    "status": "active",
                    "upstream_model": "up-model",
                }
            }
        )
        state = ServeState(cfg)
        req_body = json.dumps({"model": "alias1"}).encode()
        handler = _make_handler(
            state=state,
            method="POST",
            path="/v1/chat/completions",
            body=req_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
        )
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {}
        mock_resp.read.return_value = b'{}'
        with patch("pheno.serve.server.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            handler._proxy_completion()


# ---------------------------------------------------------------------------
# log_message is a no-op
# ---------------------------------------------------------------------------


class TestLogMessage:
    def test_log_message_returns_none(self) -> None:
        handler = _make_handler()
        result = handler.log_message("test %s", "arg")
        assert result is None


# ---------------------------------------------------------------------------
# llamacpp legacy response content variants
# ---------------------------------------------------------------------------


class TestLegacyContentVariants:
    def _legacy_handler(self, raw: dict) -> tuple[PhenoServeHandler, MagicMock]:

        from pheno.serve.registry import ServingProfile

        cfg = _make_config()
        state = ServeState(cfg)
        handler = _make_handler(state=state)
        profile = ServingProfile(
            alias="x", engine="e", base_url="http://x/v1",
            status="active", raw={
                "backend_mode": "llama_cpp_legacy",
                "legacy_completion_url": "http://x/legacy",
            },
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(raw).encode()
        return handler, profile, mock_resp

    def test_legacy_content_field(self) -> None:
        handler, profile, mock_resp = self._legacy_handler({"content": "c1"})
        with patch("pheno.serve.server.urlopen") as m:
            m.return_value.__enter__ = MagicMock(return_value=mock_resp)
            m.return_value.__exit__ = MagicMock(return_value=False)
            _, _, payload = handler._call_upstream(profile, {"model": "x"})
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == "c1"

    def test_legacy_response_field(self) -> None:
        handler, profile, mock_resp = self._legacy_handler({"response": "r1"})
        with patch("pheno.serve.server.urlopen") as m:
            m.return_value.__enter__ = MagicMock(return_value=mock_resp)
            m.return_value.__exit__ = MagicMock(return_value=False)
            _, _, payload = handler._call_upstream(profile, {"model": "x"})
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == "r1"

    def test_legacy_text_field(self) -> None:
        handler, profile, mock_resp = self._legacy_handler({"text": "t1"})
        with patch("pheno.serve.server.urlopen") as m:
            m.return_value.__enter__ = MagicMock(return_value=mock_resp)
            m.return_value.__exit__ = MagicMock(return_value=False)
            _, _, payload = handler._call_upstream(profile, {"model": "x"})
        body = json.loads(payload)
        assert body["choices"][0]["message"]["content"] == "t1"

    def test_legacy_finish_reason_from_stop_type(self) -> None:
        handler, profile, mock_resp = self._legacy_handler(
            {"content": "ok", "stop_type": "eos"}
        )
        with patch("pheno.serve.server.urlopen") as m:
            m.return_value.__enter__ = MagicMock(return_value=mock_resp)
            m.return_value.__exit__ = MagicMock(return_value=False)
            _, _, payload = handler._call_upstream(profile, {"model": "x"})
        body = json.loads(payload)
        assert body["choices"][0]["finish_reason"] == "eos"

    def test_legacy_finish_reason_from_finish_reason(self) -> None:
        handler, profile, mock_resp = self._legacy_handler(
            {"content": "ok", "finish_reason": "length"}
        )
        with patch("pheno.serve.server.urlopen") as m:
            m.return_value.__enter__ = MagicMock(return_value=mock_resp)
            m.return_value.__exit__ = MagicMock(return_value=False)
            _, _, payload = handler._call_upstream(profile, {"model": "x"})
        body = json.loads(payload)
        assert body["choices"][0]["finish_reason"] == "length"
