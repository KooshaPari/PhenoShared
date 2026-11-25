"""Tests for dispatch_mcp.server.

Note: These tests mock httpx.Client to avoid requiring a live OmniRoute server.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCallOmniroute:
    """Tests for _call_omniroute via dispatch_custom and dispatch_health."""

    def test_dispatch_custom_success(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "tier": "worker",
                "message": "hello",
            }
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            result = dispatch_custom("worker", "hello")
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:8080/dispatch"
            assert call_args[1]["json"] == {"tier": "worker", "message": "hello"}
            assert result == {"ok": True, "tier": "worker", "message": "hello"}

    def test_dispatch_custom_connection_error(self) -> None:
        import httpx

        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(httpx.ConnectError):
                dispatch_custom("main", "test")

    def test_dispatch_custom_timeout(self) -> None:
        import httpx

        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(httpx.TimeoutException):
                dispatch_custom("worker", "test")

    def test_dispatch_custom_http_error(self) -> None:
        import httpx

        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(httpx.HTTPStatusError):
                dispatch_custom("worker", "test")

    def test_dispatch_custom_json_decode_error(self) -> None:
        import json

        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            inner = json.JSONDecodeError("invalid", "", 0)
            mock_response.json.side_effect = inner
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(RuntimeError, match="invalid response"):
                dispatch_custom("worker", "test")

    def test_dispatch_health_success_sanitized(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "ok",
                "upstream_id": "secret-internal",
                "error": None,
            }
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_health

            result = dispatch_health()
            assert "status" in result
            assert "upstream_id" not in result
            assert result == {"status": "ok", "error": None}

    def test_invalid_omniroute_url_raises(self) -> None:
        with patch.dict("os.environ", {"OMNIROUTE_URL": "javascript:alert(1)"}):
            from dispatch_mcp.server import dispatch_health

            with pytest.raises(ValueError, match="must use http or https"):
                dispatch_health()

    def test_missing_omniroute_url_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(ValueError, match="OMNIROUTE_URL"):
                dispatch_custom("worker", "test")


class TestDispatchCustomTierValidation:
    """Tests for dispatch_custom tier validation."""

    def test_invalid_tier_raises(self) -> None:
        from dispatch_mcp.server import dispatch_custom

        with pytest.raises(ValueError, match="Invalid tier 'rogue'"):
            dispatch_custom("rogue", "test")

    def test_empty_tier_raises(self) -> None:
        from dispatch_mcp.server import dispatch_custom

        with pytest.raises(ValueError, match="Invalid tier ''"):
            dispatch_custom("", "test")


class TestTierTools:
    """Tests that tier dispatch tools are registered and callable."""

    def test_all_tier_tools_importable(self) -> None:
        from dispatch_mcp.server import (
            dispatch_codeman,
            dispatch_freetier,
            dispatch_gemini,
            dispatch_haiku,
            dispatch_kimi,
            dispatch_kimi_thinking,
            dispatch_main,
            dispatch_minimax,
            dispatch_opus,
            dispatch_worker,
        )

        tools = [
            dispatch_worker,
            dispatch_main,
            dispatch_codeman,
            dispatch_freetier,
            dispatch_kimi,
            dispatch_kimi_thinking,
            dispatch_minimax,
            dispatch_opus,
            dispatch_haiku,
            dispatch_gemini,
        ]
        for tool in tools:
            assert callable(tool)

    def test_all_tier_tools_have_unique_references(self) -> None:
        """Regression: ensure no silent tool-name collisions."""
        from dispatch_mcp.server import (
            dispatch_codeman,
            dispatch_freetier,
            dispatch_gemini,
            dispatch_haiku,
            dispatch_kimi,
            dispatch_kimi_thinking,
            dispatch_main,
            dispatch_minimax,
            dispatch_opus,
            dispatch_worker,
        )

        tools = [
            dispatch_worker,
            dispatch_main,
            dispatch_codeman,
            dispatch_freetier,
            dispatch_kimi,
            dispatch_kimi_thinking,
            dispatch_minimax,
            dispatch_opus,
            dispatch_haiku,
            dispatch_gemini,
        ]
        seen: dict[int, str] = {}
        for tool in tools:
            id_ = id(tool)
            assert id_ not in seen, f"Duplicate tool reference for {seen[id_]}"
            seen[id_] = getattr(tool, "__name__", str(tool))



class TestMessageSizeLimit:
    """Tests for MAX_MESSAGE_LENGTH enforcement."""

    def test_unicode_message_is_accepted(self) -> None:
        from dispatch_mcp.server import dispatch_custom

        with patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}), \
             patch("dispatch_mcp.server.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            dispatch_custom("worker", "hello 🐍")
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["message"] == "hello 🐍"


    def test_liveness_does_not_call_backend(self) -> None:
        with patch("dispatch_mcp.server.httpx.Client") as mock_client_cls:
            from dispatch_mcp.server import dispatch_liveness

            dispatch_liveness()
            mock_client_cls.assert_not_called()

    def test_dispatch_custom_rejects_oversized_message(self) -> None:
        from dispatch_mcp.server import dispatch_custom

        with pytest.raises(ValueError, match="exceeds maximum length"):
            dispatch_custom("worker", "x" * 5000)

    def test_dispatch_worker_rejects_oversized_message(self) -> None:
        # All named tier functions share _make_dispatch; verify one explicitly.
        from dispatch_mcp.server import dispatch_worker

        with pytest.raises(ValueError, match="exceeds maximum length"):
            dispatch_worker("x" * 5000)

    def test_dispatch_custom_accepts_exact_limit(self) -> None:
        from dispatch_mcp.server import MAX_MESSAGE_LENGTH, dispatch_custom

        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            # exactly at limit should pass
            msg = "x" * MAX_MESSAGE_LENGTH
            result = dispatch_custom("worker", msg)
            assert result == {"ok": True}


class TestLivenessProbe:
    """Tests for dispatch_liveness."""

    def test_liveness_returns_alive_status(self) -> None:
        from dispatch_mcp.server import dispatch_liveness

        result = dispatch_liveness()
        assert result["status"] == "alive"
        assert result["server"] == "dispatch-mcp"


class TestOmniRouteUrlEdgeCases:
    """URL construction edge cases."""

    def test_trailing_slash_in_url_not_duplicated(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080/"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            dispatch_custom("worker", "hello")
            call_args = mock_client.post.call_args
            # must not produce http://localhost:8080//dispatch
            assert "//dispatch" not in call_args[0][0]
            assert call_args[0][0] == "http://localhost:8080/dispatch"

    def test_leading_slash_in_route_not_duplicated(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            dispatch_custom("worker", "hello")
            call_args = mock_client.post.call_args
            # must not produce http://localhost:8080//dispatch
            assert "//dispatch" not in call_args[0][0]


class TestSanitizeResponse:
    """Tests for _sanitize_response."""

    def test_allowlisted_keys_pass_through(self) -> None:
        from dispatch_mcp.server import _sanitize_response

        result = _sanitize_response({"ok": True, "tier": "worker", "message": "hi"})
        assert result == {"ok": True, "tier": "worker", "message": "hi"}

    def test_internal_keys_are_stripped(self) -> None:
        from dispatch_mcp.server import _sanitize_response

        result = _sanitize_response(
            {
                "ok": True,
                "upstream_hostname": "internal-db.local",
                "stack_trace": "...",
                "internal_id": "abc123",
            }
        )
        assert result == {"ok": True}
        assert "upstream_hostname" not in result
        assert "stack_trace" not in result
        assert "internal_id" not in result

    def test_error_key_preserved(self) -> None:
        from dispatch_mcp.server import _sanitize_response

        result = _sanitize_response({"error": "something went wrong", "ok": False})
        assert result == {"error": "something went wrong", "ok": False}


class TestRedirectPolicy:
    """Tests that httpx.Client is configured with follow_redirects=False."""

    def test_no_redirect_followed(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.server.httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True}
            mock_response.raise_for_status = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            from dispatch_mcp.server import dispatch_custom

            dispatch_custom("worker", "hello")
            mock_client_cls.assert_called_once_with(timeout=10, follow_redirects=False)
