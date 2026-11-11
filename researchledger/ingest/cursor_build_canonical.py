#!/usr/bin/env python3
"""W9e part 2: build canonical items from migrated_cursor_messages.

For each cursor message in `migrated_cursor_messages`, insert a row in `items`
keyed by source_id=9 (cursor) with:
- item_kind = "cursor_message" (or "cursor_chat" for parent summary rows)
- author = "koosha" for user, "cursor:<model>" for assistant, "cursor:system" for system,
  "cursor:tool" for tool
- title = "cursor/<chat_uuid>/<role>/<first-60-chars>/<date>"
- body = full content_text
- redaction_state = "partial"
- evidence_type = "direct"
- confidence = 0.9
- attrs_json includes chat_external_id, ordinal, role, has_tool_calls, tool_call_names

Idempotent via INSERT OR IGNORE on UNIQUE external_id in items.

Usage:
    python3 cursor_build_canonical.py
"""
from __future__ import annotations

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

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
SOURCE_KIND = "cursor"


# Tool-name TEXT -> JSON-array conversion lives in canonical_attrs so the four
# builders (jcode, kcode, codex, cursor) all use one implementation. Cursor
# historically called this _tool_call_names_to_array; the function is generic
# over the field name, so it now uses the same _tool_names_to_array name.
from canonical_attrs import _tool_names_to_array  # noqa: E402,F401


