#!/usr/bin/env python3
"""
fixup_tool_name_json.py - Convert malformed tool-name strings to JSON arrays.

DISCOVERED: 2026-10-15 during cold-read test of handoff §5.5. jcode has
183,111 items where attrs_json.tool_use_names is a comma-separated string
like "bash,bash,read" rather than a JSON array. cursor has 1 item with
tool_call_names = "?". Running json_each() on these raises
sqlite3.OperationalError: malformed JSON.

FIX:
- For jcode (source_id=5): parse the comma-separated string and rewrite
  as a JSON array.
- For cursor (source_id=9): the single "?" item becomes an empty array [].

The fix is idempotent: WHERE clause only touches malformed rows, and a
re-run after a successful apply touches 0 rows.

Usage:
  python3 fixup_tool_name_json.py --dry-run
  python3 fixup_tool_name_json.py --apply
"""
import argparse
import json
import os
import sqlite3
import sys
import time

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402


DEFAULT_DB = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")


def open_rw(db_path):
    """Open the DB in read-write mode (the existing CLI is read-only)."""
    if not os.path.exists(db_path):
        sys.exit(f"DB not found: {db_path}")
    return sqlite3.connect(db_path)


def parse_string_to_array(s):
    """Parse a comma-separated tool-name string into a JSON array.

    Examples:
      "bash"           -> ["bash"]
      "bash,bash,read" -> ["bash", "bash", "read"]
      "?"              -> []   (no real tool name)
      ""               -> []
      None             -> None (no change)
    """
    if s is None:
        return None
    s = s.strip()
    if not s or s == "?":
        return []
    # Split on comma, strip whitespace, drop empty strings
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts


