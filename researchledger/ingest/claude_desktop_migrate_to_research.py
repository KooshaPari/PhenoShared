#!/usr/bin/env python3
"""W9f: claude_desktop (Claude Code CLI) → migrated_claude_desktop_*

Sources from ~/.claude/:
  - __store.db: drizzle sqlite with base_messages, user_messages, assistant_messages,
    conversation_summaries (small but full conversation pairs with cost_usd + model)
  - history.jsonl: 12,958 user commands with display, project, timestamp, pastedContents
    (just user commands, no assistant responses)
  - projects/*/memory/*.md: 292 markdown notes (SKIPPED this round)

Idempotent: INSERT OR IGNORE on UNIQUE external_id.

Usage:
    python3 claude_desktop_migrate_to_research.py
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, write_with_retry

CLAUDE_DIR = Path.home() / ".claude"
SOURCE_KIND = "claude_desktop"


def ms_to_iso(ms):
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        return None


def get_or_create_source(db):
    row = db.execute("SELECT id FROM sources WHERE kind = ?", (SOURCE_KIND,)).fetchone()
    if row:
        return row[0]
    # Compute total size
    total_size = 0
    if CLAUDE_DIR.exists():
        for p in CLAUDE_DIR.rglob("*"):
            if p.is_file():
                try:
                    total_size += p.stat().st_size
                except Exception:
                    pass
    cur = db.execute(
        """
        INSERT INTO sources (kind, base_path, captured_at, byte_size, schema_version, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            SOURCE_KIND,
            str(CLAUDE_DIR),
            "2026-10-15T09:00:00Z",
            total_size,
            "v1.0",
            f"claude_desktop passthrough from {CLAUDE_DIR} (__store.db drizzle + history.jsonl + projects/*/memory/*.md; ~{total_size/1024/1024:.0f}MB total, ~{total_size:,} bytes)",
        ),
    )
    db.commit()
    return cur.lastrowid


