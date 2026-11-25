"""claude_build_canonical characterization.

Pins down the claude canonical items + attachments builder. Reads the 7
migrated_anthropic_claude_* tables and emits 7 item_kinds:

  claude_conversation, claude_message, claude_memory,
  claude_project, claude_project_doc,
  claude_design_chat, claude_design_chat_message

plus one attachment kind 'file' (one per migrated_anthropic_claude_attachments).

CLAUDE_SOURCE_ID = 2 (pinned). The builder requires a sources row with
id=2, kind='claude'.

We seed one row in each migrated table, then assert the items/attachments
contracts and FK integrity.
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
def claude_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("claude_build_canonical")
    return mod


def _seed_claude_db(p: Path) -> None:
    from research_ledger_init.sources_chat import claude_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in claude_migrated_schema():
            conn.execute(stmt)
        # CLAUDE_SOURCE_ID = 2 (pinned in claude_build_canonical.py).
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (2, 'claude', '/fake/claude', '2026-09-01T00:00:00Z')
        """)
        # 1 conversation
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_conversations (
                id, external_id, name, summary, created_at, updated_at,
                account_uuid, n_messages, source_path
            ) VALUES (
                1, 'conv-1', 'My Chat', 'A short summary', '2026-09-01T00:00:00Z',
                '2026-09-01T01:00:00Z', 'acct-1', 2, '/fake/claude/conv-1.json'
            )
        """)
        # 2 messages in that conversation: 1 human + 1 assistant
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_messages (
                id, conversation_external_id, message_external_id, sender,
                created_at, updated_at, text, content_json,
                parent_message_uuid, n_parts, n_attachments, n_files
            ) VALUES (
                10, 'conv-1', 'msg-h-1', 'human',
                '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z',
                NULL, '[{"type":"text","text":"Hello, Claude."}]',
                NULL, 1, 0, 0
            )
        """)
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_messages (
                id, conversation_external_id, message_external_id, sender,
                created_at, updated_at, text, content_json,
                parent_message_uuid, n_parts, n_attachments, n_files
            ) VALUES (
                11, 'conv-1', 'msg-a-1', 'assistant',
                '2026-09-01T00:00:30Z', '2026-09-01T00:00:30Z',
                NULL, ?,
                'msg-h-1', 2, 0, 0
            )
        """, ('[{"type":"text","text":"Hi there, koosha."},'
              '{"type":"tool_use","name":"search","input":{"q":"a"}}]',))
        # 1 attachment on msg-a-1
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_attachments (
                id, msg_external_id, conversation_external_id, file_name,
                file_size, file_type, extracted_content, content_len
            ) VALUES (
                100, 'msg-a-1', 'conv-1', 'data.txt', 42,
                'text/plain', 'the quick brown fox', 19
            )
        """)
        # 1 memory row
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_memories (
                id, account_uuid, conversations_memory,
                project_memories_json, memory_files_json, source_path
            ) VALUES (
                1, 'acct-1', 'I like koalas.', '{}', '{}', '/fake/claude/mem.json'
            )
        """)
        # 1 project + 1 doc
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_projects (
                id, external_id, name, description, is_private,
                is_starter_project, prompt_template, created_at, updated_at,
                creator_uuid, source_path
            ) VALUES (
                1, 'proj-1', 'Reverse Engineering', 'Re-architect X.', 1,
                0, 'You are a reverse engineer.', '2026-09-01T00:00:00Z',
                '2026-09-01T00:00:00Z', 'acct-1', '/fake/claude/proj-1.json'
            )
        """)
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_project_docs (
                id, project_external_id, doc_external_id, filename,
                content, created_at
            ) VALUES (
                1, 'proj-1', 'proj-1:doc-1', 'design.md',
                '# Design\nThe koala project doc.', '2026-09-01T00:00:00Z'
            )
        """)
        # 1 design chat + 1 design message
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_design_chats (
                id, external_id, title, project_uuid, project_name,
                created_at, updated_at, source_path
            ) VALUES (
                1, 'dc-1', 'Design Chat 1', 'proj-1', 'Reverse Engineering',
                '2026-09-01T00:00:00Z', '2026-09-01T00:00:00Z', '/fake/claude/dc-1.json'
            )
        """)
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_design_chat_messages (
                id, chat_external_id, message_external_id, role, created_at,
                content_text, content_json
            ) VALUES (
                1, 'dc-1', 'dcm-1', 'user', '2026-09-01T00:00:00Z',
                'Initial design thoughts', NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_claude_builder_emits_seven_item_kinds_and_one_attachment_kind(
    research_db, monkeypatch, claude_builder
):
    _seed_claude_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "claude_build_canonical.py", "--research", str(research_db),
    ])
    rc = claude_builder.main()
    assert rc == 0

    conn = sqlite3.connect(research_db)
    try:
        # Counts by item_kind (one each in the fixture, EXCEPT
        # claude_message which has 2 in the fixture).
        by_kind = conn.execute("""
            SELECT item_kind, COUNT(*) FROM items
            WHERE source_id = 2
            GROUP BY item_kind ORDER BY item_kind
        """).fetchall()
        for expected in [
            ("claude_conversation", 1),
            ("claude_memory", 1),
            ("claude_message", 2),
            ("claude_project", 1),
            ("claude_project_doc", 1),
            ("claude_design_chat", 1),
            ("claude_design_chat_message", 1),
        ]:
            assert expected in by_kind, f"missing {expected}"

        # 1 attachment of kind='file' (per migrated_anthropic_claude_attachments row).
        n_att = conn.execute("""
            SELECT COUNT(*) FROM attachments WHERE source_id = 2
        """).fetchone()[0]
        assert n_att == 1
        att = conn.execute("""
            SELECT kind, byte_size, mime_type, item_id, extracted_text
            FROM attachments WHERE source_id = 2
        """).fetchone()
        assert att[0] == "file"
        assert att[1] == 42
        assert att[2] == "text/plain"
        assert att[3] is not None  # bound to msg-a-1
        assert att[4] == "the quick brown fox"

        # Conversation item carries name=summary and a JSON attrs with n_messages.
        conv = conn.execute("""
            SELECT title, body, attrs_json
            FROM items
            WHERE source_id = 2 AND external_id = 'conv-1'
        """).fetchone()
        ctitle, cbody, cattrs = conv
        assert ctitle == "My Chat"
        assert cbody == "A short summary"
        cparsed = json.loads(cattrs)
        assert cparsed["summary"] == "A short summary"
        assert cparsed["n_messages"] == 2
        assert cparsed["platform"] == "claude"

        # Human message: body is the single text part; author='human'.
        m1 = conn.execute("""
            SELECT author, body FROM items
            WHERE source_id = 2 AND external_id = 'msg-h-1'
        """).fetchone()
        assert m1 == ("human", "Hello, Claude.")

        # Assistant message: body is ONLY the text parts (tool_use is dropped).
        # author='assistant', parent_id points to the conversation.
        m2 = conn.execute("""
            SELECT author, body, parent_id FROM items
            WHERE source_id = 2 AND external_id = 'msg-a-1'
        """).fetchone()
        m2_author, m2_body, m2_parent = m2
        assert m2_author == "assistant"
        assert m2_body == "Hi there, koosha."
        assert m2_parent is not None
        # Parent must be the conversation item.
        parent_kind = conn.execute(
            "SELECT item_kind FROM items WHERE id = ?", (m2_parent,)
        ).fetchone()[0]
        assert parent_kind == "claude_conversation"

        # Project doc: parent must be the project item.
        doc = conn.execute("""
            SELECT parent_id, body, title FROM items
            WHERE source_id = 2 AND external_id = 'proj-1:doc-1'
        """).fetchone()
        doc_parent, doc_body, doc_title = doc
        assert doc_title == "design.md"
        assert "koala project doc" in doc_body
        doc_parent_kind = conn.execute(
            "SELECT item_kind FROM items WHERE id = ?", (doc_parent,)
        ).fetchone()[0]
        assert doc_parent_kind == "claude_project"

        # Design chat message: parent must be the design chat.
        dcm = conn.execute("""
            SELECT parent_id, author FROM items
            WHERE source_id = 2 AND external_id = 'dcm-1'
        """).fetchone()
        dcm_parent, dcm_author = dcm
        assert dcm_author == "user"
        dcm_parent_kind = conn.execute(
            "SELECT item_kind FROM items WHERE id = ?", (dcm_parent,)
        ).fetchone()[0]
        assert dcm_parent_kind == "claude_design_chat"

        # Memory item: external_id='memory:<account_uuid>'.
        mem = conn.execute("""
            SELECT body, title FROM items
            WHERE source_id = 2 AND item_kind = 'claude_memory'
        """).fetchone()
        assert mem[0] == "I like koalas."
        assert mem[1].startswith("User memory (")

        # FK integrity (per the validate() output).
        n_orphan_msg = conn.execute("""
            SELECT COUNT(*) FROM items m
            WHERE m.source_id = 2 AND m.item_kind = 'claude_message'
              AND (m.parent_id IS NULL
                   OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = m.parent_id
                                  AND p.item_kind = 'claude_conversation'))
        """).fetchone()[0]
        assert n_orphan_msg == 0

        n_orphan_att = conn.execute("""
            SELECT COUNT(*) FROM attachments a
            WHERE a.source_id = 2
              AND (a.item_id IS NULL
                   OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = a.item_id
                                  AND p.item_kind = 'claude_message'))
        """).fetchone()[0]
        assert n_orphan_att == 0

        # FTS5 sanity: 'koala' should match the doc body.
        n_fts = conn.execute("""
            SELECT COUNT(*) FROM items_fts
            WHERE items_fts MATCH 'koala'
        """).fetchone()[0]
        assert n_fts >= 1
    finally:
        conn.close()


