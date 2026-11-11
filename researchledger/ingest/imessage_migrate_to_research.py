"""
imessage_migrate_to_research.py — pump ~/Library/Messages/chat.db into research_ledger.migrated_imessage_*

Reads chat.db in ?mode=ro (URI), applies Apr 2025+ filter (consistent with extract_sessions.py),
skips empty/system/spam, registers the source as id=4 (kind=imessage).

Usage:
    python3 imessage_migrate_to_research.py             # default
    python3 imessage_migrate_to_research.py --db PATH   # custom research_ledger path
    python3 imessage_migrate_to_research.py --since 2024-01-01   # override Apr 2025+ filter

Date convention: macOS stores `date` as nanoseconds since 2001-01-01 UTC
(Apple Cocoa Core Data, post-High Sierra). We convert to ISO 8601 UTC.
Pre-HS records used integer seconds; we detect via magnitude (>1e15 → ns,
>1e12 → ms, else seconds).

PII policy: handle.uncanonicalized_id is the operator's own iMessage data;
we store it raw with redaction_state='none' on the source row, consistent
with chatgpt/claude/gemini. Set the source redaction_state if a different
default is needed.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, register_source

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
CHAT_DB = Path.home() / "Library" / "Messages" / "chat.db"

# Apple Cocoa Core Data epoch: 2001-01-01 00:00:00 UTC
APPLE_EPOCH = 978307200
# Default Apr 2025+ filter (matches extract_sessions.py s8 constraint)
DEFAULT_SINCE_UNIX = 1743465600  # 2025-04-01 00:00:00 UTC


def apple_ns_to_iso(t: int | None) -> str | None:
    """Convert macOS chat.db date (ns since 2001-01-01 UTC) to ISO 8601 UTC."""
    if t is None or t <= 0:
        return None
    if t > 1e15:        # nanoseconds
        secs = t / 1e9
    elif t > 1e12:      # milliseconds (pre-HS or some internal fields)
        secs = t / 1e3
    else:               # seconds
        secs = float(t)
    if secs < 0 or secs > 4e9:
        return None
    try:
        return datetime.fromtimestamp(secs + APPLE_EPOCH, timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def open_source() -> sqlite3.Connection:
    """Open chat.db in read-only URI mode."""
    uri = f"file:{CHAT_DB}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def migrate_chats(src: sqlite3.Connection, dst: sqlite3.Connection,
                  since_unix: int, src_id: int) -> tuple[int, int, int]:
    """migrated_imessage_chats + handles."""
    since_ns = (since_unix - APPLE_EPOCH) * 1_000_000_000
    dst_cur = dst.cursor()

    # Determine which chats have any message in the filter window
    active_chat_ids = {
        r[0] for r in src.execute("""
            SELECT DISTINCT cmj.chat_id
            FROM chat_message_join cmj
            JOIN message m ON m.ROWID = cmj.message_id
            WHERE m.date >= ?
              AND COALESCE(m.is_spam, 0) = 0
              AND COALESCE(m.is_system_message, 0) = 0
              AND (m.text IS NULL OR length(m.text) > 0 OR COALESCE(m.cache_has_attachments, 0) = 1)
        """, (since_ns,)).fetchall()
    }

    # Migrate handles first (FK target for messages)
    n_handles = 0
    for r in src.execute("""
        SELECT ROWID, id, service, uncanonicalized_id, country
        FROM handle
    """).fetchall():
        h_rowid, h_id, service, uncid, country = r
        ext_id = f"handle:{h_rowid}"
        dst_cur.execute("""
            INSERT OR IGNORE INTO migrated_imessage_handles
                (external_id, handle_rowid, service, uncanonicalized_id, country, is_me_handle)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (ext_id, h_rowid, service, uncid, country))
        if dst_cur.rowcount > 0:
            n_handles += 1
    dst.commit()

    # Migrate active chats only
    n_chats = 0
    n_skipped = 0
    for r in src.execute("""
        SELECT ROWID, guid, service_name, style, display_name, chat_identifier,
               is_archived, last_read_message_timestamp
        FROM chat
    """).fetchall():
        chat_rowid, guid, svc, style, disp_name, chat_id, archived, last_read_ns = r
        if chat_rowid not in active_chat_ids:
            n_skipped += 1
            continue
        # Count messages in this chat that pass the filter
        n_msg = src.execute("""
            SELECT COUNT(*) FROM chat_message_join cmj
            JOIN message m ON m.ROWID = cmj.message_id
            WHERE cmj.chat_id = ? AND m.date >= ?
              AND COALESCE(m.is_spam, 0) = 0
              AND COALESCE(m.is_system_message, 0) = 0
              AND (m.text IS NULL OR length(m.text) > 0 OR COALESCE(m.cache_has_attachments, 0) = 1)
        """, (chat_rowid, since_ns)).fetchone()[0]
        ext_id = f"chat:{chat_rowid}"
        dst_cur.execute("""
            INSERT OR IGNORE INTO migrated_imessage_chats
                (external_id, chat_guid, service_name, style, display_name,
                 chat_identifier, is_archived, last_read_message_iso, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ext_id, guid, svc, style, disp_name, chat_id,
            archived, apple_ns_to_iso(last_read_ns), n_msg,
        ))
        if dst_cur.rowcount > 0:
            n_chats += 1
    dst.commit()
    return n_chats, n_skipped, n_handles


def migrate_messages(src: sqlite3.Connection, dst: sqlite3.Connection,
                     since_unix: int) -> int:
    since_ns = (since_unix - APPLE_EPOCH) * 1_000_000_000
    dst_cur = dst.cursor()

    # Pre-build chat_external_id map (must be inserted first; we did that)
    n_inserted = 0
    rows = src.execute("""
        SELECT m.ROWID, m.guid, cmj.chat_id, m.handle_id, m.is_from_me,
               m.text, m.date, m.date_read, m.date_delivered,
               COALESCE(m.is_empty, 0), COALESCE(m.is_read, 0),
               COALESCE(m.is_delivered, 0), COALESCE(m.is_audio_message, 0),
               COALESCE(m.is_archive, 0), COALESCE(m.cache_has_attachments, 0),
               m.service, m.item_type, m.associated_message_type
        FROM message m
        JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        WHERE m.date >= ?
          AND COALESCE(m.is_spam, 0) = 0
          AND COALESCE(m.is_system_message, 0) = 0
          AND (m.text IS NULL OR length(m.text) > 0 OR COALESCE(m.cache_has_attachments, 0) = 1)
        ORDER BY m.ROWID
    """, (since_ns,)).fetchall()

    for r in rows:
        (rowid, guid, chat_id, handle_id, is_from_me, text, date_ns, date_read_ns,
         date_delivered_ns, is_empty, is_read, is_delivered, is_audio, is_archive,
         has_attach, service, item_type, assoc_msg_type) = r

        ext_id = f"msg:{rowid}"
        chat_ext = f"chat:{chat_id}"
        handle_ext = f"handle:{handle_id}" if handle_id else None

        # Skip if chat wasn't migrated (inactive or doesn't pass filter)
        if not dst_cur.execute(
            "SELECT 1 FROM migrated_imessage_chats WHERE external_id = ?",
            (chat_ext,)
        ).fetchone():
            continue

        dst_cur.execute("""
            INSERT OR IGNORE INTO migrated_imessage_messages
                (external_id, msg_guid, chat_external_id, handle_external_id,
                 is_from_me, text, date_iso, date_raw_ns,
                 date_read_iso, date_delivered_iso,
                 is_empty, is_read, is_delivered, is_audio_message, is_archive,
                 has_attachments, service, item_type, associated_message_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ext_id, guid, chat_ext, handle_ext,
            is_from_me, text,
            apple_ns_to_iso(date_ns), date_ns,
            apple_ns_to_iso(date_read_ns), apple_ns_to_iso(date_delivered_ns),
            is_empty, is_read, is_delivered, is_audio, is_archive,
            has_attach, service, item_type, assoc_msg_type,
        ))
        if dst_cur.rowcount > 0:
            n_inserted += 1
        # commit every 1000
        if n_inserted % 1000 == 0 and n_inserted > 0:
            dst.commit()
    dst.commit()
    return n_inserted


