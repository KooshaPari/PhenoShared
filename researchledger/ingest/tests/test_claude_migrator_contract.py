"""claude_migrate_to_research.py — output contract characterization.

Builds a synthetic raw-dir mirroring claude-20261010/raw/ layout and runs
the migrator against a temp research_ledger target. Pins:

  * All 11 migrated_anthropic_claude_* tables exist with the expected cols.
  * Every JSON column (content_json, event_json, project_memories_json,
    memory_files_json, design_chat_messages.content_json) round-trips.
  * exit code 0; nothing written to the canonical corpus.

The migrator reads JSON directly off disk (not sqlite), so the fixture is a
tmp_path tree, not a sqlite database. argparse routes via sys.argv because
claude_migrate_to_research.main() takes no positional arguments.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from researchledger import corpus_guard  # noqa: E402

ANALYSIS = Path(__file__).resolve().parent.parent
SCRATCH = ANALYSIS / ".scratch-w9-16"  # harmless scratch dir (gitignored)


def _open(p: Path) -> sqlite3.Connection:
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def claude_raw_dir(tmp_path: Path) -> Path:
    """Build a tiny stand-in for claude-20261010/raw/ with 1 conv, 1 user,
    1 login event, 1 memory blob, 1 project + 1 doc, 1 design chat + 1 msg.
    """
    rd = tmp_path / "claude_raw"

    # conversations.json
    conv_dir = rd / "conversations-000"
    conv_dir.mkdir(parents=True)
    convs = [{
        "uuid": "conv-uuid-1",
        "name": "test conv",
        "summary": "",
        "created_at": "2026-09-01T10:00:00Z",
        "updated_at": "2026-09-01T10:05:00Z",
        "account": {"uuid": "acct-uuid-1"},
        "chat_messages": [
            {
                "uuid": "msg-uuid-1",
                "sender": "human",
                "text": "hi",
                "content": [{"type": "text", "text": "hi"}],
                "created_at": "2026-09-01T10:00:00Z",
                "updated_at": "2026-09-01T10:00:00Z",
                "parent_message_uuid": None,
                "attachments": [
                    {
                        "file_name": "screenshot.png",
                        "file_size": 1234,
                        "file_type": "image/png",
                        "extracted_content": "fake extracted text",
                    },
                ],
                "files": [
                    {"file_uuid": "file-uuid-1", "file_name": "doc.pdf"},
                ],
            },
        ],
    }]
    (conv_dir / "conversations.json").write_text(json.dumps(convs))

    # light_metadata
    lm = rd / "light_metadata-000"
    lm.mkdir()
    users = [{"uuid": "acct-uuid-1", "full_name": "Alice",
              "email_address": "a@example.com",
              "verified_phone_number": None}]
    (lm / "users.json").write_text(json.dumps(users))
    login = {"login_events": [{"account_uuid": "acct-uuid-1",
                                "ip": "127.0.0.1",
                                "logged_in_at": "2026-09-01"}]}
    (lm / "login_history.json").write_text(json.dumps(login))

    # memories
    mem = rd / "memories-000"
    mem.mkdir()
    (mem / "acct-uuid-1.json").write_text(json.dumps({
        "account_uuid": "acct-uuid-1",
        "conversations_memory": "remembered",
        "project_memories": {"proj-a": "note"},
        "memory_files": {"file-a.txt": "data"},
    }))

    # projects
    proj_root = rd / "projects-000" / "projects"
    proj_root.mkdir(parents=True)
    (proj_root / "proj-uuid-1.json").write_text(json.dumps({
        "uuid": "proj-uuid-1",
        "name": "P",
        "description": "d",
        "is_private": True,
        "is_starter_project": False,
        "prompt_template": None,
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z",
        "creator": {"uuid": "acct-uuid-1"},
        "docs": [{"uuid": "doc-uuid-1", "filename": "r.txt",
                  "content": "hello",
                  "created_at": "2026-09-01T00:00:00Z"}],
    }))

    # design_chats
    dc_root = rd / "design_chats-000" / "design_chats"
    dc_root.mkdir(parents=True)
    (dc_root / "dc-uuid-1.json").write_text(json.dumps({
        "uuid": "dc-uuid-1",
        "title": "design",
        "project": {"uuid": "proj-uuid-1", "name": "P"},
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z",
        "messages": [{
            "uuid": "dmsg-uuid-1",
            "role": "user",
            "created_at": "2026-09-01T00:00:00Z",
            "content": {"role": "user", "content": "ping"},
        }],
    }))

    return rd


def test_claude_writes_all_eleven_tables_with_expected_columns(
    tmp_path, claude_raw_dir, research_db, monkeypatch
):
    """Phase: 11 migrated_anthropic_claude_* tables, with the right cols."""
    monkeypatch.setattr(sys, "argv", [
        "claude_migrate_to_research.py",
        "--raw-dir", str(claude_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("claude_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    expected = {
        "migrated_anthropic_claude_conversations": {
            "external_id", "name", "summary", "created_at", "updated_at",
            "account_uuid", "n_messages", "source_path",
        },
        "migrated_anthropic_claude_messages": {
            "conversation_external_id", "message_external_id", "sender",
            "created_at", "text", "content_json",
            "parent_message_uuid", "n_parts", "n_attachments", "n_files",
        },
        "migrated_anthropic_claude_attachments": {
            "msg_external_id", "conversation_external_id", "file_name",
            "file_size", "file_type", "extracted_content", "content_len",
        },
        "migrated_anthropic_claude_files": {
            "msg_external_id", "conversation_external_id", "file_external_id",
            "file_name",
        },
        "migrated_anthropic_claude_users": {
            "external_id", "full_name", "email_address", "verified_phone_number",
        },
        "migrated_anthropic_claude_login_events": {
            "user_external_id", "event_json", "source_path",
        },
        "migrated_anthropic_claude_memories": {
            "account_uuid", "conversations_memory",
            "project_memories_json", "memory_files_json", "source_path",
        },
        "migrated_anthropic_claude_projects": {
            "external_id", "name", "description", "is_private",
            "is_starter_project", "prompt_template", "created_at",
            "updated_at", "creator_uuid", "source_path",
        },
        "migrated_anthropic_claude_project_docs": {
            "project_external_id", "doc_external_id", "filename", "content",
            "created_at",
        },
        "migrated_anthropic_claude_design_chats": {
            "external_id", "title", "project_uuid", "project_name",
            "created_at", "updated_at", "source_path",
        },
        "migrated_anthropic_claude_design_chat_messages": {
            "chat_external_id", "message_external_id", "role", "created_at",
            "content_text", "content_json",
        },
    }

    conn = _open(research_db)
    try:
        for tbl, want in expected.items():
            cols = {r[1] for r in conn.execute(
                f"PRAGMA table_info({tbl})").fetchall()}
            assert cols >= want, f"{tbl} missing: {want - cols}"
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            assert n >= 1, f"{tbl} empty"
    finally:
        conn.close()


def test_claude_json_columns_round_trip_with_correct_shapes(
    tmp_path, claude_raw_dir, research_db, monkeypatch
):
    """The regression guard: every JSON column must be valid JSON.

    messages.content_json / design_chat_messages.content_json — content
    blocks, should expand via json_each. login_events.event_json — object.
    memories.project_memories_json / memory_files_json — objects.
    """
    monkeypatch.setattr(sys, "argv", [
        "claude_migrate_to_research.py",
        "--raw-dir", str(claude_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("claude_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    conn = _open(research_db)
    try:
        # messages.content_json: ARRAY — the canonical regression case
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_messages
            WHERE content_json IS NOT NULL
              AND (json_valid(content_json) = 0
                   OR json_type(content_json) != 'array')
        """).fetchone()[0]
        assert bad == 0

        n_each = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_messages m,
                 json_each(m.content_json)
            WHERE m.content_json IS NOT NULL
        """).fetchone()[0]
        assert n_each >= 1

        # login_events.event_json: any valid JSON
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_login_events
            WHERE event_json IS NOT NULL
              AND json_valid(event_json) = 0
        """).fetchone()[0]
        assert bad == 0

        # memories.*_json: objects (json_type IN ('object','null'))
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_memories
            WHERE project_memories_json IS NOT NULL
              AND json_type(project_memories_json) NOT IN ('object', 'null')
        """).fetchone()[0]
        assert bad == 0
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_memories
            WHERE memory_files_json IS NOT NULL
              AND json_type(memory_files_json) NOT IN ('object', 'null')
        """).fetchone()[0]
        assert bad == 0

        # design_chat_messages.content_json: any valid JSON
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_anthropic_claude_design_chat_messages
            WHERE content_json IS NOT NULL
              AND json_valid(content_json) = 0
        """).fetchone()[0]
        assert bad == 0
    finally:
        conn.close()


def test_claude_migrator_writes_only_to_target(
    tmp_path, claude_raw_dir, research_db, monkeypatch
):
    """Confirm the migrator did not touch the canonical corpus."""
    assert str(research_db).startswith(str(tmp_path))

    monkeypatch.setattr(sys, "argv", [
        "claude_migrate_to_research.py",
        "--raw-dir", str(claude_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("claude_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    from researchledger.corpus_guard import guard_write_target, CANONICAL
    import os
    assert os.path.exists(CANONICAL)
    with pytest.raises(SystemExit):
        guard_write_target(CANONICAL, allow_canonical=False)
