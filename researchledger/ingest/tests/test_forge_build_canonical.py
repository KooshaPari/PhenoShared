"""forge_build_canonical characterization.

Pins down the forge canonical items builder. Reads migrated_forge_prompts
and writes items with item_kind='forge_prompt', author='koosha',
redaction_state='partial', and a specific title shape.

We seed a synthetic migrated_forge_prompts row plus a sources row with
kind='forge' (the builder requires it). Then we run main() and assert the
items table output contract.
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
def forge_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("forge_build_canonical")
    return mod


def _seed_forge_db(p: Path) -> None:
    from research_ledger_init.sources_harness import forge_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in forge_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (10, 'forge', '/fake/forge', '2026-09-01T00:00:00Z')
        """)
        conn.execute("""
            INSERT INTO migrated_forge_prompts (
                id, external_id, forge_prompt_id, conversation_id,
                workspace_id, message_index, source_tool, source,
                content_hash, title, created_at, extracted_at,
                content_text, content_length, content_json, metadata_json
            ) VALUES (
                1, 'forge_prompt:abc-123', 'abc-123', 'conv-1',
                'ws-1', 0, 'codex', 'database',
                'deadbeef', 'My Conversation Title',
                '2026-09-15 12:34:56.789', '2026-09-15T19:34:56.789Z',
                'Hello world from forge prompt', 26, '{}', '{}'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_forge_builds_prompt_item_with_correct_contract(
    research_db, monkeypatch, forge_builder
):
    """One migrated row → one item with the pinned title and attrs JSON."""
    _seed_forge_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "forge_build_canonical.py", "--db", str(research_db),
    ])
    rc = forge_builder.main()
    assert rc == 0

    conn = sqlite3.connect(research_db)
    try:
        row = conn.execute("""
            SELECT external_id, item_kind, author, redaction_state,
                   title, body, attrs_json
            FROM items
        """).fetchone()
        assert row is not None
        ext, kind, author, redact, title, body, attrs_json = row
        # external_id is the same as the migrated external_id.
        assert ext == "forge_prompt:abc-123"
        assert kind == "forge_prompt"
        assert author == "koosha"
        assert redact == "partial"
        # Title shape: forge/<title[:40]>/<first_line[:60]>/<date[:10]>
        assert title == "forge/My Conversation Title/Hello world from forge prompt/2026-09-15"
        assert body == "Hello world from forge prompt"
        # attrs_json is a real JSON object (not a quoted string) and has
        # the expected keys. This is the exact bug class we want to pin:
        # the column must be parseable, and json_extract must work on it.
        parsed = json.loads(attrs_json)
        assert parsed["source_tool"] == "codex"
        assert parsed["source"] == "database"
        assert parsed["conversation_id"] == "conv-1"
        assert parsed["workspace_id"] == "ws-1"
        assert parsed["message_index"] == 0
        assert parsed["content_hash"] == "deadbeef"
        assert parsed["content_length"] == 26
        # Cross-row tool breakdown (1 row total in this fixture).
        by_tool = conn.execute("""
            SELECT json_extract(attrs_json, '$.source_tool'), COUNT(*)
            FROM items GROUP BY 1
        """).fetchall()
        assert by_tool == [("codex", 1)]
    finally:
        conn.close()


def test_forge_builder_is_idempotent(research_db, monkeypatch, forge_builder):
    """Run twice → still exactly 1 row in items (UNIQUE external_id)."""
    _seed_forge_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "forge_build_canonical.py", "--db", str(research_db),
    ])
    forge_builder.main()
    # Run a second time.
    forge_builder.main()
    conn = sqlite3.connect(research_db)
    try:
        n = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        assert n == 1
    finally:
        conn.close()


def test_forge_builder_falls_back_to_short_title_when_first_line_blank(
    research_db, monkeypatch, forge_builder
):
    """Empty content_text + a title → title_str drops the first_line segment.

    When only the title is present, the shape is forge/<title[:80]>/<date>.
    """
    from research_ledger_init.sources_harness import forge_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(research_db)
    conn = sqlite3.connect(research_db)
    try:
        for stmt in forge_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (11, 'forge', '/x', '2026-09-01T00:00:00Z')
        """)
        conn.execute("""
            INSERT INTO migrated_forge_prompts (
                id, external_id, forge_prompt_id, conversation_id,
                workspace_id, message_index, source_tool, source,
                content_hash, title, created_at, extracted_at,
                content_text, content_length, content_json, metadata_json
            ) VALUES (
                2, 'forge_prompt:no-body', 'no-body', 'conv-2',
                'ws-2', 0, 'claude', 'database',
                'cafebabe', 'Just A Title',
                '2026-09-15 12:34:56.789', '2026-09-15T19:34:56.789Z',
                '', 0, '{}', '{}'
            )
        """)
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(sys, "argv", [
        "forge_build_canonical.py", "--db", str(research_db),
    ])
    forge_builder.main()
    conn = sqlite3.connect(research_db)
    try:
        title = conn.execute(
            "SELECT title FROM items WHERE external_id='forge_prompt:no-body'"
        ).fetchone()[0]
        # content_text empty → no first_line segment.
        assert title == "forge/Just A Title/2026-09-15"
    finally:
        conn.close()