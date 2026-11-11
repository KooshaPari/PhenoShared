"""Tests for scripts/validate_stale_patterns.py.

The scan exists to keep retired MCP anti-patterns out of guidance while still
letting append-only records state what happened and letting ban-defining docs
name the ban. These tests pin both halves of that contract, plus the guards that
stop an exemption from becoming a silent blanket pass.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_stale_patterns", ROOT / "scripts" / "validate_stale_patterns.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


vsp = _load()

GUIDANCE = "docs/guides/example.md"
RECORD = "docs/monorepo-state/STATUS.md"
MARKER = "<!-- stale-patterns: file-allow=ADR that retires the pattern -->"


def _failures(text: str, rel: str = GUIDANCE) -> list[str]:
    failures, _ = vsp.scan_text(rel, text)
    return failures


def test_clean_text_passes() -> None:
    assert _failures("# Title\n\nNothing banned here.\n") == []


def test_bare_banned_pattern_fails() -> None:
    failures = _failures("Do a mirror-to-empty bootstrap for the new repo.\n")
    assert len(failures) == 1
    assert failures[0].startswith(f"{GUIDANCE}:1")
    assert "mirror-to-empty" in failures[0]


def test_failure_names_the_line_not_just_the_file() -> None:
    failures = _failures("line one\nline two\nstandalone cheap-llm-mcp repo\n")
    assert len(failures) == 1
    assert failures[0].startswith(f"{GUIDANCE}:3")


def test_word_boundary_spares_branch_names_and_filenames() -> None:
    # A branch name and a filename embed the repo name but name something else.
    text = (
        "chore/w1-1-cheap-llm-mcp-deprecation-note-2026-06-15\n"
        "see [mirror-to-empty-repo](mirror-to-empty-repo.md)\n"
    )
    assert _failures(text) == []


def test_never_mirror_prose_is_not_a_violation() -> None:
    assert _failures("Never mirror-to-empty a repository.\n") == []


def test_record_scope_is_exempt_without_any_marker() -> None:
    text = "cheap-llm-mcp was deleted.\nmirror-to-empty was the root cause.\n"
    failures, granted = vsp.scan_text(RECORD, text)
    assert failures == []
    assert len(granted) == 2
    assert all("historical record" in g for g in granted)


def test_record_file_outside_a_record_tree_is_exempt() -> None:
    text = "cheap-llm-mcp appears in this dated audit.\n"
    failures, granted = vsp.scan_text("docs/operations/sd-retire-audit-2026-06-17.md", text)
    assert failures == []
    assert len(granted) == 1


def test_exemption_does_not_extend_to_neighbouring_trees() -> None:
    # A live operations doc is NOT a record and must still be caught.
    text = "Use cheap-llm-mcp for this.\n"
    failures = _failures(text, rel="docs/operations/runbook.md")
    assert len(failures) == 1


def test_file_marker_exempts_ban_defining_guidance() -> None:
    text = f"{MARKER}\n# ADR\n\nmirror-to-empty was retired here.\n"
    failures, granted = vsp.scan_text("docs/adrs/ADR-999.md", text)
    assert failures == []
    assert len(granted) == 1
    assert "ADR that retires the pattern" in granted[0]


def test_file_marker_outside_header_window_is_not_honoured() -> None:
    text = "filler\n" * 12 + f"{MARKER}\nmirror-to-empty was retired here.\n"
    failures = _failures(text)
    assert len(failures) == 1
    assert "banned pattern" in failures[0]


def test_orphan_file_marker_fails() -> None:
    failures = _failures(f"{MARKER}\nNo matches in this guidance file.\n")
    assert len(failures) == 1
    assert "orphan file exemption marker" in failures[0]


def test_file_marker_without_reason_fails() -> None:
    text = "<!-- stale-patterns: file-allow= -->\nmirror-to-empty was retired here.\n"
    failures = _failures(text)
    assert any("needs a justification" in f for f in failures)


def test_file_marker_short_reason_fails() -> None:
    text = "<!-- stale-patterns: file-allow=ok -->\nmirror-to-empty was retired.\n"
    failures = _failures(text)
    assert any("needs a justification" in f for f in failures)


def test_repo_scan_is_clean() -> None:
    """The checked-in tree must pass; this is the same gate CI runs."""
    failures: list[str] = []
    for rel, path in vsp.iter_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        file_failures, _ = vsp.scan_text(rel, text)
        failures.extend(file_failures)
    assert failures == [], "\n".join(failures)


def test_main_exit_codes(monkeypatch, capsys) -> None:
    assert vsp.main() == 0
    assert "OK no banned MCP patterns" in capsys.readouterr().out

    monkeypatch.setattr(
        vsp, "iter_files", lambda: [("docs/bad.md", _FakePath("mirror-to-empty\n"))]
    )
    assert vsp.main() == 1
    assert "STALE:" in capsys.readouterr().out


class _FakePath:
    def __init__(self, text: str) -> None:
        self._text = text

    def read_text(self, encoding: str = "utf-8", errors: str = "replace") -> str:
        return self._text
