#!/usr/bin/env python3
"""
ask_research_ledger.py — Read-only CLI for the unified research ledger.

Wraps SELECT queries against research_ledger.sqlite with safe presets and a
read-only enforced escape hatch. The unified corpus combines 11 sources
(chatgpt, claude, gemini, imessage, jcode, kcode, codex, forge, cursor,
claude_desktop, helioslite) into a single FTS5-searchable schema.

Three modes:
  1. presets:   --preset counts|by-source|by-day|search|tokens-by-source|...
  2. custom:    --query "SELECT ..."
  3. inspect:   --inspect schema | sources | items-schema | items-sample | counts-summary

Read-only enforcement: opens the DB with mode=ro URI. Even if a preset or
custom query tries to write, sqlite rejects it.

Usage:
  python3 ask_research_ledger.py --preset counts
  python3 ask_research_ledger.py --preset tokens-by-source --format json
  python3 ask_research_ledger.py --preset search --query "agent swarm" --format table
  python3 ask_research_ledger.py --query "SELECT id, kind FROM sources WHERE id <= 5"
  python3 ask_research_ledger.py --inspect schema
  python3 ask_research_ledger.py --list-presets
"""
import argparse
import csv
import io
import json
import os
import sqlite3
import sys

from ask_research_ledger_presets import PRESETS, PYTHON_PRESETS, INSPECT_QUERIES


DEFAULT_DB = os.path.expanduser("~/CodeProjects/Exports/analysis/research_ledger.sqlite")


def open_ro(db_path):
    """Open a SQLite database in read-only mode (mode=ro URI)."""
    if not os.path.exists(db_path):
        sys.exit(f"DB not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def render(conn, sql, params, fmt):
    """Run a query and render in the requested format. Returns the rendered text."""
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    if fmt == "json":
        return json.dumps(
            [dict(zip(cols, row)) for row in rows],
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        if cols:
            w.writerow(cols)
        for row in rows:
            w.writerow(row)
        return buf.getvalue().rstrip("\n")
    if fmt == "tsv":
        lines = []
        if cols:
            lines.append("\t".join(cols))
        for row in rows:
            lines.append("\t".join(str(c) if c is not None else "" for c in row))
        return "\n".join(lines)
    # default: table
    if not cols:
        return "(no rows)"
    widths = [len(c) for c in cols]
    for row in rows:
        for i, c in enumerate(row):
            s = str(c) if c is not None else ""
            if len(s) > 60:
                s = s[:57] + "..."
            widths[i] = max(widths[i], len(s))
    lines = []
    lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    lines.append("  ".join("-" * widths[i] for i in range(len(cols))))
    for row in rows:
        cells = []
        for i, c in enumerate(row):
            s = str(c) if c is not None else ""
            if len(s) > 60:
                s = s[:57] + "..."
            cells.append(s.ljust(widths[i]))
        lines.append("  ".join(cells))
    return "\n".join(lines)


def python_preset_tokens_by_day(conn, fmt):
    """Per-day total input tokens across all sources (Python aggregation)."""
    sql = (
        "SELECT s.kind, i.captured_at, "
        "  COALESCE(json_extract(i.attrs_json, '$.input_tokens'), 0) AS in_tok, "
        "  COALESCE(json_extract(i.attrs_json, '$.output_tokens'), 0) AS out_tok "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "WHERE json_extract(i.attrs_json, '$.input_tokens') IS NOT NULL"
    )
    by_day = {}
    for kind, captured_at, in_tok, out_tok in conn.execute(sql):
        if not captured_at:
            continue
        day = captured_at[:10]
        d = by_day.setdefault(day, {"input": 0, "output": 0, "sources": set()})
        d["input"] += in_tok
        d["output"] += out_tok
        d["sources"].add(kind)
    rows = []
    for day in sorted(by_day, reverse=True)[:60]:
        d = by_day[day]
        rows.append((
            day,
            f"{len(d['sources'])} src",
            f"{d['input'] / 1e9:.2f}B",
            f"{d['output'] / 1e6:.1f}M",
        ))
    cols = ["day", "sources", "input", "output"]
    if fmt == "json":
        return json.dumps([dict(zip(cols, r)) for r in rows], indent=2)
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        w.writerows(rows)
        return buf.getvalue().rstrip("\n")
    if fmt == "tsv":
        return "\n".join(["\t".join(cols)] + ["\t".join(str(c) for c in r) for r in rows])
    widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))]
    lines.append("  ".join("-" * widths[i] for i in range(len(cols))))
    for r in rows:
        lines.append("  ".join(str(r[i]).ljust(widths[i]) for i in range(len(cols))))
    return "\n".join(lines)


