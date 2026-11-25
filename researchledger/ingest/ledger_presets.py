"""Preset definitions for ask_ledger.py — pure data, no logic.

Round-7 (W7-1.1): split out of ask_ledger.py to bring that file back under
the 500-line hard limit (it had grown to 544 lines by the end of round-6).
This module holds only the three preset dicts; all execution logic stays in
ask_ledger.py.

Each dict maps a preset name to a tuple consumed by ask_ledger.main():

  PRESETS         -> {name: (description, sql)}       run via conn.execute(sql)
  PYTHON_PRESETS  -> {name: description}               dispatched in main()
  INSPECT_QUERIES -> {name: (description, sql)}        schema introspection

ask_ledger_mcp.py auto-reloads this module (and ask_ledger) when its mtime
changes, so editing a preset here is picked up on the next MCP call without
a server restart.
"""

# --preset definitions. Each is a (description, sql) pair.
PRESETS = {
    "counts": (
        "Per-harness/device session counts",
        "SELECT harness, device, COUNT(*) AS n FROM sessions GROUP BY harness, device ORDER BY device, harness",
    ),
    "by-harness": (
        "Per-harness total counts (all devices)",
        "SELECT harness, COUNT(*) AS n FROM sessions GROUP BY harness ORDER BY n DESC",
    ),
    "by-day": (
        "Per-day session counts (last 30 days)",
        "SELECT DATE(started_at) AS day, COUNT(*) AS n FROM sessions "
        "WHERE started_at IS NOT NULL AND started_at >= DATE('now', '-30 days') "
        "GROUP BY DATE(started_at) ORDER BY day DESC",
    ),
    "by-model": (
        "Top 20 models by session count",
        "SELECT model, COUNT(*) AS n FROM sessions "
        "WHERE model IS NOT NULL GROUP BY model ORDER BY n DESC LIMIT 20",
    ),
    "recent": (
        "Most recent 10 sessions",
        "SELECT harness, device, session_id, started_at, model, title "
        "FROM sessions ORDER BY started_at DESC LIMIT 10",
    ),
    "spend": (
        "Provider spend (most recent day per provider)",
        "SELECT provider, day_date, day_usd, month_usd, all_time_usd "
        "FROM provider_spend ORDER BY all_time_usd DESC",
    ),
    "spend-today": (
        "Provider spend for the most recent day (today if present, else latest day)",
        "WITH latest AS (SELECT MAX(day_date) AS d FROM provider_spend) "
        "SELECT provider, day_date, day_usd, month_usd, all_time_usd "
        "FROM provider_spend WHERE day_date = (SELECT d FROM latest) "
        "ORDER BY day_usd DESC NULLS LAST",
    ),
    "spend-opencode-go": (
        "Just the opencode-go (subscription) spend across all days",
        "SELECT day_date, day_usd, month_usd, all_time_usd, last_used "
        "FROM provider_spend WHERE provider = 'openai-compatible:opencode-go' "
        "ORDER BY day_date DESC",
    ),
    # Round-5 (W5-4): chatgpt data export queries.
    "chatgpt-conversations": (
        "ChatGPT export: top 20 conversations by message count (round-5 W5-4)",
        "SELECT uuid, name, summary, created_at, updated_at, n_messages "
        "FROM openai_chatgpt_conversations ORDER BY n_messages DESC LIMIT 20",
    ),
    "chatgpt-stats": (
        "ChatGPT export: totals by month + sender (round-5 W5-4)",
        "SELECT SUBSTR(created_at, 1, 7) AS month, sender, COUNT(*) AS n "
        "FROM openai_chatgpt_messages GROUP BY month, sender ORDER BY month DESC, sender",
    ),
    "chatgpt-recent": (
        "ChatGPT export: 10 most recently updated conversations (round-5 W5-4)",
        "SELECT uuid, name, created_at, updated_at, n_messages "
        "FROM openai_chatgpt_conversations ORDER BY updated_at DESC LIMIT 10",
    ),
    "chatgpt-files": (
        "ChatGPT export: messages that include files or attachments (round-5 W5-4, +n_attachments round-5 W5-VAL2)",
        "SELECT conversation_uuid, sender, n_files, n_attachments, has_attachments, created_at "
        "FROM openai_chatgpt_messages WHERE has_files = 1 OR has_attachments = 1 "
        "ORDER BY created_at DESC LIMIT 20",
    ),
    "chatgpt-attachments": (
        "ChatGPT export: total attachment count per year (round-5 W5-VAL2)",
        "SELECT SUBSTR(created_at, 1, 4) AS year, SUM(n_attachments) AS total_attachments, COUNT(*) AS msg_count "
        "FROM openai_chatgpt_messages WHERE n_attachments > 0 "
        "GROUP BY year ORDER BY year DESC",
    ),
    "chatgpt-threads": (
        "ChatGPT export: messages that have a parent (thread tracking via parent_message_uuid, round-5 W5-VAL3)",
        "SELECT conversation_uuid, COUNT(*) AS replies, "
        "       COUNT(DISTINCT parent_message_uuid) AS distinct_parents "
        "FROM openai_chatgpt_messages WHERE parent_message_uuid IS NOT NULL "
        "GROUP BY conversation_uuid ORDER BY replies DESC LIMIT 20",
    ),
    # Round-6 (W6-1): five cross-cutting insight queries that surface data
    # hidden from the per-table presets. Each uses json_each/json_extract
    # to walk content_json; the json1 extension is built into Python 3.9+.
    "chatgpt-orphans": (
        "ChatGPT export: messages whose parent_message_uuid points to a non-existent message (cross-conversation threading, round-6 W6-1)",
        "SELECT m.uuid AS msg_uuid, m.conversation_uuid AS msg_conv, "
        "       m.parent_message_uuid AS parent_uuid, m.sender, "
        "       SUBSTR(m.text, 1, 200) AS text_preview, m.created_at "
        "FROM openai_chatgpt_messages m "
        "WHERE m.parent_message_uuid IS NOT NULL "
        "  AND NOT EXISTS (SELECT 1 FROM openai_chatgpt_messages m2 "
        "                  WHERE m2.uuid = m.parent_message_uuid) "
        "ORDER BY m.created_at DESC LIMIT 50",
    ),
    "chatgpt-thinking": (
        "ChatGPT export: messages with thinking content blocks (round-6 W6-1)",
        "SELECT m.conversation_uuid, m.sender, m.created_at, "
        "       (SELECT COUNT(*) FROM json_each(m.content_json) "
        "        WHERE json_extract(value, '$.type') = 'thinking') AS n_thinking_blocks "
        "FROM openai_chatgpt_messages m "
        "WHERE EXISTS (SELECT 1 FROM json_each(m.content_json) "
        "              WHERE json_extract(value, '$.type') = 'thinking') "
        "ORDER BY m.created_at DESC LIMIT 50",
    ),
    "chatgpt-summaries": (
        "ChatGPT export: 65 conversations with non-empty summaries (round-6 W6-1)",
        "SELECT uuid, name, SUBSTR(summary, 1, 300) AS summary_preview, "
        "       n_messages, updated_at "
        "FROM openai_chatgpt_conversations "
        "WHERE summary IS NOT NULL AND summary != '' "
        "ORDER BY updated_at DESC LIMIT 50",
    ),
    "chatgpt-tool-use": (
        "ChatGPT export: messages with tool_use_id (tool calls, round-6 W6-1)",
        "SELECT m.conversation_uuid, m.sender, m.created_at, "
        "       (SELECT COUNT(*) FROM json_each(m.content_json) "
        "        WHERE json_extract(value, '$.tool_use_id') IS NOT NULL) AS n_tool_calls "
        "FROM openai_chatgpt_messages m "
        "WHERE EXISTS (SELECT 1 FROM json_each(m.content_json) "
        "              WHERE json_extract(value, '$.tool_use_id') IS NOT NULL) "
        "ORDER BY m.created_at DESC LIMIT 50",
    ),
    "chatgpt-1x1": (
        "ChatGPT export: single-message conversations (1x1 exchanges, round-6 W6-1)",
        "SELECT uuid, name, created_at, updated_at, n_messages "
        "FROM openai_chatgpt_conversations "
        "WHERE n_messages = 1 "
        "ORDER BY updated_at DESC LIMIT 50",
    ),
    # Round-7 (W7-2.7-2.9): presets over the three new child tables
    # (openai_chatgpt_files / openai_chatgpt_attachment_content /
    # openai_chatgpt_tool_results) added in W7-2.1-2.6.
    "chatgpt-pasted-code": (
        "ChatGPT export: largest pasted-file attachments by content size (round-7 W7-2.7)",
        "SELECT a.file_name, a.file_type, a.content_len, "
        "       m.conversation_uuid, m.created_at, "
        "       SUBSTR(a.extracted_content, 1, 120) AS content_preview "
        "FROM openai_chatgpt_attachment_content a "
        "JOIN openai_chatgpt_messages m ON m.uuid = a.msg_uuid "
        "WHERE a.extracted_content IS NOT NULL "
        "ORDER BY a.content_len DESC LIMIT 20",
    ),
    "chatgpt-tool-results": (
        "ChatGPT export: per-tool result counts, error rates, payload sizes (round-7 W7-2.8)",
        "SELECT name, COUNT(*) AS n_results, SUM(is_error) AS n_errors, "
        "       ROUND(AVG(content_len)) AS avg_bytes, MAX(content_len) AS max_bytes "
        "FROM openai_chatgpt_tool_results "
        "GROUP BY name ORDER BY n_results DESC LIMIT 30",
    ),
    "chatgpt-file-links": (
        "ChatGPT export: per-conversation file reference graph (round-7 W7-2.9)",
        "SELECT f.conversation_uuid, c.name, COUNT(*) AS file_links, "
        "       COUNT(DISTINCT f.file_uuid) AS distinct_files "
        "FROM openai_chatgpt_files f "
        "JOIN openai_chatgpt_conversations c ON c.uuid = f.conversation_uuid "
        "GROUP BY f.conversation_uuid ORDER BY file_links DESC LIMIT 20",
    ),
}

# Round-5 (W4-3): by-model-cost is a Python-side multi-DB join, so it is
# handled in main() rather than as a pure-SQL preset. Listed here so
# --list-presets sees it.
PYTHON_PRESETS = {
    "by-model-cost": (
        "Per-model spend allocation: joins provider_spend with turns from "
        "model-usage-v1.sqlite3, attributes each provider's all_time_usd "
        "across its models weighted by turn count",
    ),
    "chatgpt-reconcile": (
        "W6-5: cross-source reconciliation — pairs local sessions (by title) "
        "with chatgpt conversations (by name) via case-insensitive substring match. "
        "Helps find sessions that worked on a chatgpt conversation topic.",
    ),
}

# Schema introspection queries (one per table)
INSPECT_QUERIES = {
    "schema": (
        "All tables and their CREATE statements",
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
    ),
    "sessions": (
        "sessions table schema",
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='sessions'",
    ),
    "opencode_usage": (
        "opencode_usage table schema",
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='opencode_usage'",
    ),
}
