"""
gemini_build_canonical.py — Pump migrated_google_gemini_* → canonical items/attachments.

Reads (read-only):
  research_ledger.sqlite
    - sources (id=3 for gemini)
    - migrated_google_gemini_records  (752 rows: 709 with gemini.app URL, 43 image-only)
    - migrated_google_gemini_media    (341 file metadata rows; 199 MB total, not loaded)

Writes (idempotent):
  items table (item_kind='gemini_prompt_response')  — one per record
  attachments table                                 — inline images + media files

Item kinds emitted:
  gemini_prompt_response: each record (752)

Attachment kinds emitted:
  gemini_image_inline: image_url from records that have an inline image
                       (only when filename ends in .png/.jpg/.jpeg/.webp/.heic)
  gemini_media_file:    one per migrated_google_gemini_media row (341)

Per spec §4.3 every row carries:
  source_id=3, source_kind='gemini', source_path=<orig file path>,
  evidence_type='direct', confidence='high' (gemini takeout is from
  the user's own Google account, so the data is direct evidence).

Usage:
    python3 gemini_build_canonical.py
    python3 gemini_build_canonical.py --db <PATH>
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
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
GEMINI_RAW_DIR = Path("/Users/kooshapari/Exports/gemini-20261010/raw")
GEMINI_MEDIA_DIR = GEMINI_RAW_DIR / "Takeout" / "My Activity" / "Gemini Apps"
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.bmp'}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get_source_id(conn: sqlite3.Connection, kind: str) -> int:
    cur = conn.cursor()
    r = cur.execute("SELECT id FROM sources WHERE kind = ?", (kind,)).fetchone()
    if not r:
        raise RuntimeError(f"source kind={kind!r} not found in sources table; "
                           f"run {kind}_migrate_to_research.py first")
    return r[0]


def build_items(conn: sqlite3.Connection, src_id: int, captured_at: str) -> int:
    """Insert one item per gemini record. Idempotent via items UNIQUE(source_id, external_id)."""
    cur = conn.cursor()
    n = 0
    cur.execute("""
        SELECT external_id, gemini_id, url, title, date_display, date_iso,
               prompt_text, response_text, has_image, image_url, caption_html, source_path
        FROM migrated_google_gemini_records
    """)
    for r in cur.fetchall():
        external_id, gemini_id, url, _title, date_display, date_iso, \
            prompt_text, response_text, has_image, image_url, caption_html, source_path = r

        body_parts = []
        if prompt_text:
            body_parts.append(f"[prompt]\n{prompt_text}")
        if response_text:
            body_parts.append(f"[response]\n{response_text}")
        body = "\n\n".join(body_parts)

        title_text = (prompt_text or "(no prompt)")[:120]

        attrs = {
            'gemini_id': gemini_id,
            'date_display': date_display,
            'has_image': bool(has_image),
            'image_url': image_url,
            'caption_html_len': len(caption_html) if caption_html else 0,
        }

        cur.execute("""
            INSERT OR IGNORE INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id,
            external_id,
            captured_at,
            date_iso or date_display or 'unknown',
            'direct',
            'high',
            'none',
            'gemini_prompt_response',
            'koosha',  # user is the prompt author
            title_text,
            body,
            url,
            source_path,  # raw_json_path doubles as source_path here
            json.dumps(attrs, ensure_ascii=False),
        ))
        if cur.rowcount > 0:
            n += 1
    conn.commit()
    return n


