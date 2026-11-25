#!/usr/bin/env python3
"""W9e-fix: re-derive model attribution for cursor_chat items.

The original cursor_build_canonical.py used regex
  r"You are ([A-Za-z0-9\.\- ]+?)(?:\.|\n|\r|$)"
which matched "an interactive CLI tool that helps users with software
engineering tasks." because cursor system prompts start with
"You are an interactive CLI tool...".

Real model attribution is in TWO places:
  1. "powered by <MODEL>."  (most reliable: Cursor Grok 4.5, Composer, Opus 4.8, GPT-5.6 Luna, GPT-5.6 Sol, etc.)
  2. "You are <MODEL>, a language model" or "You are <MODEL>."

We use the FIRST system message of each chat and extract the model.

Updates only the parent cursor_chat item's attrs_json -> model field.
Idempotent.
"""
import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

DB_PATH = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
SOURCE_ID = 9  # cursor

# Pattern 1 (preferred): "powered by <MODEL>" until '. ', ', ', newline, " which"/" to"
# Model names contain periods (e.g., "Cursor Grok 4.5", "GPT-5.6 Luna")
# so we use a non-greedy match that requires whitespace after the period
POWERED_BY_RE = re.compile(
    r"powered by ([A-Za-z0-9][A-Za-z0-9\.\- ]*?[A-Za-z0-9])(?:\.\s|,\s|\n| which| to | with |\Z)",
    re.IGNORECASE,
)
# Pattern 2 (fallback): "You are <MODEL>, a language model..." or "You are <MODEL>."
YOU_ARE_RE = re.compile(
    r"You are ([A-Z][A-Za-z0-9\.\- ]+?)(?:\.\s|,\s+(?:a language model|trained|an AI)|\n)",
)
# Some system prompts say "You are powered by X" too
YOU_ARE_POWERED_RE = re.compile(
    r"You are powered by ([A-Za-z0-9\.\- ]+?)(?:\.|,|\n|\Z)",
    re.IGNORECASE,
)


def extract_model(body):
    if not body:
        return None
    # Try "powered by" first
    m = POWERED_BY_RE.search(body)
    if m:
        return m.group(1).strip()
    # Try "You are powered by"
    m = YOU_ARE_POWERED_RE.search(body)
    if m:
        return m.group(1).strip()
    # Try "You are MODEL,"
    m = YOU_ARE_RE.search(body)
    if m:
        candidate = m.group(1).strip()
        # Skip known false positives
        if candidate.lower() not in (
            "an interactive cli tool",
            "a helpful ai assistant",
            "a coding assistant",
        ):
            return candidate
    return None


def main():
    ap = argparse.ArgumentParser(description="W9e-fix: re-derive model attribution for cursor_chat items")
    ap.add_argument("--db", default=str(DB_PATH),
                    help="Path to research_ledger.sqlite (default: canonical corpus)")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Opt in to writing the canonical research_ledger corpus (required when --db is the sealed corpus path)")
    args = ap.parse_args()

    guard_write_target(args.db, allow_canonical=args.allow_canonical)
    db = sqlite3.connect(args.db, timeout=60)
    db.row_factory = sqlite3.Row

    # Pre-fetch all system message bodies in one pass, indexed by chat_external_id
    sys_msgs = {}  # chat_external_id -> first system body
    print("  loading all system messages...")
    t0 = time.time()
    for r in db.execute(
        """
        SELECT json_extract(attrs_json, '$.chat_external_id') AS chat_ext_id, body
        FROM items
        WHERE source_id = 9 AND item_kind = 'cursor_message'
          AND json_extract(attrs_json, '$.role') = 'system'
        ORDER BY id
        """
    ):
        chat_ext_id = r["chat_ext_id"]
        if chat_ext_id and chat_ext_id not in sys_msgs:
            sys_msgs[chat_ext_id] = r["body"]
    print(f"  {len(sys_msgs)} unique chats with system prompts in {time.time()-t0:.1f}s")

    # Get all cursor_chat items
    rows = db.execute(
        "SELECT external_id, attrs_json FROM items WHERE source_id = 9 AND item_kind = 'cursor_chat'"
    ).fetchall()
    print(f"  scanning {len(rows)} cursor_chat items")
    updated = 0
    model_dist = {}
    t0 = time.time()
    for r in rows:
        chat_ext_id = r["external_id"]
        old_attrs = json.loads(r["attrs_json"] or "{}")
        sys_body = sys_msgs.get(chat_ext_id)
        if not sys_body:
            continue
        new_model = extract_model(sys_body)
        if not new_model:
            continue
        if old_attrs.get("model") == new_model:
            continue
        old_attrs["model"] = new_model
        db.execute(
            "UPDATE items SET attrs_json = ? WHERE source_id = 9 AND item_kind = 'cursor_chat' AND external_id = ?",
            (json.dumps(old_attrs, ensure_ascii=False), chat_ext_id),
        )
        updated += 1
        model_dist[new_model] = model_dist.get(new_model, 0) + 1
    db.commit()

    print(f"  updated {updated} cursor_chat items in {time.time()-t0:.1f}s")
    print("\n=== New model distribution ===")
    for model, n in sorted(model_dist.items(), key=lambda x: -x[1]):
        print(f"  {model}: {n}")

    print("\n=== Verified by query ===")
    for r in db.execute(
        """
        SELECT json_extract(attrs_json, '$.model') AS model, COUNT(*) AS n
        FROM items
        WHERE source_id = 9 AND item_kind = 'cursor_chat'
          AND json_extract(attrs_json, '$.model') IS NOT NULL
        GROUP BY model
        ORDER BY n DESC
        LIMIT 20
        """
    ):
        print(f"  {r[0]}: {r[1]}")

    db.close()


if __name__ == "__main__":
    main()
