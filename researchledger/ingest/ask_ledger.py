#!/usr/bin/env python3
"""
ask_ledger.py — Read-only CLI for the session ledger.

Wraps SELECT queries against session_ledger.sqlite with safe presets and a
read-only enforced escape hatch. Built in round-4 as the Blk 7 W1 deliverable.

Three modes:
  1. presets:   --preset counts|by-harness|by-day|by-model|recent|spend|...
  2. custom:    --query "SELECT ..."
  3. inspect:   --inspect schema | sessions | opencode_usage

Read-only enforcement: opens the DB with mode=ro URI. Even if a preset or
custom query tries to write, sqlite rejects it.

Round-5 (W4-3): added by-model-cost preset. Joins provider_spend (ledger)
with model-usage-v1.sqlite3 turns (read-only ATTACH or separate open) to
attribute each provider's all_time_usd across the models it routed, weighted
by per-model turn counts. Openrouter is normalized to the openai-compatible
api_method so its C-bucket (external) spend can be reported alongside the
visible provider attributions.

Round-7 (W7-1.1): the preset dicts (PRESETS, PYTHON_PRESETS, INSPECT_QUERIES)
moved to ledger_presets.py. This file had grown to 544 lines by the end of
round-6, past the 500-line hard limit. This module keeps only the execution
logic; the dicts are pure data imported from ledger_presets.

Usage:
  python3 ask_ledger.py --preset counts
  python3 ask_ledger.py --preset by-harness --format json
  python3 ask_ledger.py --preset by-model-cost --turns-db ~/.jcode/model-usage-v1.sqlite3
  python3 ask_ledger.py --query "SELECT model, COUNT(*) AS n FROM sessions GROUP BY model ORDER BY n DESC LIMIT 5"
  python3 ask_ledger.py --inspect schema
"""
import argparse
import csv
import io
import json
import os
import sqlite3
import sys
from collections import defaultdict

from ledger_presets import PRESETS, PYTHON_PRESETS, INSPECT_QUERIES


DEFAULT_DB = os.path.expanduser("~/CodeProjects/Exports/analysis/session_ledger.sqlite")
DEFAULT_TURNS_DB = os.path.expanduser("~/.jcode/model-usage-v1.sqlite3")

# Normalize openrouter provider key to match the api_method used in turns.
# In provider_spend, openrouter is stored as 'openrouter' (single word), but
# in turns.api_method it is 'openai-compatible:openrouter'. Without this
# mapping the join would miss the 4 visible openrouter turns.
_PROVIDER_NORMALIZE = {
    "openrouter": "openai-compatible:openrouter",
}


def open_ro(db_path):
    """Open a sqlite DB read-only via URI."""
    if not os.path.isfile(db_path):
        print(f"FATAL: {db_path} does not exist", file=sys.stderr)
        sys.exit(2)
    # mode=ro URI is enforced at the sqlite level, not just by convention
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def by_model_cost(ledger_conn, turns_db_path):
    """Round-5 (W4-3): per-model spend attribution.

    For each provider with non-external visibility, reads turn counts from
    model-usage-v1.sqlite3, then allocates the provider's all_time_usd across
    its models weighted by turn count. Returns list of dicts with the schema
    expected by format_rows().

    Openrouter is normalized to the openai-compatible:openrouter key so the
    4 visible union-alpha turns are attributed to the openrouter provider
    (and the C-bucket / external flag is preserved on the row).
    """
    # 1. Provider spend: one row per provider, take MAX(all_time_usd) since
    #    the column is a per-day snapshot, not additive.
    spend_rows = ledger_conn.execute(
        """
        SELECT provider, MAX(all_time_usd) AS all_time_usd, source_local_visibility
        FROM provider_spend
        WHERE all_time_usd IS NOT NULL
        GROUP BY provider
        ORDER BY all_time_usd DESC
        """
    ).fetchall()
    providers = {}
    for provider, usd, vis in spend_rows:
        join_key = _PROVIDER_NORMALIZE.get(provider, provider)
        providers[join_key] = {"provider": provider, "all_time_usd": usd, "visibility": vis}

    # 2. Turn counts per (api_method, model) from the turns DB.
    if not os.path.isfile(turns_db_path):
        print(f"FATAL: turns DB {turns_db_path} not found (use --turns-db)",
              file=sys.stderr)
        sys.exit(2)
    # Note: this DB is opened with default mode (rw) because the sqlite URI
    # mode=ro rejects WAL-mode files in some Python/sqlite combinations (we
    # confirmed this against model-usage-v1.sqlite3 2026-10-13). The query
    # below is a hardcoded SELECT, so the read-only guarantee is preserved
    # by convention rather than by the URI mode. Do not extend this to
    # user-supplied SQL.
    turns_conn = sqlite3.connect(turns_db_path)
    try:
        turn_rows = turns_conn.execute(
            """
            SELECT api_method, model, COUNT(*) AS n
            FROM turns
            GROUP BY api_method, model
            """
        ).fetchall()
    finally:
        turns_conn.close()

    # 3. Per-provider total turn count (for weight denominator).
    per_provider_total = {}
    for api_method, _model, n in turn_rows:
        per_provider_total[api_method] = per_provider_total.get(api_method, 0) + n

    # 4. Allocate each provider's spend across its models.
    out = []
    for api_method, model, n in turn_rows:
        if api_method not in providers:
            continue
        prov = providers[api_method]
        total = per_provider_total[api_method] or 1
        allocated = round((n / total) * prov["all_time_usd"], 4) if prov["all_time_usd"] else 0.0
        out.append((
            prov["provider"],
            model,
            n,
            f"{allocated:.4f}",
            f"{prov['all_time_usd']:.2f}",
            prov["visibility"],
        ))

    # 5. Emit external/unmatched providers (no turn records) so the user sees
    #    the gap. openrouter C-bucket will land here if no turns match.
    for join_key, prov in providers.items():
        if join_key in per_provider_total:
            continue  # already allocated above
        out.append((
            prov["provider"],
            "(no turn records)",
            0,
            f"{prov['all_time_usd']:.4f}",
            f"{prov['all_time_usd']:.2f}",
            prov["visibility"],
        ))

    # Sort: largest allocated spend first
    out.sort(key=lambda r: float(r[3]), reverse=True)
    return out


