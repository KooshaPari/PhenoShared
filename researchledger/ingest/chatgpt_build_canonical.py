"""
chatgpt_build_canonical.py — Pump migrated_openai_chatgpt_* passthrough tables
into the canonical research_ledger tables (items, attachments).

Applies the §4.3 provenance policy to every row:
  source_id=1, evidence_type=direct, confidence=high, redaction_state=partial
  (messages may contain personal data, so partial is honest)

Item kinds produced:
  - conversation: one per migrated_openai_chatgpt_conversations row
  - message:      one per migrated_openai_chatgpt_messages row, parent=conversation
  - tool_result:  one per migrated_openai_chatgpt_tool_results row, parent=message

Attachment kinds produced:
  - file (extracted_content)  one per migrated_openai_chatgpt_attachment_content row
                              attached to the message it belongs to

Message body extraction (chatgpt-specific):
  migrated_openai_chatgpt_messages.content_json is always a JSON list of parts;
  each part has type='text'|'code' etc with a 'text' field. We concatenate all
  text-bearing parts into the items.body column so FTS5 searches the prose.

Idempotent: every insert uses (source_id, external_id) uniqueness, so re-runs
are safe (the unique index handles it).

Usage:
    python3 chatgpt_build_canonical.py
    python3 chatgpt_build_canonical.py --dry-run
    python3 chatgpt_build_canonical.py --research PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
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
DEFAULT_RESEARCH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"

CHATGPT_SOURCE_ID = 1  # matches the row in `sources` registered by chatgpt_migrate_to_research.py

DEFAULT_REDACTION_STATE = "partial"  # messages may contain personal data → honest default


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(s: str | None, n: int = 16) -> str | None:
    if not s:
        return None
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:n]


def extract_text_from_content_json(content_json: str | None, text: str | None) -> str:
    """Extract plain text from a chatgpt content_json blob.

    chatgpt stores message body as either:
      - a list of parts (each with type='text'|'code' and a 'text' field)
      - a dict with similar structure
      - a plain JSON string
      - the legacy `text` column (when present, prefer it)
    """
    if text and text.strip():
        return text
    if not content_json or not content_json.strip():
        return ""
    try:
        parsed = json.loads(content_json)
    except (ValueError, TypeError):
        # Plain string content
        return content_json
    parts: list[str] = []
    if isinstance(parsed, list):
        for p in parsed:
            if isinstance(p, dict):
                # text/code/asset_pointer/etc
                for key in ("text", "caption", "transcript"):
                    v = p.get(key)
                    if isinstance(v, str) and v.strip():
                        parts.append(v)
    elif isinstance(parsed, dict):
        for key in ("text", "caption", "transcript"):
            v = parsed.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(v)
    return "\n".join(parts)


def build_conversations(dst: sqlite3.Connection) -> int:
    """One item per conversation (item_kind='conversation')."""
    rows = dst.execute("""
        SELECT external_id, title, summary, created_at, updated_at, n_messages
        FROM migrated_openai_chatgpt_conversations
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'chatgpt_conversation',
                ?, ?, json_object('summary', ?, 'n_messages', ?, 'platform', 'chatgpt'))
    """
    n = 0
    captured = now_iso()
    for r in rows:
        ext, title, summary, created_at, updated_at, n_msgs = r
        dst.execute(sql, (
            CHATGPT_SOURCE_ID, ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            title,
            summary or "",  # body = summary if no message body
            summary, n_msgs,
        ))
        n += 1
    return n


def build_messages(dst: sqlite3.Connection) -> int:
    """One item per message (item_kind='message'), parent=conversation."""
    rows = dst.execute("""
        SELECT m.conversation_external_id, m.message_external_id, m.author, m.role,
               m.created_at, m.content_type, m.content_text, m.content_json,
               m.parent_message_uuid
        FROM migrated_openai_chatgpt_messages m
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, author, title, body, parent_id, dedupe_hash,
             attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'chatgpt_message',
                ?, ?, ?, ?, ?,
                json_object('role', ?, 'content_type', ?, 'platform', 'chatgpt'))
    """
    n = 0
    captured = now_iso()
    # Build a conv_external_id -> conv_id map (one query, in memory)
    conv_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='chatgpt_conversation'",
        (CHATGPT_SOURCE_ID,)).fetchall()}
    for r in rows:
        conv_ext, msg_ext, author, role, created_at, ctype, text, cjson, parent_uuid = r
        parent_id = conv_map.get(conv_ext)
        body = extract_text_from_content_json(cjson, text)
        # dedupe_hash: conversation + message uuid (stable)
        dh = sha256_hex(f"{conv_ext}:{msg_ext}")
        dst.execute(sql, (
            CHATGPT_SOURCE_ID, msg_ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            author,            # title = author
            None,              # no title for messages
            body,              # body = extracted text from content_json
            parent_id,         # parent = conversation
            dh,
            role, ctype,
        ))
        n += 1
    return n


def build_tool_results(dst: sqlite3.Connection) -> int:
    """One item per tool_result (item_kind='tool_result'), parent=message."""
    rows = dst.execute("""
        SELECT message_external_id, conversation_external_id, block_index, name,
               tool_call_id, is_error, content_json, content_len
        FROM migrated_openai_chatgpt_tool_results
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, author, title, body, parent_id, dedupe_hash,
             attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'chatgpt_tool_result',
                ?, ?, ?, ?, ?,
                json_object('tool_name', ?, 'is_error', ?, 'block_index', ?,
                            'conversation_external_id', ?, 'platform', 'chatgpt'))
    """
    n = 0
    captured = now_iso()
    msg_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='chatgpt_message'",
        (CHATGPT_SOURCE_ID,)).fetchall()}
    for r in rows:
        msg_ext, conv_ext, block_index, name, tool_call_id, is_error, cjson, content_len = r
        parent_id = msg_map.get(msg_ext)
        # external_id: tool_use_id if present, else msg_ext:tool_call_id, else msg_ext:block_index
        ext = tool_call_id or f"{msg_ext}:{block_index}"
        body = cjson or ""
        dh = sha256_hex(f"tool_result:{ext}")
        dst.execute(sql, (
            CHATGPT_SOURCE_ID, ext, captured, None,  # source_captured_at: unknown
            DEFAULT_REDACTION_STATE,
            "tool",         # author
            name,           # title = tool name
            body,           # body = content_json
            parent_id,
            dh,
            name, is_error, block_index, conv_ext,
        ))
        n += 1
    return n


def build_files_attachments(dst: sqlite3.Connection) -> int:
    """One attachment per attachment_content row, attached to its message."""
    # attachment_content table is keyed by msg_external_id + file_name
    rows = dst.execute("""
        SELECT a.msg_external_id, a.conversation_external_id, a.file_name,
               a.file_size, a.file_type, a.extracted_content, a.content_len
        FROM migrated_openai_chatgpt_attachment_content a
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO attachments
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_id, kind, byte_size, mime_type, extracted_text)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, ?, 'file', ?, ?, ?)
    """
    n = 0
    captured = now_iso()
    msg_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='chatgpt_message'",
        (CHATGPT_SOURCE_ID,)).fetchall()}
    for r in rows:
        msg_ext, conv_ext, file_name, file_size, file_type, content, content_len = r
        item_id = msg_map.get(msg_ext)
        # external_id: msg + file_name (natural key)
        ext = f"{msg_ext}:{file_name}:{content_len}"
        dst.execute(sql, (
            CHATGPT_SOURCE_ID, ext, captured, None,
            DEFAULT_REDACTION_STATE,
            item_id,
            file_size,
            file_type,
            content,
        ))
        n += 1
    return n


PHASE_FNS = {
    "conversations": build_conversations,
    "messages": build_messages,
    "tool_results": build_tool_results,
    "files_attachments": build_files_attachments,
}


def validate(dst: sqlite3.Connection) -> dict:
    out = {}
    for kind in ("chatgpt_conversation", "chatgpt_message", "chatgpt_tool_result"):
        n = dst.execute(
            "SELECT COUNT(*) FROM items WHERE source_id=? AND item_kind=?",
            (CHATGPT_SOURCE_ID, kind)).fetchone()[0]
        out[f"items:{kind}"] = n
    n = dst.execute(
        "SELECT COUNT(*) FROM attachments WHERE source_id=?",
        (CHATGPT_SOURCE_ID,)).fetchone()[0]
    out["attachments:file"] = n

    # FTS5 sanity
    fts_match = dst.execute(
        "SELECT COUNT(*) FROM items_fts WHERE items_fts MATCH 'test' OR items_fts MATCH 'chatgpt'"
    ).fetchone()[0]
    out["items_fts:test_or_chatgpt"] = fts_match

    # Provenance completeness
    n_missing_provenance = dst.execute(f"""
        SELECT COUNT(*) FROM items
        WHERE source_id={CHATGPT_SOURCE_ID}
          AND (evidence_type IS NULL OR confidence IS NULL OR captured_at IS NULL)
    """).fetchone()[0]
    out["items:missing_provenance"] = n_missing_provenance

    # Parent/child integrity: messages must have a parent conversation
    n_orphans = dst.execute(f"""
        SELECT COUNT(*) FROM items m
        WHERE m.source_id={CHATGPT_SOURCE_ID} AND m.item_kind='chatgpt_message'
          AND (m.parent_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = m.parent_id
                              AND p.item_kind='chatgpt_conversation'))
    """).fetchone()[0]
    out["items:orphan_messages"] = n_orphans

    # tool_results must have a parent message
    n_orphan_tr = dst.execute(f"""
        SELECT COUNT(*) FROM items t
        WHERE t.source_id={CHATGPT_SOURCE_ID} AND t.item_kind='chatgpt_tool_result'
          AND (t.parent_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = t.parent_id
                              AND p.item_kind='chatgpt_message'))
    """).fetchone()[0]
    out["items:orphan_tool_results"] = n_orphan_tr

    # attachments must have a parent message
    n_orphan_att = dst.execute(f"""
        SELECT COUNT(*) FROM attachments a
        WHERE a.source_id={CHATGPT_SOURCE_ID}
          AND (a.item_id IS NULL
               OR NOT EXISTS (SELECT 1 FROM items p WHERE p.id = a.item_id
                              AND p.item_kind='chatgpt_message'))
    """).fetchone()[0]
    out["attachments:orphan_attachments"] = n_orphan_att

    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--research", type=Path, required=True,
                   help="Path to research_ledger DB to write. REQUIRED — the "
                        "canonical corpus is rejected unless --allow-canonical "
                        "is also passed. Flag name kept for backward compat "
                        "with existing test harnesses.")
    p.add_argument("--allow-canonical", action="store_true",
                   help="Permit writing the canonical corpus (dangerous).")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    research_path = args.research
    if not research_path.exists():
        print(f"ERROR: research_ledger not found: {research_path}", file=sys.stderr)
        return 1

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--research) path, not any migrated source path.
    guard_write_target(str(research_path), allow_canonical=args.allow_canonical)

    print(f"research: {research_path}")
    print(f"dry-run:  {args.dry_run}")
    print()

    dst = sqlite3.connect(str(research_path))
    dst.execute("PRAGMA journal_mode = WAL")
    dst.execute("PRAGMA synchronous = NORMAL")
    dst.execute("PRAGMA foreign_keys = ON")
    try:
        # Pre-flight: ensure chatgpt source is registered
        n_src = dst.execute(
            "SELECT COUNT(*) FROM sources WHERE id=? AND kind='session_ledger_migrated'",
            (CHATGPT_SOURCE_ID,)).fetchone()[0]
        if n_src != 1:
            print(f"ERROR: source id={CHATGPT_SOURCE_ID} (session_ledger_migrated) not registered. Run chatgpt_migrate_to_research.py first.", file=sys.stderr)
            return 1

        # Pre-flight: migrated_* row counts
        print("Migrated row counts:")
        for t in ['migrated_openai_chatgpt_conversations', 'migrated_openai_chatgpt_messages',
                  'migrated_openai_chatgpt_files', 'migrated_openai_chatgpt_attachment_content',
                  'migrated_openai_chatgpt_tool_results']:
            n = dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n:,}")
        print()

        if args.dry_run:
            for phase, fn in PHASE_FNS.items():
                print(f"  {phase:20s}  (would insert, dry-run)")
            return 0

        # Run phases (order matters: conversations before messages before tool_results)
        results = {}
        for phase in ["conversations", "messages", "tool_results", "files_attachments"]:
            t0 = time.time()
            n = PHASE_FNS[phase](dst)
            dst.commit()
            results[phase] = (n, time.time() - t0)
            print(f"  {phase:20s}  inserted={n:>7,}  {results[phase][1]:6.2f}s")

        # Validate
        print("\nValidation:")
        v = validate(dst)
        for k, val in v.items():
            tag = "OK" if (k.startswith("items:missing_") or k.endswith("orphans") or k.endswith("orphan_attachments") or k.endswith("orphan_messages") or k.endswith("orphan_tool_results")) and val == 0 else "OK"
            if (k.endswith("missing_provenance") or k.endswith("orphans") or "orphan" in k) and val != 0:
                tag = "FAIL"
            print(f"  {k:45s}  {val:>7,}  {tag}")

        return 0
    finally:
        dst.close()


if __name__ == "__main__":
    sys.exit(main())
