#!/usr/bin/env python3
"""
import_chatgpt_export.py — round-5 W5-2: openai ChatGPT data export → ledger.

Reads ~/Downloads/conversations.json (or a path passed via --export) and
populates openai_chatgpt_conversations + openai_chatgpt_messages. Idempotent
(REPLACE on uuid). message.text is truncated to 4 KiB per the schema
contract in ledger_db.py; full structured content (tool_use/tool_result/
thinking) is preserved as JSON for forensic use.

Privacy:
  The export contains user/assistant message text. We do NOT redact by
  default because the export is the operator's own data export from
  openai.com. To redact, pass --redact-text which substitutes the text
  with "(redacted: see source_path)".

Usage:
  python3 import_chatgpt_export.py                   # default path
  python3 import_chatgpt_export.py --export <PATH>   # custom path
  python3 import_chatgpt_export.py --redact-text     # privacy mode
  python3 import_chatgpt_export.py --dry-run         # parse only, no writes
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add this dir to sys.path so we can import ledger_db
sys.path.insert(0, str(Path(__file__).parent))
from ledger_db import (
    open_db,
    insert_chatgpt_conversation,
    insert_chatgpt_message,
    insert_chatgpt_file,
    insert_chatgpt_attachment_content,
    insert_chatgpt_tool_result,
)


DEFAULT_EXPORT = os.path.expanduser("~/Downloads/conversations.json")
DEFAULT_LEDGER = os.path.expanduser("~/Exports/analysis/session_ledger.sqlite")
TEXT_TRUNCATE_BYTES = 4096  # 4 KiB cap on message.text per the schema


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def truncate_text(s: str, max_bytes: int) -> str:
    """Truncate a string to <= max_bytes (UTF-8). Append a marker if cut."""
    if not s:
        return s
    enc = s.encode("utf-8")
    if len(enc) <= max_bytes:
        return s
    cut = enc[: max_bytes - 32].decode("utf-8", errors="ignore")
    return cut + f"... [truncated to {max_bytes} bytes]"


def ingest(export_path: str, ledger_path: str, redact_text: bool = False,
           dry_run: bool = False, truncate_first: bool = False) -> dict:
    """Ingest the export. Returns a stats dict."""
    if not os.path.isfile(export_path):
        raise FileNotFoundError(f"export not found: {export_path}")

    file_size = os.path.getsize(export_path)
    file_mtime = datetime.fromtimestamp(os.path.getmtime(export_path), tz=timezone.utc).isoformat()
    print(f"[import_chatgpt_export] reading {export_path} ({file_size:,} bytes, mtime {file_mtime})")
    t0 = time.time()
    with open(export_path) as f:
        data = json.load(f)
    parse_secs = time.time() - t0
    print(f"[import_chatgpt_export] parsed in {parse_secs:.2f}s: {len(data):,} conversations")

    if not isinstance(data, list):
        raise ValueError(f"expected list, got {type(data).__name__}")

    if dry_run:
        # Sample the first few to confirm structure
        n_msgs = sum(len(c.get("chat_messages", [])) for c in data)
        print(f"[dry-run] would insert {len(data):,} conversations, {n_msgs:,} messages")
        return {
            "conversations": len(data),
            "messages": n_msgs,
            "dry_run": True,
        }

    ingested_at = now_iso()
    n_conv = 0
    n_msg = 0
    n_files = 0
    n_attcontent = 0
    n_tool_results = 0
    errors = []

    conn = open_db(ledger_path)
    try:
        # W6-3: --truncate-first support. When set, DELETE existing chatgpt
        # rows before ingest so the new file becomes the source of truth
        # (idempotent replace-from-scratch). Uses DELETE not TRUNCATE so
        # WAL-mode journal is preserved and indexes stay consistent. Order
        # is messages first (no FK to delete, but child-first is conventional)
        # then conversations. After DELETE the next INSERT OR REPLACE
        # proceeds as usual.
        if truncate_first:
            n_existing_msg = conn.execute(
                "SELECT COUNT(*) FROM openai_chatgpt_messages"
            ).fetchone()[0]
            n_existing_conv = conn.execute(
                "SELECT COUNT(*) FROM openai_chatgpt_conversations"
            ).fetchone()[0]
            # W7-2.3-2.6: the three child tables must be cleared too,
            # in child-first order (grandchildren before parents).
            conn.execute("DELETE FROM openai_chatgpt_tool_results")
            conn.execute("DELETE FROM openai_chatgpt_attachment_content")
            conn.execute("DELETE FROM openai_chatgpt_files")
            conn.execute("DELETE FROM openai_chatgpt_messages")
            conn.execute("DELETE FROM openai_chatgpt_conversations")
            print(f"[import_chatgpt_export] truncate-first: deleted "
                  f"{n_existing_msg:,} messages + {n_existing_conv:,} conversations "
                  f"(+ files/attachment_content/tool_results child rows)")
        for c in data:
            cuuid = c.get("uuid")
            if not cuuid:
                errors.append(f"conv missing uuid: {c.get('name', '?')[:40]}")
                continue

            msgs = c.get("chat_messages", [])
            insert_chatgpt_conversation(conn,
                uuid=cuuid,
                name=c.get("name"),
                summary=c.get("summary"),
                created_at=c.get("created_at"),
                updated_at=c.get("updated_at"),
                account_uuid=c.get("account", {}).get("uuid") if isinstance(c.get("account"), dict) else None,
                n_messages=len(msgs),
                source_path=export_path,
                ingested_at=ingested_at,
            )
            n_conv += 1

            for m in msgs:
                muuid = m.get("uuid")
                if not muuid:
                    errors.append(f"msg missing uuid in conv {cuuid[:8]}")
                    continue
                content = m.get("content", []) or []
                files = m.get("files", []) or []
                attachments = m.get("attachments", []) or []
                text = m.get("text") or ""
                if redact_text and text:
                    text = "(redacted: see source_path)"
                text = truncate_text(text, TEXT_TRUNCATE_BYTES)
                insert_chatgpt_message(conn,
                    uuid=muuid,
                    conversation_uuid=cuuid,
                    sender=m.get("sender", "unknown"),
                    text=text,
                    content_json=json.dumps(content, ensure_ascii=False) if content else None,
                    n_content_items=len(content),
                    has_attachments=1 if attachments else 0,
                    n_attachments=len(attachments),
                    has_files=1 if files else 0,
                    n_files=len(files),
                    parent_message_uuid=m.get("parent_message_uuid"),
                    created_at=m.get("created_at"),
                    updated_at=m.get("updated_at"),
                    source_path=export_path,
                    ingested_at=ingested_at,
                )
                n_msg += 1

                # Round-7 (W7-2.3-2.6): extract the three previously-dropped
                # child arrays. Each row carries (msg_uuid, conversation_uuid)
                # for join-free filtering plus the ledger provenance columns.
                for f_item in files:
                    fuuid = f_item.get("file_uuid")
                    if not fuuid:
                        continue  # files without uuid carry no link value
                    insert_chatgpt_file(
                        conn,
                        msg_uuid=muuid,
                        conversation_uuid=cuuid,
                        file_uuid=fuuid,
                        file_name=f_item.get("file_name"),
                        source_path=export_path,
                        ingested_at=ingested_at,
                    )
                    n_files += 1

                for a in attachments:
                    # attachments[] have no uuid; keyed by (msg_uuid, file_name)
                    # per the schema. extracted_content is stored FULL (no
                    # truncation) — it is the searchable pasted-code history.
                    ec = a.get("extracted_content")
                    if ec is None and not a.get("file_name"):
                        continue  # nothing to store
                    insert_chatgpt_attachment_content(
                        conn,
                        msg_uuid=muuid,
                        conversation_uuid=cuuid,
                        file_name=a.get("file_name"),
                        file_size=a.get("file_size"),
                        file_type=a.get("file_type"),
                        extracted_content=ec,
                        content_len=len(ec) if isinstance(ec, str) else 0,
                        source_path=export_path,
                        ingested_at=ingested_at,
                    )
                    n_attcontent += 1

                # tool_result blocks live inside content[]; block_index is the
                # position in the content array so (msg_uuid, block_index) is
                # stable and idempotent across re-ingests of the same export.
                for idx, item in enumerate(content):
                    if not isinstance(item, dict) or item.get("type") != "tool_result":
                        continue
                    c_payload = item.get("content")
                    c_json = json.dumps(c_payload, ensure_ascii=False) if c_payload is not None else None
                    insert_chatgpt_tool_result(
                        conn,
                        msg_uuid=muuid,
                        conversation_uuid=cuuid,
                        block_index=idx,
                        name=item.get("name"),
                        tool_use_id=item.get("tool_use_id"),
                        is_error=1 if item.get("is_error") else 0,
                        content_json=c_json,
                        content_len=len(c_json) if c_json else 0,
                        source_path=export_path,
                        ingested_at=ingested_at,
                    )
                    n_tool_results += 1

        conn.commit()
    finally:
        conn.close()

    elapsed = time.time() - t0
    stats = {
        "conversations_inserted": n_conv,
        "messages_inserted": n_msg,
        "files_inserted": n_files,
        "attachment_content_inserted": n_attcontent,
        "tool_results_inserted": n_tool_results,
        "errors": len(errors),
        "first_errors": errors[:5],
        "elapsed_secs": round(elapsed, 2),
        "ingested_at": ingested_at,
        "source_path": export_path,
        "source_size_bytes": file_size,
        "truncate_first": truncate_first,
    }
    print(f"[import_chatgpt_export] inserted {n_conv:,} conversations, {n_msg:,} messages, "
          f"{n_files:,} files, {n_attcontent:,} attachment_content, {n_tool_results:,} tool_results in {elapsed:.2f}s")
    if errors:
        print(f"[import_chatgpt_export] {len(errors)} errors; first: {errors[:3]}")
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", default=DEFAULT_EXPORT, help="path to conversations.json")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER, help="path to ledger sqlite")
    ap.add_argument("--redact-text", action="store_true", help="replace message text with placeholder")
    ap.add_argument("--dry-run", action="store_true", help="parse but don't write")
    ap.add_argument("--truncate-first", action="store_true",
                    help="DELETE existing chatgpt rows before ingest (use to "
                         "shrink-to-fit the ledger to the current export file)")
    args = ap.parse_args()
    stats = ingest(args.export, args.ledger, redact_text=args.redact_text,
                   dry_run=args.dry_run, truncate_first=args.truncate_first)
    if not args.dry_run:
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
