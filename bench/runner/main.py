"""Back-compat CLI entry: ``bench.runner.main`` → ``bench.cli``."""

from bench.cli import build_parser, main

__all__ = ["build_parser", "main"]
