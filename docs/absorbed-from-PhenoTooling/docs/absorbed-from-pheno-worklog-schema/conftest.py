"""Conftest for pheno-worklog-schema tests.

Adds ``src/`` to ``sys.path`` and to ``os.environ['PYTHONPATH']`` so the
in-tree ``pheno_worklog_schema`` package can be imported by both this
process and any subprocesses it spawns — without requiring
``pip install -e .`` first.

The test environment may use a different Python interpreter than the
one ``pip`` is bound to (e.g. python3.14 with pip pointing at a
python3.13 site-packages on the MacBook). This conftest ensures the
in-tree package is always importable.

This file is loaded automatically by pytest before any test module is
imported, so the package is available to every test and to any
``subprocess.run(...)`` invocations inside tests (the CLI tests in
``test_emit_jsonl.py`` rely on the ``PYTHONPATH`` injection to find
the in-tree package).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.exists():
    _src_str = str(_SRC)
    if _src_str not in sys.path:
        sys.path.insert(0, _src_str)
    # Prepend to PYTHONPATH so subprocesses (e.g. CLI tests that invoke
    # `sys.executable -m pheno_worklog_schema.emit_jsonl`) also see the
    # in-tree package. Colon-separated on POSIX, semicolon on Windows.
    sep = ";" if os.name == "nt" else ":"
    existing = os.environ.get("PYTHONPATH", "")
    parts = [p for p in existing.split(sep) if p]
    if _src_str not in parts:
        parts.insert(0, _src_str)
    os.environ["PYTHONPATH"] = sep.join(parts)