def python_preset_model_routing(conn, fmt):
    """Cross-source model usage. Helps the operator see which models route to which source."""
    sql = (
        "SELECT s.kind, json_extract(i.attrs_json, '$.model') AS model, COUNT(*) AS n "
        "FROM items i JOIN sources s ON s.id = i.source_id "
        "WHERE json_extract(i.attrs_json, '$.model') IS NOT NULL "
        "GROUP BY s.kind, model ORDER BY n DESC LIMIT 50"
    )
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return _render_rows(cols, rows, fmt)


def _render_rows(cols, rows, fmt):
    """Render rows using the same logic as render() but on already-fetched rows."""
    if fmt == "json":
        return json.dumps([dict(zip(cols, r)) for r in rows], indent=2, default=str)
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        w.writerows(rows)
        return buf.getvalue().rstrip("\n")
    if fmt == "tsv":
        return "\n".join(["\t".join(cols)] + ["\t".join(str(c) if c is not None else "" for c in r) for r in rows])
    if not cols:
        return "(no rows)"
    widths = [len(c) for c in cols]
    for row in rows:
        for i, c in enumerate(row):
            s = str(c) if c is not None else ""
            if len(s) > 60:
                s = s[:57] + "..."
            widths[i] = max(widths[i], len(s))
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))]
    lines.append("  ".join("-" * widths[i] for i in range(len(cols))))
    for row in rows:
        cells = [str(c) if c is not None else "" for c in row]
        cells = [s[:57] + "..." if len(s) > 60 else s for s in cells]
        lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(cells)))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Read-only CLI for the unified research ledger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", default=DEFAULT_DB, help="Path to research_ledger.sqlite")
    ap.add_argument("--preset", help="Use a named preset (see --list-presets)")
    ap.add_argument("--query", help="Custom SQL (read-only enforced); also FTS5 term for --preset search")
    ap.add_argument("--inspect", choices=sorted(INSPECT_QUERIES), help="Schema/source/items introspection")
    ap.add_argument("--format", choices=["table", "json", "csv", "tsv"], default="table",
                    help="Output format (default: table)")
    ap.add_argument("--list-presets", action="store_true", help="List all preset names and one-line descriptions")
    args = ap.parse_args()

    if args.list_presets:
        print("PRESETS:")
        for name, (desc, _sql) in sorted(PRESETS.items()):
            print(f"  {name:30s}  {desc}")
        print("\nPYTHON_PRESETS:")
        for name, desc in sorted(PYTHON_PRESETS.items()):
            print(f"  {name:30s}  {desc}")
        print("\nINSPECT:")
        for name, (desc, _sql) in sorted(INSPECT_QUERIES.items()):
            print(f"  {name:30s}  {desc}")
        return 0

    if not (args.preset or args.query or args.inspect):
        ap.print_help()
        return 1

    conn = open_ro(args.db)

    try:
        if args.inspect:
            desc, sql = INSPECT_QUERIES[args.inspect]
            print(render(conn, sql, (), args.format))
            return 0

        if args.preset == "search":
            if not args.query:
                sys.exit("--preset search requires --query 'fts5 expression'")
            sql = PRESETS["search"][1]
            print(render(conn, sql, (args.query,), args.format))
            return 0

        if args.preset in PYTHON_PRESETS:
            if args.preset == "tokens-by-day":
                print(python_preset_tokens_by_day(conn, args.format))
                return 0
            if args.preset == "model-routing":
                print(python_preset_model_routing(conn, args.format))
                return 0

        if args.preset:
            if args.preset not in PRESETS:
                sys.exit(f"Unknown preset: {args.preset}. Try --list-presets.")
            desc, sql = PRESETS[args.preset]
            print(render(conn, sql, (), args.format))
            return 0

        if args.query:
            print(render(conn, args.query, (), args.format))
            return 0

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
