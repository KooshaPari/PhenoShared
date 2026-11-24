"""Harness / IDE-IDE-coding migrated passthrough schemas.

Schema functions for sources that store full conversation transcripts
captured locally by AI coding harnesses and IDE-resident chat tools.

  - jcode  (jcode JSON sessions)
  - kcode  (kcode JSON sessions, jcode fork)
  - codex  (OpenAI Codex CLI, .jsonl rollouts)
  - forge  (ForgeCode / unified-prompts.db)
  - cursor (Cursor IDE chats store.db)

Each function returns the DDL list expected by `init()` and the
per-source `migrate_*_to_research` script.
"""

from __future__ import annotations


def jcode_migrated_schema() -> list[str]:
    """
    jcode passthrough tables (read from ~/.jcode/sessions/session_*.json).

    Each session is one .json file with: id, parent_id, title, created_at,
    updated_at, messages[], provider_key, model, is_canary, working_dir,
    short_name, status, last_pid, last_active_at, is_debug, saved, save_label.

    Each message has: id, role (user/assistant/tool), content (array of blocks),
    timestamp, token_usage. Content blocks can be: text, reasoning, tool_use,
    tool_result, image, audio, document, etc.

    We split sessions vs messages so that 'jcode_session' is one canonical
    item and 'jcode_message' is another (one per message in the session),
    matching the chatgpt/claude pattern (where one session has many messages).
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_jcode_sessions (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'jcode_session:<session_id>'
            session_id TEXT NOT NULL,                -- the .json id (session_<short>_<ts>_<hash>)
            short_name TEXT,                         -- 'ant', 'skunk', etc.
            title TEXT,                              -- operator-set session title (often null)
            parent_id TEXT,                          -- parent session if this is a child
            provider_key TEXT,                       -- 'opencode-go', 'openai-api', etc.
            provider_session_id TEXT,                -- upstream provider session id (if any)
            model TEXT,                              -- e.g. 'mimo-v2.5', 'gpt-6-astra'
            reasoning_effort TEXT,
            subagent_model TEXT,
            is_canary INTEGER,
            is_debug INTEGER,
            working_dir TEXT,
            status_json TEXT,                        -- raw status (string or {Crashed: ...} dict)
            created_at TEXT,                         -- ISO UTC
            updated_at TEXT,                         -- ISO UTC
            last_active_at TEXT,
            message_count INTEGER,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_cache_read_tokens INTEGER DEFAULT 0,
            saved INTEGER,
            save_label TEXT,
            raw_json_path TEXT                       -- absolute path to source .json file
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_jcode_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'jcode_msg:<message_id>'
            msg_id TEXT NOT NULL,                    -- jcode message.id
            session_external_id TEXT NOT NULL,       -- FK to migrated_jcode_sessions.external_id
            role TEXT,                               -- 'user' | 'assistant' | 'tool'
            timestamp_iso TEXT,                      -- ISO UTC
            content_text TEXT,                       -- concatenated text content (may be null for tool-only)
            content_json TEXT,                       -- full raw content array as JSON
            block_count INTEGER,                     -- number of content blocks
            text_block_count INTEGER,
            tool_use_count INTEGER,
            tool_result_count INTEGER,
            image_block_count INTEGER,
            reasoning_block_count INTEGER,
            tool_use_names TEXT,                     -- comma-separated tool names used
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read_input_tokens INTEGER
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_jcode_messages_session
            ON migrated_jcode_messages (session_external_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_jcode_messages_role
            ON migrated_jcode_messages (role)
        """,
    ]


