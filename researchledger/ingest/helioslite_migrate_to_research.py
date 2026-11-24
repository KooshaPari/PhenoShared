#!/usr/bin/env python3
"""W9g: helioslite (~/.helioslite/) — minimal/no-op ingest.

Helioslite is the additive-only fork of forgecode (renamed per
docs/RENAMES-STRATEGY.md, internal FORGE_* env names preserved until >50% fork
divergence). However, on this workstation it has been installed but not used:

  - 118M of 119M is just the bin/ executables (forge, forge_dbd, forge-dev,
    helioslite binaries = 38M each)
  - .forge.writes.db is empty (0 rows in conversations table, just an empty
    schema + FTS5 indexes)
  - logs/ has 2 nearly-empty log files
  - AGENTS.md is the fork's own AGENTS stub
  - .credentials.json is the API key

There is no conversation data to migrate. We register a source row so the
harness is represented in the ledger, but skip migration.

Usage:
    python3 helioslite_migrate_to_research.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, register_source

DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
HELIOSLITE_DIR = Path.home() / ".helioslite"
SOURCE_KIND = "helioslite"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    add_common_args(p, db_required=False, db_default=DB_PATH)
    # Library callers (tests) call main() with no args and expect defaults to win.
    # CLI callers go through `if __name__ == "__main__"` below, which passes sys.argv[1:].
    args = p.parse_args(argv if argv is not None else [])

    # Refuse to write the canonical corpus unless --allow-canonical was passed.
    # guard_and_connect preserves the load-bearing order: guard FIRST, then connect.
    db = guard_and_connect(args.db, allow_canonical=args.allow_canonical)

    print("W9g: helioslite (no-op ingest)")
    print(f"  src: {HELIOSLITE_DIR}")
    print(f"  db:  {args.db}")

    # Check for existing source row
    row = db.execute("SELECT id, byte_size, notes FROM sources WHERE kind = ?", (SOURCE_KIND,)).fetchone()
    if row:
        print(f"  source_id={row[0]} already exists (bytes={row[1]:,})")
        print(f"  notes: {row[2][:120]}...")
        db.close()
        return

    # Compute total size
    total_size = 0
    if HELIOSLITE_DIR.exists():
        for p in HELIOSLITE_DIR.rglob("*"):
            if p.is_file():
                try:
                    total_size += p.stat().st_size
                except Exception:
                    pass

    # 0 conversations in the local db
    conv_count = 0
    writes_db = HELIOSLITE_DIR / ".forge.writes.db"
    if writes_db.exists():
        try:
            s = sqlite3.connect(f"file:{writes_db}?mode=ro", uri=True)
            conv_count = s.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            s.close()
        except Exception as e:
            print(f"  WARN: {e}")

    print(f"  total bytes: {total_size:,} ({total_size/1024/1024:.0f} MB)")
    print(f"  conversations in local db: {conv_count}")

    src_id = register_source(
        db,
        kind=SOURCE_KIND,
        base_path=str(HELIOSLITE_DIR),
        byte_size=total_size,
        captured_at="2026-10-15T09:00:00Z",
        notes=(
            f"helioslite (additive-only fork of forgecode) from {HELIOSLITE_DIR}; "
            f"{total_size/1024/1024:.0f}MB total but 118MB is just bin/ executables; "
            f"0 conversation rows in .forge.writes.db. NO-OP: no conversation data to migrate."
        ),
    )
    db.commit()
    print(f"  source_id: {src_id}")
    print("  W9g complete (no items, source row only).")
    db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
