"""Tests for :mod:`phenotype_py_utils.logging`."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Generator

import pytest

from phenotype_py_utils.logging import DEFAULT_FORMAT, JsonFormatter, setup_logging


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Generator[None, None, None]:
    """Each test starts with a clean root logger."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    yield
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def test_default_setup_uses_stderr_and_info(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.INFO
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)
    logging.getLogger("phenotype_py_utils").info("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.err
    assert "INFO" in captured.err


def test_custom_level_case_insensitive() -> None:
    setup_logging("debug")
    assert logging.getLogger().level == logging.DEBUG


def test_json_output_produces_parseable_json(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("INFO", json_output=True)
    logging.getLogger("phenotype_py_utils").info("json-msg")
    captured = capsys.readouterr()
    line = captured.err.strip()
    payload = json.loads(line)
    assert payload["msg"] == "json-msg"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "phenotype_py_utils"
    assert "ts" in payload


def test_custom_format_string(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging("INFO", format="CUSTOM %(message)s")
    logging.getLogger("phenotype_py_utils").info("hi")
    captured = capsys.readouterr()
    assert "CUSTOM hi" in captured.err


def test_custom_stream() -> None:
    buf = io.StringIO()
    setup_logging("INFO", stream=buf)
    logging.getLogger("phenotype_py_utils").info("buffered")
    assert "buffered" in buf.getvalue()


def test_clears_existing_handlers() -> None:
    root = logging.getLogger()
    root.addHandler(logging.NullHandler())
    root.addHandler(logging.NullHandler())
    setup_logging()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)


def test_json_formatter_includes_exception() -> None:
    fmt = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys as _sys

        record = logging.LogRecord(
            name="x",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=_sys.exc_info(),
        )
    rendered = fmt.format(record)
    payload = json.loads(rendered)
    assert payload["msg"] == "failed"
    assert "ValueError: boom" in payload["exc"]


def test_json_formatter_includes_stack_info() -> None:
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="x",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failed",
        args=(),
        exc_info=None,
    )
    record.stack_info = "Stack (most recent call last):\n  fake_frame\n"
    rendered = fmt.format(record)
    payload = json.loads(rendered)
    assert "stack" in payload
    assert "fake_frame" in payload["stack"]


def test_default_format_constant() -> None:
    # Format directive names are preserved; the field spec is "(levelname)-8s"
    # so we look at the prefix rather than the full token.
    assert "asctime" in DEFAULT_FORMAT
    assert "levelname" in DEFAULT_FORMAT
    assert "message" in DEFAULT_FORMAT
    assert "name" in DEFAULT_FORMAT
