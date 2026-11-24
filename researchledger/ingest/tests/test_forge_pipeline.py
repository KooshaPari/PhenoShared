"""forge pipeline characterization.

forge (ForgeCode) passthrough reads from a sqlite source DB with a `prompts`
table and writes to migrated_forge_prompts. content_json is JSON OBJECT
{"content": "..."}, metadata_json is JSON OBJECT (forge's metadata dict).
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
def forge_migrator():
    return importlib.import_module("forge_migrate_to_research")


@pytest.fixture
def forge_source_db(tmp_path: Path) -> Path:
    """Synthetic ~/.forge/prompt-corpus/unified-prompts.db.

    Mirrors the prompts table the migrator reads from.
    """
    db = tmp_path / "unified-prompts.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE prompts (
            id TEXT PRIMARY KEY,
            content TEXT,
            content_hash TEXT,
            source_tool TEXT,
            source TEXT,
            metadata TEXT,
            extracted_at TEXT
        );
    """)
    # Two rows so we exercise the COUNT(*) > 0 check.
    conn.execute(
        "INSERT INTO prompts VALUES (?,?,?,?,?,?,?)",
        ("p-uuid-1", "test prompt one", "hash-a", "forge", "database",
         json.dumps({"conversation_id": "conv-1", "workspace_id": "ws-1",
                     "message_index": 0, "title": "Test conv 1",
                     "created_at": "2026-05-01 12:00:00.000"}),
         "2026-06-13T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO prompts VALUES (?,?,?,?,?,?,?)",
        ("p-uuid-2", "second prompt longer than 500 chars " * 30,
         "hash-b", "codex", "history",
         json.dumps({"conversation_id": "conv-2", "workspace_id": "ws-2",
                     "message_index": 1, "title": "Test conv 2",
                     "created_at": "2026-05-02 12:00:00.000"}),
         "2026-06-13T00:00:00Z"),
    )
    conn.commit()
    conn.close()
    return db


def test_migrator_writes_forge_prompts(
    tmp_path, forge_source_db, research_db, forge_migrator
):
    """Phase A: forge_migrate_to_research populates migrated_forge_prompts.

    forge main() accepts argv as a list (uses parse_args(argv)).

    Both sources are pinned to fixtures. `--src-forge-db` MUST be passed even
    though this test only exercises the historical path: its default is the
    production store ~/.forge/.forge.db, so omitting it ingests every real
    conversation on the host into the temp DB and the row count can never
    match. Measured 2026-11-10: omitting it yielded 110,572 rows here instead
    of the 2 the fixture creates.
    """
    rc = forge_migrator.main([
        "--db", str(research_db),
        "--src", str(forge_source_db),
        "--src-forge-db", str(tmp_path / "absent-forge.db"),
    ])
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM migrated_forge_prompts"
        ).fetchone()[0]
        assert n == 2

        # content_json MUST be a valid JSON OBJECT with a "content" key.
        # The migrator wraps the truncated content as {"content": "..."}.
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_forge_prompts
            WHERE content_json IS NOT NULL
              AND (json_valid(content_json) = 0
                   OR json_type(content_json) != 'object')
        """).fetchone()[0]
        assert bad == 0, "content_json must be valid JSON OBJECT"

        # metadata_json MUST also be valid JSON (it's a dict).
        bad_meta = conn.execute("""
            SELECT COUNT(*) FROM migrated_forge_prompts
            WHERE metadata_json IS NOT NULL
              AND json_valid(metadata_json) = 0
        """).fetchone()[0]
        assert bad_meta == 0

        # The 2nd row's content is >500 chars → migrator truncates with "..."
        # and stores the truncated form in content_json.content.
        cj = conn.execute(
            "SELECT content_json FROM migrated_forge_prompts "
            "WHERE forge_prompt_id='p-uuid-2'"
        ).fetchone()[0]
        obj = json.loads(cj)
        assert isinstance(obj, dict) and "content" in obj
        # The migrator's contract: len(500) + "..." for long content.
        assert obj["content"].endswith("...")

        # Conversation metadata fields round-trip via metadata_json.
        mj = conn.execute(
            "SELECT metadata_json FROM migrated_forge_prompts "
            "WHERE forge_prompt_id='p-uuid-1'"
        ).fetchone()[0]
        meta = json.loads(mj)
        assert meta["conversation_id"] == "conv-1"
        assert meta["workspace_id"] == "ws-1"
        assert meta["title"] == "Test conv 1"

        # source_tool and source are copied through verbatim.
        tools = conn.execute(
            "SELECT source_tool, source FROM migrated_forge_prompts "
            "ORDER BY forge_prompt_id"
        ).fetchall()
        assert tools == [("forge", "database"), ("codex", "history")]

        # Sources row registered with kind=forge.
        kind = conn.execute(
            "SELECT kind FROM sources WHERE kind='forge'"
        ).fetchone()
        assert kind is not None and kind[0] == "forge"

        # external_id is deterministic: forge_prompt:<id>.
        ext = conn.execute(
            "SELECT external_id FROM migrated_forge_prompts "
            "WHERE forge_prompt_id='p-uuid-1'"
        ).fetchone()[0]
        assert ext == "forge_prompt:p-uuid-1"
    finally:
        conn.close()