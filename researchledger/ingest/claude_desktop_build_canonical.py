#!/usr/bin/env python3
"""W9f-3: Build canonical items from migrated_claude_desktop_* tables.

Creates items for:
  - 22 user_message entries (from migrated_claude_desktop_messages)
  - 17 assistant_message entries (with cost_usd, model attribution)
  - 2 conversation_summary entries
  - 12,958 history entries (from history.jsonl - user commands only)

Idempotent: skips items that already exist by external_id.
"""
import argparse
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
from migrator_base import write_with_retry

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
SOURCE_KIND = "claude_desktop"


def ms_to_iso(ms):
    """Format an epoch timestamp as ISO-8601Z.

    The two Claude Code sources disagree on unit: history.jsonl records
    epoch MILLISECONDS, while __store.db's ``timestamp`` column holds epoch
    SECONDS. Detect by magnitude so both land on the right date instead of
    the seconds-valued rows collapsing to 1970.
    """
    if ms is None:
        return None
    try:
        value = float(ms)
    except (TypeError, ValueError):
        return None
    if abs(value) < 1e11:  # epoch seconds, not milliseconds
        value *= 1000
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def get_source_id(db):
    return db.execute("SELECT id FROM sources WHERE kind = ?", (SOURCE_KIND,)).fetchone()[0]


def parse_message_content(raw):
    """Extract text from Claude message JSON {role, content}."""
    if not raw:
        return "", None
    try:
        d = json.loads(raw)
    except Exception:
        return raw[:50000], None
    content = d.get("content", "")
    if isinstance(content, str):
        return content, d.get("model")
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    parts.append(f"[tool_use: {c.get('name', '?')}]")
                elif c.get("type") == "tool_result":
                    inner = c.get("content", "")
                    if isinstance(inner, list):
                        for ic in inner:
                            if isinstance(ic, dict) and ic.get("type") == "text":
                                parts.append(f"[tool_result: {ic.get('text', '')[:200]}]")
                    elif isinstance(inner, str):
                        parts.append(f"[tool_result: {inner[:200]}]")
        return "\n".join(parts), d.get("model")
    return str(content)[:50000], d.get("model")


def build_message_items(db, source_id):
    """Build items for each message in migrated_claude_desktop_messages."""
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT * FROM migrated_claude_desktop_messages
        WHERE user_message IS NOT NULL OR assistant_message IS NOT NULL OR conversation_summary IS NOT NULL
        ORDER BY timestamp_ms
        """
    ).fetchall()
    inserted = 0
    skipped = 0
    t0 = time.time()
    for r in rows:
        d = dict(r)
        uuid = d["uuid"]
        ts_iso = ms_to_iso(d.get("timestamp_ms"))
        ext_id = f"claude_desktop_canon:{uuid}"
        # Skip if exists
        existing = db.execute(
            "SELECT 1 FROM items WHERE source_id = ? AND external_id = ?",
            (source_id, ext_id),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        if d.get("user_message"):
            content, _ = parse_message_content(d["user_message"])
            text = content[:60000]
            item_kind = "claude_desktop_user_message"
            role = "user"
        elif d.get("assistant_message"):
            content, model = parse_message_content(d["assistant_message"])
            text = content[:60000]
            item_kind = "claude_desktop_assistant_message"
            role = "assistant"
        elif d.get("conversation_summary"):
            text = d["conversation_summary"][:60000]
            item_kind = "claude_desktop_conversation_summary"
            role = "system"
        else:
            continue

        # Build attrs JSON
        attrs = {
            "uuid": uuid,
            "parent_uuid": d.get("parent_uuid"),
            "session_id": d.get("session_id"),
            "message_type": d.get("message_type"),
            "user_type": d.get("user_type"),
            "is_sidechain": bool(d.get("is_sidechain")),
            "version": d.get("version"),
        }
        if d.get("cost_usd") is not None:
            attrs["cost_usd"] = d["cost_usd"]
        if d.get("duration_ms") is not None:
            attrs["duration_ms"] = d["duration_ms"]
        if d.get("assistant_model"):
            attrs["model"] = d["assistant_model"]
        if d.get("is_api_error_message"):
            attrs["is_api_error_message"] = True
        if d.get("is_meta"):
            attrs["is_meta"] = True
        if d.get("is_at_mention_read"):
            attrs["is_at_mention_read"] = True
        if d.get("tool_use_result"):
            attrs["has_tool_use_result"] = True

        try:
            write_with_retry(db, """
                INSERT OR IGNORE INTO items (
                    source_id, external_id, captured_at, source_captured_at,
                    evidence_type, confidence, note, redaction_state,
                    item_kind, author, title, body, url, raw_json_path,
                    parent_id, dedupe_hash, attrs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    ext_id,
                    ts_iso or "2026-10-15T09:00:00Z",
                    ts_iso,
                    "direct",
                    "high",
                    None,
                    "none",
                    item_kind,
                    "koosha" if role == "user" else "anthropic",
                    None,
                    text,
                    None,
                    str(d.get("source_path") or ""),
                    None,
                    None,
                    json.dumps(attrs, ensure_ascii=False, default=str),
                ),
            )
            inserted += 1
        except Exception as e:
            if inserted + skipped <= 5:
                print(f"    WARN: {uuid}: {e}")
    db.commit()
    return inserted, skipped, len(rows)


