#!/usr/bin/env python3
"""W9f-5: build canonical items for claude_desktop memory notes.

Creates 1 item per migrated_claude_desktop_memory_notes row:
  - item_kind: claude_desktop_memory_note
  - role: 'system' (these are agent-generated memory, not user/assistant)
  - author: 'claude_code_cli'
  - body: first 60K chars of content_text
  - attrs_json: filename, project_path, file_path, frontmatter, first_heading, line_count

Idempotent: skips items that already exist by external_id.
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402
from migrator_base import write_with_retry

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
SOURCE_KIND = "claude_desktop"


def ms_to_iso(ms):
    """Format an epoch timestamp as ISO-8601Z.

    ``modified_at_ms`` is epoch milliseconds. Values that are really epoch
    seconds (as __store.db stores them) are detected by magnitude so they
    land on the right date instead of collapsing to 1970.
    """
    if ms is None:
        return None
    try:
        value = float(ms)
    except (TypeError, ValueError):
        return None
    if abs(value) < 1e11:  # epoch seconds, not milliseconds
        value *= 1000
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', type=Path, required=True,
                   help='Target research_ledger DB to write. REQUIRED — the '
                        'canonical corpus is rejected unless --allow-canonical '
                        'is also passed.')
    p.add_argument('--allow-canonical', action='store_true',
                   help='Permit writing the canonical corpus (dangerous).')
    args = p.parse_args()

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--db) path, not any migrated source path.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    print("W9f-5: build canonical items for claude_desktop memory notes")
    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout = 60000")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")

    source_id = db.execute(
        "SELECT id FROM sources WHERE kind = ?", (SOURCE_KIND,)
    ).fetchone()[0]
    print(f"  source_id: {source_id}")

    rows = db.execute(
        """
        SELECT * FROM migrated_claude_desktop_memory_notes
        ORDER BY id
        """
    ).fetchall()
    print(f"  found {len(rows)} memory notes")

    inserted = 0
    skipped = 0
    for r in rows:
        d = dict(r)
        ext_id = d["external_id"]
        ts_iso = ms_to_iso(d.get("modified_at_ms"))
        text = (d.get("content_text") or "")[:60000]

        # Parse frontmatter JSON
        try:
            fm = json.loads(d.get("frontmatter_json") or "{}")
        except Exception:
            fm = {}

        attrs = {
            "filename": d.get("filename"),
            "project_path": d.get("project_path"),
            "file_path": d.get("file_path"),
            "line_count": d.get("line_count"),
            "byte_size": d.get("byte_size"),
            "first_heading": d.get("first_heading"),
            "frontmatter": fm,
        }

        existing = db.execute(
            "SELECT 1 FROM items WHERE source_id = ? AND external_id = ?",
            (source_id, ext_id),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        try:
            write_with_retry(
                db,
                """
                INSERT OR IGNORE INTO items (
                    source_id, external_id, captured_at, source_captured_at,
                    evidence_type, confidence, note, redaction_state,
                    item_kind, author, title, body, url, raw_json_path,
                    parent_id, dedupe_hash, attrs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    ext_id,
                    ts_iso or "2026-10-15T09:00:00Z",
                    ts_iso,
                    "direct",
                    "high",
                    None,
                    "none",
                    "claude_desktop_memory_note",
                    "claude_code_cli",
                    d.get("first_heading") or d.get("filename"),
                    text,
                    None,
                    d.get("file_path"),
                    None,
                    None,
                    json.dumps(attrs, ensure_ascii=False, default=str),
                ),
            )
            inserted += 1
        except Exception as e:
            if inserted + skipped <= 5:
                print(f"    WARN: {ext_id}: {e}")
    db.commit()

    print(f"  inserted: {inserted}, skipped: {skipped}")
    print("\n=== Result by item_kind ===")
    for r in db.execute(
        """
        SELECT item_kind, COUNT(*) AS n
        FROM items
        WHERE source_id = ?
        GROUP BY item_kind
        ORDER BY n DESC
        """,
        (source_id,),
    ):
        print(f"  {r[0]}: {r[1]}")

    # A lock collision used to be swallowed per row, so the build could report
    # "inserted: 0" and still exit 0. Fail loudly instead.
    built = db.execute(
        "SELECT COUNT(*) FROM items WHERE source_id = ?", (source_id,)
    ).fetchone()[0]
    if len(rows) > 0 and built == 0:
        print("  ERROR: memory notes exist but 0 canonical items landed")
        db.close()
        return 1
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
