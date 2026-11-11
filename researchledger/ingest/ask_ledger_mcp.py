"""FastMCP wrapper for ask_ledger CLI (round-5 W4-4).

Exposes ask_ledger presets as MCP tools. Read-only by design — delegates to
ask_ledger, which enforces file:?mode=ro URI on the main ledger and uses
SELECT-only hardcoded queries against the turns DB.

Run with the fastmcp-bundled Python (the homebrew cellar python 3.14 is the
only env that has fastmcp installed; ask_ledger itself is stdlib-only so
this wrapper imports it without issue):

    /opt/homebrew/Cellar/fastmcp/3.2.4_1/libexec/bin/python \\
        ~/Exports/analysis/ask_ledger_mcp.py

Or add `~/Exports/analysis` to MCP config and reference this file as the
server entrypoint. Presets are intentionally enumerated (not user-supplied)
so the read-only surface is bounded.
"""
import os
import sys
import json
import sqlite3
import importlib
import traceback
from pathlib import Path

from fastmcp import FastMCP

# Import ask_ledger (pure stdlib sqlite3) from the same directory
sys.path.insert(0, str(Path(__file__).parent))
import ask_ledger
import ledger_presets

mcp = FastMCP("ask_ledger")

DEFAULT_LEDGER = os.path.expanduser("~/CodeProjects/Exports/analysis/session_ledger.sqlite")
DEFAULT_TURNS = os.path.expanduser("~/.jcode/model-usage-v1.sqlite3")

# W6-cleanup-1 (W7-1.4 extended): track the mtimes of ask_ledger.py AND
# ledger_presets.py so we can auto-reload both modules when the user edits
# either one (e.g. adds a new preset in ledger_presets.py). This eliminates
# the previous "must run mcp reload ask-ledger" gap: as soon as a new tool
# call lands, the modules are re-imported and any new preset is visible to
# run_sql_preset and list_presets.
#
# Reload order matters: ask_ledger does `from ledger_presets import PRESETS,`
# so ledger_presets must be reloaded FIRST, then ask_ledger re-binds to the
# fresh dicts. Reloading only ask_ledger would keep the stale dict objects.
_ASK_LEDGER_PATH = str(Path(__file__).parent / "ask_ledger.py")
_LEDGER_PRESETS_PATH = str(Path(__file__).parent / "ledger_presets.py")
_ASK_LEDGER_MTIME: float | None = None
_LEDGER_PRESETS_MTIME: float | None = None


def _maybe_reload_ask_ledger() -> None:
    """Reload ledger_presets + ask_ledger from disk if either mtime changed.

    W6-cleanup-1 (W7-1.4 extended): replaces the previous need to run
    `mcp reload ask-ledger` after editing presets. The reload is cheap
    (two importlib.reload calls) and only fires when a file actually
    changed. ledger_presets is reloaded first so ask_ledger's
    `from ledger_presets import PRESETS` re-binds to the fresh dicts.
    """
    global _ASK_LEDGER_MTIME, _LEDGER_PRESETS_MTIME
    try:
        ask_mtime = os.path.getmtime(_ASK_LEDGER_PATH)
        presets_mtime = os.path.getmtime(_LEDGER_PRESETS_PATH)
    except OSError:
        return
    ask_changed = _ASK_LEDGER_MTIME is None or ask_mtime > _ASK_LEDGER_MTIME
    presets_changed = _LEDGER_PRESETS_MTIME is None or presets_mtime > _LEDGER_PRESETS_MTIME
    if not ask_changed and not presets_changed:
        return
    _ASK_LEDGER_MTIME = ask_mtime
    _LEDGER_PRESETS_MTIME = presets_mtime
    try:
        if presets_changed or ask_changed:
            # Order matters: leaf module first, then the importer.
            importlib.reload(ledger_presets)
            importlib.reload(ask_ledger)
    except Exception as e:
        # If reload fails, keep the old module in memory and surface the
        # error in stderr so the user can see it.
        sys.stderr.write(
            f"[ask_ledger_mcp] auto-reload failed: {e}\n{traceback.format_exc()}\n"
        )


