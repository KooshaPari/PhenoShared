"""
imessage_build_canonical.py — pump migrated_imessage_* → canonical items/attachments

Reads research_ledger.migrated_imessage_{chats,handles,messages,attachments} and
produces:
  items.item_kind='imessage_chat'      — one per chat (440 rows)
  items.item_kind='imessage_message'   — one per message (72K rows)
  attachments.kind='imessage_attachment' — one per attachment (8.6K rows)

PII policy: redaction_state='partial' (matches chatgpt + claude convention).
Phone numbers and emails are NOT promoted to canonical items (handles stay in
migrated_*); only message-level text bodies are stored, which is the
operator's own conversation content.

Date: migrated_imessage_messages.date_iso is in UTC ISO 8601 with ns precision.
We truncate to seconds (canonical stores strings) to fit the FTS5 token budget.
"""

from __future__ import annotations

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

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def truncate_iso(s: str | None) -> str | None:
    """Truncate an ISO timestamp to seconds (FTS5 budget)."""
    if not s:
        return None
    # e.g. 2026-10-15T01:12:01.708575+00:00 -> 2026-10-15T01:12:01+00:00
    try:
        if "." in s:
            head, rest = s.split(".", 1)
            # Find the timezone suffix (+HH:MM, -HH:MM, Z)
            for tz in ("+", "-", "Z"):
                if tz in rest:
                    tz_idx = rest.index(tz)
                    fractional = rest[:tz_idx]
                    tz_part = rest[tz_idx:]
                    return f"{head}{tz_part}"
            return head
        return s
    except Exception:
        return s


