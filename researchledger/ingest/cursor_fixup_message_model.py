#!/usr/bin/env python3
"""
cursor_fixup_message_model.py — Propagate correct cursor_chat model to its messages.

W9e-fix only updated the cursor_chat (system-message) item. The buggy regex
in cursor_migrate_to_research.py also stored the broken value on every
cursor_message item:

  attrs_json.model = "an interactive CLI tool that helps users with
                      software engineering tasks"  (247,741 items)
  author           = "cursor:an interactive CLI tool..."  (23,050 items)

This script joins cursor_message -> cursor_chat via
attrs_json.chat_external_id, takes the chat's now-correct model, and:

  1. Sets attrs_json.model on each cursor_message to the chat's model
     (NULL when the chat has no model).
  2. Rewrites author on cursor_message items whose current author starts
     with the bogus string OR with a truncated model like "cursor:GPT-5"
     to use the correct "<model>" suffix from the chat.

Idempotent: re-running with the same chat-level model values is a no-op.

Usage:
  python3 cursor_fixup_message_model.py --dry-run
  python3 cursor_fixup_message_model.py --apply
"""
import argparse
import json
import os
import sqlite3
import sys

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402


DEFAULT_DB = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")

# Bogus model values that need to be replaced.
BOGUS_MODEL_VALUES = (
    "an interactive CLI tool that helps users with software engineering tasks",
)


def count_bad_models(conn):
    """Count cursor_message items still holding a bogus model value."""
    placeholders = ",".join("?" * len(BOGUS_MODEL_VALUES))
    return conn.execute(
        f"""
        SELECT COUNT(*) FROM items
        WHERE source_id = 9
          AND item_kind = 'cursor_message'
          AND json_extract(attrs_json, '$.model') IN ({placeholders})
        """,
        BOGUS_MODEL_VALUES,
    ).fetchone()[0]


def count_bad_authors(conn):
    placeholders = ",".join("?" * len(BOGUS_MODEL_VALUES))
    return conn.execute(
        f"""
        SELECT COUNT(*) FROM items
        WHERE source_id = 9
          AND author LIKE 'cursor:' || ? || '%'
        """,
        (BOGUS_MODEL_VALUES[0],),
    ).fetchone()[0]


def fixup_message_models(conn):
    """Propagate chat-level model to message-level attrs_json.model."""
    cur = conn.execute(
        """
        UPDATE items
        SET attrs_json = json_set(
            attrs_json,
            '$.model',
            (SELECT json_extract(c.attrs_json, '$.model')
             FROM items c
             WHERE c.source_id = 9
               AND c.item_kind = 'cursor_chat'
               AND c.external_id = json_extract(items.attrs_json, '$.chat_external_id'))
        )
        WHERE source_id = 9
          AND item_kind = 'cursor_message'
          AND json_extract(attrs_json, '$.model') IN (
              'an interactive CLI tool that helps users with software engineering tasks'
          )
        """
    )
    return cur.rowcount


def fixup_message_authors(conn):
    """Rewrite cursor_message.author when the model was bogus."""
    cur = conn.execute(
        """
        UPDATE items
        SET author = 'cursor:' || COALESCE(
            (SELECT json_extract(c.attrs_json, '$.model')
             FROM items c
             WHERE c.source_id = 9
               AND c.item_kind = 'cursor_chat'
               AND c.external_id = json_extract(items.attrs_json, '$.chat_external_id')),
            'unknown'
        )
        WHERE source_id = 9
          AND item_kind = 'cursor_message'
          AND author LIKE 'cursor:an interactive CLI tool%'
        """
    )
    return cur.rowcount


def main():
    ap = argparse.ArgumentParser(description="Propagate correct cursor_chat model to cursor_message items")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Opt in to writing the canonical research_ledger corpus (required when --db is the sealed corpus path)")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        ap.error("must pass --dry-run or --apply")

    guard_write_target(args.db, allow_canonical=args.allow_canonical)
    conn = sqlite3.connect(args.db)

    bad_models_before = count_bad_models(conn)
    bad_authors_before = count_bad_authors(conn)
    print(f"bogus attrs_json.model on cursor_message: {bad_models_before}")
    print(f"bogus cursor:<bogus> author on cursor_message: {bad_authors_before}")

    if args.dry_run:
        print("\n(dry-run; no writes)")
        conn.close()
        return 0

    n1 = fixup_message_models(conn)
    print(f"\nrewrote attrs_json.model on {n1} cursor_message items")

    n2 = fixup_message_authors(conn)
    print(f"rewrote author on {n2} cursor_message items")

    conn.commit()

    bad_models_after = count_bad_models(conn)
    bad_authors_after = count_bad_authors(conn)
    print(f"\n=== after ===")
    print(f"bogus attrs_json.model: {bad_models_after}")
    print(f"bogus author: {bad_authors_after}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
