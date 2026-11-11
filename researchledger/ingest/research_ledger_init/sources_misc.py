"""claude_desktop migrated passthrough schemas.

Schema function for the local Claude Code CLI store (`~/.claude/`):
  - claude_desktop (Anthropic Claude Code CLI: __store.db + history.jsonl + memory notes)

This module is split out from the harness group because the data shape is
fundamentally different (server-side transcripts) and pulling it in next to
jcode/kcode/codex would muddy the boundary.
"""

from __future__ import annotations


def claude_desktop_migrated_schema() -> list[str]:
    """
    claude_desktop (Claude Code CLI) passthrough tables (read from ~/.claude/).

    Claude Code CLI does NOT store full conversation transcripts locally
    in the same way jcode/kcode/codex do. The actual conversation data
    is stored server-side at Anthropic. Locally we have:

      1. __store.db (drizzle sqlite, small)
         - base_messages: 39 rows (uuid, parent_uuid, session_id, timestamp, ...)
         - user_messages: 22 rows (uuid FK, message, tool_use_result, timestamp, is_meta, is_at_mention_read)
         - assistant_messages: 17 rows (uuid FK, cost_usd, duration_ms, message JSON, model, is_api_error_message)
         - conversation_summaries: 2 rows (leaf_uuid, summary, updated_at)

      2. history.jsonl (12,958 user commands, Sept 2025 → Sept 2026)
         - display, pastedContents, timestamp, project
         - just user commands, no assistant responses

      3. projects/*/memory/*.md (292 markdown notes across all projects)
         - session memory summaries
         - SKIPPED in this round (treated as standalone artifacts)

    Two tables:
      migrated_claude_desktop_messages  -- from __store.db (full convo pairs)
      migrated_claude_desktop_history   -- from history.jsonl (just user commands)
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS migrated_claude_desktop_messages (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'claude_desktop_msg:<uuid>'
            uuid TEXT NOT NULL,
            parent_uuid TEXT,
            session_id TEXT,
            timestamp_ms INTEGER,
            message_type TEXT,                       -- 'user' | 'assistant' | etc.
            cwd TEXT,
            user_type TEXT,                          -- 'external' | 'internal' etc
            version TEXT,
            is_sidechain INTEGER,
            original_cwd TEXT,
            -- user_messages columns
            user_message TEXT,
            tool_use_result TEXT,
            is_at_mention_read INTEGER,
            is_meta INTEGER,
            -- assistant_messages columns
            cost_usd REAL,
            duration_ms INTEGER,
            assistant_message TEXT,                  -- JSON dump of message
            is_api_error_message INTEGER,
            assistant_model TEXT,
            -- conversation_summaries columns
            conversation_summary TEXT,
            summary_updated_at_ms INTEGER,
            -- common
            source_path TEXT
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_messages_session
            ON migrated_claude_desktop_messages (session_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_messages_type
            ON migrated_claude_desktop_messages (message_type)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_messages_ts
            ON migrated_claude_desktop_messages (timestamp_ms)
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_claude_desktop_history (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'claude_desktop_hist:<ts>:<idx>'
            timestamp_ms INTEGER,
            display TEXT,                            -- the user command text
            project TEXT,                            -- cwd at time of command
            pasted_contents_json TEXT,               -- JSON dump of pastedContents
            source_path TEXT
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_history_ts
            ON migrated_claude_desktop_history (timestamp_ms)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_history_project
            ON migrated_claude_desktop_history (project)
        """,
        """
        CREATE TABLE IF NOT EXISTS migrated_claude_desktop_memory_notes (
            id INTEGER PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,        -- 'claude_desktop_mem:<project_hash>:<filename_stem>'
            filename TEXT NOT NULL,
            project_path TEXT,                        -- parent project dir
            file_path TEXT NOT NULL,                  -- full path
            byte_size INTEGER,
            line_count INTEGER,
            frontmatter_json TEXT,                    -- parsed YAML frontmatter as JSON
            first_heading TEXT,                       -- first markdown heading
            content_text TEXT,                        -- full markdown body
            modified_at_ms INTEGER,
            captured_at TEXT
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_memory_project
            ON migrated_claude_desktop_memory_notes (project_path)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_migrated_claude_desktop_memory_filename
            ON migrated_claude_desktop_memory_notes (filename)
        """,
    ]
