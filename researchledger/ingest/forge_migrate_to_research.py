"""
W9d: forge (ForgeCode) → migrated_forge_prompts

Two sources, both read read-only, both landing in migrated_forge_prompts.

PRIMARY — ~/.forge/.forge.db (2.99 GB, table `conversations`)
  - 13,260 conversations; the live store Forge itself writes.
  - Columns: conversation_id, title, context (JSON text), created_at (ISO text).
  - `context` decodes to {"messages":[{"message":{"text":{"role","content"}}}]}.
    Role values are CAPITALIZED ("System", "User"), so they are matched
    case-insensitively. messages[0] is the Forge system prompt and messages[1]
    is <system_information>; only role == "user" turns are ingested.
  - Coverage 2026-03-25 → present.
  - Opened as `file:<path>?mode=ro&immutable=1` (URIs); plain `-readonly`
    fails with "unable to open database file (14)".
  - external_id = forge_db:<conversation_id>:<message_index>, and rows are
    additionally skipped when their (conversation_id, message_index) pair or
    content_hash is already present, so re-runs are idempotent and the June
    corpus is not duplicated.

HISTORICAL — ~/.forge/prompt-corpus/unified-prompts.db
  - 75,342 prompts (one per row, flat schema), extracted 2026-06-13.
  - source_tool: forge (63,075) / codex (12,219) / claude (45) / cursor (3)
  - Date range: 2026-03-25 → 2026-06-13. Superseded by .forge.db for anything
    after June, kept for its codex/claude/cursor rows and for parity with the
    already-ingested corpus.

Idempotent: UNIQUE external_id plus an explicit existence check per source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, register_source

DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
DEFAULT_FORGE_DB = Path.home() / ".forge" / "prompt-corpus" / "unified-prompts.db"
DEFAULT_FORGE_LIVE_DB = Path.home() / ".forge" / ".forge.db"

# The corpus may be under concurrent write from another builder. WAL plus a 60s
# busy timeout makes this writer wait for the lock instead of failing outright.
WRITE_PRAGMAS = ["journal_mode = WAL", "busy_timeout = 60000"]


def open_source(src: Path):
    """Open a forge source .db in read-only mode."""
    uri = f"file:{src}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def open_live_source(src: Path):
    """Open Forge's own store read-only.

    `mode=ro` alone is not enough when the file is live: SQLite tries to take
    a write lock on open and fails with "unable to open database file (14)".
    `immutable=1` tells SQLite the file is not being written through this
    connection, which is what makes a read-only open of a 3 GB live store work.
    """
    uri = f"file:{src}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def extract_user_turns(context_json: str | None) -> list[tuple[int, str]]:
    """Return [(message_index, content)] for role == 'user' turns.

    Role values in Forge's store are capitalized, so compare case-insensitively.
    Empty/whitespace-only content is dropped.
    """
    if not context_json:
        return []
    try:
        doc = json.loads(context_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(doc, dict):
        return []

    out: list[tuple[int, str]] = []
    for idx, msg in enumerate(doc.get("messages") or []):
        if not isinstance(msg, dict):
            continue
        text = (msg.get("message") or {}).get("text")
        if not isinstance(text, dict):
            continue
        role = text.get("role")
        if not isinstance(role, str) or role.strip().lower() != "user":
            continue
        content = text.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        out.append((idx, content))
    return out


def _existing_keys(dc, batch: int = 20000):
    """(conversation_id, message_index) pairs and content hashes already stored."""
    pairs: set[tuple[str, int]] = set()
    hashes: set[str] = set()
    cur = dc.execute(
        "SELECT conversation_id, message_index, content_hash FROM migrated_forge_prompts"
    )
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            break
        for conv, idx, chash in rows:
            if conv is not None and idx is not None:
                try:
                    pairs.add((str(conv), int(idx)))
                except (TypeError, ValueError):
                    pass
            if chash:
                hashes.add(chash)
    return pairs, hashes


def migrate_live_db(
    src: Path,
    db_path: Path,
    allow_canonical: bool = False,
    batch_size: int = 2000,
) -> dict:
    """Ingest ~/.forge/.forge.db conversations into migrated_forge_prompts."""
    src_db = open_live_source(src)
    db = guard_and_connect(db_path, allow_canonical, pragmas=list(WRITE_PRAGMAS))
    try:
        sc = src_db.cursor()
        dc = db.cursor()

        source_id = register_source(
            db,
            kind="forge",
            base_path=str(src),
            captured_at="2026-11-10T00:00:00Z",
            byte_size=src.stat().st_size,
            schema_version="v1.0",
            notes="forge PRIMARY: ~/.forge/.forge.db conversations (13,260 convs, user turns only, Mar 2026 ->)",
        )

        existing_pairs, existing_hashes = _existing_keys(dc)
        print(f"  existing (conversation_id, message_index) pairs: {len(existing_pairs):,}")

        # Stream: the `context` column totals ~3 GB, so never fetchall() it.
        n_conversations = sc.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        print(f"  conversations: {n_conversations:,}")
        rows_cur = sc.execute(
            "SELECT conversation_id, title, created_at, context FROM conversations"
        )

        inserted = 0
        skipped_pair = 0
        skipped_hash = 0
        skipped_empty = 0
        n_user_turns = 0

        for conv_id, title, created_at, context_json in rows_cur:
            turns = extract_user_turns(context_json)
            if not turns:
                skipped_empty += 1
                continue
            n_user_turns += len(turns)
            conv_key = str(conv_id)

            for idx, content in turns:
                if (conv_key, idx) in existing_pairs:
                    skipped_pair += 1
                    continue
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if content_hash in existing_hashes:
                    skipped_hash += 1
                    continue

                ext_id = f"forge_db:{conv_key}:{idx}"
                prompt_id = f"{conv_key}:{idx}"
                metadata = {
                    "origin": "forge_db",
                    "conversation_id": conv_key,
                    "message_index": idx,
                    "title": title,
                    "created_at": created_at,
                    "role": "user",
                }
                try:
                    dc.execute(
                        """
                        INSERT OR IGNORE INTO migrated_forge_prompts (
                            external_id, forge_prompt_id, conversation_id, workspace_id,
                            message_index, source_tool, source, content_hash, title,
                            created_at, extracted_at, content_text, content_length,
                            content_json, metadata_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            ext_id,
                            prompt_id,
                            conv_key,
                            None,
                            idx,
                            "forge",
                            "database",
                            content_hash,
                            title,
                            created_at,
                            "2026-11-10T00:00:00Z",
                            content,
                            len(content),
                            json.dumps({"content": content}, ensure_ascii=False),
                            json.dumps(metadata, ensure_ascii=False),
                        ),
                    )
                except sqlite3.Error as e:
                    print(f"  WARN: {ext_id} failed: {e}")
                    continue

                if dc.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
                    existing_pairs.add((conv_key, idx))
                    existing_hashes.add(content_hash)

            if inserted and inserted % batch_size == 0:
                db.commit()
                print(f"  ... {inserted:,} inserted")

        db.commit()

        total = dc.execute("SELECT COUNT(*) FROM migrated_forge_prompts").fetchone()[0]
        date_range = dc.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM migrated_forge_prompts"
        ).fetchone()

        return {
            "source_id": source_id,
            "conversations": n_conversations,
            "user_turns": n_user_turns,
            "rows_in_db": total,
            "inserted": inserted,
            "skipped_pair": skipped_pair,
            "skipped_hash": skipped_hash,
            "skipped_empty": skipped_empty,
            "date_range": date_range,
        }
    finally:
        src_db.close()
        db.close()


