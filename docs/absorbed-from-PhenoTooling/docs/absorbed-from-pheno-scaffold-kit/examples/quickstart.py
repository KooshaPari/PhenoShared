"""Quickstart: pheno-scaffold-kit

Run with::

    python examples/quickstart.py

Demonstrates the unified scaffold API without touching any actual repo:
runs `detect_repo_type` on this directory, then calls `init_scaffold` on a
sandbox directory under ``./out/`` and prints the structured result.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from pheno_scaffold_kit import detect_repo_type, init_scaffold


def main() -> None:
    here = Path(__file__).resolve().parent
    print(f"detect_repo_type({here}) -> {detect_repo_type(here)}")

    # Build a throwaway sandbox so init_scaffold has something to work on.
    sandbox = here / "out" / "scaffold-demo"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)

    try:
        result = init_scaffold(sandbox)
        print(f"init_scaffold({sandbox.name}) -> {result}")
    finally:
        # Leave the sandbox in place so the demo output is inspectable; comment
        # the next two lines out for a fully clean run.
        pass


if __name__ == "__main__":
    main()