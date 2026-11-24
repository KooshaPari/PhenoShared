"""Coverage tests for pheno.serve.events.

EventLog is an append-only JSONL writer with two responsibilities:
1. Make parent directories on demand (operators point events_path at a fresh tree).
2. Prefix every row with ``timestamp_utc`` so downstream consumers can trust
   the wall-clock stamp without parsing the body.

These tests pin those contracts. No subprocess, no network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pheno.serve.events import EventLog


class TestInit:
    """EventLog.__init__ stores the path verbatim."""

    def test_stores_absolute_path(self, tmp_path: Path) -> None:
        log = EventLog(tmp_path / "events.jsonl")
        assert log.path == tmp_path / "events.jsonl"

    def test_stores_relative_path(self) -> None:
        log = EventLog(Path("logs/events.jsonl"))
        assert log.path == Path("logs/events.jsonl")

    def test_path_is_public_attribute(self, tmp_path: Path) -> None:
        log = EventLog(tmp_path / "events.jsonl")
        assert hasattr(log, "path")
        assert isinstance(log.path, Path)


class TestAppendBasic:
    """EventLog.append writes a JSON line per call."""

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nest" / "events.jsonl"
        EventLog(nested).append({"request_id": "r1"})
        assert nested.parent.is_dir()
        assert nested.exists()

    def test_writes_single_line(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"request_id": "r1"})
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1

    def test_writes_multiple_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        log = EventLog(path)
        for i in range(5):
            log.append({"request_id": f"r{i}"})
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines() if line
        ]
        assert len(lines) == 5

    def test_appends_does_not_truncate(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        log = EventLog(path)
        log.append({"request_id": "r1"})
        first_size = path.stat().st_size
        log.append({"request_id": "r2"})
        assert path.stat().st_size > first_size


class TestAppendSchema:
    """Each row is JSON-parseable and includes timestamp_utc."""

    def test_row_is_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"request_id": "r1"})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert isinstance(row, dict)

    def test_row_has_timestamp_utc_prefix(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"request_id": "r1"})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert "timestamp_utc" in row

    def test_timestamp_utc_is_iso8601(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"request_id": "r1"})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        ts = row["timestamp_utc"]
        # Must round-trip through fromisoformat.
        parsed = datetime.fromisoformat(ts)
        assert isinstance(parsed, datetime)

    def test_timestamp_utc_is_utc_timezone(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"request_id": "r1"})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        parsed = datetime.fromisoformat(row["timestamp_utc"])
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == UTC.utcoffset(None)

    def test_preserves_event_payload(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append(
            {"request_id": "r1", "status": 200, "engine": "vllm"}
        )
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert row["request_id"] == "r1"
        assert row["status"] == 200
        assert row["engine"] == "vllm"

    def test_payload_keys_sorted(self, tmp_path: Path) -> None:
        """The implementation calls json.dumps(sort_keys=True). Lock that.

        With sort_keys=True, ``"a"`` < ``"b"`` < ``"c"`` < ``"timestamp_utc"``
        (alphabetical by character), so on disk the order is always
        ``a, b, c, timestamp_utc`` regardless of insertion order.
        """
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"b": 1, "a": 2, "c": 3})
        text = path.read_text(encoding="utf-8").strip()
        a_idx = text.index('"a"')
        b_idx = text.index('"b"')
        c_idx = text.index('"c"')
        ts_idx = text.index('"timestamp_utc"')
        # Alphabetical: a < b < c < t (timestamp_utc starts with 't').
        assert a_idx < b_idx < c_idx < ts_idx

    def test_caller_supplied_timestamp_utc_overrides_auto(self, tmp_path: Path) -> None:
        """Lock the current contract: caller-supplied ``timestamp_utc`` wins
        over the auto-injected value via dict-spread ``**event``. This is a
        surprising behavior surface; pin it so any future fix is detected.
        """
        path = tmp_path / "events.jsonl"
        EventLog(path).append(
            {"request_id": "r1", "timestamp_utc": "1970-01-01T00:00:00+00:00"}
        )
        text = path.read_text(encoding="utf-8").strip()
        assert "1970-01-01T00:00:00+00:00" in text
        assert text.count('"timestamp_utc"') == 1


class TestAppendAppendsSequentially:
    """Multiple appends produce independent rows that share the timestamp key."""

    def test_each_row_has_its_own_timestamp(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        log = EventLog(path)
        log.append({"request_id": "r1"})
        log.append({"request_id": "r2"})
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(rows) == 2
        assert rows[0]["request_id"] == "r1"
        assert rows[1]["request_id"] == "r2"
        assert "timestamp_utc" in rows[0]
        assert "timestamp_utc" in rows[1]

    def test_empty_event_dict_is_allowed(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert row == {"timestamp_utc": row["timestamp_utc"]}

    def test_unicode_payload_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"msg": "\u00e9l\u00e8ve \u4e2d\u6587"})
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert row["msg"] == "\u00e9l\u00e8ve \u4e2d\u6587"


class TestAppendEncoding:
    """The log is opened in text mode with utf-8 encoding."""

    def test_file_handle_uses_utf8(self, tmp_path: Path) -> None:
        """Verify the on-disk file is valid UTF-8 (json.dumps default)."""
        path = tmp_path / "events.jsonl"
        EventLog(path).append({"key": "value"})
        raw = path.read_bytes()
        # Decode cleanly as UTF-8.
        raw.decode("utf-8")
        # And ensure the file is opened in text mode (newlines translated).
        assert raw.endswith(b"\n")


@pytest.mark.parametrize("event_count", [1, 5, 50])
def test_appends_scale(tmp_path: Path, event_count: int) -> None:
    """EventLog.append must scale linearly and stay valid JSONL."""
    path = tmp_path / "events.jsonl"
    log = EventLog(path)
    for i in range(event_count):
        log.append({"i": i, "request_id": f"r{i}"})
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(rows) == event_count
    assert rows[0]["i"] == 0
    assert rows[-1]["i"] == event_count - 1


@pytest.mark.parametrize(
    "nested_path",
    [
        "a/events.jsonl",
        "a/b/events.jsonl",
        "x/y/z/events.jsonl",
    ],
)
def test_creates_arbitrary_nested_dirs(tmp_path: Path, nested_path: str) -> None:
    """Parent directories are created recursively (parents=True)."""
    target = tmp_path / nested_path
    EventLog(target).append({"ok": True})
    assert target.exists()
    assert target.parent.is_dir()
    # And all intermediate parents must exist too.
    for ancestor in target.parents:
        if ancestor == tmp_path:
            break
        assert ancestor.is_dir()