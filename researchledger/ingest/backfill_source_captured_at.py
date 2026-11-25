#!/usr/bin/env python3
"""
backfill_source_captured_at.py — Backfill NULL source_captured_at items.

Round-1 finding: orphan-check preset reports 21,941 items with NULL
source_captured_at. Two sources account for all of them:

  - 8,572 chatgpt_tool_result items have parent_id pointing at their
    parent chatgpt_message. Backfill from parent's source_captured_at.
  - 13,368 forge_prompt items are top-level rows from
    unified-prompts.db with no per-prompt timestamp. Backfill from
    sources.captured_at (the migrate run time) as a documented lower-bound.
  - 1 claude_memory item: backfill from sources.captured_at (same reason).

Usage:
  python3 backfill_source_captured_at.py --dry-run
  python3 backfill_source_captured_at.py --apply
"""
import argparse
import os
import sqlite3
import sys

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402


DEFAULT_DB = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")


def count_nulls(conn):
    cur = conn.execute("""
        SELECT s.kind, i.item_kind, COUNT(*) AS n
        FROM items i JOIN sources s ON s.id = i.source_id
        WHERE i.source_captured_at IS NULL
        GROUP BY s.kind, i.item_kind
    """)
    return cur.fetchall()


def backfill_chatgpt_tool_results(conn):
    """Backfill from parent.source_captured_at."""
    cur = conn.execute("""
        UPDATE items
        SET source_captured_at = (SELECT p.source_captured_at FROM items p WHERE p.id = items.parent_id)
        WHERE source_captured_at IS NULL
          AND item_kind = 'chatgpt_tool_result'
          AND parent_id IS NOT NULL
    """)
    return cur.rowcount


def backfill_from_sources_captured_at(conn, kinds):
    """Backfill from sources.captured_at (lower-bound = migrate run time)."""
    placeholders = ",".join("?" * len(kinds))
    cur = conn.execute(
        f"""
        UPDATE items
        SET source_captured_at = (SELECT s.captured_at FROM sources s WHERE s.id = items.source_id)
        WHERE source_captured_at IS NULL
          AND item_kind IN ({placeholders})
        """,
        kinds,
    )
    return cur.rowcount


def main():
    ap = argparse.ArgumentParser(description="Backfill NULL source_captured_at in research_ledger")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true", help="Report counts only; do not write")
    ap.add_argument("--apply", action="store_true", help="Apply the backfill (commit)")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Opt in to writing the canonical research_ledger corpus (required when --db is the sealed corpus path)")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        ap.error("must pass --dry-run or --apply")

    guard_write_target(args.db, allow_canonical=args.allow_canonical)
    conn = sqlite3.connect(args.db)

    print("== before ==")
    for r in count_nulls(conn):
        print(f"  {r[0]:30s}  {r[1]:30s}  {r[2]}")

    if args.dry_run:
        print("\n(dry-run; no writes)")
        conn.close()
        return 0

    n1 = backfill_chatgpt_tool_results(conn)
    print(f"\nbackfill chatgpt_tool_result from parent: {n1}")

    n2 = backfill_from_sources_captured_at(conn, ["forge_prompt", "claude_memory"])
    print(f"backfill forge_prompt/claude_memory from sources.captured_at: {n2}")

    conn.commit()

    print("\n== after ==")
    for r in count_nulls(conn):
        print(f"  {r[0]:30s}  {r[1]:30s}  {r[2]}")

    n3 = conn.execute("SELECT COUNT(*) FROM items WHERE source_captured_at IS NULL").fetchone()[0]
    print(f"\nremaining NULL source_captured_at: {n3}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
