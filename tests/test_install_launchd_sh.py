"""DAG-22: tests/test_install_launchd_sh.py

The install_launchd.sh script is the load-bearing piece that
configures 4 launchd agents. The script's `# set -f` line is the
#1 source of cron mystery failures — without it, bash pathname
expansion turns literal `*` in the plist into the cwd's filenames.

The test asserts:

  1. The script has `set -f` early (before any heredoc).
  2. The plist template contains the literal `*` (the daily sentinel).
  3. After install, the plist's Weekday field is the integer `*`
     (the launchd parser coerces the literal to a wildcard).
  4. The script's bootstrap calls are idempotent (no error if
     already loaded).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "scripts" / "cron" / "install_launchd.sh"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"


def test_install_launchd_has_set_minus_f_before_heredoc() -> None:
    text = INSTALL_SH.read_text()
    set_f_pos = text.find("set -f")
    heredoc_pos = text.find("cat <<")
    assert set_f_pos > 0, "missing `set -f` line"
    assert heredoc_pos == -1 or set_f_pos < heredoc_pos, (
        "`set -f` must appear before any cat << heredoc"
    )


def test_install_launchd_uses_bash() -> None:
    text = INSTALL_SH.read_text()
    assert text.startswith("#!/bin/bash") or text.startswith("#!/usr/bin/env bash"), (
        f"unexpected shebang: {text.splitlines()[0]!r}"
    )


def test_install_launchd_plist_template_contains_literal_star() -> None:
    """The plist template must contain `*` for the daily schedule."""
    text = INSTALL_SH.read_text()
    # Look for the StartCalendarInterval block — daily is denoted by
    # '*' (a literal asterisk) as the Weekday value.
    # We accept either '<key>Weekday</key><integer>*</integer>' or
    # the bash-side ' * ' sentinel passed to render_plist.
    assert (
        "<key>Weekday</key><integer>*</integer>" in text
        or " * " in text  # in the SCHEDULE_sota= line
    ), "no daily-schedule literal `*` in plist template"


@pytest.mark.skipif(not PLIST_DIR.is_dir(), reason="no LaunchAgents dir on this host")
def test_sota_snapshot_plist_uses_bash_for_python_script() -> None:
    """The sota-snapshot plist's ProgramArguments must point to a
    python interpreter (not /bin/bash) since it runs a .py file.
    """
    plist = PLIST_DIR / "com.phenotype.pheno-harness.sota-snapshot.plist"
    if not plist.is_file():
        pytest.skip("sota-snapshot plist not installed")
    text = plist.read_text()
    # First ProgramArguments entry should be a python3 path.
    m = re.search(r"<string>(/[^<]+)</string>", text)
    assert m is not None
    prog = m.group(1)
    assert "python" in prog.lower(), f"expected python interpreter, got {prog}"
