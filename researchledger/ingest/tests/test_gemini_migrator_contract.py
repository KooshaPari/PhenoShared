"""gemini_migrate_to_research.py — output contract characterization.

Builds a synthetic gemini-20261010/raw/ tree with a tiny hand-crafted
MyActivity.html (matching the outer-cell regex shape and the date format
parser) plus 2 stub media files. Pins:

  * Both target tables (migrated_google_gemini_records and _media).
  * External_id matches `gemini:<16hex>` shape.
  * exit code 0; canonical corpus untouched.
  * caption_html is HTML text, not JSON; only the URL field is a URL string.

NOTE: gemini has NO JSON column in its migrated_* schema today, so the
regression guard doesn't apply. We pin text columns instead.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from researchledger import corpus_guard  # noqa: E402

ANALYSIS = Path(__file__).resolve().parent.parent


def _open(p: Path) -> sqlite3.Connection:
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def gemini_raw_dir(tmp_path: Path) -> Path:
    """Tiny takeout: 5 records covering the 4 prompt/response shapes, plus
    2 stub media files.

    Coverage:
      rec1: response WITH date (Prompted X<br>date<br>Y)
      rec2: image-only WITH date (Prompted X<br>1 generated image.<br>date)
      rec3: response WITHOUT date, double-<br> separator
      rec4 + rec5: same prompt, different responses (regression guard for D3)

    IMPORTANT: the wrap deliberately omits <main>. A fixture that contains
    <main> hides D2 (the production parser previously used a lookahead
    terminator </main></body></html> which silently dropped the LAST record
    in real Takeout HTML, since real Takeout has no <main>).
    """
    rd = tmp_path / "gemini_raw"
    media_dir = rd / "Takeout" / "My Activity" / "Gemini Apps"
    media_dir.mkdir(parents=True)

    # The real takeout wraps each <div class="outer-cell"> inside a
    # body-level <div class="mdl-grid"> and each outer-cell has its own
    # inner <div class="mdl-grid"> + a header-cell + 3 content-cells
    # (left, right (empty), caption). The parser's caption regex requires
    # 3 closing </div>s after the caption, which only happens if the
    # outer-cell + inner mdl-grid are both closed inside the capture.
    rec1_html = """
<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid">
    <div class="header-cell mdl-cell mdl-cell--12-col">
      <p class="mdl-typography--title">Gemini Apps<br></p>
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Prompted hello<br>Sep 1, 2026, 10:00:00 AM EDT<br>world response
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 mdl-typography--text-right"></div>
    <div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">
      <b>Products:</b><br>&emsp;Gemini Apps<br>
      <b>Details:</b><br>&emsp;https://gemini.google.com/app/abc123def4567890
    </div>
  </div>
</div>
"""
    rec2_html = """
<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid">
    <div class="header-cell mdl-cell mdl-cell--12-col">
      <p class="mdl-typography--title">Gemini Apps<br></p>
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Prompted draw a cat<br>1 generated image.<br>Sep 2, 2026, 11:00:00 AM EDT
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 mdl-typography--text-right"></div>
    <div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">
      <img src="image.png" class="image-preview">
      <b>Products:</b><br>&emsp;Gemini Apps<br>
      <b>Details:</b><br>&emsp;https://gemini.google.com/app/feedfacecafebeef
    </div>
  </div>
</div>
"""
    # Response WITHOUT date; uses <br><br> separator.
    rec3_html = """
<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid">
    <div class="header-cell mdl-cell mdl-cell--12-col">
      <p class="mdl-typography--title">Gemini Apps<br></p>
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Prompted lone prompt<br><br>only response
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 mdl-typography--text-right"></div>
    <div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">
      <b>Products:</b><br>&emsp;Gemini Apps<br>
      <b>Details:</b><br>&emsp;https://gemini.google.com/app/0011223344556677
    </div>
  </div>
</div>
"""
    # Same prompt, DIFFERENT response (D3 regression guard).
    rec4_html = """
<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid">
    <div class="header-cell mdl-cell mdl-cell--12-col">
      <p class="mdl-typography--title">Gemini Apps<br></p>
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Prompted shared prompt<br><br>first response
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 mdl-typography--text-right"></div>
    <div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">
      <b>Products:</b><br>&emsp;Gemini Apps<br>
      <b>Details:</b><br>&emsp;https://gemini.google.com/app/aabbccddeeff0011
    </div>
  </div>
</div>
"""
    rec5_html = """
<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid">
    <div class="header-cell mdl-cell mdl-cell--12-col">
      <p class="mdl-typography--title">Gemini Apps<br></p>
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Prompted shared prompt<br><br>second response
    </div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 mdl-typography--text-right"></div>
    <div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">
      <b>Products:</b><br>&emsp;Gemini Apps<br>
      <b>Details:</b><br>&emsp;https://gemini.google.com/app/2233445566778899
    </div>
  </div>
