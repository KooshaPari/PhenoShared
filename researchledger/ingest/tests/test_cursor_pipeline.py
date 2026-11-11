"""cursor pipeline characterization.

cursor (Cursor IDE) reads from ~/.cursor/chats/<hash>/<chat-uuid>/ dirs,
each with meta.json + a store.db that has a `blobs` table. Writes to
migrated_cursor_chats + migrated_cursor_messages. tool_call_names is CSV;
content_json and meta_json are JSON.

Also exercises cursor_build_canonical.py's --limit row cap.
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
def cursor_migrator():
    return importlib.import_module("cursor_migrate_to_research")


@pytest.fixture
def cursor_builder():
    return importlib.import_module("cursor_build_canonical")


@pytest.fixture
def cursor_chats_root(tmp_path: Path) -> Path:
    """Synthetic ~/.cursor/chats/<hash>/<chat-uuid>/{meta.json,store.db}.

    One chat with 3 blobs (system, user, assistant+tool_call).
    """
    root = tmp_path / "chats"
    chat_dir = root / "abc12" / "chat-uuid-1"
    chat_dir.mkdir(parents=True)
    # createdAtMs is 2026-09-15 (unixepoch ms)
    meta = {
        "schemaVersion": 1,
        "createdAtMs": 1_728_000_000_000,  # 2024-09-14T22:40:00Z (irrelevant but stable)
        "updatedAtMs": 1_728_000_060_000,
        "hasConversation": True,
        "isSubagent": False,
        "cwd": "/Users/test/proj",
    }
    (chat_dir / "meta.json").write_text(json.dumps(meta))
    store = chat_dir / "store.db"
    conn = sqlite3.connect(store)
    conn.execute("CREATE TABLE blobs (id TEXT PRIMARY KEY, data BLOB)")
    conn.execute(
        "INSERT INTO blobs VALUES (?, ?)",
        ("blob-sys", json.dumps({
            "role": "system",
            "content": "You are GPT5 Luna",
        }).encode()),
    )
    conn.execute(
        "INSERT INTO blobs VALUES (?, ?)",
        ("blob-user", json.dumps({"role": "user", "content": "hi"}).encode()),
    )
    conn.execute(
        "INSERT INTO blobs VALUES (?, ?)",
        ("blob-ast", json.dumps({
            "role": "assistant",
            "content": "running ls",
            "tool_calls": [{"function": {"name": "bash"}}],
        }).encode()),
    )
    conn.commit()
    conn.close()
    return root


def test_migrator_writes_cursor_chats_and_messages(
    tmp_path, cursor_chats_root, research_db, cursor_migrator,
    cursor_builder,
):
    """Phase A: cursor migrator populates both migrated_cursor_* tables.

    cursor main() accepts argv as a list. After migration the build_canonical
    step (which has --limit) must convert tool_call_names CSV into a JSON
    ARRAY in attrs_json.
    """
    rc = cursor_migrator.main([
        "--db", str(research_db),
        "--src", str(cursor_chats_root),
    ])
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        n_chats = conn.execute(
            "SELECT COUNT(*) FROM migrated_cursor_chats"
        ).fetchone()[0]
        n_msgs = conn.execute(
            "SELECT COUNT(*) FROM migrated_cursor_messages"
        ).fetchone()[0]
        assert n_chats == 1
        assert n_msgs == 3

        # tool_call_names is CSV TEXT (only on the assistant row).
        csv = conn.execute(
            "SELECT tool_call_names FROM migrated_cursor_messages "
            "WHERE role='assistant'"
        ).fetchone()[0]
        assert csv == "bash"

        # content_json MUST be valid JSON for every row (it's the blob dict).
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_cursor_messages
            WHERE content_json IS NOT NULL
              AND (json_valid(content_json) = 0
                   OR json_type(content_json) != 'object')
        """).fetchone()[0]
        assert bad == 0, "content_json must be valid JSON OBJECT"

        # meta_json MUST be valid JSON (it's the meta.json dict).
        bad_meta = conn.execute("""
            SELECT COUNT(*) FROM migrated_cursor_chats
            WHERE meta_json IS NOT NULL
              AND (json_valid(meta_json) = 0
                   OR json_type(meta_json) != 'object')
        """).fetchone()[0]
        assert bad_meta == 0

        # model is extracted from the first system blob. QUIRK: extract_model
        # uses regex `You are (...) (?:\.|\n|\r|$)`, so any "." inside the
        # model name (e.g. "GPT-5.6") truncates the capture. Avoid periods
        # inside the model name or pin a different expected value.
        model = conn.execute(
            "SELECT model FROM migrated_cursor_chats"
        ).fetchone()[0]
        assert model == "GPT5 Luna"

        # Sources row registered with kind=cursor.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='cursor'"
        ).fetchone()
        assert kind is not None and kind[0] == "cursor"
    finally:
        conn.close()


