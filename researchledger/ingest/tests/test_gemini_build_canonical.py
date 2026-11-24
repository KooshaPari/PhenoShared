"""gemini_build_canonical characterization.

Pins down the gemini canonical items + attachments builder. Reads
migrated_google_gemini_records and migrated_google_gemini_media, then
emits items (item_kind='gemini_prompt_response' + a synthetic
'gemini_media_directory') and attachments (gemini_image_inline +
gemini_media_file).

We seed: a sources row with kind='gemini', one record with an inline
png image, and one media-file row. Then assert the output contract.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))


@pytest.fixture
def gemini_builder(tmp_path, monkeypatch):
    mod = importlib.import_module("gemini_build_canonical")
    return mod


def _seed_gemini_db(p: Path) -> None:
    from research_ledger_init.sources_chat import gemini_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(p)
    conn = sqlite3.connect(p)
    try:
        for stmt in gemini_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (3, 'gemini', '/fake/gemini', '2026-09-01T00:00:00Z')
        """)
        # One record WITH an inline image.
        conn.execute("""
            INSERT INTO migrated_google_gemini_records (
                id, external_id, gemini_id, url, title,
                date_display, date_iso, prompt_text, response_text,
                has_image, image_url, caption_html, source_path
            ) VALUES (
                1, 'gemini:abc-001', 'abc-001',
                'https://gemini.google.com/app/abc-001',
                'Gemini Apps', 'Sep 25, 2026, 2:32:49 PM EDT',
                '2026-09-25T18:32:49Z',
                'Draw a koala in space', 'A cute koala floats past Saturn.',
                1, 'koala.png',
                '<td>caption</td>', '/fake/gemini/raw/foo.html'
            )
        """)
        # One record WITHOUT an image.
        conn.execute("""
            INSERT INTO migrated_google_gemini_records (
                id, external_id, gemini_id, url, title,
                date_display, date_iso, prompt_text, response_text,
                has_image, image_url, caption_html, source_path
            ) VALUES (
                2, 'gemini:abc-002', 'abc-002',
                'https://gemini.google.com/app/abc-002',
                'Gemini Apps', 'Sep 26, 2026, 2:32:49 PM EDT',
                '2026-09-26T18:32:49Z',
                'Hello?', 'Hi there!', 0, NULL, NULL, '/fake/gemini/raw/bar.html'
            )
        """)
        # One media-file row.
        conn.execute("""
            INSERT INTO migrated_google_gemini_media (
                id, filename, file_path, byte_size, mime_type
            ) VALUES (
                10, 'media-1.mp4', '/fake/gemini/media/media-1.mp4', 12345, 'video/mp4'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def test_gemini_builds_items_and_attachments_with_pinned_contracts(
    research_db, monkeypatch, gemini_builder
):
    _seed_gemini_db(research_db)
    monkeypatch.setattr(sys, "argv", [
        "gemini_build_canonical.py", "--db", str(research_db),
    ])
    rc = gemini_builder.main()
    assert rc == 0

    conn = sqlite3.connect(research_db)
    try:
        # items: 2 gemini_prompt_response + 1 gemini_media_directory = 3
        n_items = conn.execute("""
            SELECT COUNT(*) FROM items WHERE source_id = 3
        """).fetchone()[0]
        assert n_items == 3
        by_kind = conn.execute("""
            SELECT item_kind, COUNT(*) FROM items WHERE source_id = 3
            GROUP BY item_kind ORDER BY item_kind
        """).fetchall()
        assert by_kind == [
            ("gemini_media_directory", 1),
            ("gemini_prompt_response", 2),
        ]

        # The 2 prompt_response items must carry the prompt text as body prefix
        # and a JSON attrs that includes the gemini_id.
        row = conn.execute("""
            SELECT body, attrs_json, item_kind
            FROM items WHERE external_id = 'gemini:abc-001' AND source_id = 3
        """).fetchone()
        body, attrs_json, item_kind = row
        assert item_kind == "gemini_prompt_response"
        # Body is "[prompt]\n...\n\n[response]\n...".
        assert body.startswith("[prompt]\nDraw a koala in space")
        assert "[response]\nA cute koala floats past Saturn." in body
        # attrs_json must be valid JSON (not a quoted string).
        parsed = json.loads(attrs_json)
        assert parsed["gemini_id"] == "abc-001"
        assert parsed["has_image"] is True
        assert parsed["image_url"] == "koala.png"
        assert parsed["date_display"] == "Sep 25, 2026, 2:32:49 PM EDT"

        # attachments: 1 inline image + 1 media file = 2
        n_att = conn.execute("""
            SELECT COUNT(*) FROM attachments WHERE source_id = 3
        """).fetchone()[0]
        assert n_att == 2
        by_att_kind = conn.execute("""
            SELECT kind, COUNT(*) FROM attachments WHERE source_id = 3
            GROUP BY kind ORDER BY kind
        """).fetchall()
        assert by_att_kind == [
            ("gemini_image_inline", 1),
            ("gemini_media_file", 1),
        ]

        # The inline attachment must reference the prompt item by id.
        inline = conn.execute("""
            SELECT a.external_id, a.item_id, a.mime_type, a.local_path
            FROM attachments a
            WHERE a.source_id = 3 AND a.kind = 'gemini_image_inline'
        """).fetchone()
        assert inline[0] == "inline-image:koala.png"
        assert inline[1] is not None  # bound to the prompt item
        assert inline[2] == "image/png"
        # local_path must join source_path dir + image_url.
        assert inline[3].endswith("/koala.png")

        # The media attachment must reference the synthetic media-directory
        # item, NOT a prompt item.
        media = conn.execute("""
            SELECT a.external_id, a.item_id, a.mime_type, a.byte_size,
                   a.local_path
            FROM attachments a
            WHERE a.source_id = 3 AND a.kind = 'gemini_media_file'
        """).fetchone()
        assert media[0] == "media-file:media-1.mp4"
        assert media[1] is not None
        assert media[2] == "video/mp4"
        assert media[3] == 12345
        assert media[4] == "/fake/gemini/media/media-1.mp4"

        # The synthetic directory item must exist exactly once.
        n_dir = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 3 AND item_kind = 'gemini_media_directory'
        """).fetchone()[0]
        assert n_dir == 1

        # FK integrity: no orphan attachments (item_id must exist in items).
        n_orphan = conn.execute("""
            SELECT COUNT(*) FROM attachments a
            WHERE a.source_id = 3 AND a.item_id IS NOT NULL
              AND a.item_id NOT IN (SELECT id FROM items WHERE source_id = 3)
        """).fetchone()[0]
        assert n_orphan == 0

        # FTS5 sanity: the prompt text should be searchable via items_fts.
        n_fts = conn.execute("""
            SELECT COUNT(*) FROM items_fts f
            JOIN items i ON i.id = f.rowid
            WHERE items_fts MATCH 'koala' AND i.source_id = 3
        """).fetchone()[0]
        assert n_fts == 1

        # Regression guards for D1 + D3 (added 2026-10-17):
        # The seeded records have response_text populated, so any items
        # downstream must NOT collapse the two gemini_prompt_response rows
        # by external_id (D3). Both rows must land in items separately.
        n_pr = conn.execute("""
            SELECT COUNT(*) FROM items
            WHERE source_id = 3 AND item_kind = 'gemini_prompt_response'
        """).fetchone()[0]
        assert n_pr == 2, f"D3 regression guard: expected 2 prompt_response items, got {n_pr}"

    finally:
        conn.close()


