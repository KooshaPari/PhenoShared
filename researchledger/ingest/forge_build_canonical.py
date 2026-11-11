"""
W9d: forge canonical items builder

Reads migrated_forge_prompts and creates 'forge_prompt' items in the
canonical items table.

Schema (one item per prompt):
  external_id = 'forge_prompt:<forge_prompt_id>'
  item_kind = 'forge_prompt'
  author = 'koosha' (forge prompts are user messages)
  redaction_state = 'partial' (matches jcode/kcode/codex convention)
  title = '<title>/<first 60 chars of content>/<date>' or fallback
  body = the actual prompt content

Idempotent: INSERT OR IGNORE on UNIQUE external_id.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

# The canonical corpus path is captured here ONLY so the guard can recognise it
# when the operator passes it explicitly with --allow-canonical. Do NOT pass this
# directly to sqlite3.connect() — always go through guard_write_target() first.
DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"


def iso_to_captured(forge_dt: str) -> str:
    """Convert forge's local 'YYYY-MM-DD HH:MM:SS.fff' to ISO with UTC tz.

    forge stores local time without tz suffix. We assume local time and
    convert to ISO. Most forge activity was Pacific time (the operator's
    primary TZ).
    """
    if not forge_dt:
        return ""
    try:
        # Parse naive datetime
        if "." in forge_dt:
            dt = datetime.strptime(forge_dt, "%Y-%m-%d %H:%M:%S.%f")
        else:
            dt = datetime.strptime(forge_dt, "%Y-%m-%d %H:%M:%S")
        # Mark as local time
        return dt.isoformat() + "-07:00"  # Pacific (PDT)
    except ValueError:
        return forge_dt


def build_canonical(db_path: Path, batch_size: int = 5000) -> dict:
    db = sqlite3.connect(db_path)
    try:
        c = db.cursor()

        forge_source_id = c.execute("SELECT id FROM sources WHERE kind='forge'").fetchone()[0]
        print(f"forge source_id: {forge_source_id}")

        # Get all migrated prompts
        rows = c.execute(
            """
            SELECT external_id, conversation_id, workspace_id, message_index,
                   source_tool, source, content_hash, title, created_at, extracted_at,
                   content_text, content_length
            FROM migrated_forge_prompts
            """
        ).fetchall()
        print(f"migrated rows: {len(rows):,}")

        # Pre-load existing items to skip
        existing = set(r[0] for r in c.execute("SELECT external_id FROM items WHERE source_id = ?", (forge_source_id,)))
        print(f"existing items: {len(existing):,}")

        inserted = 0
        skipped_existing = 0

        for i, r in enumerate(rows):
            (ext_id, conv_id, workspace_id, msg_index, source_tool, source,
             content_hash, title, created_at, extracted_at, content_text, content_length) = r

            if ext_id in existing:
                skipped_existing += 1
                continue

            # Map author
            author = "koosha"  # forge prompts are user messages

            # Build title
            first_line = ""
            if content_text:
                first_line = content_text.split("\n", 1)[0].strip()[:60]
            date_str = (created_at or "")[:10]
            title_str = ""
            if title and first_line:
                title_str = f"forge/{title[:40]}/{first_line}/{date_str}"
            elif title:
                title_str = f"forge/{title[:80]}/{date_str}"
            elif first_line:
                title_str = f"forge/{first_line}/{date_str}"
            else:
                title_str = f"forge/{ext_id[-12:]}/{date_str}"

            # Cap title length
            if len(title_str) > 200:
                title_str = title_str[:197] + "..."

            # Build body (full content, no truncation)
            body = content_text or ""

            # Build attrs JSON
            attrs = {
                "source_tool": source_tool,
                "source": source,
                "conversation_id": conv_id,
                "workspace_id": workspace_id,
                "message_index": msg_index,
                "content_hash": content_hash,
                "content_length": content_length,
            }

            # Captured_at from created_at (forge local) → ISO
            source_captured_at = iso_to_captured(created_at) if created_at else None

            try:
                c.execute(
                    """
                    INSERT INTO items (
                        source_id, external_id, captured_at, source_captured_at,
                        evidence_type, confidence, redaction_state, item_kind,
                        author, title, body, raw_json_path, attrs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        forge_source_id,
                        ext_id,
                        "2026-10-15T07:00:00Z",  # canonical migration time
                        source_captured_at,
                        "direct",  # direct from forge DB
                        "high",  # direct import from source DB
                        "partial",  # matches jcode/kcode/codex convention
                        "forge_prompt",
                        author,
                        title_str,
                        body,
                        f"/Users/kooshapari/.forge/prompt-corpus/unified-prompts.db#{ext_id}",
                        json.dumps(attrs, ensure_ascii=False),
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"  WARN: row {i} ({ext_id}) failed: {e}")

            if (i + 1) % batch_size == 0:
                db.commit()
                print(f"  ... {i+1:,} processed ({inserted:,} inserted, {skipped_existing:,} existing)")

        db.commit()

        # Verify
        total = c.execute(
            "SELECT COUNT(*) FROM items WHERE source_id = ?", (forge_source_id,)
        ).fetchone()[0]
        by_tool = c.execute(
            """
            SELECT json_extract(attrs_json, '$.source_tool'), COUNT(*)
            FROM items WHERE source_id = ? GROUP BY 1 ORDER BY 2 DESC
            """,
            (forge_source_id,),
        ).fetchall()

        return {
            "source_id": forge_source_id,
            "rows_in_migrated": len(rows),
            "rows_in_items": total,
            "inserted": inserted,
            "skipped_existing": skipped_existing,
            "by_tool": by_tool,
        }
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True,
                   help="Target research_ledger DB to write. REQUIRED — the "
                        "canonical corpus is rejected unless --allow-canonical "
                        "is also passed.")
    p.add_argument("--allow-canonical", action="store_true",
                   help="Permit writing the canonical corpus (dangerous).")
    args = p.parse_args(argv)

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--db) path, not any migrated source path.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    print(f"W9d: forge → items")
    print(f"  db: {args.db}")
    print()

    result = build_canonical(Path(args.db))
    print()
    print("=== Result ===")
    print(f"  source_id:        {result['source_id']}")
    print(f"  rows migrated:    {result['rows_in_migrated']:,}")
    print(f"  rows in items:    {result['rows_in_items']:,}")
    print(f"  inserted:         {result['inserted']:,}")
    print(f"  skipped existing: {result['skipped_existing']:,}")
    print()
    print("by source_tool:")
    for tool, n in result["by_tool"]:
        print(f"  {tool!r:10s} {n:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
