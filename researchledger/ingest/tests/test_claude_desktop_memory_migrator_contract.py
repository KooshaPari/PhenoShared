"""claude_desktop_memory_migrate.py — output contract characterization.

Builds a synthetic ~/.claude/projects/<proj_hash>/memory/*.md tree and
runs the migrator against a temp research_ledger target. Pins:

  * The single target table migrated_claude_desktop_memory_notes with the
    expected columns.
  * The external_id shape: 'claude_desktop_mem:<8hex>:<stem>'.
  * frontmatter_json — the only JSON column — is a valid JSON object.
  * first_heading captured correctly when a top-level heading is present.
  * exit code 0; canonical corpus untouched.
  * Migrator does NOT register a `sources` row (it operates on the same
    source registered by claude_desktop_migrate_to_research.py).
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
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
def patched_memory_migrator(tmp_path, monkeypatch):
    """Import the module and point CLAUDE_DIR at a tmp_path before tests run."""
    mod = importlib.import_module("claude_desktop_memory_migrate")
    fake = tmp_path / "fake_claude"
    fake.mkdir()
    monkeypatch.setattr(mod, "CLAUDE_DIR", fake)
    return mod


def _write_md(memory_dir: Path, project_hash: str, name: str,
              with_frontmatter: bool = True) -> Path:
    proj = memory_dir.parent
    memory_dir.mkdir(parents=True, exist_ok=True)
    body = f"# {name.replace('_', ' ').title()}\n\nThis is a note body.\n"
    if with_frontmatter:
        text = (
            "---\n"
            "name: " + name + "\n"
            "description: a test note\n"
            "metadata: skip\n"
            "---\n" + body
        )
    else:
        text = body
    p = memory_dir / f"{name}.md"
    p.write_text(text)
    return p


def test_memory_writes_table_with_expected_columns_and_external_id_shape(
    tmp_path, patched_memory_migrator, research_db,
):
    """External_id shape 'claude_desktop_mem:<8hex>:<stem>' + every expected col."""
    mod = patched_memory_migrator
    # Build projects/<hash>/memory/<stem>.md for two synthetic projects.
    proj1 = mod.CLAUDE_DIR / "projects" / "abc12345" / "memory"
    proj2 = mod.CLAUDE_DIR / "projects" / "deadbeef" / "memory"
    _write_md(proj1, "abc12345", "note1", with_frontmatter=True)
    _write_md(proj2, "deadbeef", "note2", with_frontmatter=True)

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0

    expected = {
        "external_id", "filename", "project_path", "file_path",
        "byte_size", "line_count", "frontmatter_json", "first_heading",
        "content_text", "modified_at_ms", "captured_at",
    }
    conn = _open(research_db)
    try:
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(migrated_claude_desktop_memory_notes)"
        ).fetchall()}
        assert cols >= expected, (
            f"missing cols: {expected - cols}"
        )

        rows = conn.execute("""
            SELECT external_id, filename, project_path, first_heading
            FROM migrated_claude_desktop_memory_notes
            ORDER BY filename
        """).fetchall()
        assert len(rows) == 2

        for r in rows:
            ext = r["external_id"]
            assert ext.startswith("claude_desktop_mem:"), ext
            head, stem = ext.rsplit(":", 1)
            hexpart = head.split(":", 1)[1]
            assert len(hexpart) == 8 and all(
                c in "0123456789abcdef" for c in hexpart
            ), hexpart

        # This migrator does NOT register a sources row of its own;
        # confirm we did not accidentally invent one.
        n = conn.execute(
            "SELECT COUNT(*) FROM sources WHERE kind='claude_desktop'"
        ).fetchone()[0]
        assert n == 0
    finally:
        conn.close()


def test_memory_frontmatter_json_is_valid_object_and_first_heading_captured(
    tmp_path, patched_memory_migrator, research_db,
):
    """frontmatter_json is the only JSON column in this schema. Pin it."""
    mod = patched_memory_migrator
    proj = mod.CLAUDE_DIR / "projects" / "abc12345" / "memory"
    _write_md(proj, "abc12345", "alpha", with_frontmatter=True)
    _write_md(proj, "abc12345", "beta", with_frontmatter=False)

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0

    conn = _open(research_db)
    try:
        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_claude_desktop_memory_notes
            WHERE frontmatter_json IS NOT NULL
              AND json_valid(frontmatter_json) = 0
        """).fetchone()[0]
        assert bad == 0

        bad = conn.execute("""
            SELECT COUNT(*) FROM migrated_claude_desktop_memory_notes
            WHERE frontmatter_json IS NOT NULL
              AND json_type(frontmatter_json) NOT IN ('object', 'null')
        """).fetchone()[0]
        assert bad == 0

        # The note with frontmatter has parsed keys.
        row = conn.execute("""
            SELECT frontmatter_json FROM migrated_claude_desktop_memory_notes
            WHERE filename='alpha.md'
        """).fetchone()
        assert row is not None
        parsed = json.loads(row[0])
        assert parsed.get("name") == "alpha"
        assert parsed.get("description") == "a test note"

        # The note without frontmatter has empty {} parsed frontmatter.
        row = conn.execute("""
            SELECT frontmatter_json FROM migrated_claude_desktop_memory_notes
            WHERE filename='beta.md'
        """).fetchone()
        assert row is not None
        parsed = json.loads(row[0])
        assert parsed == {}

        # first_heading is captured from '# X' markdown lines.
        head_alpha = conn.execute("""
            SELECT first_heading FROM migrated_claude_desktop_memory_notes
            WHERE filename='alpha.md'
        """).fetchone()[0]
        assert head_alpha == "Alpha"
        head_beta = conn.execute("""
            SELECT first_heading FROM migrated_claude_desktop_memory_notes
            WHERE filename='beta.md'
        """).fetchone()[0]
        assert head_beta == "Beta"

        # content_text is the body, NOT the frontmatter. Pin that
        # the frontmatter name="alpha" does NOT leak into content_text.
        body_alpha = conn.execute("""
            SELECT content_text FROM migrated_claude_desktop_memory_notes
            WHERE filename='alpha.md'
        """).fetchone()[0]
        assert "name: alpha" not in body_alpha
        assert "This is a note body." in body_alpha
    finally:
        conn.close()


def test_memory_migrator_writes_only_to_target(
    tmp_path, patched_memory_migrator, research_db,
):
    """Confirm the migrator did not touch the canonical corpus nor real ~/.claude."""
    mod = patched_memory_migrator
    assert str(research_db).startswith(str(tmp_path))
    # The real ~/.claude lives at <HOME>/.claude. Pin that our patched
    # CLAUDE_DIR does not equal that path. (Cannot use startswith(Path.home())
    # because the test runner's HOME is itself under the user's home tree.)
    real_claude = Path.home() / ".claude"
    assert mod.CLAUDE_DIR.resolve() != real_claude.resolve(), (
        f"CLAUDE_DIR leaked to {mod.CLAUDE_DIR}"
    )

    proj = mod.CLAUDE_DIR / "projects" / "abc12345" / "memory"
    _write_md(proj, "abc12345", "note1", with_frontmatter=True)

    rc = mod.main(["--db", str(research_db)])
    assert rc is None or rc == 0

    from researchledger.corpus_guard import guard_write_target, CANONICAL
    assert os.path.exists(CANONICAL)
    with pytest.raises(SystemExit):
        guard_write_target(CANONICAL, allow_canonical=False)