def test_cursor_builder_limit_cap_pins_observed_behaviour(
    tmp_path, cursor_chats_root, research_db,
    cursor_migrator, cursor_builder, monkeypatch,
):
    """cursor_build_canonical.py exposes --limit N pending-message cap.

    With 3 messages and --limit 2, exactly 2 cursor_message items land;
    a 2nd run with no cap finishes the remaining 1; chat_summary rows
    are unaffected by --limit (they always run).
    """
    # Migrate first.
    cursor_migrator.main([
        "--db", str(research_db),
        "--src", str(cursor_chats_root),
    ])
    # First build with --limit 2. cursor_build_canonical.main() takes no argv;
    # reads sys.argv directly (mirror the pattern in test_jcode_pipeline.py).
    monkeypatch.setattr(sys, "argv", [
        "cursor_build_canonical.py",
        "--db", str(research_db),
        "--limit", "2",
    ])
    rc = cursor_builder.main()
    assert rc in (None, 0)
    conn = sqlite3.connect(research_db)
    try:
        n_after_first = conn.execute(
            "SELECT COUNT(*) FROM items WHERE item_kind='cursor_message'"
        ).fetchone()[0]
        # Exactly 2 cursor_message items landed; chat summary still runs.
        assert n_after_first == 2, f"expected 2, got {n_after_first}"

        # Re-run with --limit 2 — already pending count is 1; limit still caps.
        monkeypatch.setattr(sys, "argv", [
            "cursor_build_canonical.py",
            "--db", str(research_db),
            "--limit", "2",
        ])
        cursor_builder.main()
        n_after_second = conn.execute(
            "SELECT COUNT(*) FROM items WHERE item_kind='cursor_message'"
        ).fetchone()[0]
        assert n_after_second == 3, (
            f"expected 3 after 2nd bounded run, got {n_after_second}"
        )

        # THE REGRESSION GUARD (cursor-specific): tool_call_names in
        # attrs_json MUST be a JSON ARRAY, not a CSV string. This is the
        # exact defect class that caused 195,878-row corruption.
        bad = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE item_kind='cursor_message'
              AND attrs_json IS NOT NULL
              AND (json_valid(attrs_json) = 0
                   OR json_type(json_extract(attrs_json, '$.tool_call_names'))
                      != 'array')
        """).fetchone()[0]
        assert bad == 0, "tool_call_names must be a JSON ARRAY"

        # And it expands via json_each (canonical consumer pattern).
        n_expanded = conn.execute("""
            SELECT COUNT(*) FROM items, json_each(
                json_extract(attrs_json, '$.tool_call_names'))
            WHERE item_kind='cursor_message'
        """).fetchone()[0]
        assert n_expanded >= 1

        # cursor_chat summary item exists (always inserted, --limit ignored).
        n_summary = conn.execute(
            "SELECT COUNT(*) FROM items WHERE item_kind='cursor_chat'"
        ).fetchone()[0]
        assert n_summary == 1
    finally:
        conn.close()