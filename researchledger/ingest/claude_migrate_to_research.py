"""
claude_migrate_to_research.py — Pump claude-20261010/raw into research_ledger.

Reads (read-only, never modifies):
  /Users/kooshapari/Exports/claude-20261010/raw/conversations-000/conversations.json
  /Users/kooshapari/Exports/claude-20261010/raw/light_metadata-000/{users,login_history}.json
  /Users/kooshapari/Exports/claude-20261010/raw/memories-000/<account_uuid>.json
  /Users/kooshapari/Exports/claude-20261010/raw/projects-000/projects/<uuid>.json
  /Users/kooshapari/Exports/claude-20261010/raw/design_chats-000/design_chats/<uuid>.json

Writes (idempotent, INSERT OR IGNORE on UNIQUE):
  migrated_anthropic_claude_conversations
  migrated_anthropic_claude_messages
  migrated_anthropic_claude_attachments
  migrated_anthropic_claude_files
  migrated_anthropic_claude_users
  migrated_anthropic_claude_login_events
  migrated_anthropic_claude_memories
  migrated_anthropic_claude_projects
  migrated_anthropic_claude_project_docs
  migrated_anthropic_claude_design_chats
  migrated_anthropic_claude_design_chat_messages

Usage:
    python3 claude_migrate_to_research.py
    python3 claude_migrate_to_research.py --raw-dir <PATH> --db <PATH>

Per spec §4.3 the source row carries the original JSON path so the canonical
build can prove provenance.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect

DEFAULT_RAW_DIR = Path("/Users/kooshapari/Exports/claude-20261010/raw")


def load_json(path: Path) -> object:
    with open(path) as f:
        return json.load(f)


def migrate_conversations(cur: sqlite3.Cursor, convs: list[dict], source_path: str) -> int:
    """786 conversations, 10885 messages, 842 attachments, 2109 file refs."""
    n_conv = n_msg = n_att = n_file = 0
    for c in convs:
        cur.execute("""
            INSERT OR IGNORE INTO migrated_anthropic_claude_conversations
            (external_id, name, summary, created_at, updated_at,
             account_uuid, n_messages, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c.get("uuid"),
            c.get("name") or "",
            c.get("summary") or "",
            c.get("created_at"),
            c.get("updated_at"),
            (c.get("account") or {}).get("uuid"),
            len(c.get("chat_messages", [])),
            source_path,
        ))
        if cur.rowcount > 0:
            n_conv += 1
        conv_id = c.get("uuid")
        for m in c.get("chat_messages", []):
            content = m.get("content", [])
            cur.execute("""
                INSERT OR IGNORE INTO migrated_anthropic_claude_messages
                (conversation_external_id, message_external_id, sender,
                 created_at, updated_at, text, content_json,
                 parent_message_uuid, n_parts, n_attachments, n_files)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv_id,
                m.get("uuid"),
                m.get("sender"),
                m.get("created_at"),
                m.get("updated_at"),
                m.get("text") or "",
                json.dumps(content),
                m.get("parent_message_uuid"),
                len(content),
                len(m.get("attachments", [])),
                len(m.get("files", [])),
            ))
            if cur.rowcount > 0:
                n_msg += 1
            msg_id = m.get("uuid")
            for a in m.get("attachments", []):
                content_text = a.get("extracted_content") or ""
                cur.execute("""
                    INSERT OR IGNORE INTO migrated_anthropic_claude_attachments
                    (msg_external_id, conversation_external_id, file_name,
                     file_size, file_type, extracted_content, content_len)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg_id,
                    conv_id,
                    a.get("file_name"),
                    a.get("file_size"),
                    a.get("file_type"),
                    content_text,
                    len(content_text),
                ))
                if cur.rowcount > 0:
                    n_att += 1
            for f in m.get("files", []):
                cur.execute("""
                    INSERT OR IGNORE INTO migrated_anthropic_claude_files
                    (msg_external_id, conversation_external_id, file_external_id, file_name)
                    VALUES (?, ?, ?, ?)
                """, (
                    msg_id,
                    conv_id,
                    f.get("file_uuid"),
                    f.get("file_name"),
                ))
                if cur.rowcount > 0:
                    n_file += 1
    return n_conv, n_msg, n_att, n_file


