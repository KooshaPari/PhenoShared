"""claude_desktop_build_canonical characterization.

Pins down the claude_desktop canonical items builder. Reads
migrated_claude_desktop_messages (full convo pairs: user/assistant/summary)
and migrated_claude_desktop_history (12,958 user commands from
~/.claude/history.jsonl), then emits 4 item_kinds:

  claude_desktop_user_message
  claude_desktop_assistant_message
  claude_desktop_conversation_summary
  claude_desktop_history_command

We seed 1 row in each kind plus a sources row with kind='claude_desktop',
then assert the output contract.
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
def claude_desktop_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("claude_desktop_build_canonical")
    return mod


def _seed_claude_desktop_db(p: Path) -> None:
    from research_ledger_init.sources_misc import claude_desktop_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in claude_desktop_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (50, 'claude_desktop', '/fake/.claude',
                    '2026-09-01T00:00:00Z')
        """)
        # 1 user message
        conn.execute("""
            INSERT INTO migrated_claude_desktop_messages (
                id, external_id, uuid, parent_uuid, session_id,
                timestamp_ms, message_type, cwd, user_type, version,
                is_sidechain, original_cwd, user_message, tool_use_result,
                is_at_mention_read, is_meta, cost_usd, duration_ms,
                assistant_message, is_api_error_message, assistant_model,
                conversation_summary, summary_updated_at_ms, source_path
            ) VALUES (
                1, 'claude_desktop_msg:u-1', 'u-1', NULL, 'sess-1',
                1700000000000, 'user', '/cwd', 'external', '1.0',
                0, '/cwd', '{"role":"user","content":"hello"}', NULL,
                0, 0, NULL, NULL, NULL, 0, NULL, NULL, NULL,
                '/fake/.claude/u-1.json'
            )
        """)
        # 1 assistant message with cost + model
        conn.execute("""
            INSERT INTO migrated_claude_desktop_messages (
                id, external_id, uuid, parent_uuid, session_id,
                timestamp_ms, message_type, cwd, user_type, version,
                is_sidechain, original_cwd, user_message, tool_use_result,
                is_at_mention_read, is_meta, cost_usd, duration_ms,
                assistant_message, is_api_error_message, assistant_model,
                conversation_summary, summary_updated_at_ms, source_path
            ) VALUES (
                2, 'claude_desktop_msg:a-1', 'a-1', 'u-1', 'sess-1',
                1700000001000, 'assistant', '/cwd', 'external', '1.0',
                0, '/cwd', NULL, NULL, 0, 0, 0.0123, 500,
                '{"role":"assistant","model":"claude-3-5-sonnet","content":"hi"}',
                0, 'claude-3-5-sonnet', NULL, NULL,
                '/fake/.claude/a-1.json'
            )
        """)
        # 1 conversation summary
        conn.execute("""
            INSERT INTO migrated_claude_desktop_messages (
                id, external_id, uuid, parent_uuid, session_id,
                timestamp_ms, message_type, cwd, user_type, version,
                is_sidechain, original_cwd, user_message, tool_use_result,
                is_at_mention_read, is_meta, cost_usd, duration_ms,
                assistant_message, is_api_error_message, assistant_model,
                conversation_summary, summary_updated_at_ms, source_path
            ) VALUES (
                3, 'claude_desktop_msg:cs-1', 'cs-1', 'a-1', 'sess-1',
                1700000002000, 'summary', '/cwd', 'external', '1.0',
                0, '/cwd', NULL, NULL, 0, 0, NULL, NULL, NULL, 0, NULL,
                'A summary of the conversation.', 1700000003000,
                '/fake/.claude/cs-1.json'
            )
        """)
        # 1 history entry
        conn.execute("""
            INSERT INTO migrated_claude_desktop_history (
                id, external_id, timestamp_ms, display, project,
                pasted_contents_json, source_path
            ) VALUES (
                1, 'claude_desktop_hist:1700000000:0', 1700000000,
                'show me the list of files', '/cwd',
                NULL, '/fake/.claude/history.jsonl'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_claude_desktop_builder_emits_four_item_kinds(
    research_db, monkeypatch, claude_desktop_builder
):
    _seed_claude_desktop_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "claude_desktop_build_canonical.py", "--db", str(research_db),
    ])
    rc = claude_desktop_builder.main()
    # main() returns None on success — coerce.
    assert rc is None or rc == 0

    conn = sqlite3.connect(research_db)
    try:
        by_kind = conn.execute("""
            SELECT item_kind, COUNT(*) FROM items
            WHERE source_id = 50
            GROUP BY item_kind ORDER BY item_kind
        """).fetchall()
        for expected in [
            ("claude_desktop_user_message", 1),
            ("claude_desktop_assistant_message", 1),
            ("claude_desktop_conversation_summary", 1),
            ("claude_desktop_history_command", 1),
        ]:
            assert expected in by_kind, f"missing {expected}"

        # User message: author='koosha', body=extracted text from content.
        u = conn.execute("""
            SELECT author, body, attrs_json FROM items
            WHERE source_id = 50 AND item_kind = 'claude_desktop_user_message'
        """).fetchone()
        u_author, u_body, u_attrs = u
        assert u_author == "koosha"
        assert u_body == "hello"
        u_parsed = json.loads(u_attrs)
        assert u_parsed["uuid"] == "u-1"
        assert u_parsed["session_id"] == "sess-1"
        assert u_parsed["message_type"] == "user"

        # Assistant message: author='anthropic', model + cost in attrs.
        a = conn.execute("""
            SELECT author, body, attrs_json FROM items
            WHERE source_id = 50
              AND item_kind = 'claude_desktop_assistant_message'
        """).fetchone()
        a_author, a_body, a_attrs = a
        assert a_author == "anthropic"
        assert a_body == "hi"
        a_parsed = json.loads(a_attrs)
        assert a_parsed["model"] == "claude-3-5-sonnet"
        assert a_parsed["cost_usd"] == 0.0123
        assert a_parsed["duration_ms"] == 500
        assert a_parsed["uuid"] == "a-1"

        # Conversation summary: body is the summary text directly.
        s = conn.execute("""
            SELECT author, body, attrs_json FROM items
            WHERE source_id = 50
              AND item_kind = 'claude_desktop_conversation_summary'
        """).fetchone()
        s_author, s_body, s_attrs = s
        # The author logic in the script is 'koosha' if role=='user' else
        # 'anthropic', so conversation_summary items get 'anthropic' as
        # their author.
        assert s_author == "anthropic"
        assert s_body == "A summary of the conversation."
        s_parsed = json.loads(s_attrs)
        assert s_parsed["uuid"] == "cs-1"
        # The role is 'system' (set in the script), not the author.
        assert s_parsed["message_type"] == "summary"

        # History command: external_id is rewritten from
        # 'claude_desktop_hist:...' to 'claude_desktop_hist_canon:...'.
        h = conn.execute("""
            SELECT external_id, body, author, attrs_json FROM items
            WHERE source_id = 50
              AND item_kind = 'claude_desktop_history_command'
        """).fetchone()
        h_ext, h_body, h_author, h_attrs = h
        assert h_ext == "claude_desktop_hist_canon:1700000000:0"
        assert h_body == "show me the list of files"
        assert h_author == "koosha"
        h_parsed = json.loads(h_attrs)
        assert h_parsed["raw_external_id"] == "claude_desktop_hist:1700000000:0"
        assert h_parsed["project"] == "/cwd"
        # No pasted contents → has_pasted_contents is False.
        assert h_parsed["has_pasted_contents"] is False

        # Captured_at is populated for all 4 items.
        n_null_captured = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 50 AND captured_at IS NULL
        """).fetchone()[0]
        assert n_null_captured == 0

        # FTS5 sanity: 'hello' should be searchable.
        n_fts = conn.execute("""
            SELECT COUNT(*) FROM items_fts
            WHERE items_fts MATCH 'hello'
        """).fetchone()[0]
        assert n_fts >= 1
    finally:
        conn.close()


