#!/usr/bin/env python3
"""
merge_desk_local.py — Merge a locally-available desk sqlite into the ledger.

Use this when the desk SSH server is hung/unreachable but you have a recently
pulled copy of the source sqlite (e.g., /tmp/desk_state_5.sqlite).

The local file is expected to contain a `sessions` table (and optionally
`opencode_usage`) produced by extract_sessions.py --device desk on the desk.
ATTACH + INSERT OR IGNORE is used; existing rows with matching PKs are kept.

Usage:
  python3 merge_desk_local.py /path/to/desk.sqlite
  python3 merge_desk_local.py /path/to/desk.sqlite --db /path/to/ledger.sqlite
"""
import argparse
import os
import sqlite3
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("local_sqlite", help="Path to a locally-available desk sqlite file")
    ap.add_argument("--db", default=os.path.expanduser("~/Exports/analysis/session_ledger.sqlite"),
                    help="Target ledger db (default: ~/Exports/analysis/session_ledger.sqlite)")
    args = ap.parse_args()

    if not os.path.isfile(args.local_sqlite):
        print(f"FATAL: {args.local_sqlite} does not exist")
        sys.exit(2)
    if not os.path.isfile(args.db):
        print(f"FATAL: target db {args.db} does not exist; run extract_sessions.py --device mac first")
        sys.exit(2)

    # Match extract_sessions.py behaviour: cwd = script dir (defeats any
    # local stdlib-shadowing .py files in the caller's cwd).
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    conn = sqlite3.connect(args.db)
    # Borrow the merge function from extract_sessions.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_sessions import _merge_remote_db
    counts = _merge_remote_db(conn, args.local_sqlite)
    conn.close()
    print(f"=== merge done ===")
    for k, v in counts.items():
        print(f"  {k}: {v} rows in source")


if __name__ == "__main__":
    main()