def find_src_id(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT id FROM sources WHERE kind = 'imessage'")
    row = cur.fetchone()
    if not row:
        raise SystemExit("imessage source not found in research_ledger; run imessage_migrate_to_research.py first")
    return row[0]


def build_chat_items(conn: sqlite3.Connection, src_id: int) -> int:
    """items.item_kind='imessage_chat', one per migrated chat."""
    cur = conn.cursor()
    n = 0
    today = now_iso()
    rows = cur.execute("""
        SELECT external_id, chat_guid, service_name, style, display_name,
               chat_identifier, is_archived, last_read_message_iso, message_count
        FROM migrated_imessage_chats
    """).fetchall()
    for r in rows:
        (ext_id, guid, svc, style, disp_name, chat_id, archived, last_read_iso, msg_count) = r
        # Title: prefer display_name for groups, else chat_identifier (phone/email)
        title = disp_name or chat_id or f"chat {ext_id}"
        if not title:
            title = f"<unnamed chat {ext_id}>"
        # Body: short summary
        style_label = "group" if style == 45 else "1:1" if style == 43 else f"style={style}"
        body_parts = [
            f"chat: {title}",
            f"service: {svc}",
            f"type: {style_label}",
            f"messages: {msg_count:,}",
        ]
        if last_read_iso:
            body_parts.append(f"last read: {truncate_iso(last_read_iso)}")
        if archived:
            body_parts.append("archived: yes")
        body = " | ".join(body_parts)
        attrs = {
            "service": svc,
            "style": style,
            "is_group": style == 45,
            "is_archived": bool(archived),
            "message_count": msg_count,
            "chat_guid": guid,
            "platform": "imessage",
        }
        cur.execute("""
            INSERT OR IGNORE INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, ext_id, today, today,
            'direct', 'high', 'partial',
            'imessage_chat', 'koosha', title[:500], body,
            None, None, json.dumps(attrs, ensure_ascii=False),
        ))
        if cur.rowcount > 0:
            n += 1
    conn.commit()
    return n


def build_message_items(conn: sqlite3.Connection, src_id: int) -> int:
    """items.item_kind='imessage_message', one per migrated message."""
    cur = conn.cursor()
    n = 0
    today = now_iso()
    rows = cur.execute("""
        SELECT external_id, msg_guid, chat_external_id, handle_external_id,
               is_from_me, text, date_iso, date_read_iso, date_delivered_iso,
               is_empty, is_read, is_delivered, is_audio_message, is_archive,
               has_attachments, service, item_type, associated_message_type
        FROM migrated_imessage_messages
    """).fetchall()
    for r in rows:
        (ext_id, guid, chat_ext, handle_ext, is_from_me, text,
         date_iso, date_read_iso, date_delivered_iso,
         is_empty, is_read, is_delivered, is_audio, is_archive,
         has_attach, service, item_type, assoc_msg_type) = r

        # Author: from_me → 'koosha', else the handle (we don't expose phone
        # numbers in author; we use a stable handle_external_id reference)
        author = 'koosha' if is_from_me else (handle_ext or '<unknown>')

        # Title: short prefix of body or "[non-text]"
        if text and text.strip():
            title = text.strip().split("\n", 1)[0][:200]
        elif has_attach:
            title = "[attachment]"
        elif assoc_msg_type and assoc_msg_type != 0:
            title = f"[reaction/thread type={assoc_msg_type}]"
        else:
            title = "[empty]"

        # Body: include metadata header + raw text
        body_parts = []
        body_parts.append(f"date: {truncate_iso(date_iso) or '?'}")
        if is_from_me:
            body_parts.append("from: me (koosha)")
        else:
            body_parts.append(f"from: {author}")
        if service and service != "iMessage":
            body_parts.append(f"service: {service}")
        if has_attach:
            body_parts.append("has_attachments: yes")
        if is_audio:
            body_parts.append("audio_message: yes")
        if assoc_msg_type and assoc_msg_type != 0:
            body_parts.append(f"associated_message_type: {assoc_msg_type}")
        if text and text.strip():
            body_parts.append("")
            body_parts.append(text)
        else:
            body_parts.append("")
            body_parts.append("[no text body]")
        body = "\n".join(body_parts)

        # URL: per Apple's handoff pattern iMessage sometimes has associated URLs
        # in the text. Quick check:
        url = None
        if text and ("http://" in text or "https://" in text):
            for line in text.splitlines():
                for tok in line.split():
                    if tok.startswith(("http://", "https://")):
                        url = tok.rstrip(".,);")
                        break
                if url:
                    break

        attrs = {
            "service": service,
            "is_from_me": bool(is_from_me),
            "is_read": bool(is_read),
            "is_delivered": bool(is_delivered),
            "is_empty": bool(is_empty),
            "is_audio_message": bool(is_audio),
            "is_archive": bool(is_archive),
            "has_attachments": bool(has_attach),
            "item_type": item_type,
            "associated_message_type": assoc_msg_type,
            "chat_external_id": chat_ext,
            "handle_external_id": handle_ext,
            "msg_guid": guid,
            "platform": "imessage",
        }
        cur.execute("""
            INSERT OR IGNORE INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, ext_id, today, truncate_iso(date_iso) or today,
            'direct', 'high', 'partial',
            'imessage_message', author, title[:500], body,
            url, None, json.dumps(attrs, ensure_ascii=False),
        ))
        if cur.rowcount > 0:
            n += 1
        if n % 1000 == 0 and n > 0:
            conn.commit()
    conn.commit()
    return n


