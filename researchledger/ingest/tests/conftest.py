"""Characterization fixtures for the migration scripts.

These tests are READ-ONLY on production data: every fixture points at
tmp_path and the production research_ledger.sqlite / session_ledger.sqlite
are never opened.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))

from research_ledger_init import init as init_research_ledger  # noqa: E402


@pytest.fixture
def research_db(tmp_path: Path) -> Path:
    """Fresh research_ledger.sqlite initialised in tmp_path (never the real one)."""
    db = tmp_path / "research_ledger.sqlite"
    init_research_ledger(db)
    return db


@pytest.fixture
def session_ledger_with_chatgpt(tmp_path: Path) -> Path:
    """Synthetic session_ledger.sqlite with a handful of chatgpt rows.

    Mirrors the production session_ledger schema used by
    chatgpt_migrate_to_research.py (see its migrate_* functions).
    """
    db = tmp_path / "session_ledger.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE openai_chatgpt_conversations (
            uuid TEXT, name TEXT, summary TEXT, created_at TEXT,
            updated_at TEXT, account_uuid TEXT, n_messages INTEGER,
            source_path TEXT, ingested_at TEXT
        );
        CREATE TABLE openai_chatgpt_messages (
            uuid TEXT, conversation_uuid TEXT, sender TEXT, text TEXT,
            content_json TEXT, created_at TEXT, updated_at TEXT,
            parent_message_uuid TEXT, ingested_at TEXT
        );
        CREATE TABLE openai_chatgpt_files (
            msg_uuid TEXT, conversation_uuid TEXT, file_uuid TEXT,
            file_name TEXT, source_path TEXT, ingested_at TEXT
        );
        CREATE TABLE openai_chatgpt_attachment_content (
            msg_uuid TEXT, conversation_uuid TEXT, file_name TEXT,
            file_size INTEGER, file_type TEXT, extracted_content TEXT,
            content_len INTEGER, source_path TEXT, ingested_at TEXT
        );
        CREATE TABLE openai_chatgpt_tool_results (
            msg_uuid TEXT, conversation_uuid TEXT, block_index INTEGER,
            name TEXT, tool_use_id TEXT, is_error INTEGER,
            content_json TEXT, content_len INTEGER, source_path TEXT
        );
    """)
    # One conversation with one message and one tool_result + one file row
    # + one attachment_content row so every migrated_* table gets >=1 row.
    conn.execute(
        "INSERT INTO openai_chatgpt_conversations VALUES (?,?,?,?,?,?,?,?,?)",
        ("conv-uuid-1", "Test conv", "A summary",
         "2026-09-01T10:00:00Z", "2026-09-01T10:05:00Z",
         "acct-uuid", 1, "/raw/conv-1.json", "2026-10-01T00:00:00Z"),
    )
    content_json = json.dumps([{"type": "text", "text": "hello world"}])
    conn.execute(
        "INSERT INTO openai_chatgpt_messages VALUES (?,?,?,?,?,?,?,?,?)",
        ("msg-uuid-1", "conv-uuid-1", "user", "hello world",
         content_json, "2026-09-01T10:00:00Z",
         "2026-09-01T10:00:00Z", None, "2026-10-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO openai_chatgpt_files VALUES (?,?,?,?,?,?)",
        ("msg-uuid-1", "conv-uuid-1", "file-uuid-1",
         "test.txt", "/raw/test.txt", "2026-10-01T00:00:00Z"),
    )
    extracted = "file content here"
    conn.execute(
        "INSERT INTO openai_chatgpt_attachment_content VALUES (?,?,?,?,?,?,?,?,?)",
        ("msg-uuid-1", "conv-uuid-1", "test.txt", 17, "text/plain",
         extracted, len(extracted), "/raw/test.txt",
         "2026-10-01T00:00:00Z"),
    )
    tr_json = json.dumps({"result": "ok"})
    conn.execute(
        "INSERT INTO openai_chatgpt_tool_results VALUES (?,?,?,?,?,?,?,?,?)",
        ("msg-uuid-1", "conv-uuid-1", 0, "bash", "tool-call-id-1", 0,
         tr_json, len(tr_json), "/raw/conv-1.json"),
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def jcode_sessions_dir(tmp_path: Path) -> Path:
    """Synthetic ~/.jcode/sessions dir with one .json file containing one tool_use."""
    sdir = tmp_path / "sessions"
    sdir.mkdir()
    payload = {
        "id": "sess-uuid-1",
        "short_name": "test",
        "title": "T",
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
        "created_at": "2026-09-15T12:00:00Z",
        "updated_at": "2026-09-15T12:01:00Z",
        "last_active_at": "2026-09-15T12:01:00Z",
        "saved": False,
        "save_label": None,
        "messages": [
            {
                "id": "msg-uuid-1",
                "role": "assistant",
                "timestamp": "2026-09-15T12:00:30Z",
                "content": [
                    {"type": "text", "text": "Let me run something."},
                    {"type": "tool_use", "name": "bash", "input": {"command": "ls /tmp"}},
                ],
                "token_usage": {"input_tokens": 10, "output_tokens": 5,
                                "cache_read_input_tokens": 0},
            },
        ],
    }
    (sdir / "session_sess-uuid-1.json").write_text(json.dumps(payload))
    return sdir


def is_json_array(conn: sqlite3.Connection, col_expr: str) -> bool:
    """True iff every non-null value of `col_expr` is a JSON array.

    This is the exact regression we were burned by: the migrator wrote
    'bash,bash,read' (a string) where the consumer expected ["bash","read"].
    """
    rows = conn.execute(
        f"SELECT {col_expr} FROM items WHERE {col_expr} IS NOT NULL"
    ).fetchall()
    if not rows:
        return True
    bad = conn.execute(
        f"SELECT COUNT(*) FROM items WHERE {col_expr} IS NOT NULL "
        f"AND (json_valid({col_expr}) = 0 OR json_type({col_expr}) != 'ARRAY')"
    ).fetchone()[0]
    return bad == 0