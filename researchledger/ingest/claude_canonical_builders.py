"""claude_canonical_builders.py — emit items/attachments rows from migrated_anthropic_claude_*.

Pure insertion logic. The orchestrator (claude_build_canonical.py) decides phase
order, opens the connection, and prints phase summaries; this module only knows
how to scan one migrated_* table and INSERT OR IGNORE into items/attachments.

Public names are re-exported from claude_build_canonical.py so callers can write:

    from claude_build_canonical import build_messages, PHASE_FNS
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone


CLAUDE_SOURCE_ID = 2  # matches the row in `sources` registered by claude_migrate_to_research.py
DEFAULT_REDACTION_STATE = "partial"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(s: str | None, n: int = 16) -> str | None:
    if not s:
        return None
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:n]


def extract_text_from_content_json(content_json: str | None, text: str | None) -> str:
    """Extract plain text from a claude content_json blob.

    claude stores message body as a JSON list of parts. Each part has
    type='text'|'tool_use'|'tool_result'|'thinking'|'token_budget'.
    Only 'text' parts contribute to body. Other types are dropped.
    """
    if text and text.strip():
        return text
    if not content_json or not content_json.strip():
        return ""
    try:
        parsed = json.loads(content_json)
    except (ValueError, TypeError):
        return content_json
    parts: list[str] = []
    if isinstance(parsed, list):
        for p in parsed:
            if isinstance(p, dict) and p.get("type") == "text":
                v = p.get("text")
                if isinstance(v, str) and v.strip():
                    parts.append(v)
    elif isinstance(parsed, dict):
        v = parsed.get("text") or parsed.get("content")
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return "\n".join(parts)


def build_conversations(dst: sqlite3.Connection) -> int:
    rows = dst.execute("""
        SELECT external_id, name, summary, created_at, updated_at, n_messages
        FROM migrated_anthropic_claude_conversations
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_conversation',
                ?, ?, json_object('summary', ?, 'n_messages', ?, 'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    for r in rows:
        ext, name, summary, created_at, updated_at, n_msgs = r
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            name,
            summary or "",
            summary, n_msgs,
        ))
        n += 1
    return n


