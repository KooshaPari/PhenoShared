"""research_ledger_init — Bootstrap the research_ledger.sqlite schema.

Driven by analysis/specs/pmp-requirements.md §4. Idempotent.
Designed for 9+ sources (harness, chatgpt, claude, gemini, imessage, reddit,
linkedin, github, youtube) with the provenance fields the 8 pmps require.

Usage:
    python3 -m research_ledger_init --db PATH   # custom path
    python3 -m research_ledger_init --print     # print schema, no DB created

Per spec §4.3 every row carries:
  source_id, external_id, captured_at, source_captured_at, evidence_type,
  confidence, note, redaction_state

Per spec §2.4 OmniRoute-check is enforced at the application layer
(metrics) and at write time via the metrics source constraint (§4.4).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Re-export canonical constants + core schema
from .core import DEFAULT_DB, PROVENANCE_COLS, core_schema

# Re-export per-source migrated schemas (chat-style + harness-style + misc)
from .sources_chat import (
    chatgpt_migrated_schema,
    claude_migrated_schema,
    gemini_migrated_schema,
    imessage_migrated_schema,
)
from .sources_harness import (
    codex_migrated_schema,
    cursor_migrated_schema,
    forge_migrated_schema,
    jcode_migrated_schema,
    kcode_migrated_schema,
)
from .sources_misc import claude_desktop_migrated_schema

__all__ = [
    "DEFAULT_DB",
    "PROVENANCE_COLS",
    "core_schema",
    "chatgpt_migrated_schema",
    "claude_migrated_schema",
    "gemini_migrated_schema",
    "imessage_migrated_schema",
    "jcode_migrated_schema",
    "kcode_migrated_schema",
    "codex_migrated_schema",
    "forge_migrated_schema",
    "cursor_migrated_schema",
    "claude_desktop_migrated_schema",
    "init",
    "print_schema",
    "main",
]


def init(db_path: Path) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        all_ddl = core_schema() + chatgpt_migrated_schema() + claude_migrated_schema() + gemini_migrated_schema() + imessage_migrated_schema() + jcode_migrated_schema() + kcode_migrated_schema() + codex_migrated_schema() + forge_migrated_schema() + cursor_migrated_schema() + claude_desktop_migrated_schema()
        for stmt in all_ddl:
            conn.execute(stmt)
        conn.commit()
        # Validate
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        ).fetchall()]
        indexes = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]
        fts_count = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE '%_fts%'").fetchone()[0]
        size = db_path.stat().st_size if db_path.exists() else 0
        return {
            "db_path": str(db_path),
            "tables": tables,
            "indexes": indexes,
            "fts_objects": fts_count,
            "size_bytes": size,
        }
    finally:
        conn.close()


def print_schema() -> None:
    print("=== research_ledger.sqlite schema (spec §4) ===")
    for stmt in core_schema():
        print(stmt.strip()[:120], "..." if len(stmt) > 120 else "")
    print()
    print("=== migrated tables (chatgpt passthrough) ===")
    for stmt in chatgpt_migrated_schema():
        print(stmt.strip()[:120], "..." if len(stmt) > 120 else "")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(DEFAULT_DB), help="Path to research_ledger.sqlite")
    p.add_argument("--print", action="store_true", help="Print schema, do not create DB")
    args = p.parse_args(argv)

    if args.print:
        print_schema()
        return 0

    result = init(Path(args.db))
    print(f"research_ledger.sqlite initialized at {result['db_path']}")
    print(f"  tables/views: {len(result['tables'])}")
    for t in result["tables"]:
        print(f"    {t}")
    print(f"  indexes:      {len(result['indexes'])}")
    print(f"  fts objects:  {result['fts_objects']}")
    print(f"  size:         {result['size_bytes']} bytes")
    return 0