def migrate_one(src: Path, db_path: Path, allow_canonical: bool = False, batch_size: int = 5000) -> dict:
    src_db = open_source(src)
    db = guard_and_connect(db_path, allow_canonical, pragmas=list(WRITE_PRAGMAS))
    try:
        sc = src_db.cursor()
        dc = db.cursor()

        # Pre-register the source row (idempotent via WHERE NOT EXISTS in the base).
        forge_source_id = register_source(
            db,
            kind="forge",
            base_path=str(src),
            captured_at="2026-10-15T07:00:00Z",
            byte_size=src.stat().st_size,
            schema_version="v1.0",
            notes="forge passthrough from ~/.forge/prompt-corpus/unified-prompts.db (75K prompts, Mar-Jun 2026, mostly forge+codex; .forge.db is empty)",
        )

        # Check if we already migrated
        existing = dc.execute("SELECT COUNT(*) FROM migrated_forge_prompts").fetchone()[0]
        if existing > 0:
            print(f"  already migrated: {existing:,} rows. Will INSERT OR IGNORE for safety.")
            # still try to insert (idempotent)

        # Read all source rows
        rows = sc.execute(
            """
            SELECT id, content, content_hash, source_tool, source, metadata, extracted_at
            FROM prompts
            ORDER BY json_extract(metadata, '$.created_at')
            """
        ).fetchall()
        print(f"  source rows: {len(rows):,}")

        inserted = 0
        skipped_existing = 0
        for i, r in enumerate(rows):
            forge_prompt_id, content, content_hash, source_tool, source, metadata_json, extracted_at = r
            try:
                meta = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                meta = {}

            ext_id = f"forge_prompt:{forge_prompt_id}"
            try:
                dc.execute(
                    """
                    INSERT OR IGNORE INTO migrated_forge_prompts (
                        external_id, forge_prompt_id, conversation_id, workspace_id,
                        message_index, source_tool, source, content_hash, title,
                        created_at, extracted_at, content_text, content_length,
                        content_json, metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        ext_id,
                        forge_prompt_id,
                        meta.get("conversation_id"),
                        meta.get("workspace_id"),
                        meta.get("message_index"),
                        source_tool,
                        source,
                        content_hash,
                        meta.get("title"),
                        meta.get("created_at"),
                        extracted_at,
                        content,
                        len(content) if content else 0,
                        json.dumps({"content": content[:500] + "..." if content and len(content) > 500 else content}, ensure_ascii=False),
                        metadata_json,
                    ),
                )
                if dc.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
                else:
                    skipped_existing += 1
            except Exception as e:
                print(f"  WARN: row {i} failed: {e}")

            if (i + 1) % batch_size == 0:
                db.commit()
                print(f"  ... {i+1:,} processed ({inserted:,} inserted, {skipped_existing:,} existing)")

        db.commit()

        # Verify
        total = dc.execute("SELECT COUNT(*) FROM migrated_forge_prompts").fetchone()[0]
        by_tool = dc.execute(
            "SELECT source_tool, COUNT(*) FROM migrated_forge_prompts GROUP BY source_tool ORDER BY 2 DESC"
        ).fetchall()
        by_source = dc.execute(
            "SELECT source, COUNT(*) FROM migrated_forge_prompts GROUP BY source ORDER BY 2 DESC"
        ).fetchall()
        date_range = dc.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM migrated_forge_prompts"
        ).fetchone()

        return {
            "source_id": forge_source_id,
            "rows_in_source": len(rows),
            "rows_in_db": total,
            "inserted": inserted,
            "skipped_existing": skipped_existing,
            "by_tool": by_tool,
            "by_source": by_source,
            "date_range": date_range,
        }
    finally:
        src_db.close()
        db.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    add_common_args(p, db_required=True)
    p.add_argument("--src", default=str(DEFAULT_FORGE_DB),
                   help="Path to the historical unified-prompts.db corpus")
    p.add_argument("--src-forge-db", default=str(DEFAULT_FORGE_LIVE_DB),
                   help="Path to Forge's live store ~/.forge/.forge.db (default: %(default)s)")
    args = p.parse_args(argv)

    src = Path(args.src)
    live = Path(args.src_forge_db)
    if not src.exists() and not live.exists():
        print(f"ERROR: neither source found: {src} / {live}")
        return 1

    # guard_and_connect is called inside migrate_one so the guard fires
    # immediately before the first read-write connect.

    print(f"W9d: forge → migrated_forge_prompts")
    print(f"  historical source: {src}")
    print(f"  primary source:    {live}")
    print(f"  db:                {args.db}")
    print()

    live_result = None
    if live.exists():
        print("=== primary: ~/.forge/.forge.db ===")
        live_result = migrate_live_db(
            live, Path(args.db), allow_canonical=args.allow_canonical
        )
    else:
        print(f"WARN: primary source missing, skipping: {live}")

    if not src.exists():
        print(f"WARN: historical source missing, skipping: {src}")
        if live_result is None:
            return 1
        print()
        print("=== Result (primary only) ===")
        print(f"  conversations:     {live_result['conversations']:,}")
        print(f"  user turns seen:   {live_result['user_turns']:,}")
        print(f"  rows in db:        {live_result['rows_in_db']:,}")
        print(f"  inserted:          {live_result['inserted']:,}")
        print(f"  skipped (pair):    {live_result['skipped_pair']:,}")
        print(f"  skipped (hash):    {live_result['skipped_hash']:,}")
        print(f"  date range:        {live_result['date_range'][0]} → {live_result['date_range'][1]}")
        return 0

    print()
    print("=== historical: unified-prompts.db ===")
    result = migrate_one(src, Path(args.db), allow_canonical=args.allow_canonical)

    print()
    if live_result is not None:
        print("=== Result (primary: .forge.db) ===")
        print(f"  conversations:     {live_result['conversations']:,}")
        print(f"  user turns seen:   {live_result['user_turns']:,}")
        print(f"  rows in db:        {live_result['rows_in_db']:,}")
        print(f"  inserted:          {live_result['inserted']:,}")
        print(f"  skipped (pair):    {live_result['skipped_pair']:,}")
        print(f"  skipped (hash):    {live_result['skipped_hash']:,}")
        print(f"  skipped (no user): {live_result['skipped_empty']:,}")
        print(f"  date range:        {live_result['date_range'][0]} → {live_result['date_range'][1]}")
        print()

    print()
    print("=== Result (historical) ===")
    print(f"  source_id:         {result['source_id']}")
    print(f"  rows in source:    {result['rows_in_source']:,}")
    print(f"  rows in db:        {result['rows_in_db']:,}")
    print(f"  inserted:          {result['inserted']:,}")
    print(f"  skipped existing:  {result['skipped_existing']:,}")
    print(f"  date range:        {result['date_range'][0]} → {result['date_range'][1]}")
    print()
    print("by source_tool:")
    for tool, n in result["by_tool"]:
        print(f"  {tool:10s} {n:,}")
    print()
    print("by source:")
    for s, n in result["by_source"]:
        print(f"  {s:10s} {n:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
