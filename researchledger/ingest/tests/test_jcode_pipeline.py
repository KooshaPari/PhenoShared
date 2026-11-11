"""jcode pipeline characterization.

The regression that motivated this work: attrs_json.tool_use_names was being
written as a JSON STRING (the CSV from the migrator's TEXT column) instead of
a JSON ARRAY. These tests pin the array contract AND the migrator's CSV column.
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
def jcode_migrator():
    return importlib.import_module("jcode_migrate_to_research")


@pytest.fixture
def jcode_builder():
    return importlib.import_module("jcode_build_canonical")


def test_migrator_writes_session_and_message_rows(
    tmp_path, jcode_sessions_dir, research_db, jcode_migrator, monkeypatch
):
    """Phase A: 1 session, 1 message, 1 tool_use detected.

    jcode's main() takes no argv; it reads sys.argv directly. Patch sys.argv
    so we don't touch production paths.
    """
    monkeypatch.setattr(sys, "argv", [
        "jcode_migrate_to_research.py",
        "--db", str(research_db),
        "--sessions-dir", str(jcode_sessions_dir),
        "--since", "2026-09-01T00:00:00Z",
    ])
    rc = jcode_migrator.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        n_sess = conn.execute(
            "SELECT COUNT(*) FROM migrated_jcode_sessions"
        ).fetchone()[0]
        n_msg = conn.execute(
            "SELECT COUNT(*) FROM migrated_jcode_messages"
        ).fetchone()[0]
        assert n_sess == 1 and n_msg == 1

        # tool_use_names is a CSV TEXT in the migrator layer.
        # THIS IS THE COLUMN THAT THE BUG REGRESSED.
        tool_names = conn.execute(
            "SELECT tool_use_names FROM migrated_jcode_messages"
        ).fetchone()[0]
        assert tool_names == "bash"  # CSV, not JSON

        # Sources row registered.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='jcode'"
        ).fetchone()
        assert kind is not None and kind[0] == "jcode"
    finally:
        conn.close()


def test_builder_writes_tool_use_names_as_json_array(
    tmp_path, jcode_sessions_dir, research_db,
    jcode_migrator, jcode_builder, monkeypatch,
):
    """THE REGRESSION: tool_use_names MUST expand via json_each."""
    monkeypatch.setattr(sys, "argv", [
        "jcode_migrate_to_research.py",
        "--db", str(research_db),
        "--sessions-dir", str(jcode_sessions_dir),
        "--since", "2026-09-01T00:00:00Z",
    ])
    jcode_migrator.main()
    # jcode_build_canonical.main() also takes no argv.
    monkeypatch.setattr(sys, "argv", [
        "jcode_build_canonical.py", "--db", str(research_db),
    ])
    rc = jcode_builder.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        # Item kind contract: jcode_session, jcode_message at minimum.
        kinds = {r[0] for r in conn.execute(
            "SELECT DISTINCT item_kind FROM items "
            "WHERE source_id IN (SELECT id FROM sources WHERE kind='jcode')"
        ).fetchall()}
        assert {"jcode_session", "jcode_message"}.issubset(kinds)

        # THE BUG GUARD. attrs_json.tool_use_names MUST:
        #   1. be valid JSON
        #   2. parse as a JSON ARRAY (not string/object)
        #   3. expand to >=1 row via json_each
        bad = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE item_kind='jcode_message'
              AND attrs_json IS NOT NULL
              AND (json_valid(attrs_json) = 0
                   OR json_type(json_extract(attrs_json, '$.tool_use_names')) != 'array')
        """).fetchone()[0]
        assert bad == 0, "tool_use_names must be a JSON ARRAY (the regression guard)"

        n_expanded = conn.execute("""
            SELECT COUNT(*) FROM items i, json_each(
                json_extract(i.attrs_json, '$.tool_use_names'))
            WHERE i.item_kind='jcode_message'
        """).fetchone()[0]
        assert n_expanded >= 1

        # The CSV column on the migrator side is also part of the contract.
        csv = conn.execute(
            "SELECT tool_use_names FROM migrated_jcode_messages"
        ).fetchone()[0]
        assert csv == "bash"  # plain CSV string, NOT a JSON array

        # Provenance completeness.
        miss = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id IN (SELECT id FROM sources WHERE kind='jcode')
              AND (evidence_type IS NULL OR confidence IS NULL
                   OR captured_at IS NULL OR external_id IS NULL)
        """).fetchone()[0]
        assert miss == 0
    finally:
        conn.close()


def test_helper_handles_csv_to_array():
    """_tool_names_to_array must convert 'bash,bash,read' -> ['bash','bash','read'].

    After the canonical_attrs consolidation, the function lives in
    canonical_attrs.py and is re-exported by the four builders.
    """
    from canonical_attrs import _tool_names_to_array
    assert _tool_names_to_array("bash,bash,read") == ["bash", "bash", "read"]
    assert _tool_names_to_array("") == []
    assert _tool_names_to_array(None) is None
    assert _tool_names_to_array("?") == []
    # Idempotent on real lists.
    assert _tool_names_to_array(["a", "b"]) == ["a", "b"]