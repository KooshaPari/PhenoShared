"""Thin module shim so `python -m bench.run` lands on the runner entry point.

The skeleton owns `bench/cli.py` (which dispatches the `run` subcommand to the
skeleton-side print of the resolved RunSpec). This shim mirrors that namespace
but routes to the concrete runner execution engine in
`bench.main:main`. Both `python -m bench.run` and the `bench-run`
console script defined in `pyproject.toml` resolve here.
"""

from __future__ import annotations

import sys

from bench.main import main as _main

__all__ = ["main"]

main = _main


if __name__ == "__main__":
    sys.exit(int(_main()))