def migrate_attachments(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # chat.db stores `attachment.filename` as a full path like:
    #   ~/Library/Messages/Attachments/d0/00/at_0_07BC.../IMG_1697.jpeg
    # About 9% of attachments still have files at that exact path. For the
    # other 91% the file has been moved/purged but the on-disk filename
    # (or transfer_name) may still match a file under Attachments/.
    # We try direct path first (fast), then fall back to a name index.
    print("  resolving local paths (direct + name index fallback)...")
    home = Path.home()
    attach_dir = home / "Library" / "Messages" / "Attachments"

    # Build name index: filename -> path (one rglob, cached)
    print("    building name index (one rglob over Attachments dir)...")
    name_index: dict[str, str] = {}
    if attach_dir.exists():
        for p in attach_dir.rglob("*"):
            if p.is_file() and p.name not in name_index:
                name_index[p.name] = str(p)

    dst_cur = dst.cursor()
    n_inserted = 0
    n_resolved = 0
    rows = src.execute("""
        SELECT a.ROWID, a.guid, a.filename, a.mime_type, a.total_bytes,
               a.uti, COALESCE(a.is_sticker, 0), COALESCE(a.is_outgoing, 0),
               a.transfer_name, maj.message_id
        FROM attachment a
        JOIN message_attachment_join maj ON maj.attachment_id = a.ROWID
    """).fetchall()

    for r in rows:
        (aroid, aguid, fname, mime, bsize, uti, is_sticker, is_outgoing,
         transfer_name, msg_id) = r
        msg_ext = f"msg:{msg_id}"
        if not dst_cur.execute(
            "SELECT 1 FROM migrated_imessage_messages WHERE external_id = ?",
            (msg_ext,)
        ).fetchone():
            continue
        ext_id = f"attach:{aroid}"
        # 1) Direct path from chat.db
        local_path = None
        if fname and fname.startswith("~"):
            cand = home / fname[2:]
            if cand.exists():
                local_path = str(cand)
        elif fname and fname.startswith("/") and Path(fname).exists():
            local_path = fname
        # 2) Fallback: name index
        if not local_path and transfer_name and transfer_name in name_index:
            local_path = name_index[transfer_name]
        elif not local_path and fname:
            # Try the basename of the path
            base = fname.rsplit("/", 1)[-1]
            if base in name_index:
                local_path = name_index[base]
        if local_path:
            n_resolved += 1
        dst_cur.execute("""
            INSERT OR IGNORE INTO migrated_imessage_attachments
                (external_id, msg_external_id, attach_guid, filename, mime_type,
                 byte_size, uti, is_sticker, is_outgoing, local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ext_id, msg_ext, aguid, fname, mime, bsize, uti,
            is_sticker, is_outgoing, local_path,
        ))
        if dst_cur.rowcount > 0:
            n_inserted += 1
        if n_inserted % 1000 == 0 and n_inserted > 0:
            dst.commit()
    dst.commit()
    print(f"  resolved {n_resolved:,} / {n_inserted:,} local paths")
    return n_inserted


def report(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    print()
    print("=== migrated_imessage_* counts ===")
    for tbl in ['migrated_imessage_chats', 'migrated_imessage_handles',
                'migrated_imessage_messages', 'migrated_imessage_attachments']:
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:36s}  {n:>7,}")

    # Sanity: orphan messages (chat_external_id not in chats)
    n = cur.execute("""
        SELECT COUNT(*) FROM migrated_imessage_messages m
        WHERE NOT EXISTS (SELECT 1 FROM migrated_imessage_chats c
                          WHERE c.external_id = m.chat_external_id)
    """).fetchone()[0]
    print(f"  orphan messages (no chat):                     {n}")

    # Sanity: orphan attachments
    n = cur.execute("""
        SELECT COUNT(*) FROM migrated_imessage_attachments a
        WHERE NOT EXISTS (SELECT 1 FROM migrated_imessage_messages m
                          WHERE m.external_id = a.msg_external_id)
    """).fetchone()[0]
    print(f"  orphan attachments (no message):               {n}")

    # Service distribution
    print()
    print("=== service distribution ===")
    for r in cur.execute("""
        SELECT service_name, COUNT(*) FROM migrated_imessage_chats GROUP BY service_name
    """).fetchall():
        print(f"  chats: {r[0] or 'NULL':15s}  {r[1]:>5,}")
    for r in cur.execute("""
        SELECT service, COUNT(*) FROM migrated_imessage_messages GROUP BY service
    """).fetchall():
        print(f"  msgs:  {r[0] or 'NULL':15s}  {r[1]:>7,}")

    # Date range
    print()
    print("=== date range (migrated_imessage_messages) ===")
    r = cur.execute("SELECT MIN(date_iso), MAX(date_iso) FROM migrated_imessage_messages").fetchone()
    print(f"  {r[0]}  →  {r[1]}")

    # has_text breakdown
    print()
    print("=== messages by is_from_me / has_text ===")
    for r in cur.execute("""
        SELECT
            is_from_me,
            SUM(CASE WHEN text IS NOT NULL AND length(text)>0 THEN 1 ELSE 0 END) as has_text,
            SUM(CASE WHEN is_empty=1 OR (text IS NULL OR length(text)=0) THEN 1 ELSE 0 END) as empty,
            COUNT(*) as total
        FROM migrated_imessage_messages GROUP BY is_from_me
    """).fetchall():
        print(f"  from_me={r[0]}  has_text={r[1]:>6,}  empty={r[2]:>6,}  total={r[3]:>6,}")

    # Attachment local_path resolution rate
    n_total = cur.execute("SELECT COUNT(*) FROM migrated_imessage_attachments").fetchone()[0]
    n_resolved = cur.execute(
        "SELECT COUNT(*) FROM migrated_imessage_attachments WHERE local_path IS NOT NULL"
    ).fetchone()[0]
    if n_total:
        print()
        print(f"=== attachment local_path resolution: {n_resolved:,} / {n_total:,} ({100*n_resolved/n_total:.1f}%) ===")


def main() -> int:
    p = argparse.ArgumentParser()
    add_common_args(p)
    p.add_argument('--since', default='2025-04-01',
                   help='ISO date (UTC) — Apr 2025+ default per extract_sessions.py s8')
    args = p.parse_args()

    since_dt = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    since_unix = int(since_dt.timestamp())
    print(f"db: {args.db}")
    print(f"chat.db: {CHAT_DB}  ({CHAT_DB.stat().st_size:,} bytes)")
    print(f"since: {args.since}  (unix {since_unix})")

    # guard_and_connect combines guard_write_target + sqlite3.connect in the
    # canonical order (guard first, then connect). Pragmas reproduce the
    # pre-refactor settings.
    src = open_source()
    dst = guard_and_connect(
        args.db, args.allow_canonical,
        pragmas=["journal_mode = WAL", "foreign_keys = ON"],
    )

    try:
        # Register the imessage source (idempotent via WHERE NOT EXISTS on base)
        register_source(
            dst,
            kind="imessage",
            base_path=str(CHAT_DB),
            captured_at=datetime.now(timezone.utc).isoformat(),
            byte_size=CHAT_DB.stat().st_size,
            schema_version="v1.0",
            notes="Apr 2025+ filter; empty/system/spam excluded; ns-precision date preserved as date_raw_ns",
        )
        src_id = dst.execute("SELECT id FROM sources WHERE kind = 'imessage'").fetchone()[0]
        print(f"source id: {src_id} (kind=imessage)")

        print()
        print("--- migrating chats + handles ---")
        n_chats, n_skip, n_handles = migrate_chats(src, dst, since_unix, src_id)
        print(f"  chats inserted: {n_chats}  (skipped {n_skip} inactive)")
        print(f"  handles inserted: {n_handles}")

        print()
        print("--- migrating messages ---")
        n_msg = migrate_messages(src, dst, since_unix)
        print(f"  messages inserted: {n_msg:,}")

        print()
        print("--- migrating attachments ---")
        n_attach = migrate_attachments(src, dst)
        print(f"  attachments inserted: {n_attach:,}")

        report(dst)
    finally:
        src.close()
        dst.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
