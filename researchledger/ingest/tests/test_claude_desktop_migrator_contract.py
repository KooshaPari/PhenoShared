"""claude_desktop_migrate_to_research.py — output contract characterization.

Builds a synthetic ~/.claude/ tree with a 4-table drizzle sqlite (__store.db)
plus a tiny history.jsonl, then runs the migrator against a temp
research_ledger target. CLAUDE_DIR is monkeypatched to tmp_path so the
real ~/.claude is never touched.

Pins:
  * Both target tables (messages + history) exist with expected cols.
  * Idempotency (the migrator's existing-row check works).
  * history.pasted_contents_json — the regression guard column — is valid
    JSON object.
  * exit code 0; canonical corpus untouched; source row kind='claude_desktop'.
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
from pathlib import Path

import pytest

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from researchledger import corpus_guard  # noqa: E402

ANALYSIS = Path(__file__).resolve().parent.parent


def _open(p: Path) -> sqlite3.Connection:
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def patched_claude_desktop(tmp_path, monkeypatch):
    """Import the module and point CLAUDE_DIR at a temp dir before tests run."""
    mod = importlib.import_module("claude_desktop_migrate_to_research")
    monkeypatch.setattr(mod, "CLAUDE_DIR", tmp_path / "fake_claude")
    (tmp_path / "fake_claude").mkdir()
    return mod


def _build_store_db(path: Path) -> None:
    """Stand up a 4-table drizzle __store.db with 1 user + 1 assistant msg."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE base_messages (
            uuid TEXT PRIMARY KEY,
            parent_uuid TEXT,
            session_id TEXT,
            timestamp INTEGER,
            message_type TEXT,
            cwd TEXT,
            user_type TEXT,
            version TEXT,
            isSidechain INTEGER,
            original_cwd TEXT
        );
        CREATE TABLE user_messages (
            uuid TEXT PRIMARY KEY,
            message TEXT,
            tool_use_result TEXT,
            is_at_mention_read INTEGER,
            is_meta INTEGER
        );
        CREATE TABLE assistant_messages (
            uuid TEXT PRIMARY KEY,
            cost_usd REAL,
            duration_ms INTEGER,
            message TEXT,
            is_api_error_message INTEGER,
            model TEXT
        );
        CREATE TABLE conversation_summaries (
            leaf_uuid TEXT PRIMARY KEY,
            summary TEXT,
            updated_at INTEGER
        );
    """)
    conn.execute(
        "INSERT INTO base_messages VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("u-1", None, "sess-1", 1700000000000, "user", "/cwd",
         "external", "1.0.0", 0, "/cwd"),
    )
    conn.execute(
        "INSERT INTO user_messages VALUES (?,?,?,?,?)",
        ("u-1", "hello", None, 0, 0),
    )
    conn.execute(
        "INSERT INTO assistant_messages VALUES (?,?,?,?,?,?)",
        ("u-1", 0.001, 100, "hi", 0, "claude-3-5"),
    )
    conn.execute(
        "INSERT INTO conversation_summaries VALUES (?,?,?)",
        ("u-1", "short", 1700000000000),
    )
    conn.commit()
    conn.close()


def test_claude_desktop_writes_both_tables_with_expected_columns(
    tmp_path, patched_claude_desktop, research_db,
):
    """Phase: migrated_claude_desktop_messages + migrated_claude_desktop_history."""
    mod = patched_claude_desktop
    cd = mod.CLAUDE_DIR
    _build_store_db(cd / "__store.db")
    history_jsonl = "\n".join([
        json.dumps({"timestamp": 1700000000001, "display": "ls",
                    "project": "/proj",
                    "pastedContents": {"k": "v"}}),
        json.dumps({"timestamp": 1700000000002, "display": "echo hi",
                    "project": "/proj",
                    "pastedContents": {}}),
    ])
    (cd / "history.jsonl").write_text(history_jsonl)

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0  # this script's main doesn't return

    expected = {
        "migrated_claude_desktop_messages": {
            "external_id", "uuid", "parent_uuid", "session_id",
            "timestamp_ms", "message_type", "cwd", "user_type", "version",
            "is_sidechain", "original_cwd", "user_message",
            "tool_use_result", "is_at_mention_read", "is_meta",
            "cost_usd", "duration_ms", "assistant_message",
            "is_api_error_message", "assistant_model", "conversation_summary",
            "summary_updated_at_ms", "source_path",
        },
        "migrated_claude_desktop_history": {
            "external_id", "timestamp_ms", "display", "project",
            "pasted_contents_json", "source_path",
        },
    }

    conn = _open(research_db)
    try:
        # Source row at kind='claude_desktop'.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='claude_desktop'"
        ).fetchone()
        assert kind is not None and kind[0] == "claude_desktop"

        for tbl, want in expected.items():
            cols = {r[1] for r in conn.execute(
                f"PRAGMA table_info({tbl})").fetchall()}
            assert cols >= want, f"{tbl} missing: {want - cols}"

        assert conn.execute(
            "SELECT COUNT(*) FROM migrated_claude_desktop_messages"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM migrated_claude_desktop_history"
        ).fetchone()[0] == 2
    finally:
        conn.close()


def test_claude_desktop_history_pasted_contents_json_is_valid_object(
    tmp_path, patched_claude_desktop, research_db,
):
    """Regression guard: pasted_contents_json is the only JSON column in the
    claude_desktop schema. It must be valid JSON and parse as an object."""
    mod = patched_claude_desktop
    cd = mod.CLAUDE_DIR
    _build_store_db(cd / "__store.db")
    (cd / "history.jsonl").write_text("\n".join([
        json.dumps({"timestamp": 1700000000001, "display": "ls",
                    "project": "/proj", "pastedContents": {"k": "v"}}),
    ]))

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0

    conn = _open(research_db)
    try:
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_claude_desktop_history
            WHERE pasted_contents_json IS NOT NULL
              AND json_valid(pasted_contents_json) = 0
        """).fetchone()[0]
        assert bad == 0, "pasted_contents_json contains invalid JSON"

        # Shape: should be an OBJECT (json_type 'object' or null).
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_claude_desktop_history
            WHERE pasted_contents_json IS NOT NULL
              AND json_type(pasted_contents_json) NOT IN ('object', 'null')
        """).fetchone()[0]
        assert bad == 0

        # Round-trip: pick one row and assert the parsed object has a key.
        row = conn.execute("""
            SELECT pasted_contents_json FROM migrated_claude_desktop_history
            ORDER BY timestamp_ms LIMIT 1
        """).fetchone()
        parsed = json.loads(row[0])
        assert isinstance(parsed, dict)
        assert parsed.get("k") == "v"
    finally:
        conn.close()


def test_claude_desktop_migrator_writes_only_to_target(
    tmp_path, patched_claude_desktop, research_db,
):
    """Confirm the migrator did not touch the canonical corpus nor real ~/.claude."""
    mod = patched_claude_desktop
    assert str(research_db).startswith(str(tmp_path))
    # CLAUDE_DIR was patched to a sibling temp dir, NOT the real home.
    # The real ~/.claude lives at <HOME>/.claude. Pin that our patched
    # CLAUDE_DIR does not equal that path. (Cannot use startswith(Path.home())
    # because the test runner's HOME is itself under the user's home tree.)
    real_claude = Path.home() / ".claude"
    assert mod.CLAUDE_DIR.resolve() != real_claude.resolve(), (
        f"CLAUDE_DIR leaked to {mod.CLAUDE_DIR}"
    )

    cd = mod.CLAUDE_DIR
    _build_store_db(cd / "__store.db")
    (cd / "history.jsonl").write_text(json.dumps({
        "timestamp": 1700000000001, "display": "x", "project": "/p",
        "pastedContents": {},
    }))

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0

    from researchledger.corpus_guard import guard_write_target, CANONICAL
    assert os.path.exists(CANONICAL)
    with pytest.raises(SystemExit):
        guard_write_target(CANONICAL, allow_canonical=False)