def build_history_items(db, source_id):
    """Build items for each entry in migrated_claude_desktop_history."""
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT * FROM migrated_claude_desktop_history
        ORDER BY timestamp_ms
        """
    ).fetchall()
    inserted = 0
    skipped = 0
    t0 = time.time()
    for r in rows:
        d = dict(r)
        ext_id = d["external_id"]  # already includes 'claude_desktop_hist:'
        # Map to canonical external_id
        canon_ext_id = ext_id.replace("claude_desktop_hist:", "claude_desktop_hist_canon:")
        ts_iso = ms_to_iso(d.get("timestamp_ms"))
        text = (d.get("display") or "")[:60000]
        attrs = {
            "raw_external_id": ext_id,
            "project": d.get("project"),
            "has_pasted_contents": bool(d.get("pasted_contents_json") and d["pasted_contents_json"] not in (None, "", "null", "{}")),
        }
        existing = db.execute(
            "SELECT 1 FROM items WHERE source_id = ? AND external_id = ?",
            (source_id, canon_ext_id),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        try:
            write_with_retry(db, """
                    INSERT OR IGNORE INTO items (
                    source_id, external_id, captured_at, source_captured_at,
                    evidence_type, confidence, note, redaction_state,
                    item_kind, author, title, body, url, raw_json_path,
                    parent_id, dedupe_hash, attrs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    canon_ext_id,
                    ts_iso or "2026-10-15T09:00:00Z",
                    ts_iso,
                    "direct",
                    "high",
                    None,
                    "none",
                    "claude_desktop_history_command",
                    "koosha",
                    None,
                    text,
                    None,
                    str(d.get("source_path") or ""),
                    None,
                    None,
                    json.dumps(attrs, ensure_ascii=False, default=str),
                ),
            )
            inserted += 1
        except Exception as e:
            if inserted + skipped <= 5:
                print(f"    WARN: {canon_ext_id}: {e}")
        if (inserted + skipped) % 3000 == 0 and inserted + skipped > 0:
            db.commit()
            print(f"    ... {inserted+skipped:,} ({inserted:,} inserted, {skipped:,} skipped) elapsed {time.time()-t0:.1f}s")
    db.commit()
    return inserted, skipped, len(rows)


def main():
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

    print("W9f-3: build canonical items for claude_desktop")
    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout = 60000")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")

    source_id = get_source_id(db)
    print(f"  source_id: {source_id}")

    # 1) Messages
    print("=== messages (full convo pairs) ===")
    ins1, skp1, total1 = build_message_items(db, source_id)
    print(f"  total: {total1}, inserted: {ins1}, skipped: {skp1}")

    # 2) History
    print("=== history (user commands) ===")
    ins2, skp2, total2 = build_history_items(db, source_id)
    print(f"  total: {total2}, inserted: {ins2}, skipped: {skp2}")

    # Final
    print("\n=== Result ===")
    rows = db.execute(
        """
        SELECT item_kind, COUNT(*) AS n
        FROM items
        WHERE source_id = ?
        GROUP BY item_kind
        ORDER BY n DESC
        """,
        (source_id,),
    ).fetchall()
    for kind, n in rows:
        print(f"  {kind}: {n:,}")

    # A lock collision used to be swallowed per row, so the build could report
    # "inserted: 0" and still exit 0. Fail loudly instead.
    built = sum(n for _, n in rows)
    if (total1 + total2) > 0 and built == 0:
        print("  ERROR: source rows exist but 0 canonical items landed")
        db.close()
        return 1

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
