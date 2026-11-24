"""
jcode_build_canonical.py — pump migrated_jcode_* → canonical items

Reads research_ledger.migrated_jcode_{sessions,messages} and produces:
  items.item_kind='jcode_session'   — one per session (4.3K rows)
  items.item_kind='jcode_message'   — one per message (435K rows)

No attachments for jcode (harness sessions don't carry file artifacts;
they reference working_dir files instead, which is operator filesystem state).

PII policy: redaction_state='partial' (matches chatgpt + claude convention).
Session titles and message bodies are stored as-is. working_dir is a local
filesystem path; it can leak project names but no PII beyond that.
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


# Tool-name TEXT -> JSON-array conversion lives in canonical_attrs so the four
# builders (jcode, kcode, codex, cursor) all use one implementation.
from canonical_attrs import _tool_names_to_array  # noqa: E402,F401


def find_src_id(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT id FROM sources WHERE kind = 'jcode'")
    row = cur.fetchone()
    if not row:
        raise SystemExit("jcode source not found in research_ledger; run jcode_migrate_to_research.py first")
    return row[0]


def build_session_items(conn: sqlite3.Connection, src_id: int, limit: int | None = None) -> int:
    """items.item_kind='jcode_session', one per migrated session."""
    cur = conn.cursor()
    n = 0
    today = now_iso()
    sql = """
        SELECT external_id, session_id, short_name, title, parent_id,
               provider_key, provider_session_id, model, reasoning_effort,
               subagent_model, is_canary, is_debug, working_dir, status_json,
               created_at, updated_at, last_active_at, message_count,
               total_input_tokens, total_output_tokens, total_cache_read_tokens,
               saved, save_label, raw_json_path
        FROM migrated_jcode_sessions
    """
    if limit is not None:
        sql += " LIMIT ?"
        rows = cur.execute(sql, (limit,)).fetchall()
    else:
        rows = cur.execute(sql).fetchall()
    for r in rows:
        (ext_id, sid, short_name, title, parent_id, provider_key, provider_sid,
         model, reasoning, subagent_model, is_canary, is_debug, working_dir,
         status_json, created_at, updated_at, last_active_at, msg_count,
         in_t, out_t, cache_t, saved, save_label, raw_json_path) = r

        # Title: prefer operator-set title, else short_name + first 20 chars of created
        if title:
            t = title.strip()
            if not t:
                t = None
        else:
            t = None
        if not t:
            t = f"jcode/{short_name}/{created_at[:10] if created_at else '?'}"

        # Body: structured summary
        body_parts = []
        body_parts.append(f"harness: jcode")
        body_parts.append(f"short_name: {short_name}")
        if parent_id:
            body_parts.append(f"parent: {parent_id}")
        body_parts.append(f"provider: {provider_key}")
        body_parts.append(f"model: {model}")
        if reasoning:
            body_parts.append(f"reasoning_effort: {reasoning}")
        if subagent_model:
            body_parts.append(f"subagent_model: {subagent_model}")
        if working_dir:
            body_parts.append(f"working_dir: {working_dir}")
        if is_canary:
            body_parts.append("is_canary: yes")
        if is_debug:
            body_parts.append("is_debug: yes")
        body_parts.append(f"status: {status_json}")
        body_parts.append(f"created: {created_at}")
        if updated_at and updated_at != created_at:
            body_parts.append(f"updated: {updated_at}")
        body_parts.append(f"messages: {msg_count:,}")
        body_parts.append(f"tokens: in={in_t:,}  out={out_t:,}  cache={cache_t:,}")
        if saved:
            body_parts.append(f"saved: {save_label or 'yes'}")
        body = "\n".join(body_parts)

        attrs = {
            "short_name": short_name,
            "session_id": sid,
            "parent_id": parent_id,
            "provider_key": provider_key,
            "provider_session_id": provider_sid,
            "model": model,
            "reasoning_effort": reasoning,
            "subagent_model": subagent_model,
            "is_canary": bool(is_canary),
            "is_debug": bool(is_debug),
            "working_dir": working_dir,
            "status": status_json,
            "message_count": msg_count,
            "total_input_tokens": in_t,
            "total_output_tokens": out_t,
            "total_cache_read_tokens": cache_t,
            "saved": bool(saved),
            "save_label": save_label,
            "raw_json_path": raw_json_path,
            "platform": "jcode",
        }
        cur.execute("""
            INSERT OR IGNORE INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, ext_id, today, created_at or today,
            'direct', 'high', 'partial',
            'jcode_session', 'koosha', t[:500], body,
            None, raw_json_path, json.dumps(attrs, ensure_ascii=False),
        ))
        if cur.rowcount > 0:
            n += 1
    conn.commit()
    return n


