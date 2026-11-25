#!/usr/bin/env python3
"""Harbor *consumer* dry-run — verify PyPI ``harbor`` is importable and CLI-reachable.

This is intentionally a thin operator hook. It does **not** vendor or fork
Harbor / portage framework code. Install with::

    uv pip install -e ".[harbor]"

Exit codes:
  0 — harbor import + ``harbor --help`` (or equivalent) succeeded
  1 — harbor package missing (install ``.[harbor]``)
  2 — harbor importable but CLI dry-run failed
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so the local ``harbor/`` namespace
# package is findable when this script is invoked directly (otherwise
# sys.path[0] is the scripts/ directory and the namespace package is
# not on the search path).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _harbor_version() -> str:
    try:
        return importlib.metadata.version("harbor")
    except importlib.metadata.PackageNotFoundError as exc:
        raise SystemExit(
            "harbor is not installed. Run: uv pip install -e '.[harbor]'\n"
            f"detail: {exc}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run Harbor consumer boundary (PyPI harbor only)."
    )
    parser.add_argument(
        "--require-cli",
        action="store_true",
        help="Also require `harbor` on PATH and run `harbor --help`.",
    )
    args = parser.parse_args(argv)

    version = _harbor_version()
    # Import the installed package — proves the dependency resolves.
    try:
        import harbor  # noqa: F401
    except ImportError as exc:
        print(f"[harbor-dry-run] FAIL: cannot import harbor ({exc})", file=sys.stderr)
        return 1

    print(f"[harbor-dry-run] ok: harbor {version} importable")

    if args.require_cli:
        exe = shutil.which("harbor")
        if not exe:
            print(
                "[harbor-dry-run] FAIL: `harbor` not on PATH "
                "(install console script via pip/uv)",
                file=sys.stderr,
            )
            return 2
        proc = subprocess.run(
            [exe, "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            print(
                f"[harbor-dry-run] FAIL: harbor --help rc={proc.returncode}\n"
                f"{proc.stderr[-400:]}",
                file=sys.stderr,
            )
            return 2
        print(f"[harbor-dry-run] ok: CLI `{exe}` --help")

    print("[harbor-dry-run] PASS (consumer boundary; no framework fork)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
