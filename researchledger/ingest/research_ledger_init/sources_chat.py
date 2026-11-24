"""Chat-style migrated passthrough schemas.

Schema functions for sources that store conversation transcripts and
metadata captured from chat-style exports / local data:

  - chatgpt (OpenAI ChatGPT takeout)
  - claude  (Anthropic Claude data export)
  - gemini  (Google Gemini takeout)
  - imessage (macOS Messages chat.db)

Each function returns the DDL list expected by `init()` and the
per-source `migrate_*_to_research` script.
"""

from __future__ import annotations


def chatgpt_migrated_schema() -> list[str]:
    """Mirror the actual session_ledger chatgpt tables so migration is trivial.

    These tables are kept under the `migrated_` prefix and referenced via
    source_id=1, kind='session_ledger_migrated'. Migrate_chatgpt_to_research.py
    populates the canonical items/attachments tables from these.

    Columns match session_ledger exactly so INSERT OR IGNORE is a 1:1 pump.
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_openai_chatgpt_conversations (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            title TEXT,
            summary TEXT,
            created_at TEXT,
            updated_at TEXT,
            account_uuid TEXT,
            model TEXT,
            n_messages INTEGER,
            raw_json_path TEXT,
            source_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_openai_chatgpt_messages (
            id INTEGER PRIMARY KEY,
            conversation_external_id TEXT NOT NULL,
            message_external_id TEXT NOT NULL UNIQUE,
            author TEXT,
            role TEXT,
            created_at TEXT,
            updated_at TEXT,
            content_type TEXT,
            content_text TEXT,
            content_json TEXT,
            parent_message_uuid TEXT,
            UNIQUE(conversation_external_id, message_external_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_openai_chatgpt_files (
            id INTEGER PRIMARY KEY,
            conversation_external_id TEXT NOT NULL,
            msg_external_id TEXT,
            file_external_id TEXT NOT NULL,
            name TEXT,
            source_path TEXT,
            UNIQUE(conversation_external_id, file_external_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_openai_chatgpt_attachment_content (
            id INTEGER PRIMARY KEY,
            msg_external_id TEXT,
            conversation_external_id TEXT,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            extracted_content TEXT,
            content_len INTEGER,
            source_path TEXT,
            UNIQUE(msg_external_id, file_name, content_len)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_openai_chatgpt_tool_results (
            id INTEGER PRIMARY KEY,
            message_external_id TEXT NOT NULL,
            conversation_external_id TEXT,
            block_index INTEGER,
            name TEXT,
            tool_call_id TEXT,
            is_error INTEGER,
            content_json TEXT,
            content_len INTEGER,
            UNIQUE(message_external_id, block_index)
        )
        """,
    ]


