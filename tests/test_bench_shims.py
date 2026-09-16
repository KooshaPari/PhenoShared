"""Tests for bench/runner/main.py import shim + bench/run.py dead module."""
from __future__ import annotations

import pytest


class TestBenchRunnerMainShim:
    def test_main_importable(self):
        from bench.runner.main import main
        assert callable(main)

    def test_build_parser_importable(self):
        from bench.runner.main import build_parser
        assert callable(build_parser)

    def test_main_is_bench_cli_main(self):
        from bench.cli import main as cli_main
        from bench.runner.main import main
        assert main is cli_main

    def test_build_parser_is_bench_cli_parser(self):
        from bench.cli import build_parser as cli_parser
        from bench.runner.main import build_parser
        assert build_parser is cli_parser


class TestBenchRunShim:
    """bench.run imports bench.main which does not exist — dead module."""

    def test_bench_main_not_importable(self):
        with pytest.raises(ModuleNotFoundError, match="bench.main"):
            import bench.main  # noqa: F401