def build_attachments(conn: sqlite3.Connection, src_id: int, captured_at: str) -> int:
    """Insert attachments: inline images + media files.

    Idempotent via attachments UNIQUE INDEX (source_id, external_id).
    """
    cur = conn.cursor()
    n = 0
    today = captured_at

    # Build a quick lookup: item_external_id -> item_id
    item_id_by_ext = dict(cur.execute(
        "SELECT external_id, id FROM items WHERE source_id = ?", (src_id,)
    ).fetchall())

    # 1) Inline image references
    cur.execute("""
        SELECT external_id, image_url, gemini_id, source_path
        FROM migrated_google_gemini_records
        WHERE image_url IS NOT NULL AND image_url != ''
    """)
    for r in cur.fetchall():
        parent_external_id, image_url, gemini_id, source_path = r
        ext = os.path.splitext(image_url)[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        ext_id = f"inline-image:{image_url}"
        media_dir = os.path.dirname(source_path) if source_path else ""
        real_path = os.path.join(media_dir, image_url) if media_dir else image_url
        item_id = item_id_by_ext.get(parent_external_id)
        mime = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.webp': 'image/webp', '.heic': 'image/heic',
            '.bmp': 'image/bmp',
        }.get(ext, 'application/octet-stream')
        cur.execute("""
            INSERT OR IGNORE INTO attachments (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_id, kind, local_path, byte_size, mime_type, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id,
            ext_id,
            today,
            today,
            'direct',
            'high',
            'none',
            item_id,
            'gemini_image_inline',
            real_path,
            None,
            mime,
            None,  # source_url: gemini inline image references use a local filename, not a URL
        ))
        if cur.rowcount > 0:
            n += 1

    # Synthetic item_kind for the media directory itself
    if cur.execute(
        "SELECT 1 FROM items WHERE source_id = ? AND item_kind = 'gemini_media_directory'",
        (src_id,),
    ).fetchone():
        media_dir_item_id = cur.execute(
            "SELECT id FROM items WHERE source_id = ? AND item_kind = 'gemini_media_directory'",
            (src_id,),
        ).fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO items (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_kind, author, title, body, url,
                raw_json_path, attrs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id,
            'gemini:media-directory',
            captured_at,
            '2026-10-10',
            'direct',
            'high',
            'none',
            'gemini_media_directory',
            'koosha',
            'Gemini takeout media directory',
            f'341 media files in {GEMINI_MEDIA_DIR.relative_to(GEMINI_RAW_DIR)} (199 MB total)',
            None,
            str(GEMINI_MEDIA_DIR),
            json.dumps({
                'file_count': 341,
                'note': 'media files referenced by no specific record in MyActivity.html; '
                        'they correspond to inline images in old records that used the long filename scheme',
            }, ensure_ascii=False),
        ))
        media_dir_item_id = cur.lastrowid

    # 2) Media files
    cur.execute("""
        SELECT filename, file_path, byte_size, mime_type
        FROM migrated_google_gemini_media
    """)
    for r in cur.fetchall():
        filename, file_path, byte_size, mime_type = r
        ext_id = f"media-file:{filename}"
        cur.execute("""
            INSERT OR IGNORE INTO attachments (
                source_id, external_id, captured_at, source_captured_at,
                evidence_type, confidence, redaction_state,
                item_id, kind, local_path, byte_size, mime_type, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src_id,
            ext_id,
            today,
            today,
            'direct',
            'high',
            'none',
            media_dir_item_id,
            'gemini_media_file',
            file_path,
            byte_size,
            mime_type,
            None,
        ))
        if cur.rowcount > 0:
            n += 1

    conn.commit()
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True,
                    help="Target research_ledger DB to write. REQUIRED — the "
                         "canonical corpus is rejected unless --allow-canonical "
                         "is also passed.")
    ap.add_argument("--allow-canonical", action="store_true",
                    help="Permit writing the canonical corpus (dangerous).")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"error: db not found: {args.db}", file=sys.stderr)
        return 1

    # Hard guard: refuse canonical / sealed backup / symlink trickery.
    # Pass the *target* (--db) path, not any migrated source path.
    guard_write_target(str(args.db), allow_canonical=args.allow_canonical)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    print(f"db: {args.db}")
    print()

    t0 = time.time()
    src_id = get_source_id(conn, 'gemini')
    captured_at = now_iso()
    print(f"source id: {src_id} (kind=gemini)")
    print(f"captured_at: {captured_at}")
    print()

    print("--- building items ---")
    n_items = build_items(conn, src_id, captured_at)
    print(f"  inserted: {n_items}")
    conn.commit()
    print()

    print("--- building attachments ---")
    n_attach = build_attachments(conn, src_id, captured_at)
    print(f"  inserted: {n_attach}")
    conn.commit()
    print()

    print(f"elapsed: {time.time() - t0:.1f}s")
    print()

    cur = conn.cursor()
    print("Spot checks (gemini source in research_ledger):")
    for tbl, kind_col in [
        ('items', 'item_kind'),
        ('attachments', 'kind'),
    ]:
        for kind in ['gemini_prompt_response', 'gemini_image_inline', 'gemini_media_file', 'gemini_media_directory']:
            n = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {kind_col} = ? AND source_id = ?",
                            (kind, src_id)).fetchone()[0]
            print(f"  {tbl:15s} {kind:30s}  {n:6d}")

    # Verify FK integrity (item_id must exist in items)
    print()
    print("FK integrity:")
    r = cur.execute("""
        SELECT COUNT(*) FROM attachments a
        WHERE a.source_id = ? AND a.item_id IS NOT NULL
          AND a.item_id NOT IN (SELECT id FROM items WHERE source_id = ?)
    """, (src_id, src_id)).fetchone()
    print(f"  orphan attachments (item_id not in items): {r[0]}")

    # FTS5 check (joined to items to filter by source)
    print()
    print("FTS5 spot check (items_fts joined to items):")
    for q in ['agent', 'gemini', 'koosha', 'paridehpour', 'image', 'koosha OR paridehpour']:
        n = cur.execute("""
            SELECT COUNT(*) FROM items_fts f
            JOIN items i ON i.id = f.rowid
            WHERE items_fts MATCH ? AND i.source_id = ?
        """, (q, src_id)).fetchone()[0]
        print(f"  MATCH '{q}': {n}")

    # FTS5 attachments_fts check (no source_id column, so use JOIN)
    print()
    print("FTS5 spot check (attachments_fts joined to attachments):")
    for q in ['image', 'media', 'gemini', 'png', 'mp4']:
        n = cur.execute("""
            SELECT COUNT(*) FROM attachments_fts f
            JOIN attachments a ON a.id = f.rowid
            WHERE attachments_fts MATCH ? AND a.source_id = ?
        """, (q, src_id)).fetchone()[0]
        print(f"  MATCH '{q}': {n}")

    # Sample items
    print()
    print("Sample items (most recent 2):")
    for r in cur.execute("""
        SELECT id, title, occurred_at_via_attrs, body
        FROM (
            SELECT id, title, json_extract(attrs_json, '$.date_display') as occurred_at_via_attrs, body
            FROM items
            WHERE source_id = ? AND item_kind = 'gemini_prompt_response'
            ORDER BY json_extract(attrs_json, '$.date_display') DESC NULLS LAST
            LIMIT 2
        )
    """, (src_id,)).fetchall():
        print(f"  id={r[0]}  date={r[2]}")
        print(f"    title: {r[1]!r}")
        print(f"    body[:200]: {r[3][:200]!r}")
        print()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
