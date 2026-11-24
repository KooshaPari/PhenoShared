"""Project entrypoint for Import Linter."""

from __future__ import annotations


def main() -> None:
    from importlinter.cli import lint_imports_command

    lint_imports_command()
