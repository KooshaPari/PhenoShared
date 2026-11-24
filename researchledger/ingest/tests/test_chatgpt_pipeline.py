"""chatgpt pipeline characterization.

Pins down what chatgpt_migrate_to_research.py and chatgpt_build_canonical.py
write to the target DB so a future consolidation refactor is verifiable.

Note: chatgpt uses SCALAR `tool_name` (NOT an array) — this is the opposite
shape from jcode/kcode/codex. See jcode tests for the array contract.
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
def chatgpt_migrator():
    mod = importlib.import_module("chatgpt_migrate_to_research")
    return mod


@pytest.fixture
def chatgpt_builder():
    mod = importlib.import_module("chatgpt_build_canonical")
    return mod


def test_migrator_writes_all_five_tables(
    tmp_path, session_ledger_with_chatgpt, research_db, chatgpt_migrator
):
    """Phase A: chatgpt_migrate_to_research populates all 5 migrated_* tables."""
    rc = chatgpt_migrator.main([
        "--session", str(session_ledger_with_chatgpt),
        "--research", str(research_db),
    ])
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        for tbl in [
            "migrated_openai_chatgpt_conversations",
            "migrated_openai_chatgpt_messages",
            "migrated_openai_chatgpt_files",
            "migrated_openai_chatgpt_attachment_content",
            "migrated_openai_chatgpt_tool_results",
        ]:
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            assert n >= 1, f"{tbl} empty after migration"
        # Sources row registered with kind=session_ledger_migrated (id=1)
        kind = conn.execute("SELECT kind FROM sources WHERE id=1").fetchone()[0]
        assert kind == "session_ledger_migrated"
    finally:
        conn.close()


def test_builder_emits_chatgpt_items_with_attrs_json(
    tmp_path, session_ledger_with_chatgpt, research_db,
    chatgpt_migrator, chatgpt_builder,
):
    """Phase B: chatgpt_build_canonical inserts 3 item_kinds with attrs_json."""
    chatgpt_migrator.main([
        "--session", str(session_ledger_with_chatgpt),
        "--research", str(research_db),
    ])
    rc = chatgpt_builder.main(["--research", str(research_db)])
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        # Exact item_kind set is the contract.
        kinds = {r[0] for r in conn.execute(
            "SELECT DISTINCT item_kind FROM items WHERE source_id=1"
        ).fetchall()}
        assert kinds == {"chatgpt_conversation", "chatgpt_message",
                         "chatgpt_tool_result"}

        # attrs_json for tool_result MUST be a JSON object with tool_name
        # as a SCALAR string — this is the chatgpt-specific shape.
        row = conn.execute("""
            SELECT attrs_json FROM items
            WHERE source_id=1 AND item_kind='chatgpt_tool_result'
        """).fetchone()[0]
        parsed = json.loads(row)
        assert isinstance(parsed["tool_name"], str)
        assert parsed["tool_name"] == "bash"
        # Real validation: every attrs_json is valid JSON.
        valid = conn.execute(
            "SELECT COUNT(*) FROM items WHERE source_id=1 "
            "AND json_valid(attrs_json)=0"
        ).fetchone()[0]
        assert valid == 0

        # Provenance: every item carries all 5 fields per spec §4.3.
        miss = conn.execute("""
            SELECT COUNT(*) FROM items WHERE source_id=1
              AND (evidence_type IS NULL OR confidence IS NULL
                   OR captured_at IS NULL OR source_id IS NULL
                   OR external_id IS NULL)
        """).fetchone()[0]
        assert miss == 0

        # Orphan check: messages must have a parent conversation.
        orphans = conn.execute("""
            SELECT COUNT(*) FROM items WHERE source_id=1
              AND item_kind='chatgpt_message'
              AND (parent_id IS NULL OR NOT EXISTS (
                SELECT 1 FROM items p WHERE p.id=items.parent_id
                  AND p.item_kind='chatgpt_conversation'))
        """).fetchone()[0]
        assert orphans == 0
    finally:
        conn.close()