def kcode_migrated_schema() -> list[str]:
    """
    kcode passthrough tables (read from ~/.kcode/sessions/session_*.json).

    kcode is the KooshaPari fork of jcode. Session format is 99% identical
    to jcode: same id/parent_id/title/messages[]/provider_key/model/working_dir/
    status. Differences:
      - kcode has `fork_depth`, `fork_max_depth` (no `short_name`)
      - kcode is much smaller (~385 files, ~1K messages vs jcode's 4,349 / 435K)
      - kcode has many test/mock/panic-on-fork sessions (developer was iterating
        on the fork itself)

    We mirror the jcode schema 1:1 but with `kcode_` table names. The two
    pipelines (jcode_migrate_to_research + kcode_migrate_to_research) share
    the same downstream canonical shape (jcode_session/jcode_message items
    vs kcode_session/kcode_message items) but with kind='kcode' for
    attribution.
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_kcode_sessions (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'kcode_session:<session_id>'
            session_id TEXT NOT NULL,
            title TEXT,
            parent_id TEXT,
            provider_key TEXT,
            provider_session_id TEXT,
            model TEXT,
            reasoning_effort TEXT,
            subagent_model TEXT,
            is_canary INTEGER,
            is_debug INTEGER,
            working_dir TEXT,
            status_json TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_active_at TEXT,
            message_count INTEGER,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_cache_read_tokens INTEGER DEFAULT 0,
            saved INTEGER,
            save_label TEXT,
            fork_depth INTEGER,                      -- kcode-specific
            fork_max_depth INTEGER,                  -- kcode-specific
            raw_json_path TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_kcode_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'kcode_msg:<session_id>:<msg_id>'
            msg_id TEXT NOT NULL,
            session_external_id TEXT NOT NULL,
            role TEXT,
            timestamp_iso TEXT,
            content_text TEXT,
            content_json TEXT,
            block_count INTEGER,
            text_block_count INTEGER,
            tool_use_count INTEGER,
            tool_result_count INTEGER,
            image_block_count INTEGER,
            reasoning_block_count INTEGER,
            tool_use_names TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read_input_tokens INTEGER
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_kcode_messages_session
            ON migrated_kcode_messages (session_external_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_kcode_messages_role
            ON migrated_kcode_messages (role)
        """,
    ]


def codex_migrated_schema() -> list[str]:
    """
    codex passthrough tables (read from ~/.codex/sessions/*/rollout-*.jsonl).

    codex is the OpenAI Codex CLI. Session format is COMPLETELY different from
    jcode/kcode:
      - One .jsonl file per snapshot; many snapshots per session
      - One LINE per event (not per message)
      - 8 line types: session_meta, event_msg, response_item, world_state,
        turn_context, token_usage_record, inter_agent_communication_metadata,
        compacted
      - response_item.payload.type discriminates: "message" (user/assistant/
        developer text), "reasoning", "function_call", "function_call_output",
        "custom_tool_call", "agent_message"
      - model name lives in turn_context.payload.model (one per turn, may vary)
      - token totals in token_usage_record lines (per-response usage field)

    We use the LARGEST .jsonl per session_id as the canonical snapshot
    (smaller files are intermediate states; biggest is the most complete).

    Schema mirrors jcode/kcode but with kcode-specific extras:
      - cli_version (from session_meta)
      - model_provider (from session_meta, usually "openai")
      - source (from session_meta, e.g. "vscode" or "codex-tui")
      - originator (from session_meta, e.g. "codex-tui")
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_codex_sessions (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'codex_session:<session_id>'
            session_id TEXT NOT NULL,                -- uuid
            title TEXT,                              -- usually null for codex
            parent_id TEXT,                          -- not used by codex
            provider_key TEXT,                       -- 'openai' from session_meta
            provider_session_id TEXT,                -- same as session_id
            model TEXT,                              -- e.g. 'gpt-6-luna' (last turn_context)
            reasoning_effort TEXT,                   -- from turn_context.effort
            subagent_model TEXT,                     -- not used by codex
            is_canary INTEGER,                       -- not used
            is_debug INTEGER,                        -- not used
            working_dir TEXT,                        -- session_meta.payload.cwd
            status_json TEXT,                        -- not used (live sessions)
            created_at TEXT,                         -- session_meta.payload.timestamp
            updated_at TEXT,                         -- last event timestamp
            last_active_at TEXT,
            message_count INTEGER,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_cache_read_tokens INTEGER DEFAULT 0,
            cli_version TEXT,                        -- session_meta.cli_version
            source TEXT,                             -- session_meta.source (str or 'subagent' if dict)
            originator TEXT,                         -- session_meta.originator
            source_meta_json TEXT,                   -- JSON for dict source (subagent info)
            subagent_parent_id TEXT,                 -- from source.subagent.thread_spawn.parent_thread_id
            subagent_nickname TEXT,                  -- e.g. 'Wegener', 'Hegel', 'Tesla'
            subagent_role TEXT,                      -- e.g. 'worker', 'sswe-tpm-researcher'
            subagent_path TEXT,                      -- e.g. '/root/jcode_stack_reconcile'
            source_path TEXT,                        -- path to the largest .jsonl file
            snapshot_count INTEGER,                  -- how many .jsonl files for this session
            rollup_size_bytes INTEGER                 -- size of the chosen snapshot
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_codex_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'codex_msg:<session_id>:<payload_id>'
            msg_id TEXT NOT NULL,                    -- response_item.payload.id (or generated)
            session_external_id TEXT NOT NULL,
            role TEXT,                               -- 'user' | 'assistant' | 'tool' | 'developer'
            timestamp_iso TEXT,                      -- line.timestamp
            content_text TEXT,                       -- extracted text/function_call digest
            content_json TEXT,                       -- full raw content as JSON
            block_count INTEGER,                     -- number of content blocks
            text_block_count INTEGER,
            tool_use_count INTEGER,
            tool_result_count INTEGER,
            image_block_count INTEGER,
            reasoning_block_count INTEGER,
            custom_tool_call_count INTEGER,
            tool_use_names TEXT,                     -- comma-separated function_call names
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_input_tokens INTEGER DEFAULT 0
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_codex_messages_session
            ON migrated_codex_messages (session_external_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_codex_messages_role
            ON migrated_codex_messages (role)
        """,
    ]