def claude_migrated_schema() -> list[str]:
    """Anthropic Claude data export passthrough tables.

    Mirrors the JSON shape in claude-20261010/raw/. Claude has 9 data slices:
      - conversations.json (786 convs, 10885 messages, 842 attachments, 2109 file refs)
      - light_metadata/{users.json, login_history.json}
      - memories/<account_uuid>.json (4 keys: conversations_memory, project_memories, memory_files, account_uuid)
      - design_chats/design_chats/<uuid>.json (1 chat, 10 messages)
      - projects/projects/<uuid>.json (12 projects, each with docs[])

    UNIQUE constraints make inserts idempotent (re-running the migration
    is a no-op).
    """
    return [
        # ----- conversations.json -----
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_conversations (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            name TEXT,
            summary TEXT,
            created_at TEXT,
            updated_at TEXT,
            account_uuid TEXT,
            n_messages INTEGER,
            source_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_messages (
            id INTEGER PRIMARY KEY,
            conversation_external_id TEXT NOT NULL,
            message_external_id TEXT NOT NULL UNIQUE,
            sender TEXT,         -- 'human' or 'assistant'
            created_at TEXT,
            updated_at TEXT,
            text TEXT,            -- legacy top-level text (often empty)
            content_json TEXT,    -- canonical content as JSON list of parts
            parent_message_uuid TEXT,
            n_parts INTEGER,
            n_attachments INTEGER,
            n_files INTEGER,
            UNIQUE(conversation_external_id, message_external_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_attachments (
            id INTEGER PRIMARY KEY,
            msg_external_id TEXT,
            conversation_external_id TEXT,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            extracted_content TEXT,
            content_len INTEGER,
            UNIQUE(msg_external_id, file_name, content_len)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_files (
            id INTEGER PRIMARY KEY,
            msg_external_id TEXT,
            conversation_external_id TEXT,
            file_external_id TEXT NOT NULL,
            file_name TEXT,
            UNIQUE(conversation_external_id, msg_external_id, file_external_id)
        )
        """,
        # ----- light_metadata -----
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_users (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            full_name TEXT,
            email_address TEXT,
            verified_phone_number TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_login_events (
            id INTEGER PRIMARY KEY,
            user_external_id TEXT,
            event_json TEXT,
            source_path TEXT,
            UNIQUE(user_external_id, event_json)
        )
        """,
        # ----- memories -----
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_memories (
            id INTEGER PRIMARY KEY,
            account_uuid TEXT NOT NULL UNIQUE,
            conversations_memory TEXT,
            project_memories_json TEXT,
            memory_files_json TEXT,
            source_path TEXT
        )
        """,
        # ----- projects -----
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_projects (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            name TEXT,
            description TEXT,
            is_private INTEGER,
            is_starter_project INTEGER,
            prompt_template TEXT,
            created_at TEXT,
            updated_at TEXT,
            creator_uuid TEXT,
            source_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_project_docs (
            id INTEGER PRIMARY KEY,
            project_external_id TEXT NOT NULL,
            doc_external_id TEXT NOT NULL,
            filename TEXT,
            content TEXT,
            created_at TEXT,
            UNIQUE(project_external_id, doc_external_id)
        )
        """,
        # ----- design_chats -----
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_design_chats (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            title TEXT,
            project_uuid TEXT,
            project_name TEXT,
            created_at TEXT,
            updated_at TEXT,
            source_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_anthropic_claude_design_chat_messages (
            id INTEGER PRIMARY KEY,
            chat_external_id TEXT NOT NULL,
            message_external_id TEXT NOT NULL UNIQUE,
            role TEXT,
            created_at TEXT,
            content_text TEXT,
            content_json TEXT,
            UNIQUE(chat_external_id, message_external_id)
        )
        """,
    ]


def gemini_migrated_schema() -> list[str]:
    """Google Gemini takeout passthrough tables.

    Mirrors the HTML shape in gemini-20261010/raw/Takeout/My Activity/Gemini Apps/.
    Gemini takeout gives us activity history (prompt + response summary) per
    record. 760 records in the 11MB MyActivity.html, plus 342 media files
    (199 MB) in the same directory that the records reference.

    Note: only 717/760 records have a gemini.google.com/app/<id> URL; the
    other 43 are image-only metadata (no prompt, just the generated image).
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_google_gemini_records (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            gemini_id TEXT,                 -- the gemini.google.com/app/<id> suffix
            url TEXT,                       -- https://gemini.google.com/app/<id>
            title TEXT,                     -- always 'Gemini Apps' for now
            date_display TEXT,              -- 'Sep 25, 2026, 2:32:49 PM EDT'
            date_iso TEXT,                  -- normalized to ISO 8601 UTC
            prompt_text TEXT,               -- the user's input
            response_text TEXT,             -- gemini's response
            has_image INTEGER,              -- 1 if record references a generated image
            image_url TEXT,                 -- gemini cdn url if present
            caption_html TEXT,              -- the original caption cell HTML
            source_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_google_gemini_media (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT,
            byte_size INTEGER,
            mime_type TEXT,
            UNIQUE(file_path)
        )
        """,
    ]


def imessage_migrated_schema() -> list[str]:
    """
    iMessage / SMS passthrough tables (read from ~/Library/Messages/chat.db in mode=ro).

    Tables:
      migrated_imessage_chats       — one row per chat (DM or group)
      migrated_imessage_handles     — one row per phone/email contact
      migrated_imessage_messages    — one row per message (text + reactions + tap-backs)
      migrated_imessage_attachments — one row per file attachment joined to a message

    Date convention: macOS stores `date` in chat.db as nanoseconds since
    2001-01-01 UTC (Apple Cocoa Core Data, post-High-Sierra). We convert to
    ISO 8601 UTC at migration time so the canonical layer + FTS5 see only
    plain strings. The original nanosecond value is preserved in `date_raw_ns`
    for forensic round-tripping.

    PII policy: phone numbers and email addresses are operator's own data
    (this is the operator's local chat.db). We store them in handle_id as
    raw strings with redaction_state='none' — consistent with chatgpt/claude/gemini.
    To redact, set redaction_state on the source row.
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_imessage_chats (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'chat:<ROWID>'
            chat_guid TEXT,
            service_name TEXT,                       -- 'iMessage' or 'SMS'
            style INTEGER,                           -- 43=1:1, 45=group
            display_name TEXT,                       -- null for 1:1, group name for groups
            chat_identifier TEXT,                    -- e.g. '+15555550100' or 'chat123...'
            is_archived INTEGER,
            last_read_message_iso TEXT,              -- ISO UTC
            message_count INTEGER                    -- post-filter count
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_imessage_handles (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'handle:<ROWID>'
            handle_rowid INTEGER NOT NULL,           -- chat.db handle.ROWID
            service TEXT,                            -- 'iMessage' or 'SMS'
            uncanonicalized_id TEXT,                 -- raw phone/email
            country TEXT,
            is_me_handle INTEGER DEFAULT 0           -- 1 if this is the operator's own handle
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_imessage_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'msg:<ROWID>'
            msg_guid TEXT,
            chat_external_id TEXT NOT NULL,          -- FK to migrated_imessage_chats.external_id
            handle_external_id TEXT,                 -- FK to migrated_imessage_handles.external_id
            is_from_me INTEGER,                      -- 1=sent, 0=received
            text TEXT,                               -- raw text body (null for reactions / non-text)
            date_iso TEXT NOT NULL,                  -- sent timestamp ISO UTC
            date_raw_ns INTEGER,                     -- original ns since 2001-01-01
            date_read_iso TEXT,
            date_delivered_iso TEXT,
            is_empty INTEGER,                        -- 1 if no text (taps, reactions, file-only)
            is_read INTEGER,
            is_delivered INTEGER,
            is_audio_message INTEGER,
            is_archive INTEGER,
            has_attachments INTEGER,                 -- 1 if any attachment joined
            service TEXT,                            -- 'iMessage' or 'SMS'
            item_type INTEGER,                       -- apple message.item_type
            associated_message_type INTEGER          -- apple reply/Reaction type (0=none)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_imessage_attachments (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'attach:<ROWID>'
            msg_external_id TEXT NOT NULL,           -- FK to migrated_imessage_messages.external_id
            attach_guid TEXT,
            filename TEXT,
            mime_type TEXT,
            byte_size INTEGER,
            uti TEXT,                                -- uniform type identifier
            is_sticker INTEGER,
            is_outgoing INTEGER,
            local_path TEXT                          -- resolved path under ~/Library/Messages/Attachments/
        )
        """,
    ]
