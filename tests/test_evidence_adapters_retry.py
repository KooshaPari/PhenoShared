"""Tests for evidence adapter retry (exp backoff 1s×2, max 3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from pheno.evidence.adapters.base import (
    is_retryable_status,
    with_retry,
)


def _http_error(status: int) -> requests.HTTPError:
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {}
    err = requests.HTTPError(f"{status} error", response=resp)
    return err


def test_retry_on_429() -> None:
    calls: list[int] = []

    @with_retry(sleep=lambda _: None)  # type: ignore[arg-type]
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise _http_error(429)
        return "ok"

    # patch sleep inside decorator is via injected lambda, so no need to patch time.sleep
    assert flaky() == "ok"
    assert len(calls) == 3


def test_retry_on_5xx() -> None:
    calls: list[int] = []

    @with_retry(sleep=lambda _: None)  # type: ignore[arg-type]
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise _http_error(503)
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 2
    # also verify is_retryable
    assert is_retryable_status(500) is True
    assert is_retryable_status(502) is True
    assert is_retryable_status(503) is True


def test_no_retry_on_4xx() -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    def fake_sleep(s: float) -> None:
        sleeps.append(s)

    @with_retry(sleep=fake_sleep)  # type: ignore[arg-type]
    def flaky() -> str:
        calls.append(1)
        raise _http_error(400)

    with pytest.raises(requests.HTTPError):
        flaky()
    # 4xx (except 429) should not retry; one call only, no sleep
    assert len(calls) == 1
    assert sleeps == []
    assert is_retryable_status(400) is False
    assert is_retryable_status(404) is False