def forge_migrated_schema() -> list[str]:
    """
    forge (ForgeCode) passthrough tables (read from ~/.forge/prompt-corpus/unified-prompts.db).

    forge is a Rust-based agent (KooshaPari/forgecode fork). The session model
    is COMPLETELY different from jcode/kcode/codex:
      - The .forge.db (2.99 GB) is essentially empty (only diesel schema
        migrations) -- the actual prompt store was extracted to a separate
        .db/json corpus under ~/.forge/prompt-corpus/ on 2026-06-13.
      - unified-prompts.db is a flat `prompts` table (one row per prompt,
        not per conversation). 75,342 rows total.
      - 63,075 prompts are forge-specific (from `database` and `history`
        sources); 12,219 are codex (from forge's view of ~/.codex history,
        pre-W9c).
      - Prompts only (user messages); no assistant responses are captured.
      - Date range: 2026-03-25 to 2026-06-13 (4 months, pre-W9c).
      - Conversation IDs are NOT compatible with jcode (different namespace).
      - Source dirs in priority order: ~/.forge/prompt-corpus/

    Forge snapshots/ directory (350 MB, 4925 subdirs) is FILE CONTENT
    snapshots, not conversation data -- skipped.

    Forge logs/ (147 MB) are debug logs (provider events, deserialization
    events) -- not conversation data -- skipped.

    Schema mirrors jcode/kcode but with forge-specific extras:
      - source_tool (forge/codex/claude/cursor -- what tool produced this)
      - source (database/history -- forge's internal category)
      - conversation_id (forge's UUID for the conversation)
      - workspace_id (forge workspace numeric ID)
      - message_index (position within conversation)
      - content_hash (SHA256 of content for dedup)
      - title (from forge metadata, e.g. "[PARENT] **Forge Metal Objects**")
      - created_at (forge's local datetime, "YYYY-MM-DD HH:MM:SS.fff")
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_forge_prompts (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'forge_prompt:<forge_prompt_id>'
            forge_prompt_id TEXT NOT NULL,           -- the UUID forge gave this prompt
            conversation_id TEXT,                    -- forge's UUID for the conversation
            workspace_id TEXT,                       -- forge's numeric workspace ID
            message_index INTEGER,                    -- position within conversation
            source_tool TEXT,                         -- forge / codex / claude / cursor
            source TEXT,                             -- database / history (forge internal)
            content_hash TEXT,                       -- SHA256 of content (dedup key)
            title TEXT,                              -- forge's title for the conversation
            created_at TEXT,                         -- forge local "YYYY-MM-DD HH:MM:SS.fff"
            extracted_at TEXT,                       -- ISO when forge extracted this
            content_text TEXT,                       -- the actual prompt content
            content_length INTEGER,                  -- len(content_text) for stats
            content_json TEXT,                       -- full raw content as JSON
            metadata_json TEXT                       -- full forge metadata as JSON
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_forge_prompts_conv
            ON migrated_forge_prompts (conversation_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_forge_prompts_tool
            ON migrated_forge_prompts (source_tool)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_forge_prompts_created
            ON migrated_forge_prompts (created_at)
        """,
    ]


