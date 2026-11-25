#!/usr/bin/env python3
"""W9f-4: claude_desktop memory notes (~/.claude/projects/*/memory/*.md) → migrated_claude_desktop_memory_notes

Claude Code CLI writes session memory to ~/.claude/projects/<project_hash>/memory/*.md
files. Each is a markdown document with YAML frontmatter (name, description, metadata)
and a body. These are standalone session memory notes, NOT conversation transcripts.

Idempotent: INSERT OR IGNORE on UNIQUE external_id.

Usage:
    python3 claude_desktop_memory_migrate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, write_with_retry

CLAUDE_DIR = Path.home() / ".claude"
SOURCE_KIND = "claude_desktop"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def parse_frontmatter(text):
    """Parse YAML frontmatter if present; return (dict, body)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    # Simple YAML key:value parsing (no nested support; sufficient for these notes)
    fm = {}
    current_key = None
    for line in fm_raw.split("\n"):
        if line.startswith("  ") and current_key:
            # Continuation (e.g., metadata: block) - skip for now
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
            current_key = key.strip()
    return fm, body


def first_heading(text):
    m = HEADING_RE.search(text)
    return m.group(1).strip() if m else None


def project_hash_for(path):
    """Stable short hash for project path."""
    return hashlib.sha256(str(path).encode()).hexdigest()[:8]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    add_common_args(p, db_required=True)
    args = p.parse_args(argv)

    # Refuse to write the canonical corpus unless --allow-canonical was passed.
    # guard_and_connect preserves the load-bearing order: guard FIRST, then connect.
    print("W9f-4: claude_desktop memory notes → migrated_claude_desktop_memory_notes")
    print(f"  src: {CLAUDE_DIR}/projects/*/memory/*.md")
    print(f"  db:  {args.db}")
    db = guard_and_connect(
        args.db,
        allow_canonical=args.allow_canonical,
        row_factory=sqlite3.Row,
        pragmas=["busy_timeout = 60000"],
    )

    # Find all .md files
    md_files = list(CLAUDE_DIR.glob("projects/*/memory/*.md"))
    print(f"  found {len(md_files)} markdown files")

    inserted = 0
    skipped = 0
    t0 = time.time()
    for f in md_files:
        project_path = str(f.parent.parent)  # projects/<hash>/
        ext_id = f"claude_desktop_mem:{project_hash_for(project_path)}:{f.stem}"
        existing = db.execute(
            "SELECT 1 FROM migrated_claude_desktop_memory_notes WHERE external_id = ?",
            (ext_id,),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"    WARN: {f}: {e}")
            continue
        try:
            stat = f.stat()
            fm, body = parse_frontmatter(text)
            heading = first_heading(text)
            try:
                modified_at_ms = int(stat.st_mtime * 1000)
            except Exception:
                modified_at_ms = None
            write_with_retry(
                db,
                """
                INSERT OR IGNORE INTO migrated_claude_desktop_memory_notes (
                    external_id, filename, project_path, file_path, byte_size, line_count,
                    frontmatter_json, first_heading, content_text, modified_at_ms, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ext_id,
                    f.name,
                    project_path,
                    str(f),
                    stat.st_size,
                    text.count("\n") + 1,
                    json.dumps(fm, ensure_ascii=False),
                    heading,
                    body,
                    modified_at_ms,
                    "2026-10-15T09:00:00Z",
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"    WARN: {f}: {e}")
    db.commit()

    print(f"  inserted: {inserted}, skipped: {skipped}, elapsed: {time.time()-t0:.1f}s")
    n = db.execute("SELECT COUNT(*) FROM migrated_claude_desktop_memory_notes").fetchone()[0]
    print(f"  total in table: {n}")
    db.close()
    # A lock collision used to be swallowed per file, so the migrator could
    # report "inserted: 0" and still exit 0. Fail loudly instead.
    if md_files and inserted == 0 and skipped == 0:
        print(f"  ERROR: {len(md_files)} markdown files found but 0 notes landed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