def test_claude_desktop_builder_handles_assistant_tool_use_list_content(
    research_db, monkeypatch, claude_desktop_builder
):
    """When assistant content is a list with tool_use + text parts, body
    is the joined text including '[tool_use: <name>]' markers, and the
    JSON model field is captured into attrs."""
    from research_ledger_init.sources_misc import claude_desktop_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(research_db)
    conn = sqlite3.connect(research_db)
    try:
        for stmt in claude_desktop_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (51, 'claude_desktop', '/x', '2026-09-01T00:00:00Z')
        """)
        # Assistant message whose content is a list of text + tool_use.
        conn.execute("""
            INSERT INTO migrated_claude_desktop_messages (
                id, external_id, uuid, parent_uuid, session_id,
                timestamp_ms, message_type, cwd, user_type, version,
                is_sidechain, original_cwd, user_message, tool_use_result,
                is_at_mention_read, is_meta, cost_usd, duration_ms,
                assistant_message, is_api_error_message, assistant_model,
                conversation_summary, summary_updated_at_ms, source_path
            ) VALUES (
                1, 'claude_desktop_msg:m-1', 'm-1', NULL, 's',
                1700000000000, 'assistant', '/cwd', 'external', '1.0',
                0, '/cwd', NULL, NULL, 0, 0, 0.001, 100,
                ?, 0, 'claude-3-5-sonnet', NULL, NULL, '/x.json'
            )
        """, (
            '{"role":"assistant","model":"claude-3-5-sonnet",'
            '"content":[{"type":"text","text":"Let me search."},'
            '{"type":"tool_use","name":"web_search","input":{"q":"x"}}]}',
        ))
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(sys, "argv", [
        "claude_desktop_build_canonical.py", "--db", str(research_db),
    ])
    claude_desktop_builder.main()
    conn = sqlite3.connect(research_db)
    try:
        body = conn.execute("""
            SELECT body, attrs_json FROM items
            WHERE source_id = 51
              AND item_kind = 'claude_desktop_assistant_message'
        """).fetchone()
        b, attrs_json = body
        # text part + tool_use marker, in order.
        assert b == "Let me search.\n[tool_use: web_search]"
        parsed = json.loads(attrs_json)
        assert parsed["model"] == "claude-3-5-sonnet"
    finally:
        conn.close()