def test_claude_builder_falls_back_to_text_column_when_content_json_empty(
    research_db, monkeypatch, claude_builder
):
    """When content_json is empty, the message body must come from text."""
    from research_ledger_init.sources_chat import claude_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(research_db)
    conn = sqlite3.connect(research_db)
    try:
        for stmt in claude_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (2, 'claude', '/x', '2026-09-01T00:00:00Z')
        """)
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_conversations (
                id, external_id, name, summary, created_at, updated_at,
                account_uuid, n_messages, source_path
            ) VALUES (
                1, 'conv-x', 'X', '', '2026-09-01T00:00:00Z', NULL, 'a', 1, NULL
            )
        """)
        # Message with text set, content_json empty.
        conn.execute("""
            INSERT INTO migrated_anthropic_claude_messages (
                id, conversation_external_id, message_external_id, sender,
                created_at, updated_at, text, content_json,
                parent_message_uuid, n_parts, n_attachments, n_files
            ) VALUES (
                1, 'conv-x', 'msg-x', 'human',
                '2026-09-01T00:00:00Z', NULL,
                'plain text body', '', NULL, 1, 0, 0
            )
        """)
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(sys, "argv", [
        "claude_build_canonical.py", "--research", str(research_db),
    ])
    claude_builder.main()
    conn = sqlite3.connect(research_db)
    try:
        body = conn.execute("""
            SELECT body FROM items
            WHERE source_id = 2 AND external_id = 'msg-x'
        """).fetchone()[0]
        assert body == "plain text body"
    finally:
        conn.close()