def migrate_store_db(db, source_id):
    """Migrate __store.db drizzle tables to migrated_claude_desktop_messages."""
    store_db_path = CLAUDE_DIR / "__store.db"
    if not store_db_path.exists():
        print(f"  WARN: {store_db_path} not found")
        return 0, 0, 0, 0, 0

    src = sqlite3.connect(f"file:{store_db_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    # Load all 4 tables into dicts keyed by uuid
    base_msgs = {r["uuid"]: dict(r) for r in src.execute("SELECT * FROM base_messages")}
    user_msgs = {r["uuid"]: dict(r) for r in src.execute("SELECT * FROM user_messages")}
    asst_msgs = {r["uuid"]: dict(r) for r in src.execute("SELECT * FROM assistant_messages")}
    summaries = {r["leaf_uuid"]: dict(r) for r in src.execute("SELECT * FROM conversation_summaries")}
    src.close()

    print(f"  __store.db: {len(base_msgs)} base, {len(user_msgs)} user, {len(asst_msgs)} assistant, {len(summaries)} summary")

    inserted = 0
    skipped = 0
    t0 = time.time()
    for uuid, base in base_msgs.items():
        ext_id = f"claude_desktop_msg:{uuid}"
        # Skip if already inserted
        existing = db.execute(
            "SELECT 1 FROM migrated_claude_desktop_messages WHERE external_id = ?",
            (ext_id,),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        user = user_msgs.get(uuid, {})
        asst = asst_msgs.get(uuid, {})
        summ = summaries.get(uuid, {})

        try:
            write_with_retry(
                db,
                """
                INSERT OR IGNORE INTO migrated_claude_desktop_messages (
                    external_id, uuid, parent_uuid, session_id, timestamp_ms, message_type,
                    cwd, user_type, version, is_sidechain, original_cwd,
                    user_message, tool_use_result, is_at_mention_read, is_meta,
                    cost_usd, duration_ms, assistant_message, is_api_error_message, assistant_model,
                    conversation_summary, summary_updated_at_ms, source_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ext_id,
                    uuid,
                    base.get("parent_uuid"),
                    base.get("session_id"),
                    base.get("timestamp"),
                    base.get("message_type"),
                    base.get("cwd"),
                    base.get("user_type"),
                    base.get("version"),
                    base.get("isSidechain"),
                    base.get("original_cwd"),
                    user.get("message"),
                    user.get("tool_use_result"),
                    user.get("is_at_mention_read"),
                    user.get("is_meta"),
                    asst.get("cost_usd"),
                    asst.get("duration_ms"),
                    asst.get("message"),
                    asst.get("is_api_error_message"),
                    asst.get("model"),
                    summ.get("summary"),
                    summ.get("updated_at"),
                    str(store_db_path),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"    WARN: {uuid}: {e}")
    db.commit()
    return inserted, skipped, len(base_msgs), len(user_msgs), len(asst_msgs)


def migrate_history_jsonl(db, source_id):
    """Migrate history.jsonl to migrated_claude_desktop_history."""
    hist_path = CLAUDE_DIR / "history.jsonl"
    if not hist_path.exists():
        print(f"  WARN: {hist_path} not found")
        return 0, 0

    inserted = 0
    skipped = 0
    t0 = time.time()
    with hist_path.open() as f:
        for idx, line in enumerate(f):
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = d.get("timestamp")
            ext_id = f"claude_desktop_hist:{ts}:{idx}"
            # Check existing
            existing = db.execute(
                "SELECT 1 FROM migrated_claude_desktop_history WHERE external_id = ?",
                (ext_id,),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            try:
                write_with_retry(
                    db,
                    """
                    INSERT OR IGNORE INTO migrated_claude_desktop_history (
                        external_id, timestamp_ms, display, project, pasted_contents_json, source_path
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ext_id,
                        ts,
                        d.get("display"),
                        d.get("project"),
                        json.dumps(d.get("pastedContents", {}), ensure_ascii=False)[:200_000],
                        str(hist_path),
                    ),
                )
                inserted += 1
            except Exception as e:
                if skipped + inserted <= 5:
                    print(f"    WARN: {ext_id}: {e}")
            if (inserted + skipped) % 2000 == 0 and inserted + skipped > 0:
                db.commit()
                print(f"    ... {inserted+skipped:,} ({inserted:,} inserted, {skipped:,} skipped) elapsed {time.time()-t0:.1f}s")
    db.commit()
    return inserted, skipped


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    add_common_args(p, db_required=True)
    args = p.parse_args(argv)

    # Refuse to write the canonical corpus unless --allow-canonical was passed.
    # guard_and_connect preserves the load-bearing order: guard FIRST, then connect.
    print(f"W9f: claude_desktop → migrated_claude_desktop_*")
    print(f"  src: {CLAUDE_DIR}")
    print(f"  db:  {args.db}")
    # Match the pre-refactor PRAGMA set exactly (journal_mode=WAL, synchronous=NORMAL).
    # No foreign_keys here because the original code did not set it.
    db = guard_and_connect(
        args.db, allow_canonical=args.allow_canonical,
        pragmas=["journal_mode = WAL", "synchronous = NORMAL", "busy_timeout = 60000"],
    )

    source_id = get_or_create_source(db)
    print(f"  source_id: {source_id}")

    # 1) __store.db
    print("=== __store.db (full conversation pairs) ===")
    ins1, skp1, n_base, n_user, n_asst = migrate_store_db(db, source_id)
    print(f"  base: {n_base}, user: {n_user}, assistant: {n_asst}")
    print(f"  inserted: {ins1}, skipped: {skp1}")

    # 2) history.jsonl
    print("=== history.jsonl (user commands) ===")
    ins2, skp2 = migrate_history_jsonl(db, source_id)
    print(f"  inserted: {ins2}, skipped: {skp2}")

    # 3) FTS5 sync
    print("=== FTS5 sync ===")
    try:
        db.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
        db.commit()
    except Exception:
        pass

    # Final state
    print("\n=== Result ===")
    for tbl in ('migrated_claude_desktop_messages', 'migrated_claude_desktop_history'):
        n = db.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n:,}")

    # A lock collision used to be swallowed per row, so a migrate could report
    # "inserted: 0" and still exit 0. Fail loudly instead.
    if (ins1 + ins2) == 0 and (skp1 + skp2) == 0:
        print("  ERROR: nothing inserted and nothing skipped - the corpus is probably locked")
        db.close()
        return 1
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