def main():
    ap = argparse.ArgumentParser(description="Fix malformed tool-name JSON")
    ap.add_argument("--db", default=DEFAULT_DB, help="Path to research_ledger.sqlite")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change")
    ap.add_argument("--apply", action="store_true", help="Apply the fixup")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Opt in to writing the canonical research_ledger corpus (required when --db is the sealed corpus path)")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        sys.exit("Specify --dry-run or --apply")

    guard_write_target(args.db, allow_canonical=args.allow_canonical)
    conn = open_rw(args.db)
    try:
        # 1. Inventory the malformed rows BEFORE doing anything
        # Note: we use json_valid() instead of json_type() because
        # json_type() ALSO errors on malformed JSON. json_valid is the
        # safe predicate.
        cur = conn.execute("""
            SELECT source_id, COUNT(*) AS n_malformed,
                   SUM(CASE
                         WHEN json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
                              AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0
                         THEN 1 ELSE 0 END) AS jcode_malformed,
                   SUM(CASE
                         WHEN json_extract(attrs_json, '$.tool_call_names') IS NOT NULL
                              AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0
                         THEN 1 ELSE 0 END) AS cursor_malformed
            FROM items
            WHERE (json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0)
               OR (json_extract(attrs_json, '$.tool_call_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0)
            GROUP BY source_id
        """)
        rows = cur.fetchall()
        if not rows:
            print("no malformed tool-name rows found. nothing to do.")
            return 0
        print("=== inventory ===")
        for sid, n, jm, cm in rows:
            print(f"  source_id={sid}  total_malformed={n}  jcode_tool_use_names_malformed={jm or 0}  cursor_tool_call_names_malformed={cm or 0}")
        total = sum(r[1] for r in rows)
        print(f"  TOTAL: {total} malformed rows")

        if args.dry_run:
            print()
            print("=== sample of what would be rewritten (first 5) ===")
            cur = conn.execute("""
                SELECT id, source_id, json_extract(attrs_json, '$.tool_use_names') AS tn,
                       json_extract(attrs_json, '$.tool_call_names') AS tc
                FROM items
                WHERE (json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
                       AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0)
                   OR (json_extract(attrs_json, '$.tool_call_names') IS NOT NULL
                       AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0)
                LIMIT 5
            """)
            for row in cur.fetchall():
                rid, sid, tn, tc = row
                if tn is not None:
                    new = parse_string_to_array(tn)
                    print(f"  id={rid} source_id={sid}  tool_use_names: {tn!r} -> {json.dumps(new)}")
                if tc is not None:
                    new = parse_string_to_array(tc)
                    print(f"  id={rid} source_id={sid}  tool_call_names: {tc!r} -> {json.dumps(new)}")
            print()
            print(f"DRY-RUN: would update {total} rows. no changes made.")
            return 0

        # 2. APPLY: rewrite one row at a time (small enough for 183K rows)
        # Strategy:
        #   a) select all malformed rows
        #   b) for each, parse, json_set, update
        #   c) commit periodically
        print()
        print("=== applying ===")
        t0 = time.time()
        cur = conn.execute("""
            SELECT id, attrs_json
            FROM items
            WHERE (json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0)
               OR (json_extract(attrs_json, '$.tool_call_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0)
        """)
        BATCH = 5000
        n_updated = 0
        batch = []
        for row in cur:
            rid, attrs_json = row
            obj = json.loads(attrs_json) if attrs_json else {}
            changed = False
            if "tool_use_names" in obj and obj["tool_use_names"] is not None:
                # only rewrite if it's not already a list (the WHERE should
                # already filter this, but defensive)
                if not isinstance(obj["tool_use_names"], list):
                    new = parse_string_to_array(obj["tool_use_names"])
                    obj["tool_use_names"] = new
                    changed = True
            if "tool_call_names" in obj and obj["tool_call_names"] is not None:
                if not isinstance(obj["tool_call_names"], list):
                    new = parse_string_to_array(obj["tool_call_names"])
                    obj["tool_call_names"] = new
                    changed = True
            if changed:
                batch.append((rid, json.dumps(obj, ensure_ascii=False)))
                if len(batch) >= BATCH:
                    conn.executemany(
                        "UPDATE items SET attrs_json = ? WHERE id = ?",
                        [(a, r) for r, a in batch],
                    )
                    conn.commit()
                    n_updated += len(batch)
                    elapsed = time.time() - t0
                    rate = n_updated / elapsed if elapsed > 0 else 0
                    print(f"  committed {n_updated}/{total}  ({rate:.0f} rows/s, {elapsed:.1f}s elapsed)")
                    batch = []
        if batch:
            conn.executemany(
                "UPDATE items SET attrs_json = ? WHERE id = ?",
                [(a, r) for r, a in batch],
            )
            conn.commit()
            n_updated += len(batch)
            elapsed = time.time() - t0
            rate = n_updated / elapsed if elapsed > 0 else 0
            print(f"  committed {n_updated}/{total}  ({rate:.0f} rows/s, {elapsed:.1f}s elapsed)")

        elapsed = time.time() - t0
        print()
        print(f"=== applied: {n_updated} rows in {elapsed:.1f}s ({n_updated/elapsed if elapsed > 0 else 0:.0f} rows/s) ===")

        # 3. Verify
        print()
        print("=== verification ===")
        cur = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE (json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_use_names')) = 0)
               OR (json_extract(attrs_json, '$.tool_call_names') IS NOT NULL
                   AND json_valid(json_extract(attrs_json, '$.tool_call_names')) = 0)
        """)
        remaining = cur.fetchone()[0]
        if remaining == 0:
            print(f"  remaining malformed: 0  (success)")
        else:
            print(f"  remaining malformed: {remaining}  (FAILED)")
            return 1

        # 4. Sanity: a few rows should now have valid arrays
        cur = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE json_type(json_extract(attrs_json, '$.tool_use_names')) = 'array'
               OR json_type(json_extract(attrs_json, '$.tool_call_names')) = 'array'
        """)
        n_arrays = cur.fetchone()[0]
        print(f"  rows with valid tool-name arrays: {n_arrays}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
