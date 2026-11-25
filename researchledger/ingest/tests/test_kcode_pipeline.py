"""kcode pipeline characterization.

kcode is the KooshaPari fork of jcode. Schema mirrors jcode 1:1 with
fork_depth/fork_max_depth extras. tool_use_names is a CSV TEXT column;
content_json is a JSON ARRAY.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))


@pytest.fixture
def kcode_migrator():
    return importlib.import_module("kcode_migrate_to_research")


@pytest.fixture
def kcode_sessions_dir(tmp_path: Path) -> Path:
    """Synthetic ~/.kcode/sessions dir with one session + one tool_use."""
    sdir = tmp_path / "sessions"
    sdir.mkdir()
    payload = {
        "id": "ksess-uuid-1",
        "title": "kcode test",
        "parent_id": None,
        "provider_key": "opencode-go",
        "provider_session_id": None,
        "model": "mimo-v2.6-flash",
        "reasoning_effort": "low",
        "subagent_model": None,
        "is_canary": False,
        "is_debug": False,
        "working_dir": "/tmp",
        "status": "Active",
        "created_at": "2026-10-10T12:00:00Z",
        "updated_at": "2026-10-10T12:01:00Z",
        "last_active_at": "2026-10-10T12:01:00Z",
        "saved": False,
        "save_label": None,
        "fork_depth": 0,
        "fork_max_depth": 3,
        "messages": [
            {
                "id": "kmsg-uuid-1",
                "role": "assistant",
                "timestamp": "2026-10-10T12:00:30Z",
                "content": [
                    {"type": "text", "text": "Run something."},
                    {"type": "tool_use", "name": "bash",
                     "input": {"command": "ls /tmp"}},
                ],
                "token_usage": {"input_tokens": 10, "output_tokens": 5,
                                "cache_read_input_tokens": 0},
            },
        ],
    }
    (sdir / "session_ksess-uuid-1.json").write_text(json.dumps(payload))
    return sdir


def test_migrator_writes_kcode_sessions_and_messages(
    tmp_path, kcode_sessions_dir, research_db, kcode_migrator, monkeypatch
):
    """Phase A: 1 session + 1 message + 1 tool_use row written.

    kcode main() takes no argv; reads sys.argv directly.
    """
    monkeypatch.setattr(sys, "argv", [
        "kcode_migrate_to_research.py",
        "--db", str(research_db),
        "--sessions-dir", str(kcode_sessions_dir),
        "--since", "2026-10-01T00:00:00Z",
    ])
    rc = kcode_migrator.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        n_sess = conn.execute(
            "SELECT COUNT(*) FROM migrated_kcode_sessions"
        ).fetchone()[0]
        n_msg = conn.execute(
            "SELECT COUNT(*) FROM migrated_kcode_messages"
        ).fetchone()[0]
        assert n_sess == 1 and n_msg == 1

        # tool_use_names is a CSV string (not JSON)
        csv = conn.execute(
            "SELECT tool_use_names FROM migrated_kcode_messages"
        ).fetchone()[0]
        assert csv == "bash"

        # content_json MUST be valid JSON AND parse as an ARRAY.
        # This is the exact regression class that caused 195,878-row corruption.
        row = conn.execute(
            "SELECT content_json FROM migrated_kcode_messages"
        ).fetchone()[0]
        bad = conn.execute(
            "SELECT COUNT(*) FROM migrated_kcode_messages "
            "WHERE content_json IS NOT NULL "
            "AND (json_valid(content_json) = 0 "
            "OR json_type(content_json) != 'array')"
        ).fetchone()[0]
        assert bad == 0, "content_json must be valid JSON ARRAY"

        # And it expands via json_each (the canonical consumer pattern).
        n_expanded = conn.execute("""
            SELECT COUNT(*) FROM migrated_kcode_messages, json_each(content_json)
        """).fetchone()[0]
        assert n_expanded >= 1

        parsed = json.loads(row)
        assert isinstance(parsed, list) and len(parsed) >= 1

        # Sources row registered.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='kcode'"
        ).fetchone()
        assert kind is not None and kind[0] == "kcode"

        # fork_depth is preserved (kcode-specific column).
        fd = conn.execute(
            "SELECT fork_depth, fork_max_depth FROM migrated_kcode_sessions"
        ).fetchone()
        assert fd == (0, 3)
    finally:
        conn.close()