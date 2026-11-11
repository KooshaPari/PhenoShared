#!/usr/bin/env python3
"""W9e part 3: insert cursor_chat summary items (after cursor_message is done)."""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"


def main():
    ap = argparse.ArgumentParser(description="Insert cursor_chat summary items (W9e part 3)")
    ap.add_argument("--db", default=str(DB_PATH),
                    help="Path to research_ledger.sqlite (default: canonical corpus)")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Opt in to writing the canonical research_ledger corpus (required when --db is the sealed corpus path)")
    args = ap.parse_args()

    guard_write_target(args.db, allow_canonical=args.allow_canonical)
    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")
    c = db.cursor()
    source_id = 9  # cursor

    # Get all chat metadata
    chats = c.execute(
        """SELECT external_id, chat_uuid, created_at_ms, updated_at_ms, cwd,
                  is_subagent, has_conversation, chat_blob_count, model
           FROM migrated_cursor_chats"""
    ).fetchall()
    print(f"  total chats: {len(chats):,}")

    # Get per-chat message counts
    counts = dict(c.execute(
        """SELECT chat_external_id, COUNT(*)
           FROM migrated_cursor_messages
           GROUP BY chat_external_id"""
    ).fetchall())
    print(f"  chats with messages: {len(counts):,}")

    inserted = 0
    skipped = 0
    t0 = time.time()

    from datetime import datetime, timezone
    def ms_to_iso(ms):
        if ms is None:
            return None
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for r in chats:
        ext_id = r[0]
        # Check if already exists
        existing = c.execute(
            "SELECT 1 FROM items WHERE source_id=? AND external_id=?",
            (source_id, ext_id)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        chat_uuid = r[1]
        created_ms = r[2]
        updated_ms = r[3]
        cwd = r[4]
        is_subagent = r[5]
        has_conv = r[6]
        blob_count = r[7]
        model = r[8]
        item_count = counts.get(ext_id, 0)
        if item_count == 0:
            continue  # skip empty chats
        captured_at = ms_to_iso(created_ms) or "2026-10-15T07:00:00Z"
        title = f"cursor/{chat_uuid[:8]}/chat/{'sub' if is_subagent else 'main'}/{model or 'unknown'}/{captured_at[:10]}"[:200]
        body = f"Cursor chat {chat_uuid}\nmodel={model}\nsubagent={is_subagent}\ncwd={cwd}\nblobs={blob_count}\nitems={item_count}"
        item = {
            "source_id": source_id,
            "external_id": ext_id,
            "captured_at": captured_at,
            "source_captured_at": captured_at,
            "evidence_type": "direct",
            "confidence": "high",
            "note": f"cursor chat summary ({item_count} messages)",
            "redaction_state": "partial",
            "item_kind": "cursor_chat",
            "author": f"cursor:{model}" if model else "cursor:chat",
            "title": title,
            "body": body,
            "url": f"cursor://chats/{chat_uuid}",
            "raw_json_path": None,
            "parent_id": None,
            "dedupe_hash": None,
            "attrs_json": json.dumps({
                "chat_uuid": chat_uuid,
                "created_at_ms": created_ms,
                "updated_at_ms": updated_ms,
                "cwd": cwd,
                "is_subagent": bool(is_subagent),
                "has_conversation": bool(has_conv),
                "chat_blob_count": blob_count,
                "model": model,
                "item_count": item_count,
            }, ensure_ascii=False)[:200_000],
        }
        try:
            cur = c.execute(
                """
                INSERT OR IGNORE INTO items (
                    source_id, external_id, captured_at, source_captured_at,
                    evidence_type, confidence, note, redaction_state,
                    item_kind, author, title, body, url, raw_json_path,
                    parent_id, dedupe_hash, attrs_json
                ) VALUES (
                    :source_id, :external_id, :captured_at, :source_captured_at,
                    :evidence_type, :confidence, :note, :redaction_state,
                    :item_kind, :author, :title, :body, :url, :raw_json_path,
                    :parent_id, :dedupe_hash, :attrs_json
                )
                """,
                item,
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"    WARN: {chat_uuid[:8]}: {e}")
        if (inserted + skipped) % 200 == 0:
            db.commit()
            print(f"  ... {inserted + skipped}/{len(chats)} ({inserted} inserted, {skipped} skipped) elapsed {time.time()-t0:.1f}s")
    db.commit()

    # FTS5 sync
    print("  syncing FTS5...")
    db.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
    db.commit()
    print(f"  FTS5 done in {time.time()-t0:.1f}s total")

    print(f"\n=== Result ===")
    print(f"  inserted: {inserted:,}")
    print(f"  skipped:  {skipped:,}")
    print(f"  total cursor items: {c.execute('SELECT COUNT(*) FROM items WHERE source_id=9').fetchone()[0]:,}")
    for kind, n in c.execute("SELECT item_kind, COUNT(*) FROM items WHERE source_id=9 GROUP BY item_kind"):
        print(f"  {kind:20s} {n:,}")
    db.close()


if __name__ == "__main__":
    main()