</div>
"""
    # Wrap all records in a body-level mdl-grid (matches real takeout) and
    # close the same 3 levels at the end (outer-cell + inner mdl-grid +
    # body-level mdl-grid) before </body></html>. NOTE: deliberately no
    # <main>. The pre-fix records_raw regex required
    # </div></div></div></main></body></html> as a backstop alternative;
    # without <main>, real Takeout HTML silently drops the LAST record.
    html = (
        "<html><body><div class=\"mdl-grid\">"
        + rec1_html + rec2_html + rec3_html + rec4_html + rec5_html
        + "</div></div></div></div></body></html>"
    )
    (media_dir / "MyActivity.html").write_text(html)
    # Stub media files (NOT MyActivity.html so they're migrated)
    (media_dir / "image.png").write_bytes(b"\\x89PNG\\r\\n\\x1a\\n" + b"\\x00" * 32)
    (media_dir / "doc.pdf").write_bytes(b"%PDF-1.4\\n" + b"\\x00" * 32)
    return rd


def test_gemini_writes_both_tables_with_expected_columns(
    tmp_path, gemini_raw_dir, research_db, monkeypatch
):
    """Phase: migrated_google_gemini_records + migrated_google_gemini_media."""
    monkeypatch.setattr(sys, "argv", [
        "gemini_migrate_to_research.py",
        "--raw-dir", str(gemini_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("gemini_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    expected = {
        "migrated_google_gemini_records": {
            "external_id", "gemini_id", "url", "title", "date_display",
            "date_iso", "prompt_text", "response_text", "has_image",
            "image_url", "caption_html", "source_path",
        },
        "migrated_google_gemini_media": {
            "filename", "file_path", "byte_size", "mime_type",
        },
    }

    conn = _open(research_db)
    try:
        # Source row registered with kind='gemini'
        kind = conn.execute("SELECT kind FROM sources WHERE kind='gemini'"
                             ).fetchone()
        assert kind is not None and kind[0] == "gemini"

        for tbl, want in expected.items():
            cols = {r[1] for r in conn.execute(
                f"PRAGMA table_info({tbl})").fetchall()}
            assert cols >= want, f"{tbl} missing: {want - cols}"

        n_rec = conn.execute(
            "SELECT COUNT(*) FROM migrated_google_gemini_records"
        ).fetchone()[0]
        n_med = conn.execute(
            "SELECT COUNT(*) FROM migrated_google_gemini_media"
        ).fetchone()[0]
        # The synthetic HTML was crafted to feed 5 records through the
        # outer-cell regex. If parsing changes, this number changes —
        # pin it.
        assert n_rec == 5, f"expected 5 records, got {n_rec}"
        # MyActivity.html is excluded by name; the 2 stub files must land.
        assert n_med == 2, f"expected 2 media, got {n_med}"
    finally:
        conn.close()


def test_gemini_records_have_expected_text_shapes_and_external_ids(
    tmp_path, gemini_raw_dir, research_db, monkeypatch
):
    """Pin column SHAPE: external_id is gemini:<16hex>, date_iso ISO-8601 UTC,
    has_image 0/1, url present iff parsed, response_text present iff
    '\n\n' split succeeded."""
    monkeypatch.setattr(sys, "argv", [
        "gemini_migrate_to_research.py",
        "--raw-dir", str(gemini_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("gemini_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    conn = _open(research_db)
    try:
        rows = conn.execute("""
            SELECT external_id, url, date_iso, prompt_text,
                   response_text, has_image, image_url, caption_html
            FROM migrated_google_gemini_records
            ORDER BY rowid
        """).fetchall()

        # Every external_id matches the 'gemini:<16 hex>' schema.
        for r in rows:
            ext = r["external_id"]
            assert ext.startswith("gemini:"), f"bad external_id: {ext!r}"
            hexpart = ext.split(":", 1)[1]
            assert len(hexpart) == 16 and all(
                c in "0123456789abcdef" for c in hexpart
            ), f"bad hex: {hexpart!r}"

        # At least one record has a parsed URL.
        urls = [r["url"] for r in rows if r["url"]]
        assert urls, "no URL in any record"
        for u in urls:
            assert u.startswith("https://gemini.google.com/app/")

        # caption_html is HTML text (not a JSON value). Pin one row to
        # confirm it carries the outer cell shape.
        for r in rows:
            assert "Apps" in (r["caption_html"] or "")

        # has_image is an integer 0 or 1, never NULL on parsed records.
        for r in rows:
            assert r["has_image"] in (0, 1)

        # date_iso, when populated, is in 'YYYY-MM-DDTHH:MM:SSZ' shape.
        for r in rows:
            di = r["date_iso"]
            if di is not None:
                # Loose check: 20 chars, contains 'T' and ends with 'Z'.
                assert len(di) == 20 and "T" in di and di.endswith("Z"), di

        # Regression guards for D1 + D3 (added 2026-10-17):
        # D1: a record whose HTML had a response MUST come out with a
        #     non-empty response_text. rec1 carries "world response" via
        #     the date-then-response shape, rec3 carries "only response"
        #     via the <br><br> shape, and rec4/rec5 carry "first/second
        #     response" via the same <br><br> shape.
        # D3: two records with the same prompt and DIFFERENT responses
        #     (rec4 vs rec5, prompt="shared prompt") MUST produce distinct
        #     external_ids. Before the fix, response_text was "" so the
        #     hash collapsed to sha256(prompt) and the two rows collided.
        resp_by_prompt = {r["prompt_text"]: r["response_text"] for r in rows}
        assert resp_by_prompt.get("hello") == "world response", (
            f"D1 regression: record with response has empty response_text; "
            f"got {resp_by_prompt.get('hello')!r}"
        )
        assert resp_by_prompt.get("lone prompt") == "only response", (
            f"D1 regression (no-date shape): {resp_by_prompt.get('lone prompt')!r}"
        )
        shared_prompt = "shared prompt"
        shared = [r for r in rows if r["prompt_text"] == shared_prompt]
        assert len(shared) == 2, f"expected 2 shared-prompt rows, got {len(shared)}"
        shared_responses = {r["response_text"] for r in shared}
        assert shared_responses == {"first response", "second response"}, (
            f"shared-prompt responses: {shared_responses!r}"
        )
        shared_ids = {r["external_id"] for r in shared}
        assert len(shared_ids) == 2, (
            f"D3 regression: same prompt + different response collapsed to "
            f"one external_id; got {shared_ids!r}"
        )
    finally:
        conn.close()


def test_gemini_migrator_writes_only_to_target(
    tmp_path, gemini_raw_dir, research_db, monkeypatch
):
    """Confirm the migrator did not touch the canonical corpus."""
    assert str(research_db).startswith(str(tmp_path))

    monkeypatch.setattr(sys, "argv", [
        "gemini_migrate_to_research.py",
        "--raw-dir", str(gemini_raw_dir),
        "--db", str(research_db),
    ])
    mod = importlib.import_module("gemini_migrate_to_research")
    rc = mod.main()
    assert rc == 0

    from researchledger.corpus_guard import guard_write_target, CANONICAL
    import os
    assert os.path.exists(CANONICAL)
    with pytest.raises(SystemExit):
        guard_write_target(CANONICAL, allow_canonical=False)


# --------------------------------------------------------------------------
# D3 regression, the case the fixture above does NOT cover.
# --------------------------------------------------------------------------

def _record(prompt: str, date: str, response: str = "") -> str:
    """One outer-cell record in the real Takeout shape."""
    body = f"Prompted\u00a0{prompt}<br>{date}"
    if response:
        body += f"<br>{response}"
    return (
        '<div class="outer-cell">'
        '<p class="mdl-typography--title">Gemini Apps</p>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f"{body}"
        "</div>"
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        "Details: https://gemini.google.com/app/aaaabbbb"
        "</div>"
        "</div>"
    )


def test_d3_same_prompt_same_response_different_timestamp_are_distinct():
    """D3 regression: the case that actually lost data.

    A user legitimately asks the SAME thing repeatedly and gets the SAME answer
    (three ``Your video is ready!`` rows on three dates; the same prompt re-sent
    minutes apart). external_id originally hashed prompt+response only, so those
    distinct interactions collided and -- because migrated_google_gemini_records
    .external_id is UNIQUE with INSERT OR IGNORE -- all but one were silently
    dropped. Measured before the timestamp was added to the hash:
    761 parsed -> 753 stored (8 records lost across 7 collision groups).

    The pre-existing D3 assertion compares same-prompt with DIFFERENT responses.
    That case passes even without the timestamp, which is why this one is needed.
    """
    html = (
        _record("same prompt", "Jan 1, 2026, 1:00:00 PM EST", "same response")
        + _record("same prompt", "Jan 2, 2026, 1:00:00 PM EST", "same response")
        + _record("same prompt", "Jan 3, 2026, 1:00:00 PM EST", "same response")
    )
    # Deliberately NO </main></body></html> tail: the real Takeout HTML has no
    # <main>, and a fixture that added one is exactly what hid D2.
    mod = importlib.import_module("gemini_migrate_to_research")
    records = mod.parse_records(html)

    assert len(records) == 3, f"D2 regression: expected 3 records, got {len(records)}"
    ids = [r["external_id"] for r in records]
    assert len(set(ids)) == 3, (
        "D3 regression: same prompt + same response at DIFFERENT times must "
        f"produce distinct external_ids, got {ids!r}. The timestamp is missing "
        "from the identity hash."
    )
    assert all(r["prompt_text"] == "same prompt" for r in records)
    assert all(r["response_text"] == "same response" for r in records)


def test_d3_duplicate_prompt_no_response_different_minutes_are_distinct():
    """The narrower half of D3: no-response records differ only by minute.

    The real data had ``name it ArgisRoute...`` at 4:50:51AM and 4:46:53AM with
    no response text at all. Under sha256(prompt) those are identical.
    """
    html = (
        _record("repeat me", "Dec 10, 2025, 4:50:51 AM EST")
        + _record("repeat me", "Dec 10, 2025, 4:46:53 AM EST")
    )
    mod = importlib.import_module("gemini_migrate_to_research")
    records = mod.parse_records(html)
    assert len(records) == 2, f"expected 2 records, got {len(records)}"
    assert len({r["external_id"] for r in records}) == 2, (
        "D3 regression: two no-response records one minute apart collapsed"
    )