def test_gemini_same_prompt_different_responses_produce_distinct_external_ids(
    research_db, monkeypatch, gemini_builder
):
    """D1+D3 regression guard: two records sharing a prompt but differing in
    response must produce DISTINCT external_ids (and therefore distinct
    items downstream). Before the fix, response_text was always '' so the
    external_id collapsed to sha256(prompt) and the second row was lost."""
    from research_ledger_init.sources_chat import gemini_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(research_db)
    conn = sqlite3.connect(research_db)
    try:
        for stmt in gemini_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (3, 'gemini', '/fake/gemini', '2026-09-01T00:00:00Z')
        """)
        # Same prompt, different responses. id is INTEGER, external_id TEXT.
        for ext, resp, rid in (
            ('gemini:coll-a', 'first answer', 1001),
            ('gemini:coll-b', 'second answer', 1002),
        ):
            conn.execute("""
                INSERT INTO migrated_google_gemini_records (
                    id, external_id, gemini_id, url, title,
                    date_display, date_iso, prompt_text, response_text,
                    has_image, image_url, caption_html, source_path
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                rid, ext, ext[7:],
                f'https://gemini.google.com/app/{ext[7:]}',
                'Gemini Apps', 'Sep 25, 2026, 2:32:49 PM EDT',
                '2026-09-25T18:32:49Z',
                'same prompt', resp,
                0, None, '<td>caption</td>', '/fake/gemini/raw/foo.html',
            ))
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(sys, "argv", [
        "gemini_build_canonical.py", "--db", str(research_db),
    ])
    rc = gemini_builder.main()
    assert rc == 0
    conn = sqlite3.connect(research_db)
    try:
        rows = conn.execute("""
            SELECT external_id, item_kind
            FROM items WHERE source_id = 3 AND item_kind = 'gemini_prompt_response'
        """).fetchall()
        assert len(rows) == 2, (
            f"D3 regression: same-prompt records collapsed to {len(rows)} item(s); "
            f"expected 2 distinct external_ids. Got: {rows!r}"
        )
        ext_ids = {r[0] for r in rows}
        assert len(ext_ids) == 2, (
            f"D3 regression: two rows share an external_id: {ext_ids!r}"
        )
    finally:
        conn.close()


def test_gemini_builder_skips_non_image_extensions(
    research_db, monkeypatch, gemini_builder
):
    """Records whose image_url has a non-image extension must NOT produce
    an inline attachment. (regression: a .txt 'image_url' would otherwise
    spawn an inline-image attachment with a wrong mime type.)"""
    from research_ledger_init.sources_chat import gemini_migrated_schema
    from research_ledger_init import init as init_research_ledger

    init_research_ledger(research_db)
    conn = sqlite3.connect(research_db)
    try:
        for stmt in gemini_migrated_schema():
            conn.execute(stmt)
        conn.execute("""
            INSERT INTO sources (id, kind, base_path, captured_at)
            VALUES (3, 'gemini', '/x', '2026-09-01T00:00:00Z')
        """)
        conn.execute("""
            INSERT INTO migrated_google_gemini_records (
                id, external_id, gemini_id, url, title,
                date_display, date_iso, prompt_text, response_text,
                has_image, image_url, caption_html, source_path
            ) VALUES (
                99, 'gemini:txt', 'txt',
                'https://gemini.google.com/app/txt', 'Gemini Apps',
                'Sep 25, 2026, 2:32:49 PM EDT', '2026-09-25T18:32:49Z',
                'p', 'r', 1, 'data.txt', NULL, '/fake/gemini/raw'
            )
        """)
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(sys, "argv", [
        "gemini_build_canonical.py", "--db", str(research_db),
    ])
    gemini_builder.main()
    conn = sqlite3.connect(research_db)
    try:
        n_inline = conn.execute("""
            SELECT COUNT(*) FROM attachments
            WHERE source_id = 3 AND kind = 'gemini_image_inline'
        """).fetchone()[0]
        assert n_inline == 0
    finally:
        conn.close()