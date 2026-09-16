"""Root pytest configuration for pheno-harness.

Platform notes:
- On Windows, pytest's default basetemp lives under the home directory
  (e.g. ``C:\\Users\\<user>\\AppData\\Local\\Temp\\pytest-of-<user>``). When the
  working tree path exceeds MAX_PATH (260 chars), pytest fails with
  ``PermissionError: [WinError 5] Access is denied`` while trying to set up
  its scratch directory. Pointing ``basetemp`` at a short-path location
  keeps the suite portable.
- On Linux/macOS this also shortens tmp paths and avoids home-directory
  permission races.
- Operators may override the scratch root with the ``PHENO_PYTEST_BASETEMP``
  environment variable, or by passing ``--basetemp=`` on the CLI (the CLI
  value wins).
"""

from __future__ import annotations

import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest


def _resolve_basetemp() -> Path:
    """Pick a short, writable scratch directory for pytest's basetemp.

    Preference order:
      1. ``PHENO_PYTEST_BASETEMP`` env var
      2. ``<tempdir>/pheno-pytest-<pid>-<rand>`` (per-process, always writable,
         always short; the PID + random suffix prevents cross-invocation
         collisions where one pytest run leaves behind an open file handle
         that prevents the next run from materialising its scratch dir
         under MAX_PATH on Windows).
      3. ``sys.prefix + /pheno-pytest-tmp`` (fallback for read-only sys.prefix)
    """
    override = os.environ.get("PHENO_PYTEST_BASETEMP")
    if override:
        return Path(override)
    # tempfile.gettempdir() is always writable for the current user and
    # resolves to a short path on every platform (TMPDIR, /tmp, etc.).
    # The PID + 8-hex suffix isolates each pytest invocation so file
    # handles leaked by a previous (perhaps crashed) test don't block
    # the next one.
    suffix = f"{os.getpid()}-{secrets.token_hex(4)}"
    return Path(tempfile.gettempdir()) / f"pheno-pytest-{suffix}"


def pytest_configure(config: pytest.Config) -> None:
    """Force pytest's basetemp to a short, predictable path."""
    basetemp = _resolve_basetemp()
    try:
        basetemp.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only filesystem (rare): fall back to a guaranteed-writable
        # location under sys.prefix if writable, else the process cwd.
        fallback = Path(sys.prefix) / "pheno-pytest-tmp"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            basetemp = fallback
        except OSError:
            basetemp = Path.cwd() / "pheno-pytest-tmp"
            basetemp.mkdir(parents=True, exist_ok=True)
    # Only override if the user didn't explicitly pass --basetemp= on CLI.
    cli_args = config.invocation_params.args or ()
    cli_basetemp = any(
        arg == "--basetemp" or arg.startswith("--basetemp=")
        for arg in cli_args
    )
    if not cli_basetemp:
        config.option.basetemp = str(basetemp)
