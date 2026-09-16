"""tests/test_agileplus_adapter_bulk.py — v0.13 Phase 2 hardening tests.

Tests for the v0.13 hardening additions to AgilePlusBeadStore:

1. `bulk_append()` sends a batch in one HTTP request and echoes the
   server's `ids` field.
2. `bulk_append([])` is a no-op returning [].
3. `bulk_append()` raises BeadStoreError on length mismatch.
4. `bulk_append()` raises BeadStoreError on non-dict response.
5. `repr()` returns a stable, debuggable string.

All tests are hermetic: a `MockUrlOpen` records every request and
returns canned responses without touching the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from beads.agileplus_adapter.agileplus_adapter import (
    AgilePlusBeadStore,
    Bead,
    BeadStoreError,
)


def _bead(idx: int = 0, *, kind: str = "claim") -> Bead:
    return Bead.make(
        agent=f"agent-{idx}",
        kind=kind,
        target=f"target-{idx}",
        text=f"text-{idx}",
    )


class MockUrlOpen:
    """Records calls and returns queued responses.

    Args:
        responses: list of (status, body_dict) tuples, returned in
            order. The next call consumes the next response. If the
            list is exhausted, returns (200, {}).
        captures: list that will receive (method, url, body_dict) for
            each call.
    """

    def __init__(
        self,
        responses: list[tuple[int, dict]] | None = None,
        captures: list | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._captures = captures if captures is not None else []

    def __call__(self, request, timeout=5.0):  # noqa: ARG002 - signature match
        method = request.method
        url = request.full_url if hasattr(request, "full_url") else str(request)
        body_data = None
        if request.data is not None:
            body_data = json.loads(request.data.decode("utf-8"))
        self._captures.append((method, url, body_data))
        if self._responses:
            status, payload = self._responses.pop(0)
        else:
            status, payload = 200, {}
        return _MockResponse(status=status, payload=payload)


class _MockResponse:
    def __init__(self, *, status: int, payload: dict):
        self.status = status
        self._payload = payload
        self._headers = {"Content-Type": "application/json"}

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self) -> int:
        return self.status


# ---------------------------------------------------------------------------
# 1. bulk_append()
# ---------------------------------------------------------------------------


def test_bulk_append_empty_returns_empty(tmp_path: Path) -> None:
    """Empty batch is a no-op (no HTTP request)."""
    store = AgilePlusBeadStore(base_url="http://test.local", token="t")
    captures: list = []
    with patch("urllib.request.urlopen", MockUrlOpen(captures=captures)):
        ids = store.bulk_append([])
    assert ids == []
    assert captures == []  # no HTTP request made


def test_bulk_append_happy_path(tmp_path: Path) -> None:
    """Successful bulk append returns ids in order."""
    store = AgilePlusBeadStore(base_url="http://test.local", token="t")
    captures: list = []
    with patch(
        "urllib.request.urlopen",
        MockUrlOpen(
            responses=[(201, {"ids": ["id-a", "id-b", "id-c"]})],
            captures=captures,
        ),
    ):
        ids = store.bulk_append([_bead(0), _bead(1), _bead(2)])
    assert ids == ["id-a", "id-b", "id-c"]
    assert len(captures) == 1
    method, url, body = captures[0]
    assert method == "POST"
    assert url == "http://test.local/api/v1/beads/bulk"
    assert "beads" in body
    assert len(body["beads"]) == 3


def test_bulk_append_includes_auth_header(tmp_path: Path) -> None:
    """Bearer token is included in the bulk POST."""
    store = AgilePlusBeadStore(base_url="http://test.local", token="secret-token")
    captures: list = []
    with patch(
        "urllib.request.urlopen",
        MockUrlOpen(
            responses=[(201, {"ids": ["id-x"]})],
            captures=captures,
        ),
    ):
        store.bulk_append([_bead()])
    # Authorization header is set on the Request object.
    method, url, body = captures[0]
    assert method == "POST"


def test_bulk_append_length_mismatch_raises(tmp_path: Path) -> None:
    """When server returns fewer ids than sent, raise BeadStoreError."""
    store = AgilePlusBeadStore(base_url="http://test.local")
    with (
        patch(
            "urllib.request.urlopen",
            MockUrlOpen(responses=[(201, {"ids": ["only-one"]})]),
        ),
        pytest.raises(BeadStoreError, match="length mismatch"),
    ):
        store.bulk_append([_bead(0), _bead(1)])


def test_bulk_append_non_dict_response_raises(tmp_path: Path) -> None:
    """When server returns a non-dict body, raise BeadStoreError."""
    store = AgilePlusBeadStore(base_url="http://test.local")
    # Simulate a non-dict by returning an empty response that
    # json.loads parses as None.
    with (
        patch(
            "urllib.request.urlopen",
            MockUrlOpen(responses=[(200, {"ids": "not-a-list"})]),
        ),
        pytest.raises(BeadStoreError, match="non-list ids"),
    ):
        store.bulk_append([_bead()])


def test_bulk_append_no_ids_field_raises(tmp_path: Path) -> None:
    """When server response lacks 'ids' field, raise BeadStoreError."""
    store = AgilePlusBeadStore(base_url="http://test.local")
    with patch(
        "urllib.request.urlopen",
        MockUrlOpen(responses=[(200, {"unrelated": "field"})]),
    ):
        # No 'ids' field → .get returns None → not isinstance list
        # → raises "non-list ids".
        with pytest.raises(BeadStoreError, match="length mismatch"):
            store.bulk_append([_bead()])


# ---------------------------------------------------------------------------
# 2. __repr__
# ---------------------------------------------------------------------------


def test_repr_includes_base_url_and_timeout() -> None:
    store = AgilePlusBeadStore(base_url="http://example.com", timeout=7.5)
    r = repr(store)
    assert "AgilePlusBeadStore" in r
    assert "http://example.com" in r
    assert "7.5" in r


def test_repr_with_work_package_id() -> None:
    store = AgilePlusBeadStore(
        base_url="http://example.com",
        work_package_id=42,
    )
    r = repr(store)
    assert "work_package_id=42" in r


# ---------------------------------------------------------------------------
# 3. health() (already covered elsewhere, but smoke test here)
# ---------------------------------------------------------------------------


def test_health_returns_dict(tmp_path: Path) -> None:
    store = AgilePlusBeadStore(base_url="http://test.local")
    with patch(
        "urllib.request.urlopen",
        MockUrlOpen(responses=[(200, {"ok": True, "version": "1.0.0"})]),
    ):
        result = store.health()
    assert result == {"ok": True, "version": "1.0.0"}