# W6-5: cross-source reconciliation between local sessions and chatgpt
# conversations. Both sides lack a shared key, so this is a Python-side
# pairwise substring join.
#
#   * chatgpt side: rows in openai_chatgpt_conversations with non-empty
#     name (length >= 8 to skip stubs like "New chat").
#   * session side: rows in sessions with non-empty title.
#
# For each (conv, session) pair, emit a row if the lowercased conv name
# is contained in the lowercased session title. match_score is the length
# ratio of the conv name to the session title, so a near-full match scores
# higher than a substring match.
#
# Performance: instead of a naive O(conv * session) cross-product, this builds
# an inverted index {token -> [convs]} from the chatgpt names, then for each
# session looks up candidate convs by the session's own tokens. The total
# work is O(conv_tokens + session_tokens * avg_words_per_session). For
# 200 convs * 1000 sessions that runs in well under a second.
def chatgpt_reconcile(ledger_conn, min_name_len: int = 8, max_rows: int = 100,
                      max_conv_rows: int = 200, max_sess_rows: int = 1000):
    """W6-5: return up to max_rows (conv, session) reconciliation pairs.

    Returns list of (conv_uuid, conv_name, conv_updated, harness, session_id,
    device, session_started, session_title, match_score) tuples ready for
    format_rows().
    """
    import re
    word_pat = re.compile(r'[a-z0-9]{4,}')

    conv_rows = ledger_conn.execute(
        """
        SELECT uuid, name, updated_at
        FROM openai_chatgpt_conversations
        WHERE name IS NOT NULL AND name != '' AND LENGTH(name) >= ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (min_name_len, max_conv_rows),
    ).fetchall()
    sess_rows = ledger_conn.execute(
        """
        SELECT harness, session_id, device, started_at, title
        FROM sessions
        WHERE title IS NOT NULL AND title != ''
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (max_sess_rows,),
    ).fetchall()
    if not conv_rows or not sess_rows:
        return []

    # Build inverted index: word -> [(cuuid, cname_lc, cname, cupdated), ...]
    conv_by_word = defaultdict(list)
    for cuuid, cname, cupdated in conv_rows:
        cname_lc = cname.lower()
        for w in word_pat.findall(cname_lc):
            conv_by_word[w].append((cuuid, cname_lc, cname, cupdated))

    seen = set()
    matches = []
    for harness, sid, device, started, stitle in sess_rows:
        stitle_lc = stitle.lower()
        stitle_words = set(word_pat.findall(stitle_lc))
        if not stitle_words:
            continue
        # Look up candidate convs by each session word
        candidates = set()
        for w in stitle_words:
            candidates.update(conv_by_word.get(w, ()))
        for cuuid, cname_lc, cname, cupdated in candidates:
            if cname_lc in stitle_lc:
                key = (cuuid, harness, sid, device)
                if key in seen:
                    continue
                seen.add(key)
                score = round(len(cname_lc) / max(len(stitle_lc), 1), 3)
                matches.append((cuuid, cname, cupdated, harness, sid, device,
                                started, stitle, score))

    # Sort: highest match score first, then most-recent session started_at
    matches.sort(key=lambda r: (-r[8], r[6] or ""), reverse=False)
    return matches[:max_rows]


