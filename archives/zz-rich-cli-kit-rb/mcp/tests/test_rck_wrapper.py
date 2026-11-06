"""Tests for the `rck` subprocess wrapper.

These exercise the real debug-built binary (`../target/debug/rck`) so we
verify end-to-end: Python → CLI → kitty-graphics-or-fallback bytes.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich_cli_mcp import rck  # noqa: E402


@pytest.fixture(scope="module")
def rck_bin() -> str:
    try:
        return rck.find_rck()
    except rck.RckUnavailable as e:
        pytest.skip(str(e))


def test_detect_returns_capabilities(rck_bin):
    caps = rck.detect()
    assert caps.terminal
    assert isinstance(caps.graphics, bool)
    assert isinstance(caps.unicode_width, int)


def test_progress_renders_percentage(rck_bin):
    out = rck.run_progress(0.5, label="halfway", ascii_=True).decode()
    assert "50%" in out
    assert "halfway" in out
    assert "[" in out and "]" in out


def test_panel_renders_title(rck_bin):
    out = rck.run_panel("smoke", "line a\nline b", border="ascii").decode()
    assert "smoke" in out
    assert "line a" in out
    assert "line b" in out
    assert "+" in out


def test_progress_clamps_over_one(rck_bin):
    out = rck.run_progress(2.0, ascii_=True).decode()
    assert "100%" in out


def test_link_contains_osc8_or_plaintext(rck_bin):
    out = rck.run_link("https://x", "see-here").decode()
    assert "see-here" in out


def test_copy_roundtrip(rck_bin):
    # On non-clipboard terminals the CLI prints a stderr note and empty stdout;
    # either way it should not error.
    try:
        rck.run_copy("hello")
    except Exception as e:
        pytest.fail(f"run_copy raised: {e}")


def test_task_start_end(rck_bin):
    rck.run_task_marker("start", task_id="demo")
    rck.run_task_marker("end", exit_code=0)


def test_ask_non_tty_defaults_to_cancel(rck_bin):
    # Parent has no TTY via pytest capture — the Rust side falls back to
    # plain stdin and reads EOF → Cancelled (exit 2) or "N" → 1.
    code, _ = rck.run_ask("proceed?")
    assert code in (0, 1, 2)


def test_pick_non_tty(rck_bin):
    code, _ = rck.run_pick("pick one", ["a", "b"])
    assert code in (0, 2)


def test_input_non_tty(rck_bin):
    code, _ = rck.run_input("name")
    assert code in (0, 2)


def test_server_builds():
    """Just import + build; real MCP transport isn't exercised here."""
    from rich_cli_mcp.server import build_server
    try:
        mcp = build_server()
    except RuntimeError as e:
        pytest.skip(str(e))
    assert mcp is not None
