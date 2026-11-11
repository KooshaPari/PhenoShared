"""FastMCP wrapper for ask_research_ledger CLI (round-9 W9-14).

Exposes the unified research-ledger presets as MCP tools. Read-only by
design — every code path opens the DB with mode=ro URI, and the ad-hoc
SQL tool rejects anything that is not a single SELECT/WITH statement.

Run with the fastmcp-bundled Python (the homebrew cellar python 3.14 is
the only env that has fastmcp installed; ask_research_ledger itself is
stdlib-only so this wrapper imports it without issue):

    /opt/homebrew/Cellar/fastmcp/3.2.4_1/libexec/bin/python \\
        ~/Exports/analysis/ask_research_ledger_mcp.py

Or add `~/Exports/analysis` to MCP config and reference this file as the
server entrypoint. Presets are intentionally enumerated (not user-supplied)
so the read-only surface is bounded; the only ad-hoc surface is a guarded
SELECT-only run_query tool.
"""
import os
import re
import sys
import sqlite3
import importlib
import traceback
from pathlib import Path

from fastmcp import FastMCP

# Import ask_research_ledger (pure stdlib sqlite3) from the same directory.
sys.path.insert(0, str(Path(__file__).parent))
import ask_research_ledger  # noqa: E402
import ask_research_ledger_presets as _rl_presets  # noqa: E402

mcp = FastMCP("ask_research_ledger")

DEFAULT_DB = os.path.expanduser("~/CodeProjects/Exports/analysis/research_ledger.sqlite")

# Auto-reload on edit: track mtimes of both ask_research_ledger.py and
# ask_research_ledger_presets.py. ask_research_ledger imports the presets
# module with `from ... import PRESETS, ...`, so reload the leaf first,
# then the importer — otherwise ask_research_ledger keeps stale dict
# bindings. This matches the W6-cleanup-1 pattern in ask_ledger_mcp.py.
_RL_PATH = str(Path(__file__).parent / "ask_research_ledger.py")
_RL_PRESETS_PATH = str(Path(__file__).parent / "ask_research_ledger_presets.py")
_RL_MTIME: float | None = None
_RL_PRESETS_MTIME: float | None = None


def _maybe_reload_research_ledger() -> None:
    """Reload presets + research_ledger from disk if either mtime changed."""
    global _RL_MTIME, _RL_PRESETS_MTIME
    try:
        rl_mtime = os.path.getmtime(_RL_PATH)
        presets_mtime = os.path.getmtime(_RL_PRESETS_PATH)
    except OSError:
        return
    rl_changed = _RL_MTIME is None or rl_mtime > _RL_MTIME
    presets_changed = (
        _RL_PRESETS_MTIME is None or presets_mtime > _RL_PRESETS_MTIME
    )
    if not rl_changed and not presets_changed:
        return
    _RL_MTIME = rl_mtime
    _RL_PRESETS_MTIME = presets_mtime
    try:
        # Leaf first so ask_research_ledger re-binds to fresh dicts.
        importlib.reload(_rl_presets)
        importlib.reload(ask_research_ledger)
    except Exception as e:
        sys.stderr.write(
            f"[ask_research_ledger_mcp] auto-reload failed: {e}\n"
            f"{traceback.format_exc()}\n"
        )


def _open_db(path: str) -> sqlite3.Connection:
    """Open research_ledger.sqlite with mode=ro URI (sqlite-enforced read-only)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"research ledger DB not found: {path}")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


# SQL allowlist for run_query. Reject anything that is not a single
# SELECT/WITH statement. PRAGMA introspection is reachable through the
# `inspect()` tool, so run_query stays SELECT/WITH-only and we don't
# need to enumerate the read-only PRAGMA subset at this boundary.
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|DROP|ALTER|CREATE|ATTACH|DETACH|"
    r"REINDEX|VACUUM|TRUNCATE|GRANT|REVOKE|PRAGMA)\b",
    re.IGNORECASE,
)
_SELECT_LEAD = re.compile(r"\s*(SELECT|WITH)\b", re.IGNORECASE)


def _validate_select_sql(sql: str) -> None:
    """Raise ValueError unless sql is a single read-only SELECT/WITH statement."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("query must be a non-empty string")
    stripped = sql.strip().rstrip(";").strip()
    # Reject anything that looks like multi-statement input. We strip a
    # trailing semicolon above; anything left inside is treated as part of
    # the single statement, but we also reject internal `;` to be safe.
    if ";" in stripped:
        raise ValueError(
            "multi-statement SQL is not allowed (found ';' inside the query)"
        )
    if not _SELECT_LEAD.match(stripped):
        raise ValueError(
            "only single SELECT or WITH statements are allowed; "
            f"query starts with: {stripped[:40]!r}"
        )
    bad = _FORBIDDEN_SQL.search(stripped)
    if bad:
        raise ValueError(f"forbidden SQL keyword: {bad.group(0).upper()}")