def build_messages(dst: sqlite3.Connection) -> int:
    rows = dst.execute("""
        SELECT conversation_external_id, message_external_id, sender,
               created_at, updated_at, text, content_json, parent_message_uuid,
               n_parts, n_attachments, n_files
        FROM migrated_anthropic_claude_messages
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, author, title, body, parent_id, dedupe_hash,
             attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_message',
                ?, ?, ?, ?, ?,
                json_object('n_parts', ?, 'n_attachments', ?, 'n_files', ?,
                            'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    conv_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='claude_conversation'",
        (CLAUDE_SOURCE_ID,)).fetchall()}
    for r in rows:
        (conv_ext, msg_ext, sender, created_at, updated_at, text, cjson,
         parent_uuid, n_parts, n_attachments, n_files) = r
        parent_id = conv_map.get(conv_ext)
        body = extract_text_from_content_json(cjson, text)
        dh = sha256_hex(f"claude:{conv_ext}:{msg_ext}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, msg_ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            sender,        # author = human or assistant
            None,          # no title for messages
            body,
            parent_id,
            dh,
            n_parts, n_attachments, n_files,
        ))
        n += 1
    return n


def build_memories(dst: sqlite3.Connection) -> int:
    """The user's memory blob — conversations_memory, project_memories, memory_files."""
    rows = dst.execute("""
        SELECT account_uuid, conversations_memory, project_memories_json,
               memory_files_json
        FROM migrated_anthropic_claude_memories
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, dedupe_hash, attrs_json)
        VALUES (?, ?, ?, NULL, 'direct', 'high', ?, 'claude_memory',
                ?, ?, ?, json_object('account_uuid', ?, 'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    for r in rows:
        account_uuid, cmemory, pmemory_json, mfiles_json = r
        body = cmemory or ""
        ext = f"memory:{account_uuid}"
        dh = sha256_hex(f"claude:memory:{account_uuid}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, ext, captured,
            DEFAULT_REDACTION_STATE,
            f"User memory ({account_uuid[:8]})",
            body,
            dh,
            account_uuid,
        ))
        # Stash the structured fields in the item's attrs_json
        # Note: we just put account_uuid above; the raw blob is in the migrated
        # table and accessible by joining. Keeping attrs_json small.
        n += 1
    return n


def build_projects(dst: sqlite3.Connection) -> int:
    rows = dst.execute("""
        SELECT external_id, name, description, is_private, is_starter_project,
               prompt_template, created_at, updated_at, creator_uuid
        FROM migrated_anthropic_claude_projects
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, dedupe_hash, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_project',
                ?, ?, ?, json_object('description', ?, 'is_private', ?, 'is_starter', ?,
                            'creator_uuid', ?, 'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    for r in rows:
        (ext, name, desc, is_priv, is_starter, prompt_t, created_at,
         updated_at, creator_uuid) = r
        body = desc or ""
        dh = sha256_hex(f"claude:project:{ext}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            name,
            body,
            dh,
            desc, is_priv, is_starter, creator_uuid,
        ))
        n += 1
    return n


def build_project_docs(dst: sqlite3.Connection) -> int:
    """Each doc has a real content body — FTS5-searchable."""
    rows = dst.execute("""
        SELECT project_external_id, doc_external_id, filename, content, created_at
        FROM migrated_anthropic_claude_project_docs
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, parent_id, dedupe_hash, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_project_doc',
                ?, ?, ?, ?, json_object('filename', ?, 'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    proj_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='claude_project'",
        (CLAUDE_SOURCE_ID,)).fetchall()}
    for r in rows:
        proj_ext, doc_ext, filename, content, created_at = r
        parent_id = proj_map.get(proj_ext)
        body = content or ""
        dh = sha256_hex(f"claude:project_doc:{doc_ext}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, doc_ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            filename,
            body,
            parent_id,
            dh,
            filename,
        ))
        n += 1
    return n


def build_design_chats(dst: sqlite3.Connection) -> int:
    rows = dst.execute("""
        SELECT external_id, title, project_uuid, project_name, created_at, updated_at
        FROM migrated_anthropic_claude_design_chats
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, title, body, dedupe_hash, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_design_chat',
                ?, ?, ?, json_object('project_uuid', ?, 'project_name', ?, 'platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    for r in rows:
        ext, title, project_uuid, project_name, created_at, updated_at = r
        body = title or ""
        dh = sha256_hex(f"claude:design_chat:{ext}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            title,
            body,
            dh,
            project_uuid, project_name,
        ))
        n += 1
    return n


def build_design_chat_messages(dst: sqlite3.Connection) -> int:
    rows = dst.execute("""
        SELECT chat_external_id, message_external_id, role, created_at,
               content_text, content_json
        FROM migrated_anthropic_claude_design_chat_messages
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO items
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_kind, author, title, body, parent_id, dedupe_hash, attrs_json)
        VALUES (?, ?, ?, ?, 'direct', 'high', ?, 'claude_design_chat_message',
                ?, ?, ?, ?, ?, json_object('platform', 'claude'))
    """
    n = 0
    captured = now_iso()
    chat_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='claude_design_chat'",
        (CLAUDE_SOURCE_ID,)).fetchall()}
    for r in rows:
        chat_ext, msg_ext, role, created_at, content_text, content_json = r
        parent_id = chat_map.get(chat_ext)
        body = content_text or ""
        dh = sha256_hex(f"claude:design_msg:{msg_ext}")
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, msg_ext, captured, created_at,
            DEFAULT_REDACTION_STATE,
            role,
            None,
            body,
            parent_id,
            dh,
        ))
        n += 1
    return n


def build_files_attachments(dst: sqlite3.Connection) -> int:
    """One attachment per attachment row, attached to its message."""
    rows = dst.execute("""
        SELECT msg_external_id, conversation_external_id, file_name,
               file_size, file_type, extracted_content, content_len
        FROM migrated_anthropic_claude_attachments
    """).fetchall()
    sql = """
        INSERT OR IGNORE INTO attachments
            (source_id, external_id, captured_at, source_captured_at,
             evidence_type, confidence, redaction_state,
             item_id, kind, byte_size, mime_type, extracted_text)
        VALUES (?, ?, ?, NULL, 'direct', 'high', ?, ?, 'file', ?, ?, ?)
    """
    n = 0
    captured = now_iso()
    msg_map = {r[0]: r[1] for r in dst.execute(
        "SELECT external_id, id FROM items WHERE source_id=? AND item_kind='claude_message'",
        (CLAUDE_SOURCE_ID,)).fetchall()}
    for r in rows:
        msg_ext, conv_ext, file_name, file_size, file_type, content, content_len = r
        item_id = msg_map.get(msg_ext)
        ext = f"{msg_ext}:{file_name}:{content_len}"
        dst.execute(sql, (
            CLAUDE_SOURCE_ID, ext, captured,
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
    "memories": build_memories,
    "projects": build_projects,
    "project_docs": build_project_docs,
    "design_chats": build_design_chats,
    "design_chat_messages": build_design_chat_messages,
    "files_attachments": build_files_attachments,
}
