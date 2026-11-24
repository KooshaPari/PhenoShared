"""
codex_build_canonical.py — pump migrated_codex_* → items (canonical schema)

Mirrors jcode_build_canonical.py / kcode_build_canonical.py but handles the
codex-specific fields (subagent metadata, model from turn_context, etc.).

For each migrated_codex_session, create a 'codex_session' item.
For each migrated_codex_message, create a 'codex_message' item.

idempotent: external_id is unique on items.
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

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Tool-name TEXT -> JSON-array conversion lives in canonical_attrs so the four
# builders (jcode, kcode, codex, cursor) all use one implementation.
from canonical_attrs import _tool_names_to_array  # noqa: E402,F401


def build_canonical(db_path: Path, limit: int | None = None) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    # Find the codex source row
    src = conn.execute("SELECT id FROM sources WHERE kind = 'codex'").fetchone()
    if not src:
        print("ERROR: no codex source row in DB. Run codex_migrate_to_research.py first.")
        sys.exit(1)
    src_id = src[0]
    print(f"  source id: {src_id}")

    # Existing items (so we can skip them)
    existing_items = {
        r[0] for r in
        conn.execute("SELECT external_id FROM items WHERE source_id = ?", (src_id,))
        .fetchall()
    }
    print(f"  existing items for codex: {len(existing_items):,}")

    cur = conn.cursor()
    n_sess_items = 0
    n_msg_items = 0
    n_skipped = 0

    # Sessions
    print()
    print("--- building codex_session items ---")
    sess_sql = """
        SELECT
            external_id, session_id, title, parent_id,
            provider_key, provider_session_id, model, reasoning_effort,
            subagent_model, is_canary, is_debug, working_dir, status_json,
            created_at, updated_at, last_active_at, message_count,
            total_input_tokens, total_output_tokens, total_cache_read_tokens,
            cli_version, source, originator, source_meta_json,
            subagent_parent_id, subagent_nickname, subagent_role, subagent_path,
            source_path, snapshot_count, rollup_size_bytes
        FROM migrated_codex_sessions
        ORDER BY created_at
    """
    if limit is not None:
        sess_sql += " LIMIT ?"
        sess_rows = list(conn.execute(sess_sql, (limit,)))
    else:
        sess_rows = list(conn.execute(sess_sql))
    for r in sess_rows:
        (ext, sid, title, parent_id, provider_key, provider_sid, model, reasoning_effort,
         subagent_model, is_canary, is_debug, working_dir, status_json,
         created_at, updated_at, last_active_at, message_count,
         in_t, out_t, cache_t,
         cli_version, source, originator, source_meta_json,
         subagent_parent_id, subagent_nickname, subagent_role, subagent_path,
         source_path, snapshot_count, rollup_size_bytes) = r

        item_ext = f"item:codex_session:{sid}"
        if item_ext in existing_items:
            n_skipped += 1
            continue

        attrs = {
            "session_id": sid,
            "provider_key": provider_key,
            "provider_session_id": provider_sid,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "working_dir": working_dir,
            "message_count": message_count,
            "total_input_tokens": in_t,
            "total_output_tokens": out_t,
            "total_cache_read_tokens": cache_t,
            "cli_version": cli_version,
            "source": source,
            "originator": originator,
            "source_meta_json": source_meta_json,
            "subagent_parent_id": subagent_parent_id,
            "subagent_nickname": subagent_nickname,
            "subagent_role": subagent_role,
            "subagent_path": subagent_path,
            "source_path": source_path,
            "snapshot_count": snapshot_count,
            "rollup_size_bytes": rollup_size_bytes,
        }

        # Build a useful title. For sub-agent threads, show the nickname/role.
        if subagent_nickname:
            title_str = f"codex sub-agent {subagent_nickname} ({subagent_role or 'no-role'}) — {subagent_path or 'no-path'}"
        else:
            # Use first message if available
            first_msg = conn.execute("""
                SELECT content_text FROM migrated_codex_messages
                WHERE session_external_id = ? AND role = 'user' AND content_text IS NOT NULL
                ORDER BY timestamp_iso ASC LIMIT 1
            """, (ext,)).fetchone()
            if first_msg and first_msg[0]:
                title_str = f"codex/{first_msg[0][:60]}/{created_at[:10] if created_at else 'unknown'}"
            else:
                title_str = f"codex/{sid[:36]}/{created_at[:10] if created_at else 'unknown'}"

        # author = the human or coordinator. For sub-agent threads, the parent session's user.
        if subagent_parent_id:
            author = "koosha"
        else:
            author = "koosha"

        cur.execute("""
            INSERT INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, item_ext, NOW, created_at or NOW,
            "direct", "high", "partial",
            "codex_session", author, title_str, None,
            None, None, json.dumps(attrs, ensure_ascii=False),
        ))
        n_sess_items += 1

    conn.commit()
    print(f"  sessions: {n_sess_items:,} inserted, {n_skipped:,} skipped")

    # Messages
    print()
    print("--- building codex_message items ---")
    n_skipped = 0
    msg_sql = """
        SELECT
            m.external_id, m.msg_id, m.session_external_id, m.role,
            m.timestamp_iso, m.content_text, m.content_json,
            m.block_count, m.text_block_count, m.tool_use_count,
            m.tool_result_count, m.image_block_count, m.reasoning_block_count,
            m.custom_tool_call_count, m.tool_use_names
        FROM migrated_codex_messages m
        ORDER BY m.timestamp_iso
    """
    if limit is not None:
        msg_sql += " LIMIT ?"
        msg_rows = list(conn.execute(msg_sql, (limit,)))
    else:
        msg_rows = list(conn.execute(msg_sql))
    for r in msg_rows:
        (ext, msg_id, sess_ext, role, ts, text, content_json,
         block_count, n_text, n_tool_use, n_tool_result, n_image, n_reasoning,
         n_custom_tool, tool_names) = r

        # Get the codex session item external_id (the item, not the migrated row)
        # The migrated_codex_sessions.external_id is 'codex_session:<sid>'
        # The item.external_id is 'item:codex_session:<sid>'
        sid = sess_ext.replace("codex_session:", "", 1)
        item_sess_ext = f"item:codex_session:{sid}"

        item_ext = f"item:{ext}"  # item:codex_msg:<sid>:<msg_id>
        if item_ext in existing_items:
            n_skipped += 1
            continue

        # Author
        if role == "user":
            author = "koosha"
        elif role == "assistant":
            # Get model from the session
            model = conn.execute("""
                SELECT model FROM migrated_codex_sessions WHERE external_id = ?
            """, (sess_ext,)).fetchone()
            author = f"codex:{model[0] if model else 'unknown'}"
        elif role == "tool":
            author = "codex:tool"
        elif role == "developer":
            author = "codex:system"
        else:
            author = "codex:unknown"

        attrs = {
            "msg_id": msg_id,
            "session_external_id": sess_ext,
            "block_count": block_count,
            "text_block_count": n_text,
            "tool_use_count": n_tool_use,
            "tool_result_count": n_tool_result,
            "image_block_count": n_image,
            "reasoning_block_count": n_reasoning,
            "custom_tool_call_count": n_custom_tool,
            "tool_use_names": _tool_names_to_array(tool_names),
        }

        # Title = truncated first line of content (if available) or msg id
        if text:
            first_line = text.split("\n", 1)[0][:100]
            title_str = first_line
        else:
            title_str = f"codex/{role}/{msg_id[:30] if msg_id else 'no-id'}"

        cur.execute("""
            INSERT INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id, item_ext, NOW, ts or NOW,
            "direct", "high", "partial",
            "codex_message", author, title_str, text,
            None, None, json.dumps(attrs, ensure_ascii=False),
        ))
        n_msg_items += 1

    conn.commit()
    print(f"  messages: {n_msg_items:,} inserted, {n_skipped:,} skipped")

    # Update sources byte_size
    total_size = conn.execute("""
        SELECT COALESCE(SUM(rollup_size_bytes), 0) FROM migrated_codex_sessions
    """).fetchone()[0]
    conn.execute("""
        UPDATE sources SET byte_size = ?, captured_at = ?
        WHERE id = ?
    """, (int(total_size), now_iso(), src_id))
    conn.commit()
    print(f"  updated source byte_size: {total_size:,} bytes")

    conn.close()

    return {
        "sessions_inserted": n_sess_items,
        "messages_inserted": n_msg_items,
        "skipped": n_skipped,
    }


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
    r = build_canonical(args.db, args.limit)
    print()
    print("=== codex canonical summary ===")
    print(f"  sessions inserted: {r['sessions_inserted']:,}")
    print(f"  messages inserted: {r['messages_inserted']:,}")
    print(f"  skipped:           {r['skipped']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
