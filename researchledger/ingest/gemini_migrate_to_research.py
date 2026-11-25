"""
gemini_migrate_to_research.py — Pump gemini-20261010 takeout into research_ledger.

Reads (read-only, never modifies):
  /Users/kooshapari/Exports/gemini-20261010/raw/Takeout/My Activity/Gemini Apps/MyActivity.html
  /Users/kooshapari/Exports/gemini-20261010/raw/Takeout/My Activity/Gemini Apps/*.{png,jpg,mp4,...}

Writes (idempotent, INSERT OR IGNORE on UNIQUE):
  migrated_google_gemini_records  (760 records: 717 with URL, 43 image-only)
  migrated_google_gemini_media    (342 media files: png, jpg, mp4, heic, pdf, pptx, ...)

Per spec §4.3 the source row carries the original path so the canonical
build can prove provenance.

Usage:
    python3 gemini_migrate_to_research.py
    python3 gemini_migrate_to_research.py --raw-dir <PATH> --db <PATH>
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from migrator_base import add_common_args, guard_and_connect, register_source

DEFAULT_RAW_DIR = Path("/Users/kooshapari/Exports/gemini-20261010/raw")
DEFAULT_DB = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"
SOURCE_ID = 3  # gemini is source #3 in the research_ledger (after session_ledger, claude)

GEMINI_HTML_REL = Path("Takeout/My Activity/Gemini Apps/MyActivity.html")
GEMINI_MEDIA_DIR_REL = Path("Takeout/My Activity/Gemini Apps")


def parse_records(html: str) -> list[dict]:
    """Parse the 11MB MyActivity.html into structured records.

    Each outer-cell record contains:
      - title: 'Gemini Apps' (always)
      - left content-cell: 'Prompted <prompt>\\n\\n<response>' + date
      - caption cell: products, details URL, why_is_this_here boilerplate
    """
    # Split on the opening marker (more robust than a tail-anchored lookahead:
    # the real Takeout HTML has no <main>, so a </main> terminator silently
    # drops the LAST record). Skip the first part (HTML preamble before any
    # record) and strip each opening tag's attributes to recover the original
    # capture content.
    parts = html.split('<div class="outer-cell')
    records_raw = []
    for p in parts[1:]:
        tag_end = p.find('>')
        if tag_end == -1:
            continue
        records_raw.append(p[tag_end + 1:])

    out = []
    for r in records_raw:
        # Title
        title_m = re.search(r'<p class="mdl-typography--title">([^<]+)<', r)
        title = title_m.group(1).strip() if title_m else None

        # Left content-cell (6-col body-1)
        left_m = re.search(
            r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">(.*?)</div>\s*<div class="content-cell',
            r, re.DOTALL,
        )
        left_html = left_m.group(1) if left_m else ""

        # Date (last <br>-preceded string in left_html)
        date_m = re.search(
            r'([A-Z][a-z]{2} \d{1,2}, \d{4},?\s*\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*(?:EDT|EST|UTC|[A-Z]{2,3}|[+-]\d+)?)',
            left_html,
        )
        date = date_m.group(1).strip() if date_m else None

        # Strip HTML, normalize whitespace. KEEP multi-line structure for
        # the prompt/response split below (see the comment in that block).
        left_text = re.sub(r'<br\s*/?>', '\n', left_html)
        left_text_raw = left_text  # preserve pre-collapse for the split
        left_text = re.sub(r'<[^>]+>', '', left_text)

        # Now split into prompt + response. We must do this BEFORE collapsing
        # '\n+' because the boundary in real Takeout HTML is a SINGLE newline
        # between (prompt / date / response), not '\n\n'. The records have one
        # of these shapes:
        #   Prompted <prompt>\n<date>\n<response>...   (date, then response)
        #   Prompted <prompt>\n<date>                   (date, no response)
        #   Prompted <prompt>\n\n<response>...          (blank line, then response)
        #   Prompted <prompt>\n                         (image-only, no response)
        prompt_text = ""
        response_text = ""
        if date:
            # The date line sits between the prompt and (optional) response.
            lines_pre = left_text.split('\n')
            date_idx = None
            for i, ln in enumerate(lines_pre):
                if date in ln:
                    date_idx = i
                    break
            if date_idx is not None:
                prompt_raw = '\n'.join(lines_pre[:date_idx])
                response_raw = '\n'.join(lines_pre[date_idx + 1:])
            else:
                # Date matched the loose regex but its line wasn't found via
                # 'in'; fall back to date-strip on the full text.
                prompt_raw = left_text.replace(date, '')
                response_raw = ""
        elif '\n\n' in left_text:
            prompt_raw, response_raw = left_text.split('\n\n', 1)
        else:
            prompt_raw = left_text
            response_raw = ""

        # Collapse whitespace and trim each side independently. The previous
        # implementation collapsed '\n+' on the entire left_text BEFORE the
        # split, which destroyed the prompt/response boundary (D1).
        prompt_text = re.sub(r'\n+', '\n', prompt_raw).strip()
        response_text = re.sub(r'\n+', '\n', response_raw).strip()

        # Strip the "Prompted " prefix that google inserts.
        if prompt_text.startswith('Prompted\xa0') or prompt_text.startswith('Prompted '):
            prompt_text = re.sub(r'^Prompted[\s\xa0]+', '', prompt_text)

        # Strip trailing metadata: "1 generated image.", "Attached N file.", "- filename"
        # These appear after the actual prompt for image-generation records.
        # IMPORTANT: any combination of these can trail the prompt, possibly
        # all three stacked. Strip them all in a loop, repeatedly, until
        # nothing matches anymore (handle all orderings).
        has_image = 0
        if re.search(r'\b\d+\s+generated\s+image', prompt_text, re.IGNORECASE):
            has_image = 1
        if re.search(r'\bAttached\s+\d+\s+file', prompt_text, re.IGNORECASE):
            has_image = 1
        prev = None
        while prev != prompt_text:
            prev = prompt_text
            prompt_text = re.sub(r'\n+Attached\s+\d+\s+files?\.?\s*$', '', prompt_text, flags=re.IGNORECASE)
            prompt_text = re.sub(r'\n+\d+\s+generated\s+image\.?\s*$', '', prompt_text, flags=re.IGNORECASE)
            prompt_text = re.sub(r'\n+-\s+\S+\s*$', '', prompt_text)
        prompt_text = prompt_text.strip()

        # Image preview: <img src="..." class="image-preview"> (src comes BEFORE class in source).
        # Also catch the inverse order for robustness.
        img_m = (
            re.search(r'<img[^>]+src="([^"]+)"[^>]*class="image-preview"', r)
            or re.search(r'<img[^>]+class="image-preview"[^>]*src="([^"]+)"', r)
        )
        image_url = img_m.group(1) if img_m else None
        if image_url:
            has_image = 1

        # Caption cell: products, details, why
        caption_m = re.search(
            r'<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">(.*?)</div>\s*</div>\s*</div>',
            r, re.DOTALL,
        )
        caption = caption_m.group(1) if caption_m else ""

        # URL
        url_m = re.search(r'https://gemini\.google\.com/app/[a-f0-9]+', caption)
        url = url_m.group(0) if url_m else None
        gemini_id = url.split('/')[-1] if url else None

        # Content-hash as the stable natural key. Why? The gemini.google.com/app/<id>
        # URL is shared across many activity-history rows (2,199 URL occurrences
        # collapse to 198 unique sessions), so it is NOT a per-record key.
        # The record identity is prompt + response + timestamp; see the block
        # below for why the timestamp cannot be omitted.
        import hashlib
        # Identity = prompt + response + TIMESTAMP. The timestamp is essential:
        # a user legitimately asks the same thing repeatedly and gets the same
        # answer back (e.g. three "Your video is ready!" rows on three dates,
        # or the same prompt re-sent minutes apart). Without the date those
        # distinct interactions hash identically and, because
        # migrated_google_gemini_records.external_id is UNIQUE with
        # INSERT OR IGNORE, all but one are silently dropped.
        # Measured before this fix: 761 parsed -> 753 stored (8 records lost
        # across 7 collision groups).
        content_for_hash = (
            (prompt_text or '') + '\x00'
            + (response_text or '') + '\x00'
            + (date or '')
        )
        external_id = "gemini:" + hashlib.sha256(
            content_for_hash.encode('utf-8', errors='ignore')
        ).hexdigest()[:16]

        out.append({
            'external_id': external_id,
            'gemini_id': gemini_id,
            'url': url,
            'title': title,
            'date_display': date,
            'prompt_text': prompt_text,
            'response_text': response_text,
            'has_image': has_image,
            'image_url': image_url,
            'caption_html': caption,
        })
    return out


def normalize_date_to_iso(date_display: str | None) -> str | None:
    """Convert 'Sep 25, 2026, 2:32:49 PM EDT' -> '2026-09-25T18:32:49Z' (approximate)."""
    if not date_display:
        return None
    # Strip narrow no-break space
    s = date_display.replace('\u202f', ' ').replace('\xa0', ' ')
    s = re.sub(r',\s+', ' ', s)  # 'Sep 25, 2026 2:32:49 PM EDT'
    # Timezone abbrev -> UTC offset (rough; eastern time treated as -04:00 in summer, -05:00 in winter)
    tz_map = {
        'EDT': '-04:00', 'EST': '-05:00',
        'PDT': '-07:00', 'PST': '-08:00',
        'CDT': '-05:00', 'CST': '-06:00',
        'MDT': '-06:00', 'MST': '-07:00',
        'UTC': '+00:00', 'GMT': '+00:00',
    }
    tz = None
    for k, v in tz_map.items():
        if s.endswith(' ' + k):
            tz = v
            s = s[:-(len(k)+1)]
            break
    # Try parsing
    for fmt in ('%b %d %Y %I:%M:%S %p', '%b %d %Y %I:%M %p'):
        try:
            dt = datetime.strptime(s, fmt)
            if tz is None:
                tz = '-04:00'  # assume EDT by default for EST/EDT-looking strings
            iso = dt.strftime('%Y-%m-%dT%H:%M:%S') + tz
            # convert to UTC
            try:
                from datetime import timezone
                dt_with_tz = datetime.fromisoformat(iso)
                dt_utc = dt_with_tz.astimezone(timezone.utc)
                return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            except Exception:
                return iso
        except ValueError:
            continue
    return date_display  # fallback: keep original


def migrate_records(cur: sqlite3.Cursor, records: list[dict], source_path: str) -> int:
    n = 0
    for r in records:
        date_iso = normalize_date_to_iso(r['date_display'])
        cur.execute("""
            INSERT OR IGNORE INTO migrated_google_gemini_records
            (external_id, gemini_id, url, title, date_display, date_iso,
             prompt_text, response_text, has_image, image_url, caption_html, source_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['external_id'],
            r['gemini_id'],
            r['url'],
            r['title'],
            r['date_display'],
            date_iso,
            r['prompt_text'],
            r['response_text'],
            r['has_image'],
            r['image_url'],
            r['caption_html'],
            source_path,
        ))
        if cur.rowcount > 0:
            n += 1
    return n