def migrate_light_metadata(cur: sqlite3.Cursor, raw_dir: Path) -> tuple[int, int]:
    n_user = n_login = 0
    users_path = raw_dir / "light_metadata-000" / "users.json"
    if users_path.exists():
        for u in load_json(users_path):
            cur.execute("""
                INSERT OR IGNORE INTO migrated_anthropic_claude_users
                (external_id, full_name, email_address, verified_phone_number)
                VALUES (?, ?, ?, ?)
            """, (
                u.get("uuid"),
                u.get("full_name"),
                u.get("email_address"),
                u.get("verified_phone_number"),
            ))
            if cur.rowcount > 0:
                n_user += 1
    lh_path = raw_dir / "light_metadata-000" / "login_history.json"
    if lh_path.exists():
        d = load_json(lh_path)
        events = d.get("login_events", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        for ev in events:
            cur.execute("""
                INSERT OR IGNORE INTO migrated_anthropic_claude_login_events
                (user_external_id, event_json, source_path)
                VALUES (?, ?, ?)
            """, (
                ev.get("account_uuid") if isinstance(ev, dict) else None,
                json.dumps(ev),
                str(lh_path),
            ))
            if cur.rowcount > 0:
                n_login += 1
    return n_user, n_login


def migrate_memories(cur: sqlite3.Cursor, raw_dir: Path) -> int:
    n = 0
    mem_dir = raw_dir / "memories-000"
    if not mem_dir.exists():
        return 0
    for fn in os.listdir(mem_dir):
        path = mem_dir / fn
        if not path.suffix == ".json":
            continue
        d = load_json(path)
        cur.execute("""
            INSERT OR IGNORE INTO migrated_anthropic_claude_memories
            (account_uuid, conversations_memory, project_memories_json,
             memory_files_json, source_path)
            VALUES (?, ?, ?, ?, ?)
        """, (
            d.get("account_uuid"),
            d.get("conversations_memory"),
            json.dumps(d.get("project_memories", {})),
            json.dumps(d.get("memory_files", {})),
            str(path),
        ))
        if cur.rowcount > 0:
            n += 1
    return n


def migrate_projects(cur: sqlite3.Cursor, raw_dir: Path) -> tuple[int, int]:
    n_proj = n_doc = 0
    proj_dir = raw_dir / "projects-000" / "projects"
    if not proj_dir.exists():
        return 0, 0
    for fn in os.listdir(proj_dir):
        path = proj_dir / fn
        if not path.suffix == ".json":
            continue
        d = load_json(path)
        cur.execute("""
            INSERT OR IGNORE INTO migrated_anthropic_claude_projects
            (external_id, name, description, is_private, is_starter_project,
             prompt_template, created_at, updated_at, creator_uuid, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("uuid"),
            d.get("name"),
            d.get("description"),
            1 if d.get("is_private") else 0,
            1 if d.get("is_starter_project") else 0,
            d.get("prompt_template"),
            d.get("created_at"),
            d.get("updated_at"),
            (d.get("creator") or {}).get("uuid"),
            str(path),
        ))
        if cur.rowcount > 0:
            n_proj += 1
        for doc in d.get("docs", []):
            cur.execute("""
                INSERT OR IGNORE INTO migrated_anthropic_claude_project_docs
                (project_external_id, doc_external_id, filename, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                d.get("uuid"),
                doc.get("uuid"),
                doc.get("filename"),
                doc.get("content"),
                doc.get("created_at"),
            ))
            if cur.rowcount > 0:
                n_doc += 1
    return n_proj, n_doc


def migrate_design_chats(cur: sqlite3.Cursor, raw_dir: Path) -> tuple[int, int]:
    n_chat = n_msg = 0
    dc_dir = raw_dir / "design_chats-000" / "design_chats"
    if not dc_dir.exists():
        return 0, 0
    for fn in os.listdir(dc_dir):
        path = dc_dir / fn
        if not path.suffix == ".json":
            continue
        d = load_json(path)
        cur.execute("""
            INSERT OR IGNORE INTO migrated_anthropic_claude_design_chats
            (external_id, title, project_uuid, project_name, created_at, updated_at, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("uuid"),
            d.get("title"),
            (d.get("project") or {}).get("uuid"),
            (d.get("project") or {}).get("name"),
            d.get("created_at"),
            d.get("updated_at"),
            str(path),
        ))
        if cur.rowcount > 0:
            n_chat += 1
        for m in d.get("messages", []):
            content = m.get("content") or {}
            content_text = content.get("content") if isinstance(content, dict) else str(content)
            cur.execute("""
                INSERT OR IGNORE INTO migrated_anthropic_claude_design_chat_messages
                (chat_external_id, message_external_id, role, created_at,
                 content_text, content_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                d.get("uuid"),
                m.get("uuid"),
                (m.get("content") or {}).get("role") if isinstance(m.get("content"), dict) else m.get("role"),
                m.get("created_at"),
                content_text or "",
                json.dumps(m.get("content")),
            ))
            if cur.rowcount > 0:
                n_msg += 1
    return n_chat, n_msg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    add_common_args(ap, db_required=True)
    args = ap.parse_args()

    if not args.raw_dir.exists():
        print(f"error: raw dir not found: {args.raw_dir}", file=sys.stderr)
        return 1
    if not args.db.exists():
        print(f"error: db not found: {args.db} -- run research_ledger_init.py first", file=sys.stderr)
        return 1

    # guard_then_connect: refuse to write the canonical corpus unless --allow-canonical
    # was passed. The guard is called by guard_and_connect BEFORE the sqlite3.connect.
    conn = guard_and_connect(args.db, args.allow_canonical,
                             pragmas=["foreign_keys = ON", "journal_mode = WAL"])
    cur = conn.cursor()

    print(f"raw dir:  {args.raw_dir}")
    print(f"db:       {args.db}")
    print()

    t0 = time.time()

    print("--- conversations.json ---")
    conv_path = args.raw_dir / "conversations-000" / "conversations.json"
    convs = load_json(conv_path)
    n_conv, n_msg, n_att, n_file = migrate_conversations(cur, convs, str(conv_path))
    print(f"  conversations:  {n_conv:6d}")
    print(f"  messages:       {n_msg:6d}")
    print(f"  attachments:    {n_att:6d}")
    print(f"  file refs:      {n_file:6d}")
    conn.commit()
    print()

    print("--- light_metadata-000 ---")
    n_user, n_login = migrate_light_metadata(cur, args.raw_dir)
    print(f"  users:          {n_user:6d}")
    print(f"  login events:   {n_login:6d}")
    conn.commit()
    print()

    print("--- memories-000 ---")
    n_mem = migrate_memories(cur, args.raw_dir)
    print(f"  memory blobs:   {n_mem:6d}")
    conn.commit()
    print()

    print("--- projects-000 ---")
    n_proj, n_doc = migrate_projects(cur, args.raw_dir)
    print(f"  projects:       {n_proj:6d}")
    print(f"  project docs:   {n_doc:6d}")
    conn.commit()
    print()

    print("--- design_chats-000 ---")
    n_chat, n_dcm = migrate_design_chats(cur, args.raw_dir)
    print(f"  design chats:   {n_chat:6d}")
    print(f"  design msgs:    {n_dcm:6d}")
    conn.commit()
    print()

    print(f"elapsed: {time.time() - t0:.1f}s")
    print()

    print("Spot checks (research_ledger claude rows):")
    for table in [
        "migrated_anthropic_claude_conversations",
        "migrated_anthropic_claude_messages",
        "migrated_anthropic_claude_attachments",
        "migrated_anthropic_claude_files",
        "migrated_anthropic_claude_users",
        "migrated_anthropic_claude_login_events",
        "migrated_anthropic_claude_memories",
        "migrated_anthropic_claude_projects",
        "migrated_anthropic_claude_project_docs",
        "migrated_anthropic_claude_design_chats",
        "migrated_anthropic_claude_design_chat_messages",
    ]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:60s}  {n:6d}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