def _open_ledger(path: str) -> sqlite3.Connection:
    """Open the main ledger with mode=ro URI (read-only at sqlite level)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"ledger DB not found: {path}")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


@mcp.tool
def list_presets() -> dict:
    """Enumerate every preset the ask_ledger CLI understands."""
    _maybe_reload_ask_ledger()
    return {
        "sql_presets": sorted(ask_ledger.PRESETS.keys()),
        "python_presets": sorted(ask_ledger.PYTHON_PRESETS.keys()),
    }


@mcp.tool
def run_sql_preset(preset: str, ledger_db: str = DEFAULT_LEDGER) -> list[dict]:
    """Run a SQL preset from ask_ledger.PRESETS. Returns rows as dicts."""
    _maybe_reload_ask_ledger()
    if preset not in ask_ledger.PRESETS:
        raise ValueError(
            f"unknown preset: {preset!r}; see list_presets()"
        )
    conn = _open_ledger(ledger_db)
    try:
        # PRESETS values are (description, sql) tuples. W5-VAL2 bug fix.
        _desc, sql = ask_ledger.PRESETS[preset]
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


@mcp.tool
def by_model_cost(
    ledger_db: str = DEFAULT_LEDGER,
    turns_db: str = DEFAULT_TURNS,
) -> list[dict]:
    """Per-model spend allocation (round-5 W4-3 preset).

    Joins provider_spend from the main ledger with turn counts from the jcode
    turns DB, allocating each provider's all_time_usd across its models
    weighted by turn count. Returns 11 rows by default (the 4 visible
    opencode-go models, 2 visible zai models, 1 union-alpha, 1 oauth
    unpriced, 1 zai, and any external providers with no turn records).
    """
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        rows = ask_ledger.by_model_cost(conn, turns_db)
        cols = ["provider", "model", "turns", "allocated_usd",
                "provider_total_usd", "visibility"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


@mcp.tool
def inspect_schema(ledger_db: str = DEFAULT_LEDGER) -> list[dict]:
    """DESCRIBE every base table in the ledger (read-only)."""
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name"
        ).fetchall()]
        out = []
        for t in tables:
            cols = conn.execute(
                f"PRAGMA table_info({t})"
            ).fetchall()
            out.append({
                "table": t,
                "columns": [
                    {"name": c[1], "type": c[2], "nullable": not c[3]}
                    for c in cols
                ],
            })
        return out
    finally:
        conn.close()


# Round-5 (W5-5): ChatGPT export MCP tools. The 4 chatgpt-* SQL presets
# in ask_ledger.PRESETS are also available via run_sql_preset, but these
# give them friendly names and structured column expectations.
@mcp.tool
def chatgpt_conversations(ledger_db: str = DEFAULT_LEDGER, limit: int = 20) -> list[dict]:
    """Top N ChatGPT export conversations by message count (default 20)."""
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        cur = conn.execute(
            "SELECT uuid, name, summary, created_at, updated_at, n_messages "
            "FROM openai_chatgpt_conversations ORDER BY n_messages DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


@mcp.tool
def chatgpt_stats(ledger_db: str = DEFAULT_LEDGER) -> list[dict]:
    """Per-month, per-sender message counts in the ChatGPT export."""
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        cur = conn.execute(
            "SELECT SUBSTR(created_at, 1, 7) AS month, sender, COUNT(*) AS n "
            "FROM openai_chatgpt_messages GROUP BY month, sender "
            "ORDER BY month DESC, sender"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


@mcp.tool
def chatgpt_recent(ledger_db: str = DEFAULT_LEDGER, limit: int = 10) -> list[dict]:
    """N most recently updated ChatGPT export conversations (default 10)."""
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        cur = conn.execute(
            "SELECT uuid, name, created_at, updated_at, n_messages "
            "FROM openai_chatgpt_conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


# Round-6 (W6-2): unified chatgpt_insights tool. One entry point for the
# five W6-1 cross-cutting insights (orphans / thinking / summaries /
# tool-use / 1x1). Replaces what would otherwise be 5 more @mcp.tool
# functions. Each kind is a small SQL preset embedded in the dispatcher.
@mcp.tool
def chatgpt_insights(
    kind: str = "thinking",
    ledger_db: str = DEFAULT_LEDGER,
    limit: int = 50,
) -> list[dict]:
    """W6-2: cross-cutting chatgpt export insights.

    kind choices:
      orphans   — messages whose parent_message_uuid points to a non-existent
                  message (cross-conversation threading, 875 expected)
      thinking  — messages with thinking content blocks (assistant reasoning)
      summaries — conversations with non-empty summary text (~65 expected)
      tool-use  — messages that include a tool_use_id (tool call)
      1x1       — single-message conversations (1x1 exchanges)

    Returns up to `limit` rows as dicts.
    """
    _maybe_reload_ask_ledger()
    queries = {
        "orphans": (
            "SELECT m.uuid AS msg_uuid, m.conversation_uuid AS msg_conv, "
            "       m.parent_message_uuid AS parent_uuid, m.sender, "
            "       SUBSTR(m.text, 1, 200) AS text_preview, m.created_at "
            "FROM openai_chatgpt_messages m "
            "WHERE m.parent_message_uuid IS NOT NULL "
            "  AND NOT EXISTS (SELECT 1 FROM openai_chatgpt_messages m2 "
            "                  WHERE m2.uuid = m.parent_message_uuid) "
            "ORDER BY m.created_at DESC LIMIT ?"
        ),
        "thinking": (
            "SELECT m.conversation_uuid, m.sender, m.created_at, "
            "       (SELECT COUNT(*) FROM json_each(m.content_json) "
            "        WHERE json_extract(value, '$.type') = 'thinking') AS n_thinking_blocks "
            "FROM openai_chatgpt_messages m "
            "WHERE EXISTS (SELECT 1 FROM json_each(m.content_json) "
            "              WHERE json_extract(value, '$.type') = 'thinking') "
            "ORDER BY m.created_at DESC LIMIT ?"
        ),
        "summaries": (
            "SELECT uuid, name, SUBSTR(summary, 1, 300) AS summary_preview, "
            "       n_messages, updated_at "
            "FROM openai_chatgpt_conversations "
            "WHERE summary IS NOT NULL AND summary != '' "
            "ORDER BY updated_at DESC LIMIT ?"
        ),
        "tool-use": (
            "SELECT m.conversation_uuid, m.sender, m.created_at, "
            "       (SELECT COUNT(*) FROM json_each(m.content_json) "
            "        WHERE json_extract(value, '$.tool_use_id') IS NOT NULL) AS n_tool_calls "
            "FROM openai_chatgpt_messages m "
            "WHERE EXISTS (SELECT 1 FROM json_each(m.content_json) "
            "              WHERE json_extract(value, '$.tool_use_id') IS NOT NULL) "
            "ORDER BY m.created_at DESC LIMIT ?"
        ),
        "1x1": (
            "SELECT uuid, name, created_at, updated_at, n_messages "
            "FROM openai_chatgpt_conversations "
            "WHERE n_messages = 1 "
            "ORDER BY updated_at DESC LIMIT ?"
        ),
    }
    if kind not in queries:
        raise ValueError(
            f"unknown kind: {kind!r}; choices: {sorted(queries.keys())}"
        )
    conn = _open_ledger(ledger_db)
    try:
        cur = conn.execute(queries[kind], (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


# Round-6 (W6-5): cross-source reconciliation dispatcher. Reads the
# (conv, session) pairs from ask_ledger.chatgpt_reconcile, which uses an
# inverted index for O(n+m) matching (see ask_ledger.py docstring).
@mcp.tool
def chatgpt_reconcile(ledger_db: str = DEFAULT_LEDGER, max_rows: int = 100) -> list[dict]:
    """W6-5: pair local sessions (by title) with chatgpt conversations
    (by name) via case-insensitive substring match. Returns up to
    max_rows (conv, session) reconciliation pairs sorted by match_score
    desc. Useful for finding sessions that worked on a chatgpt conversation
    topic. With the current data this typically returns 0 rows because
    chatgpt convs are older project topics and recent local sessions are
    lane tasks; rerun after ingestion of older sessions to find matches.
    """
    _maybe_reload_ask_ledger()
    conn = _open_ledger(ledger_db)
    try:
        rows = ask_ledger.chatgpt_reconcile(conn, max_rows=max_rows)
    finally:
        conn.close()
    cols = ["conv_uuid", "conv_name", "conv_updated",
            "harness", "session_id", "device", "session_started",
            "session_title", "match_score"]
    return [dict(zip(cols, r)) for r in rows]


if __name__ == "__main__":
    mcp.run()
