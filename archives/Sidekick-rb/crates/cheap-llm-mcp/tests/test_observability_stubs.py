"""Observability stubs for SIDE-OBS-004 (audit remediation)."""

from __future__ import annotations

import logging

import pytest

from cheap_llm_mcp.observability import operation_span, standard_field_names


def test_observability_stub_standard_fields_defined() -> None:
    fields = standard_field_names()
    assert "op" in fields
    assert "request_id" in fields
    assert "duration_ms" in fields


def test_observability_stub_operation_span_emits(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="cheap-llm-mcp.observability")
    with operation_span("test.stub", provider="stub", model="audit"):
        pass
    messages = [r.message for r in caplog.records]
    assert any("op.start" in m for m in messages)
    assert any("op.complete" in m for m in messages)


def test_observability_stub_operation_span_request_id_bound() -> None:
    with operation_span("test.bind") as payload:
        assert payload["request_id"] is not None
        assert len(payload["request_id"]) > 0