def _rows_to_dicts(cur: sqlite3.Cursor) -> list[dict]:
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool
def list_presets() -> dict:
    """Enumerate every preset ask_research_ledger understands.

    Returns three sorted key lists:
      sql_presets    — preset names whose (description, sql) pairs run as
                       raw conn.execute(sql)
      python_presets — preset names that need Python post-processing
                       (e.g. tokens-by-day, model-routing)
      inspect        — schema/source/items introspection queries
    """
    _maybe_reload_research_ledger()
    return {
        "sql_presets": sorted(ask_research_ledger.PRESETS.keys()),
        "python_presets": sorted(ask_research_ledger.PYTHON_PRESETS.keys()),
        "inspect": sorted(ask_research_ledger.INSPECT_QUERIES.keys()),
    }


@mcp.tool
def run_sql_preset(preset: str, db_path: str = DEFAULT_DB) -> list[dict]:
    """Run a SQL preset from ask_research_ledger.PRESETS. Returns rows as dicts."""
    _maybe_reload_research_ledger()
    if preset not in ask_research_ledger.PRESETS:
        raise ValueError(
            f"unknown SQL preset: {preset!r}; see list_presets()"
        )
    conn = _open_db(db_path)
    try:
        _desc, sql = ask_research_ledger.PRESETS[preset]
        cur = conn.execute(sql)
        return _rows_to_dicts(cur)
    finally:
        conn.close()


@mcp.tool
def run_python_preset(
    preset: str, db_path: str = DEFAULT_DB, fmt: str = "json"
) -> str:
    """Run a Python preset (tokens-by-day | model-routing). Returns the rendered text.

    Python presets are slower than SQL presets because they stream rows
    client-side and aggregate in Python. tokens-by-day in particular
    walks the entire items table and can take a minute on a 16GB DB.
    Use the SQL preset `tokens-by-model` if you only need top-N.
    """
    _maybe_reload_research_ledger()
    if preset not in ask_research_ledger.PYTHON_PRESETS:
        raise ValueError(
            f"unknown python preset: {preset!r}; see list_presets()"
        )
    if fmt not in ("table", "json", "csv", "tsv"):
        raise ValueError(
            f"fmt must be one of table|json|csv|tsv, got {fmt!r}"
        )
    conn = _open_db(db_path)
    try:
        if preset == "tokens-by-day":
            return ask_research_ledger.python_preset_tokens_by_day(conn, fmt)
        if preset == "model-routing":
            return ask_research_ledger.python_preset_model_routing(conn, fmt)
        raise ValueError(f"unhandled python preset: {preset!r}")
    finally:
        conn.close()


@mcp.tool
def inspect(
    target: str = "schema",
    db_path: str = DEFAULT_DB,
) -> list[dict]:
    """Schema / sources / items introspection. target choices:
      schema          — all tables/views/indexes
      sources         — contents of the sources table
      items-schema    — CREATE TABLE for items
      items-sample    — 10 most-recent items
      counts-summary  — headline counts (items, attachments, sources, FTS, ...)
    """
    _maybe_reload_research_ledger()
    if target not in ask_research_ledger.INSPECT_QUERIES:
        raise ValueError(
            f"unknown inspect target: {target!r}; "
            f"choices: {sorted(ask_research_ledger.INSPECT_QUERIES.keys())}"
        )
    conn = _open_db(db_path)
    try:
        _desc, sql = ask_research_ledger.INSPECT_QUERIES[target]
        cur = conn.execute(sql)
        return _rows_to_dicts(cur)
    finally:
        conn.close()


@mcp.tool
def search(query: str, db_path: str = DEFAULT_DB) -> list[dict]:
    """FTS5 search across items.title/body/author.

    `query` is passed verbatim to the FTS5 engine, so use FTS5 syntax
    (e.g. 'agent swarm', 'token*', 'model:foo'). Returns up to 20 rows
    ranked by FTS5 rank. Bounded — safe to call without a LIMIT.
    """
    _maybe_reload_research_ledger()
    if not query or not query.strip():
        raise ValueError("search query must be non-empty")
    sql = ask_research_ledger.PRESETS["search"][1]
    conn = _open_db(db_path)
    try:
        cur = conn.execute(sql, (query,))
        return _rows_to_dicts(cur)
    finally:
        conn.close()


@mcp.tool
def run_query(
    sql: str, db_path: str = DEFAULT_DB, params: list | None = None
) -> list[dict]:
    """Run a single read-only SELECT/WITH statement and return rows as dicts.

    The query is validated against an allowlist before it ever reaches
    sqlite: it must be non-empty, contain no internal `;`, lead with
    SELECT/WITH, and contain no INSERT/UPDATE/DELETE/REPLACE/DROP/ALTER/
    CREATE/ATTACH/DETACH/REINDEX/VACUUM/TRUNCATE/GRANT/REVOKE/PRAGMA.
    The DB is also opened mode=ro, so sqlite itself rejects any write
    attempt as a second line of defense. Use the `inspect()` tool for
    schema introspection instead of `PRAGMA` here. `params` is an optional
    list of positional bind values (passed as-is to sqlite3).
    """
    _maybe_reload_research_ledger()
    _validate_select_sql(sql)
    conn = _open_db(db_path)
    try:
        cur = conn.execute(sql, params or [])
        return _rows_to_dicts(cur)
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()