def cursor_migrated_schema() -> list[str]:
    """
    cursor (Cursor IDE) passthrough tables (read from ~/.cursor/chats/<hash>/<uuid>/).

    Cursor is the Anysphere IDE with built-in AI chat. The session model
    is COMPLETELY different from jcode/kcode/codex/forge:
      - 5 chat-hash directories under ~/.cursor/chats/
      - Each chat = a subdirectory with <chat-uuid> as its name
      - Each chat contains: meta.json, store.db, store.db-shm, store.db-wal
      - meta.json has: schemaVersion=1, createdAtMs, updatedAtMs,
        hasConversation, isSubagent (93% of chats are sub-agents!), cwd
      - store.db has a single 'blobs' table (id TEXT PK, data BLOB)
        where data is a JSON message: {role, content} or
        {role, content, tool_calls, tool_call_id}
      - Roles: system (with AI persona like "GPT-5.6 Luna"), user, assistant
      - 707 chats, 253,410 blobs (messages) total
      - Date range: 2026-07-17 to 2026-10-14 (3 months)
      - Sub-agent threads have minimal meta (no cwd) -- they're spawned
        from the parent chat
      - Single biggest chat has 25,632 blobs

    Cursor ai-code-tracking.db (90 MB) tracks AI code edits (575 rows).
    This is a code-edit log, not conversation data -- skipped.

    Cursor projects/ (160 MB) contains workspace state -- skipped.

    Schema mirrors jcode/kcode but with cursor-specific extras:
      - chat_hash (5-char dir under chats/)
      - meta_schema_version, meta_has_conversation, meta_is_subagent
      - cwd (working dir, may be null for sub-agents)
      - chat_blob_count (how many blobs in this chat's store.db)
      - model (extracted from system prompt: "You are GPT-5.6 Luna")
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_cursor_chats (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'cursor_chat:<chat_uuid>'
            chat_uuid TEXT NOT NULL,
            chat_hash TEXT,                          -- 5-char dir under chats/
            created_at_ms INTEGER,                   -- meta.createdAtMs
            updated_at_ms INTEGER,                   -- meta.updatedAtMs
            cwd TEXT,                                -- meta.cwd (may be null)
            is_subagent INTEGER,                     -- meta.isSubagent (1/0)
            has_conversation INTEGER,                -- meta.hasConversation
            schema_version INTEGER,                  -- meta.schemaVersion (always 1)
            chat_blob_count INTEGER,                 -- count of blobs in store.db
            model TEXT,                              -- extracted from first system blob
            source_path TEXT,                        -- path to chat dir
            meta_json TEXT                           -- full meta.json dump
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_cursor_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'cursor_msg:<chat_uuid>:<blob_id>'
            chat_external_id TEXT NOT NULL,
            chat_uuid TEXT NOT NULL,
            blob_id TEXT NOT NULL,                   -- blob.id (sha256 hex)
            ordinal INTEGER,                         -- order within chat (alphabetical by id)
            role TEXT,                               -- 'system' | 'user' | 'assistant' | 'tool'
            content_text TEXT,                       -- extracted text content
            content_length INTEGER,                  -- len(content_text) for stats
            content_json TEXT,                       -- full raw blob data as JSON
            has_tool_calls INTEGER,                  -- 1 if message has tool_calls
            tool_call_names TEXT,                    -- comma-separated tool names if any
            blob_index INTEGER,                      -- index of blob in chat (by rowid)
            chat_created_at_ms INTEGER               -- denormalized from chat
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_cursor_messages_chat
            ON migrated_cursor_messages (chat_external_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_cursor_messages_role
            ON migrated_cursor_messages (role)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_cursor_chats_hash
            ON migrated_cursor_chats (chat_hash)
        """,
    ]