def build_message_items(conn: sqlite3.Connection, src_id: int, limit: int | None = None) -> int:
    """items.item_kind='jcode_message', one per migrated message."""
    cur = conn.cursor()
    n = 0
    today = now_iso()
    sql = """
        SELECT m.external_id, m.msg_id, m.session_external_id, m.role,
               m.timestamp_iso, m.content_text, m.content_json,
               m.block_count, m.text_block_count, m.tool_use_count,
               m.tool_result_count, m.image_block_count, m.reasoning_block_count,
               m.tool_use_names, m.input_tokens, m.output_tokens, m.cache_read_input_tokens,
               s.session_id, s.short_name, s.model, s.working_dir, s.title
        FROM migrated_jcode_messages m
        JOIN migrated_jcode_sessions s ON s.external_id = m.session_external_id
    """
    if limit is not None:
        sql += " LIMIT ?"
        rows = cur.execute(sql, (limit,)).fetchall()
    else:
        rows = cur.execute(sql).fetchall()
    for r in rows:
        (ext_id, mid, sess_ext, role, ts, content_text, content_json,
         n_blocks, n_text, n_tool_use, n_tool_result, n_image, n_reasoning,
         tool_names, in_t, out_t, cache_t,
         sid, short_name, model, working_dir, sess_title) = r

        # Author: 'koosha' for user, '<role>' for assistant/tool
        if role == 'user':
            author = 'koosha'
        elif role == 'assistant':
            author = f'jcode:{model}' if model else 'jcode:assistant'
        elif role == 'tool':
            author = 'jcode:tool'
        else:
            author = f'jcode:{role}' if role else 'jcode'

        # Title: first text block (truncated) or role+tool descriptor
        if content_text:
            t = content_text.split("\n", 1)[0][:200].strip()
        else:
            if n_tool_use:
                t = f"[assistant tool_use: {tool_names or '?'}]"
            elif role == 'tool':
                t = "[tool result]"
            else:
                t = f"[{role or '?'} (no text)]"

        # Body
        body_parts = []
        body_parts.append(f"harness: jcode")
        body_parts.append(f"session: {sess_ext}")
        if sess_title:
            body_parts.append(f"session title: {sess_title}")
        body_parts.append(f"role: {role}")
        body_parts.append(f"model: {model}")
        body_parts.append(f"timestamp: {ts or '?'}")
        if working_dir:
            body_parts.append(f"working_dir: {working_dir}")
        if in_t or out_t:
            body_parts.append(f"tokens: in={in_t:,} out={out_t:,} cache={cache_t:,}")
        if tool_names:
            body_parts.append(f"tools: {tool_names}")
        body_parts.append(
            f"blocks: total={n_blocks} text={n_text} reasoning={n_reasoning} "
            f"tool_use={n_tool_use} tool_result={n_tool_result} image={n_image}"
        )
        if content_text:
            body_parts.append("")
            body_parts.append(content_text)
        else:
            body_parts.append("")
            body_parts.append("[no text content]")
        body = "\n".join(body_parts)

        # URL: rarely. Could pull from tool_use or content but skip for now
        url = None

        attrs = {
            "session_id": sid,
            "session_external_id": sess_ext,
            "msg_id": mid,
            "role": role,
            "model": model,
            "working_dir": working_dir,
            "block_count": n_blocks,
            "text_block_count": n_text,
            "tool_use_count": n_tool_use,
            "tool_result_count": n_tool_result,
            "image_block_count": n_image,
            "reasoning_block_count": n_reasoning,
            "tool_use_names": _tool_names_to_array(tool_names),
            "input_tokens": in_t,
            "output_tokens": out_t,
            "cache_read_input_tokens": cache_t,
            "content_json_size": len(content_json) if content_json else 0,
            "platform": "jcode",
        }
        cur.execute("""
            INSERT OR IGNORE INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, ext_id, today, ts or today,
            'direct', 'high', 'partial',
            'jcode_message', author, t[:500], body,
            url, None, json.dumps(attrs, ensure_ascii=False),
        ))
        if cur.rowcount > 0:
            n += 1
        if n % 5000 == 0 and n > 0:
            conn.commit()
    conn.commit()
    return n


def report(conn: sqlite3.Connection, src_id: int,
           n_sess: int, n_msg: int) -> None:
    cur = conn.cursor()
    print()
    print("Spot checks (jcode source in research_ledger):")
    for kind in ['jcode_session', 'jcode_message']:
        n = cur.execute("SELECT COUNT(*) FROM items WHERE item_kind = ? AND source_id = ?",
                        (kind, src_id)).fetchone()[0]
        print(f"  items {kind:25s}  {n:>9,}")
    n = cur.execute("SELECT COUNT(*) FROM attachments WHERE source_id = ?", (src_id,)).fetchone()[0]
    print(f"  attachments (any kind)        {n:>9,}")

    # Role breakdown
    print()
    print("messages by role:")
    for r in cur.execute("""
        SELECT json_extract(attrs_json, '$.role') as role, COUNT(*)
        FROM items WHERE source_id = ? AND item_kind = 'jcode_message'
        GROUP BY role ORDER BY 2 DESC
    """, (src_id,)).fetchall():
        print(f"  {r[0] or 'null':15s} {r[1]:>9,}")

    # Top tool names
    print()
    print("top tool names from message attrs_json:")
    for r in cur.execute("""
        SELECT json_extract(attrs_json, '$.tool_use_names') as tn, COUNT(*)
        FROM items WHERE source_id = ? AND item_kind = 'jcode_message'
            AND json_extract(attrs_json, '$.tool_use_names') IS NOT NULL
        GROUP BY tn ORDER BY 2 DESC LIMIT 10
    """, (src_id,)).fetchall():
        print(f"  {r[0][:60] if r[0] else '':60s} {r[1]:>7,}")

    # FTS5 spot check
    print()
    print("FTS5 spot check (jcode messages):")
    for q in ['research_ledger', 'autonomous', 'iMessage', 'chatgpt', 'gemini',
              'jcode', 'subagent', 'PII', 'proco', 'datamine', 'Phenotype']:
        n = cur.execute("""
            SELECT COUNT(*) FROM items_fts f
            JOIN items i ON i.id = f.rowid
            WHERE items_fts MATCH ? AND i.source_id = ?
        """, (q, src_id)).fetchone()[0]
        print(f"  MATCH '{q}': {n}")

    # Sample session
    print()
    print("Sample session (most messages):")
    r = cur.execute("""
        SELECT id, source_captured_at, author, title, substr(body, 1, 300)
        FROM items
        WHERE source_id = ? AND item_kind = 'jcode_session'
        ORDER BY length(body) DESC LIMIT 1
    """, (src_id,)).fetchone()
    if r:
        print(f"  id={r[0]}")
        print(f"  date={r[1]}")
        print(f"  author={r[2]}")
        print(f"  title={r[3]}")
        print(f"  body={r[4]}")

    # Sample message
    print()
    print("Sample message (most recent 3 user messages):")
    for r in cur.execute("""
        SELECT id, source_captured_at, author, title, substr(body, 1, 200)
        FROM items
        WHERE source_id = ? AND item_kind = 'jcode_message'
            AND json_extract(attrs_json, '$.role') = 'user'
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
    p.add_argument('--limit', type=int, default=None,
                   help='Cap source rows per query to N (non-negative). '
                        'Default: full scan. Use to bound rebuild risk.')
    args = p.parse_args()

    if args.limit is not None and args.limit < 0:
        p.error("--limit must be non-negative")

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--db) path, not any migrated source path.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    print(f"db: {args.db}")
    if args.limit is not None:
        print(f"limit: {args.limit} source rows per query")
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    try:
        src_id = find_src_id(conn)
        print(f"source id: {src_id} (kind=jcode)")

        print()
        print("--- building session items ---")
        n_sess = build_session_items(conn, src_id, args.limit)
        print(f"  inserted: {n_sess:,}")

        print()
        print("--- building message items (this may take a while: 435K rows) ---")
        n_msg = build_message_items(conn, src_id, args.limit)
        print(f"  inserted: {n_msg:,}")

        report(conn, src_id, n_sess, n_msg)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
