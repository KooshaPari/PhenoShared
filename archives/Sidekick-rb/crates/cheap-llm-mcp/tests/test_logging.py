from __future__ import annotations

import json
import logging

import pytest

from cheap_llm_mcp.logging_util import JsonFormatter, request_scope


@pytest.mark.requirement("FR-LLM-060")
def test_json_formatter_basic():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="p",
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    line = JsonFormatter().format(record)
    obj = json.loads(line)
    assert obj["msg"] == "hello world"
    assert obj["level"] == "INFO"
    assert obj["logger"] == "test"


@pytest.mark.requirement("FR-LLM-061")
def test_json_formatter_includes_request_id():
    with request_scope("abc123"):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="p",
            lineno=1,
            msg="x",
            args=(),
            exc_info=None,
        )
        obj = json.loads(JsonFormatter().format(record))
        assert obj["request_id"] == "abc123"


@pytest.mark.requirement("FR-LLM-062")
def test_request_scope_auto_generates():
    with request_scope() as rid:
        assert rid is not None
        assert len(rid) == 12


@pytest.mark.requirement("FR-LLM-063")
def test_request_scope_restores_outer():
    with request_scope("outer"):
        with request_scope("inner"):
            pass
        # Outer restored
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname="p",
            lineno=1,
            msg="x",
            args=(),
            exc_info=None,
        )
        obj = json.loads(JsonFormatter().format(record))
        assert obj["request_id"] == "outer"