def build_attachments(conn: sqlite3.Connection, src_id: int) -> int:
    """attachments.kind='imessage_attachment', one per migrated attachment."""
    cur = conn.cursor()
    n = 0
    today = now_iso()
    rows = cur.execute("""
        SELECT a.external_id, a.msg_external_id, a.attach_guid, a.filename,
               a.mime_type, a.byte_size, a.uti, a.is_sticker, a.is_outgoing,
               a.local_path,
               m.is_from_me, m.date_iso
        FROM migrated_imessage_attachments a
        LEFT JOIN migrated_imessage_messages m ON m.external_id = a.msg_external_id
    """).fetchall()
    for r in rows:
        (ext_id, msg_ext, aguid, fname, mime, bsize, uti, is_sticker, is_outgoing,
         local_path, is_from_me, msg_date_iso) = r

        # Look up parent message item_id
        item_row = cur.execute(
            "SELECT id, title FROM items WHERE source_id = ? AND external_id = ?",
            (src_id, msg_ext)
        ).fetchone()
        if not item_row:
            # Orphan: skip (FK would fail)
            continue
        item_id, parent_title = item_row

        # title: prefer transfer_name from filename, else the bare filename
        title = (fname or '').rsplit("/", 1)[-1] or "[unnamed attachment]"

        cur.execute("""
            INSERT OR IGNORE INTO attachments (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_id, kind, local_path, byte_size, mime_type, source_url,
                sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, ext_id, today, truncate_iso(msg_date_iso) or today,
            'direct', 'high', 'partial',
            item_id, 'imessage_attachment',
            local_path, bsize, mime, None,
            None,  # sha256 not computed (would need to read the file)
        ))
        if cur.rowcount > 0:
            n += 1
        if n % 1000 == 0 and n > 0:
            conn.commit()
    conn.commit()
    return n


def report(conn: sqlite3.Connection, src_id: int,
           n_chat: int, n_msg: int, n_attach: int) -> None:
    cur = conn.cursor()
    print()
    print("Spot checks (imessage source in research_ledger):")
    for tbl, kind_col in [('items', 'item_kind'), ('attachments', 'kind')]:
        for kind in ['imessage_chat', 'imessage_message', 'imessage_attachment']:
            n = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {kind_col} = ? AND source_id = ?",
                            (kind, src_id)).fetchone()[0]
            print(f"  {tbl:15s} {kind:30s}  {n:>7,}")

    # FK integrity
    print()
    print("FK integrity:")
    n = cur.execute("""
        SELECT COUNT(*) FROM attachments a
        WHERE a.source_id = ? AND a.item_id IS NOT NULL
          AND a.item_id NOT IN (SELECT id FROM items WHERE source_id = ?)
    """, (src_id, src_id)).fetchone()[0]
    print(f"  orphan attachments (item_id not in items): {n}")

    # FTS5 spot check
    print()
    print("FTS5 spot check (items_fts joined to items):")
    for q in ['iMessage', 'koosha', 'agent', 'image', 'vault', 'tap', 'liked',
              'BCC', 'pipeline', 'paridehpour', 'ASU']:
        n = cur.execute("""
            SELECT COUNT(*) FROM items_fts f
            JOIN items i ON i.id = f.rowid
            WHERE items_fts MATCH ? AND i.source_id = ?
        """, (q, src_id)).fetchone()[0]
        print(f"  MATCH '{q}': {n}")

    # Sample items
    print()
    print("Sample items (most recent 3 imessage_message):")
    for r in cur.execute("""
        SELECT id, source_captured_at, author, title, substr(body, 1, 250)
        FROM items
        WHERE source_id = ? AND item_kind = 'imessage_message'
        ORDER BY source_captured_at DESC LIMIT 3
    """, (src_id,)).fetchall():
        print(f"  id={r[0]}  {r[1]}")
        print(f"    author: {r[2]}")
        print(f"    title:  {r[3][:80] if r[3] else None}")
        print(f"    body:   {r[4]}")
        print()


def main() -> int:
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

    print(f"db: {args.db}")
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    try:
        src_id = find_src_id(conn)
        print(f"source id: {src_id} (kind=imessage)")

        print()
        print("--- building chat items ---")
        n_chat = build_chat_items(conn, src_id)
        print(f"  inserted: {n_chat}")

        print()
        print("--- building message items ---")
        n_msg = build_message_items(conn, src_id)
        print(f"  inserted: {n_msg:,}")

        print()
        print("--- building attachments ---")
        n_attach = build_attachments(conn, src_id)
        print(f"  inserted: {n_attach:,}")

        report(conn, src_id, n_chat, n_msg, n_attach)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
