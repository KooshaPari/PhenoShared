"""
W9e: cursor (Cursor IDE) → migrated_cursor_chats + migrated_cursor_messages

Reads from ~/.cursor/chats/<hash>/<chat-uuid>/ and inserts into research_ledger.

Format:
  - 5 chat-hash directories
  - Each chat is a subdirectory containing:
    - meta.json (createdAtMs, updatedAtMs, isSubagent, cwd, ...)
    - store.db (sqlite with single 'blobs' table: id TEXT PK, data BLOB)
  - blobs.data is JSON: {role, content} or {role, content, tool_calls, ...}

Scope:
  - 707 chats, 253,410 blobs total
  - 93% are sub-agents (isSubagent=true)
  - Date range: 2026-07-17 to 2026-10-14
  - Single biggest chat: 25,632 blobs

Idempotent: INSERT OR IGNORE on UNIQUE external_id.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, register_source

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
DEFAULT_CURSOR_ROOT = Path.home() / ".cursor" / "chats"

MODEL_RE = re.compile(r"You are ([A-Za-z0-9\.\- ]+?)(?:\.|\\n|\\r|$)")


def extract_model(content: str) -> str | None:
    """Extract model name from system prompt like 'You are GPT-5.6 Luna.'"""
    if not content:
        return None
    m = MODEL_RE.search(content[:1000])
    if m:
        return m.group(1).strip()[:100]
    return None


def discover_chats(cursor_root: Path) -> list[dict]:
    """Find all chat dirs (each with meta.json + store.db)."""
    chats = []
    if not cursor_root.exists():
        return chats
    for hash_dir in sorted(cursor_root.iterdir()):
        if not hash_dir.is_dir():
            continue
        for chat_dir in sorted(hash_dir.iterdir()):
            if not chat_dir.is_dir():
                continue
            store_db = chat_dir / "store.db"
            meta_json = chat_dir / "meta.json"
            if not store_db.exists() or not meta_json.exists():
                continue
            chats.append({
                "chat_dir": chat_dir,
                "store_db": store_db,
                "meta_json": meta_json,
                "chat_hash": hash_dir.name,
                "chat_uuid": chat_dir.name,
            })
    return chats


def read_meta(meta_path: Path) -> dict:
    try:
        return json.load(open(meta_path))
    except Exception:
        return {}


def read_blobs(store_db_path: Path) -> list[tuple[str, dict, bool]]:
    """Read all blobs from a chat's store.db.

    Returns (id, parsed_dict, is_raw_text) tuples.
    is_raw_text=True means the blob had a binary prefix and is raw text,
    not JSON.
    """
    try:
        # open in read-only mode
        uri = f"file:{store_db_path}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        rows = db.execute("SELECT id, data FROM blobs").fetchall()
        db.close()
    except Exception as e:
        print(f"    WARN: failed to read {store_db_path}: {e}")
        return []
    result = []
    for blob_id, data in rows:
        # Try JSON first
        try:
            d = json.loads(data)
            result.append((blob_id, d, False))
            continue
        except Exception:
            pass
        # Not JSON -- it's a raw text blob (cursor's binary-prefixed format)
        # Try to extract the text after the binary header
        # Pattern: \n<one byte> + 32 hex chars (16 bytes hash) + \n + text
        # The first \x00 byte marks the end of the header
        try:
            # Skip initial \n + length byte
            text = data
            if data.startswith(b"\n"):
                # find first \x00 or first printable run
                nul_idx = data.find(b"\x00")
                if nul_idx > 0 and nul_idx < 100:
                    text = data[nul_idx + 1:]
                else:
                    # try to find where text starts (usually \n followed by printable)
                    for i in range(1, min(len(data), 200)):
                        if data[i:i+1].isalpha() or data[i:i+1] in (b" ", b"-"):
                            text = data[i:]
                            break
            text_str = text.decode("utf-8", errors="replace").strip()
            # Heuristic: raw text blobs are USER messages
            d = {"role": "user", "content": text_str, "_is_raw": True}
            result.append((blob_id, d, True))
        except Exception:
            d = {"_raw": data.decode("utf-8", errors="replace")}
            result.append((blob_id, d, True))
    return result


def migrate_one(chat: dict, db_path: Path) -> tuple[bool, int]:
    """Migrate one chat. Returns (chat_inserted, msg_count)."""
    chat_uuid = chat["chat_uuid"]
    chat_hash = chat["chat_hash"]
    chat_dir = chat["chat_dir"]

    db = sqlite3.connect(db_path)
    try:
        c = db.cursor()
        chat_ext_id = f"cursor_chat:{chat_uuid}"

        # Read meta
        meta = read_meta(chat["meta_json"])
        meta_json_str = json.dumps(meta, ensure_ascii=False)

        # Read blobs
        blobs = read_blobs(chat["store_db"])
        if not blobs:
            # skip empty chats
            return (False, 0)

        # Extract model from first system blob
        model = None
        for _, d, _ in blobs:
            if d.get("role") == "system":
                model = extract_model(str(d.get("content", "")))
                if model:
                    break

        # Try to insert chat row
        try:
            c.execute(
                """
                INSERT OR IGNORE INTO migrated_cursor_chats (
                    external_id, chat_uuid, chat_hash, created_at_ms, updated_at_ms,
                    cwd, is_subagent, has_conversation, schema_version, chat_blob_count,
                    model, source_path, meta_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    chat_ext_id,
                    chat_uuid,
                    chat_hash,
                    meta.get("createdAtMs"),
                    meta.get("updatedAtMs"),
                    meta.get("cwd"),
                    1 if meta.get("isSubagent") else 0,
                    1 if meta.get("hasConversation") else 0,
                    meta.get("schemaVersion", 1),
                    len(blobs),
                    model,
                    str(chat_dir),
                    meta_json_str,
                ),
            )
            chat_inserted = c.execute("SELECT changes()").fetchone()[0] > 0
        except Exception as e:
            print(f"    WARN: chat insert failed for {chat_uuid}: {e}")
            return (False, 0)

        # Check if messages already exist
        existing = c.execute(
            "SELECT COUNT(*) FROM migrated_cursor_messages WHERE chat_external_id = ?",
            (chat_ext_id,),
        ).fetchone()[0]
        if existing == len(blobs):
            return (chat_inserted, 0)  # already fully migrated

        # Insert messages
        msg_count = 0
        chat_created_ms = meta.get("createdAtMs")
        for ordinal, (blob_id, d, is_raw) in enumerate(blobs):
            msg_ext_id = f"cursor_msg:{chat_uuid}:{blob_id}"
            role = d.get("role", "unknown")
            content = d.get("content", "")
            if isinstance(content, list):
                # Cursor sometimes has content as list of blocks
                content = "\n".join(
                    (b.get("text", "") if isinstance(b, dict) else str(b))
                    for b in content
                )
            content_text = str(content) if content else ""

            has_tc = 1 if d.get("tool_calls") else 0
            tc_names = ""
            if d.get("tool_calls"):
                tc_names = ",".join(
                    (tc.get("function", {}).get("name", "?") if isinstance(tc, dict) else "?")
                    for tc in d["tool_calls"]
                )

            try:
                c.execute(
                    """
                    INSERT OR IGNORE INTO migrated_cursor_messages (
                        external_id, chat_external_id, chat_uuid, blob_id,
                        ordinal, role, content_text, content_length,
                        content_json, has_tool_calls, tool_call_names,
                        blob_index, chat_created_at_ms
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        msg_ext_id,
                        chat_ext_id,
                        chat_uuid,
                        blob_id,
                        ordinal,
                        role,
                        content_text,
                        len(content_text),
                        json.dumps(d, ensure_ascii=False),
                        has_tc,
                        tc_names,
                        ordinal,
                        chat_created_ms,
                    ),
                )
                if c.execute("SELECT changes()").fetchone()[0] > 0:
                    msg_count += 1
            except Exception as e:
                pass  # silent for individual msg failures
        return (chat_inserted, msg_count)
    finally:
        db.commit()
        db.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    add_common_args(p)
    p.add_argument("--src", default=str(DEFAULT_CURSOR_ROOT))
    args = p.parse_args(argv)

    cursor_root = Path(args.src)
    db_path = Path(args.db)

    print(f"W9e: cursor → migrated_cursor_*")
    print(f"  src: {cursor_root}")
    print(f"  db:  {db_path}")
    print()

    chats = discover_chats(cursor_root)
    print(f"discovered {len(chats):,} chats")

    # Compute total size for the source row
    total_size = sum(p.stat().st_size for cd in chats for p in cd["chat_dir"].iterdir() if p.is_file())

    # guard_and_connect combines guard_write_target + sqlite3.connect in the
    # canonical order (guard first, then connect). Migrate-one's internal
    # sqlite3.connect is path-level, not connection-level, so it can keep
    # using its own connection.
    db = guard_and_connect(db_path, args.allow_canonical, pragmas=None)
    try:
        # Pre-register source row
        register_source(
            db,
            kind="cursor",
            base_path=str(cursor_root),
            captured_at="2026-10-15T07:30:00Z",
            byte_size=total_size,
            schema_version="v1.0",
            notes="cursor passthrough from ~/.cursor/chats/<hash>/<chat-uuid>/ (707 chats, 253K blobs, 93% sub-agents)",
        )
        db.commit()
    finally:
        db.close()

    chat_inserted = 0
    chat_skipped = 0
    msg_inserted = 0
    chats_with_msgs = 0
    failed = 0

    for i, chat in enumerate(chats):
        try:
            ci, mi = migrate_one(chat, db_path)
            if ci:
                chat_inserted += 1
            else:
                chat_skipped += 1
            if mi > 0:
                msg_inserted += mi
                chats_with_msgs += 1
        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"  WARN: chat {chat['chat_uuid']} failed: {e}")

        if (i + 1) % 50 == 0:
            print(f"  ... {i+1:,}/{len(chats):,} chats ({chat_inserted:,} new, {msg_inserted:,} msgs)")

    # Final stats
    db = sqlite3.connect(db_path)
    try:
        c = db.cursor()
        total_chats = c.execute("SELECT COUNT(*) FROM migrated_cursor_chats").fetchone()[0]
        total_msgs = c.execute("SELECT COUNT(*) FROM migrated_cursor_messages").fetchone()[0]
        by_role = c.execute(
            "SELECT role, COUNT(*) FROM migrated_cursor_messages GROUP BY role ORDER BY 2 DESC"
        ).fetchall()
        by_hash = c.execute(
            "SELECT chat_hash, COUNT(*) FROM migrated_cursor_chats GROUP BY chat_hash ORDER BY 2 DESC"
        ).fetchall()
        sub_count = c.execute("SELECT COUNT(*) FROM migrated_cursor_chats WHERE is_subagent = 1").fetchone()[0]
        has_cwd = c.execute("SELECT COUNT(*) FROM migrated_cursor_chats WHERE cwd IS NOT NULL").fetchone()[0]
        date_range = c.execute(
            "SELECT MIN(datetime(created_at_ms/1000, 'unixepoch')), MAX(datetime(created_at_ms/1000, 'unixepoch')) FROM migrated_cursor_chats"
        ).fetchone()
    finally:
        db.close()

    print()
    print("=== Result ===")
    print(f"  chats discovered:    {len(chats):,}")
    print(f"  chat_inserted:       {chat_inserted:,}")
    print(f"  chat_skipped:        {chat_skipped:,}")
    print(f"  msg_inserted:        {msg_inserted:,}")
    print(f"  failed:              {failed:,}")
    print()
    print(f"  Total in db: {total_chats:,} chats, {total_msgs:,} msgs")
    print(f"  Sub-agents:  {sub_count:,} / {total_chats:,} ({sub_count*100//max(1,total_chats)}%)")
    print(f"  Has cwd:     {has_cwd:,} / {total_chats:,}")
    print(f"  Date range:  {date_range[0]} → {date_range[1]}")
    print()
    print("by role:")
    for role, n in by_role:
        print(f"  {role:10s} {n:,}")
    print()
    print("by chat_hash:")
    for h, n in by_hash:
        print(f"  {h:10s} {n:,} chats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