def migrate_media(cur: sqlite3.Cursor, media_dir: Path) -> int:
    """List all media files in the directory; we don't read content (199 MB)."""
    n = 0
    if not media_dir.exists():
        return 0
    for entry in sorted(os.listdir(media_dir)):
        path = media_dir / entry
        if not path.is_file():
            continue
        # Skip the MyActivity.html itself
        if entry == "MyActivity.html":
            continue
        byte_size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(path))
        cur.execute("""
            INSERT OR IGNORE INTO migrated_google_gemini_media
            (filename, file_path, byte_size, mime_type)
            VALUES (?, ?, ?, ?)
        """, (
            entry,
            str(path),
            byte_size,
            mime_type or "application/octet-stream",
        ))
        if cur.rowcount > 0:
            n += 1
    return n





def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    add_common_args(ap)
    args = ap.parse_args()

    if not args.raw_dir.exists():
        print(f"error: raw dir not found: {args.raw_dir}", file=sys.stderr)
        return 1
    if not args.db.exists():
        print(f"error: db not found: {args.db} -- run research_ledger_init.py first", file=sys.stderr)
        return 1

    html_path = args.raw_dir / GEMINI_HTML_REL
    if not html_path.exists():
        print(f"error: gemini MyActivity.html not found: {html_path}", file=sys.stderr)
        return 1

    media_dir = args.raw_dir / GEMINI_MEDIA_DIR_REL

    # guard_and_connect combines guard_write_target + sqlite3.connect in the
    # canonical order (guard first, then connect). Pragmas reproduce the
    # pre-refactor settings.
    conn = guard_and_connect(
        args.db, args.allow_canonical,
        pragmas=["journal_mode = WAL", "foreign_keys = ON"],
    )
    cur = conn.cursor()

    print(f"raw dir:  {args.raw_dir}")
    print(f"html:     {html_path}")
    print(f"media:    {media_dir}")
    print(f"db:       {args.db}")
    print()

    # Register the source (idempotent via WHERE NOT EXISTS on base)
    register_source(
        conn,
        kind="gemini",
        base_path=str(DEFAULT_RAW_DIR),
        captured_at="2026-10-10",
        byte_size=0,
        schema_version="v1.0",
        notes="Google Gemini takeout (MyActivity.html + 342 media files)",
    )
    conn.commit()
    cur.execute("SELECT id FROM sources WHERE kind = 'gemini'")
    src_id = cur.fetchone()[0]
    print(f"source id: {src_id}")
    print()

    t0 = time.time()

    # 1) Parse records
    print("--- parsing MyActivity.html ---")
    with open(html_path) as f:
        html = f.read()
    records = parse_records(html)
    print(f"  records parsed: {len(records)}")
    print(f"  with gemini URL: {sum(1 for r in records if r['url'])}")
    print(f"  image-only:      {sum(1 for r in records if not r['url'])}")
    print(f"  with prompt:     {sum(1 for r in records if r['prompt_text'])}")
    print(f"  with response:   {sum(1 for r in records if r['response_text'])}")
    print()

    # 2) Migrate records
    print("--- migrated_google_gemini_records ---")
    n_rec = migrate_records(cur, records, str(html_path))
    print(f"  inserted: {n_rec}")
    conn.commit()
    print()

    # 3) Migrate media (file metadata only)
    print("--- migrated_google_gemini_media ---")
    n_med = migrate_media(cur, media_dir)
    print(f"  inserted: {n_med}")
    conn.commit()
    print()

    print(f"elapsed: {time.time() - t0:.1f}s")
    print()

    print("Spot checks (research_ledger gemini rows):")
    for table in ["migrated_google_gemini_records", "migrated_google_gemini_media"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:50s}  {n:6d}")

    # Sample date range
    r = cur.execute("""
        SELECT MIN(date_iso), MAX(date_iso),
               SUM(has_image), COUNT(*)
        FROM migrated_google_gemini_records
        WHERE date_iso IS NOT NULL
    """).fetchone()
    print()
    print(f"  date range: {r[0]} to {r[1]}")
    print(f"  with image: {r[2]} / {r[3]} records")

    # Total media bytes
    r = cur.execute("SELECT COUNT(*), SUM(byte_size) FROM migrated_google_gemini_media").fetchone()
    print(f"  media files: {r[0]} ({r[1]:,} bytes = {r[1]/1024/1024:.1f} MB)")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
