"""TDD: cell assignment + transcript dual-read helpers (contract v0.3)."""

from __future__ import annotations

from bench.contracts.cell_assignment import (
    acceptance_text,
    build_chat_trace,
    cell_assignment_fields,
    chat_transcript,
    reply_text,
    task_description,
    task_title,
)


def test_cell_assignment_fields_flat_shape():
    fields = cell_assignment_fields(
        suite="terminal-bench",
        task_id="tb-easy-00",
        prompt="echo the current date and time",
        reply="Sun Jul 21 18:00:00 PDT 2026\n",
        expected="ok",
        difficulty="easy",
    )
    assert fields["task_title"] == "tb-easy-00"
    assert "terminal-bench" in fields["task_description"]
    assert fields["acceptance"]
    assert fields["rubric"] == fields["acceptance"]
    assert fields["prompt"] == "echo the current date and time"
    assert fields["reply"] == "Sun Jul 21 18:00:00 PDT 2026\n"
    assert fields["reply_full"] == fields["reply"]
    assert isinstance(fields["progress_trace"], list)
    assert fields["chat_trace"] == fields["progress_trace"]
    kinds = {span.get("kind") for span in fields["progress_trace"]}
    assert "turn" in kinds
    assert "llm" in kinds


def test_cell_assignment_nested_dual_read():
    cell = {
        "assignment": {
            "title": "Nested Title",
            "description": "Nested description body",
            "acceptance": "Must print date",
            "rubric": "unused when acceptance present",
        }
    }
    assert task_title(cell) == "Nested Title"
    assert task_description(cell) == "Nested description body"
    assert acceptance_text(cell) == "Must print date"


def test_cell_assignment_flat_overrides_nested():
    cell = {
        "task_title": "Flat Title",
        "assignment": {"title": "Nested Title", "description": "d"},
        "task_description": "Flat desc",
        "rubric": "Rubric-only acceptance",
    }
    assert task_title(cell) == "Flat Title"
    assert task_description(cell) == "Flat desc"
    assert acceptance_text(cell) == "Rubric-only acceptance"


def test_chat_transcript_dual_reads_progress_or_chat_trace():
    spans = [{"kind": "turn", "turn": 0, "role": "user", "content": "hi"}]
    assert chat_transcript({"progress_trace": spans}) == spans
    assert chat_transcript({"chat_trace": spans}) == spans
    assert chat_transcript({"progress_trace": [], "chat_trace": spans}) == spans
    assert chat_transcript({}) == []


def test_reply_text_prefers_full():
    assert reply_text({"reply": "trunc", "reply_full": "full answer"}) == "full answer"
    assert reply_text({"reply": "only"}) == "only"
    assert reply_text({}) == ""


def test_build_chat_trace_span_kinds():
    spans = build_chat_trace(
        prompt="q?",
        reply="a!",
        model="smoke",
        tool_calls=[{"name": "bash", "ok": True}],
    )
    assert spans[0]["kind"] == "turn" and spans[0]["role"] == "user"
    assert any(s["kind"] == "tool" and s.get("tool_name") == "bash" for s in spans)
    assert any(s["kind"] == "turn" and s.get("role") == "assistant" for s in spans)