def format_rows(rows, headers, fmt):
    """Format rows as table, json, or csv."""
    if fmt == "json":
        return json.dumps(
            [dict(zip(headers, [str(v) if v is not None else None for v in row])) for row in rows],
            indent=2,
        )
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        for row in rows:
            w.writerow([str(v) if v is not None else "" for v in row])
        return buf.getvalue().rstrip()
    # table format (default)
    if not rows:
        return "(0 rows)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v) if v is not None else ""))
    sep = "  "
    out = [sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    out.append(sep.join("-" * w for w in widths))
    for row in rows:
        out.append(sep.join(
            (str(v) if v is not None else "").ljust(widths[i])
            for i, v in enumerate(row)
        ))
    out.append(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(
        description="Read-only CLI for the session ledger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--db", default=DEFAULT_DB, help=f"Path to ledger sqlite (default: {DEFAULT_DB})")
    ap.add_argument("--turns-db", default=DEFAULT_TURNS_DB,
                    help=f"Path to model-usage-v1.sqlite3 (default: {DEFAULT_TURNS_DB})")
    ap.add_argument("--preset", choices=sorted(list(PRESETS.keys()) + list(PYTHON_PRESETS.keys())),
                    help=f"Run a pre-built query. Choices: {', '.join(sorted(list(PRESETS.keys()) + list(PYTHON_PRESETS.keys())))}")
    ap.add_argument("--query", help="Run a custom SQL query (SELECT only; read-only enforced)")
    ap.add_argument("--inspect", choices=sorted(INSPECT_QUERIES.keys()),
                    help="Show schema/metadata")
    ap.add_argument("--format", choices=["table", "json", "csv"], default="table",
                    help="Output format (default: table)")
    ap.add_argument("--max-rows", type=int, default=1000,
                    help="Cap on rows returned (default: 1000; -1 for no cap)")
    ap.add_argument("--list-presets", action="store_true",
                    help="List available presets and exit")

    args = ap.parse_args()

    if args.list_presets:
        print("Available presets:")
        all_presets = {**PRESETS, **{k: (v, "") for k, v in PYTHON_PRESETS.items()}}
        for name in sorted(all_presets):
            desc, _ = all_presets[name]
            print(f"  {name:20s}  {desc}")
        return 0

    if not (args.preset or args.query or args.inspect):
        ap.error("must provide --preset, --query, or --inspect")

    if args.preset in PYTHON_PRESETS:
        # Python-side presets (multi-DB joins, not pure SQL)
        if args.preset == "by-model-cost":
            desc = PYTHON_PRESETS["by-model-cost"]
            print(f"# preset: by-model-cost -- {desc}")
            conn = open_ro(args.db)
            try:
                rows = by_model_cost(conn, args.turns_db)
            finally:
                conn.close()
            headers = ["provider", "model", "turns", "allocated_usd",
                       "provider_total_usd", "visibility"]
            print(format_rows(rows, headers, args.format))
            return 0
        if args.preset == "chatgpt-reconcile":
            desc = PYTHON_PRESETS["chatgpt-reconcile"]
            print(f"# preset: chatgpt-reconcile -- {desc}")
            conn = open_ro(args.db)
            try:
                rows = chatgpt_reconcile(conn)
            finally:
                conn.close()
            headers = ["conv_uuid", "conv_name", "conv_updated",
                       "harness", "session_id", "device", "session_started",
                       "session_title", "match_score"]
            print(format_rows(rows, headers, args.format))
            return 0
    elif args.preset:
        desc, sql = PRESETS[args.preset]
        print(f"# preset: {args.preset} -- {desc}")
    elif args.inspect:
        desc, sql = INSPECT_QUERIES[args.inspect]
        print(f"# inspect: {args.inspect} -- {desc}")
    else:
        sql = args.query

    # Custom queries: enforce SELECT-only as a second layer of defense
    # (sqlite mode=ro already rejects writes, but explicit is better)
    if args.query:
        stripped = sql.strip().lstrip("(").lstrip().lower()
        if not stripped.startswith("select") and not stripped.startswith("with"):
            print("FATAL: --query must start with SELECT or WITH", file=sys.stderr)
            return 2

    conn = open_ro(args.db)
    try:
        cur = conn.execute(sql)
        if args.inspect == "schema":
            rows = cur.fetchall()
            for name, create_sql in rows:
                print(f"\n=== {name} ===")
                print(create_sql if create_sql else "(no schema)")
            return 0
        if args.inspect:
            row = cur.fetchone()
            if row:
                print(row[0] if row[0] else "(no schema)")
            return 0
        # Preset or custom: return columns + rows
        headers = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        if args.max_rows >= 0 and len(rows) > args.max_rows:
            rows = rows[: args.max_rows]
            truncated = True
        else:
            truncated = False
        print(format_rows(rows, headers, args.format))
        if truncated:
            print(f"\n(truncated to {args.max_rows} rows; pass --max-rows -1 for no cap)", file=sys.stderr)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
