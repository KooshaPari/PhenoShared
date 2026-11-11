"""
chatgpt_migrate_to_research.py — Pump W6/W7 chatgpt data from session_ledger
into research_ledger's migrated_openai_chatgpt_* passthrough tables.

Read-only on session_ledger.sqlite. Writes to research_ledger.sqlite.
Idempotent (INSERT OR IGNORE via UNIQUE constraints on the migrated tables).

Usage:
    python3 chatgpt_migrate_to_research.py                       # auto-detect paths
    python3 chatgpt_migrate_to_research.py --session PATH --research PATH
    python3 chatgpt_migrate_to_research.py --dry-run             # report only
    python3 chatgpt_migrate_to_research.py --only conversations # limit phase

The migrated_* tables are passthrough — they preserve the W6/W7 schema exactly
so the canonical items/attachments layer can be built incrementally without
losing the row-level detail.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import guard_and_connect, register_source

DEFAULT_SESSION = Path.home() / "Exports" / "analysis" / "session_ledger.sqlite"

PHASES = ("conversations", "messages", "files", "attachment_content", "tool_results")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def open_readonly(path: Path) -> sqlite3.Connection:
    """Open session_ledger read-only (URI mode, no writes possible)."""
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate_conversations(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # session_ledger: uuid, name, summary, created_at, updated_at, account_uuid,
    #                 n_messages, source_path, ingested_at
    # migrated:     external_id, title, created_at, updated_at, model, n_messages, raw_json_path
    rows = src.execute("""
        SELECT uuid, name, summary, created_at, updated_at, account_uuid,
               n_messages, source_path
        FROM openai_chatgpt_conversations
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO migrated_openai_chatgpt_conversations
            (external_id, title, summary, created_at, updated_at, model,
             n_messages, raw_json_path, account_uuid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    n = 0
    for r in rows:
        # tuple: uuid, name, summary, created_at, updated_at, account_uuid,
        #        n_messages, source_path
        dst.execute(sql, (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[5]))
        n += 1
    return n


def migrate_messages(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # session_ledger: uuid, conversation_uuid, sender, text, content_json, ...
    # migrated:     conversation_external_id, message_external_id, author, role,
    #               created_at, content_type, content_text, content_json, parent_message_uuid
    rows = src.execute("""
        SELECT uuid, conversation_uuid, sender, text, content_json,
               created_at, updated_at, parent_message_uuid
        FROM openai_chatgpt_messages
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO migrated_openai_chatgpt_messages
            (conversation_external_id, message_external_id, author, role,
             created_at, content_type, content_text, content_json,
             parent_message_uuid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    n = 0
    for r in rows:
        # tuple: uuid, conversation_uuid, sender, text, content_json,
        #        created_at, updated_at, parent_message_uuid
        # content_type: 'text' if sender != 'tool', else 'tool_result'
        ctype = 'tool_result' if r[2] == 'tool' else 'text'
        dst.execute(sql, (
            r[1],  # conversation_uuid
            r[0],  # message uuid
            r[2],  # sender (user/assistant/tool/system)
            r[2],  # role (same as sender)
            r[5],  # created_at
            ctype,
            r[3],  # text
            r[4],  # content_json
            r[7],  # parent_message_uuid
        ))
        n += 1
    return n


def migrate_files(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # session_ledger: msg_uuid, conversation_uuid, file_uuid, file_name,
    #                 source_path, ingested_at
    # migrated:     conversation_external_id, file_external_id, name, mime_type, byte_size
    rows = src.execute("""
        SELECT msg_uuid, conversation_uuid, file_uuid, file_name, source_path
        FROM openai_chatgpt_files
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO migrated_openai_chatgpt_files
            (conversation_external_id, msg_external_id, file_external_id,
             name, source_path)
        VALUES (?, ?, ?, ?, ?)
    """
    n = 0
    for r in rows:
        dst.execute(sql, r)
        n += 1
    return n


def migrate_attachment_content(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # session_ledger: msg_uuid, conversation_uuid, file_name, file_size, file_type,
    #                 extracted_content, content_len, source_path, ingested_at
    # migrated:     file_external_id, msg_external_id, conversation_external_id,
    #               file_name, file_size, file_type, extracted_content, content_len
    rows = src.execute("""
        SELECT msg_uuid, conversation_uuid, file_name, file_size, file_type,
               extracted_content, content_len, source_path
        FROM openai_chatgpt_attachment_content
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO migrated_openai_chatgpt_attachment_content
            (msg_external_id, conversation_external_id, file_name, file_size,
             file_type, extracted_content, content_len, source_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    n = 0
    for r in rows:
        dst.execute(sql, r)
        n += 1
    return n


def migrate_tool_results(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    # session_ledger: msg_uuid, conversation_uuid, block_index, name, tool_use_id,
    #                 is_error, content_json, content_len, source_path
    # migrated:     message_external_id, tool_call_id, content_json, content_len
    rows = src.execute("""
        SELECT msg_uuid, conversation_uuid, block_index, name, tool_use_id,
               is_error, content_json, content_len
        FROM openai_chatgpt_tool_results
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO migrated_openai_chatgpt_tool_results
            (message_external_id, conversation_external_id, block_index,
             name, tool_call_id, is_error, content_json, content_len)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    n = 0
    for r in rows:
        dst.execute(sql, r)
        n += 1
    return n


PHASE_FNS = {
    "conversations": migrate_conversations,
    "messages": migrate_messages,
    "files": migrate_files,
    "attachment_content": migrate_attachment_content,
    "tool_results": migrate_tool_results,
}


def validate_row_counts(src: sqlite3.Connection, dst: sqlite3.Connection) -> dict:
    """Compare row counts between session_ledger and research_ledger migrated tables."""
    pairs = [
        ("openai_chatgpt_conversations", "migrated_openai_chatgpt_conversations"),
        ("openai_chatgpt_messages", "migrated_openai_chatgpt_messages"),
        ("openai_chatgpt_files", "migrated_openai_chatgpt_files"),
        ("openai_chatgpt_attachment_content", "migrated_openai_chatgpt_attachment_content"),
        ("openai_chatgpt_tool_results", "migrated_openai_chatgpt_tool_results"),
    ]
    out = {}
    for src_t, dst_t in pairs:
        s = src.execute(f"SELECT COUNT(*) FROM {src_t}").fetchone()[0]
        d = dst.execute(f"SELECT COUNT(*) FROM {dst_t}").fetchone()[0]
        out[src_t] = {"src": s, "dst": d, "match": s == d}
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", default=str(DEFAULT_SESSION), help="session_ledger.sqlite path (read-only)")
    p.add_argument("--research", required=True,
                   help="research_ledger.sqlite path to write into (REQUIRED; no default — see corpus_guard.py)")
    p.add_argument("--allow-canonical", action="store_true",
                   help="Permit writing the canonical corpus (dangerous).")
    p.add_argument("--only", choices=PHASES, help="Run only one phase")
    p.add_argument("--dry-run", action="store_true", help="Report counts, do not write")
    args = p.parse_args(argv)

    session_path = Path(args.session)
    research_path = Path(args.research)

    if not session_path.exists():
        print(f"ERROR: session_ledger not found: {session_path}", file=sys.stderr)
        return 1
    if not research_path.exists():
        print(f"ERROR: research_ledger not found: {research_path}", file=sys.stderr)
        return 1

    # guard_and_connect combines guard_write_target + sqlite3.connect in the
    # canonical order (guard first, then connect). The pragmas reproduce the
    # pre-refactor settings that followed the connect call.
    print(f"session:  {session_path}")
    print(f"research: {research_path}")
    print(f"dry-run:  {args.dry_run}")
    print()

    src = open_readonly(session_path)
    dst = guard_and_connect(
        research_path,
        args.allow_canonical,
        pragmas=["journal_mode = WAL", "synchronous = NORMAL", "foreign_keys = ON"],
    )
    try:
        # Pre-flight: report source counts
        print("Source counts (session_ledger):")
        for t in ["openai_chatgpt_conversations", "openai_chatgpt_messages",
                  "openai_chatgpt_files", "openai_chatgpt_attachment_content",
                  "openai_chatgpt_tool_results"]:
            n = src.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n:,}")
        print()

        # Register research_ledger source
        if not args.dry_run:
            register_source(
                dst,
                kind="session_ledger_migrated",
                base_path=str(session_path),
                captured_at=now_iso(),
                byte_size=session_path.stat().st_size,
                schema_version="v1.0",
                notes="chatgpt passthrough from session_ledger W6/W7",
            )

        # Run phases
        phases = [args.only] if args.only else list(PHASES)
        results = {}
        for phase in phases:
            t0 = time.time()
            if args.dry_run:
                # Just count what we'd write
                src_count = src.execute(
                    f"SELECT COUNT(*) FROM openai_chatgpt_{phase}" if phase != "attachment_content"
                    else f"SELECT COUNT(*) FROM openai_chatgpt_attachment_content"
                ).fetchone()[0]
                results[phase] = {"src": src_count, "written": 0, "elapsed_s": 0.0, "dry_run": True}
            else:
                n = PHASE_FNS[phase](src, dst)
                dst.commit()
                results[phase] = {
                    "src": src.execute(
                        f"SELECT COUNT(*) FROM openai_chatgpt_{phase}" if phase != "attachment_content"
                        else f"SELECT COUNT(*) FROM openai_chatgpt_attachment_content"
                    ).fetchone()[0],
                    "written": n,
                    "elapsed_s": time.time() - t0,
                    "dry_run": False,
                }
            r = results[phase]
            print(f"  {phase:20s}  src={r['src']:>7,}  written={r['written']:>7,}  {r['elapsed_s']:6.2f}s  "
                  + ("DRY-RUN" if r.get('dry_run') else "OK"))

        if args.dry_run:
            print("\n(dry-run, no changes written)")
            return 0

        # Validate
        print("\nPost-migration validation:")
        for t, info in validate_row_counts(src, dst).items():
            tag = "OK" if info["match"] else "MISMATCH"
            print(f"  {t:50s}  src={info['src']:>7,}  dst={info['dst']:>7,}  {tag}")

        # Spot check
        print("\nSpot checks:")
        n_dst_conv = dst.execute("SELECT COUNT(*) FROM migrated_openai_chatgpt_conversations").fetchone()[0]
        n_dst_msg = dst.execute("SELECT COUNT(*) FROM migrated_openai_chatgpt_messages").fetchone()[0]
        n_dst_attc = dst.execute("SELECT COUNT(*) FROM migrated_openai_chatgpt_attachment_content").fetchone()[0]
        n_dst_tr = dst.execute("SELECT COUNT(*) FROM migrated_openai_chatgpt_tool_results").fetchone()[0]
        print(f"  research_ledger chatgpt rows:  {n_dst_conv} convs / {n_dst_msg} msgs / {n_dst_attc} attcontent / {n_dst_tr} tool_results")
        return 0
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    sys.exit(main())
