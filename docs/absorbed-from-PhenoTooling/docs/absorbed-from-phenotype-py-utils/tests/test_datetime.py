"""Tests for :mod:`phenotype_py_utils.datetime`."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from phenotype_py_utils.datetime import from_unix, iso_now

ISO_8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def test_iso_now_is_parseable() -> None:
    s = iso_now()
    assert ISO_8601_RE.match(s), f"unexpected iso format: {s!r}"
    # Round-trip: parse the Z-suffix as UTC
    parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_iso_now_ends_with_z() -> None:
    assert iso_now().endswith("Z")


def test_from_unix_round_trip() -> None:
    ts = 1_700_000_000.0  # 2023-11-14T22:13:20Z
    s = from_unix(ts)
    assert ISO_8601_RE.match(s)
    # The second-precision output should match exactly
    assert s.startswith("2023-11-14T22:13:20Z")


def test_from_unix_ends_with_z() -> None:
    assert from_unix(0.0).endswith("Z")


def test_iso_now_close_to_now() -> None:
    before = time.time()
    s = iso_now()
    after = time.time()
    parsed = datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    assert before - 1 <= parsed <= after + 1
