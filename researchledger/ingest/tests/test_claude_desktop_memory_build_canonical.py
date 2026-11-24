"""claude_desktop_memory_build_canonical characterization.

Pins down the claude_desktop memory notes canonical items builder. Reads
migrated_claude_desktop_memory_notes and emits one item per row:

  item_kind:   claude_desktop_memory_note
  author:      'claude_code_cli'  (pinned)
  redaction:   'none'
  title:       first_heading (or filename as fallback)
  body:        first 60K chars of content_text
  attrs_json:  filename, project_path, file_path, line_count, byte_size,
               first_heading, frontmatter

We seed 2 memory notes with different frontmatter shapes (valid JSON
and malformed JSON) and assert the output contract.
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
def memory_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("claude_desktop_memory_build_canonical")
    return mod


def _seed_memory_db(p: Path) -> None:
    from research_ledger_init.sources_misc import claude_desktop_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in claude_desktop_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (60, 'claude_desktop', '/fake/.claude',
                    '2026-09-01T00:00:00Z')
        """)
        # Note 1: valid frontmatter, first_heading set.
        conn.execute("""
            INSERT INTO migrated_claude_desktop_memory_notes (
                id, external_id, filename, project_path, file_path,
                byte_size, line_count, frontmatter_json, first_heading,
                content_text, modified_at_ms, captured_at
            ) VALUES (
                1, 'claude_desktop_mem:proj-1:note-a',
                'note-a.md', '/proj-1', '/proj-1/memory/note-a.md',
                1234, 42,
                '{"name":"agent","model":"claude-3-5-sonnet","tags":["x"]}',
                'Initial agent design notes',
                'A long body of memory note text. Mentions koalas.',
                1700000000000, '2026-09-01T00:00:00Z'
            )
        """)
        # Note 2: malformed frontmatter, no first_heading.
        conn.execute("""
            INSERT INTO migrated_claude_desktop_memory_notes (
                id, external_id, filename, project_path, file_path,
                byte_size, line_count, frontmatter_json, first_heading,
                content_text, modified_at_ms, captured_at
            ) VALUES (
                2, 'claude_desktop_mem:proj-2:note-b',
                'note-b.md', '/proj-2', '/proj-2/memory/note-b.md',
                567, 18,
                '{not valid json',
                NULL,
                'Another memory note body.',
                1700001000000, '2026-09-02T00:00:00Z'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_memory_builder_emits_one_item_per_note_with_pinned_contract(
    research_db, monkeypatch, memory_builder
):
    _seed_memory_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "claude_desktop_memory_build_canonical.py", "--db", str(research_db),
    ])
    memory_builder.main()  # no return value

    conn = sqlite3.connect(research_db)
    try:
        n_items = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 60 AND item_kind = 'claude_desktop_memory_note'
        """).fetchone()[0]
        assert n_items == 2

        # Note 1: title=first_heading, body=content_text, attrs contains
        # parsed frontmatter.
        n1 = conn.execute("""
            SELECT title, body, author, attrs_json, raw_json_path
            FROM items
            WHERE source_id = 60
              AND external_id = 'claude_desktop_mem:proj-1:note-a'
        """).fetchone()
        n1_title, n1_body, n1_author, n1_attrs, n1_raw = n1
        assert n1_title == "Initial agent design notes"
        assert n1_body == "A long body of memory note text. Mentions koalas."
        assert n1_author == "claude_code_cli"
        assert n1_raw == "/proj-1/memory/note-a.md"
        n1_parsed = json.loads(n1_attrs)
        assert n1_parsed["filename"] == "note-a.md"
        assert n1_parsed["project_path"] == "/proj-1"
        assert n1_parsed["file_path"] == "/proj-1/memory/note-a.md"
        assert n1_parsed["line_count"] == 42
        assert n1_parsed["byte_size"] == 1234
        assert n1_parsed["first_heading"] == "Initial agent design notes"
        assert n1_parsed["frontmatter"] == {
            "name": "agent", "model": "claude-3-5-sonnet", "tags": ["x"]
        }

        # Note 2: title=filename (fallback), frontmatter is {} (malformed JSON
        # is swallowed, not raised).
        n2 = conn.execute("""
            SELECT title, body, attrs_json
            FROM items
            WHERE source_id = 60
              AND external_id = 'claude_desktop_mem:proj-2:note-b'
        """).fetchone()
        n2_title, n2_body, n2_attrs = n2
        assert n2_title == "note-b.md"
        assert n2_body == "Another memory note body."
        n2_parsed = json.loads(n2_attrs)
        assert n2_parsed["filename"] == "note-b.md"
        assert n2_parsed["first_heading"] is None
        assert n2_parsed["frontmatter"] == {}  # malformed → empty dict

        # Both items have captured_at and redaction_state='none'.
        n_missing_redaction = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 60
              AND item_kind = 'claude_desktop_memory_note'
              AND redaction_state != 'none'
        """).fetchone()[0]
        assert n_missing_redaction == 0

        n_null_captured = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 60
              AND item_kind = 'claude_desktop_memory_note'
              AND captured_at IS NULL
        """).fetchone()[0]
        assert n_null_captured == 0

        # FTS5 sanity: 'koalas' should be searchable.
        n_fts = conn.execute("""
            SELECT COUNT(*) FROM items_fts
            WHERE items_fts MATCH 'koalas'
        """).fetchone()[0]
        assert n_fts >= 1
    finally:
        conn.close()


def test_memory_builder_is_idempotent(research_db, monkeypatch, memory_builder):
    """Re-running inserts nothing (existing external_id skip)."""
    _seed_memory_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "claude_desktop_memory_build_canonical.py", "--db", str(research_db),
    ])
    memory_builder.main()
    memory_builder.main()  # second run
    conn = sqlite3.connect(research_db)
    try:
        n = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 60
              AND item_kind = 'claude_desktop_memory_note'
        """).fetchone()[0]
        assert n == 2
    finally:
        conn.close()