def get_source_id(db):
    row = db.execute(
        "SELECT id FROM sources WHERE kind = ?", (SOURCE_KIND,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"source row for kind={SOURCE_KIND} not found; run migrate first")
    return row[0]


def fetch_pending_messages(db, limit: int | None = None):
    """Fetch messages that don't yet have an item row.

    When `limit` is set, fetch at most that many pending messages
    (useful for bound rebuilds / --limit smoke tests).
    """
    sql = """
        SELECT m.external_id, m.chat_external_id, m.chat_uuid, m.blob_id, m.ordinal,
               m.role, m.content_text, m.content_length, m.content_json,
               m.has_tool_calls, m.tool_call_names, m.blob_index, m.chat_created_at_ms,
               c.model, c.cwd, c.is_subagent
        FROM migrated_cursor_messages m
        LEFT JOIN migrated_cursor_chats c ON c.external_id = m.chat_external_id
        WHERE NOT EXISTS (
            SELECT 1 FROM items i
            WHERE i.source_id = ? AND i.external_id = m.external_id
        )
        ORDER BY m.chat_uuid, m.ordinal
    """
    params = [get_source_id(db)]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return db.execute(sql, params).fetchall()


def ms_to_iso(ms):
    if ms is None:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def author_for(role, model):
    if role == "user":
        return "koosha"
    if role == "assistant":
        return f"cursor:{model}" if model else "cursor:assistant"
    if role == "system":
        return "cursor:system"
    if role == "tool":
        return "cursor:tool"
    return "cursor:unknown"


def title_for(role, chat_uuid, content, created_iso):
    first = (content or "").split("\n", 1)[0].strip()[:60]
    first = first.replace("\n", " ").replace("\r", " ")
    date_str = (created_iso or "")[:10] or "unknown"
    return f"cursor/{chat_uuid[:8]}/{role}/{first}/{date_str}"[:200]


def insert_item(db, source_id, m):
    """Insert one item row. Returns True if inserted (False if already exists)."""
    ext_id, chat_ext_id, chat_uuid, blob_id, ordinal, role = m[0], m[1], m[2], m[3], m[4], m[5]
    content_text, content_length, content_json = m[6], m[7], m[8]
    has_tc, tc_names, blob_idx, chat_created_ms = m[9], m[10], m[11], m[12]
    model, cwd, is_subagent = m[13], m[14], m[15]

    captured_at = ms_to_iso(chat_created_ms) or "2026-10-15T07:00:00Z"
    body = content_text or ""
    if not body and content_json:
        body = content_json[:200_000]

    item = {
        "source_id": source_id,
        "external_id": ext_id,
        "captured_at": captured_at,
        "source_captured_at": captured_at,
        "evidence_type": "direct",
        "confidence": "high",
        "note": f"cursor {role} message from chat {chat_uuid[:8]}, ordinal {ordinal}",
        "redaction_state": "partial",
        "item_kind": "cursor_message",
        "author": author_for(role, model),
        "title": title_for(role, chat_uuid, body, captured_at),
        "body": body[:1_000_000],  # cap body at 1MB
        "url": f"cursor://chats/{chat_uuid}/{blob_id}",
        "raw_json_path": None,
        "parent_id": None,
        "dedupe_hash": None,
        "attrs_json": json.dumps({
            "chat_external_id": chat_ext_id,
            "chat_uuid": chat_uuid,
            "blob_id": blob_id,
            "ordinal": ordinal,
            "role": role,
            "content_length": content_length,
            "has_tool_calls": bool(has_tc),
            "tool_call_names": _tool_names_to_array(tc_names),
            "model": model,
            "cwd": cwd,
            "is_subagent": bool(is_subagent),
            "blob_index": blob_idx,
        }, ensure_ascii=False)[:200_000],
    }
    cur = db.execute(
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
    return cur.rowcount > 0


def insert_chat_summary(db, source_id):
    """Insert a parent 'cursor_chat' summary row per chat that has any item."""
    rows = db.execute(
        """
        SELECT c.external_id, c.chat_uuid, c.created_at_ms, c.updated_at_ms,
               c.cwd, c.is_subagent, c.has_conversation, c.chat_blob_count,
               c.model,
               (SELECT COUNT(*) FROM items i
                WHERE i.source_id = ? AND i.item_kind = 'cursor_message'
                  AND json_extract(i.attrs_json, '$.chat_external_id') = c.external_id) AS item_count
        FROM migrated_cursor_chats c
        WHERE NOT EXISTS (
            SELECT 1 FROM items i
            WHERE i.source_id = ? AND i.external_id = c.external_id
        )
          AND EXISTS (
            SELECT 1 FROM items i
            WHERE i.source_id = ? AND i.item_kind = 'cursor_message'
              AND json_extract(i.attrs_json, '$.chat_external_id') = c.external_id
        )
        """,
        (source_id, source_id, source_id),
    ).fetchall()

    inserted = 0
    for r in rows:
        ext_id, chat_uuid, created_ms, updated_ms = r[0], r[1], r[2], r[3]
        cwd, is_subagent, has_conv, blob_count = r[4], r[5], r[6], r[7]
        model, item_count = r[8], r[9]
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
        cur = db.execute(
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
    return inserted


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', type=Path, required=True,
                   help='Target research_ledger DB to write. REQUIRED — the '
                        'canonical corpus is rejected unless --allow-canonical '
                        'is also passed.')
    p.add_argument('--allow-canonical', action='store_true',
                   help='Permit writing the canonical corpus (dangerous).')
    p.add_argument('--limit', type=int, default=None,
                   help='Cap pending-message fetch to N (non-negative). '
                        'Default: full scan. Use to bound rebuild risk.')
    args = p.parse_args()
    if args.limit is not None and args.limit < 0:
        p.error("--limit must be non-negative")

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--db) path, not any migrated source path.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    db_path: Path = args.db

    print(f"W9e: cursor → items (canonical)")
    print(f"  db: {db_path}")
    if args.limit is not None:
        print(f"  limit: {args.limit} pending messages")
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")

    source_id = get_source_id(db)
    print(f"  source_id: {source_id}")

    pending = fetch_pending_messages(db, args.limit)
    print(f"  pending messages: {len(pending):,}")

    if not pending:
        print("  nothing to do")
    else:
        t0 = time.time()
        inserted = 0
        failed = 0
        for i, m in enumerate(pending, 1):
            try:
                if insert_item(db, source_id, m):
                    inserted += 1
            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"    WARN: failed on {m[2]}/{m[3][:16]}: {e}")
            if i % 5000 == 0:
                db.commit()
                print(f"  ... {i:,}/{len(pending):,} ({inserted:,} inserted, {failed} failed) elapsed {time.time()-t0:.1f}s")
        db.commit()
        print(f"  done: {inserted:,} inserted, {failed} failed in {time.time()-t0:.1f}s")

    # Add chat summary items
    print("  inserting chat summary items...")
    t0 = time.time()
    chat_inserted = insert_chat_summary(db, source_id)
    db.commit()
    print(f"  chat summaries: {chat_inserted:,} inserted in {time.time()-t0:.1f}s")

    # FTS5 sync
    print("  syncing FTS5...")
    try:
        db.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
    except sqlite3.OperationalError as e:
        print(f"  FTS5 rebuild: {e}")
    db.commit()

    # Final stats
    total = db.execute("SELECT COUNT(*) FROM items WHERE source_id = ?", (source_id,)).fetchone()[0]
    print(f"\n=== Result ===")
    print(f"  total items for source_id={source_id}: {total:,}")
    for r in db.execute(
        "SELECT item_kind, COUNT(*) FROM items WHERE source_id = ? GROUP BY item_kind ORDER BY 2 DESC",
        (source_id,),
    ):
        print(f"  {r[0]:30s} {r[1]:,}")
    db.close()


if __name__ == "__main__":
    sys.exit(main())
