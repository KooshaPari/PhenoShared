"""V5 cell assignment + transcript fields (contract v0.3).

Producers emit flat assignment fields and a SpanKind-compatible chat/tool
transcript. Consumers dual-read nested ``assignment`` / ``chat_trace`` /
``reply_full`` / ``rubric`` aliases for backward compatibility.
"""

from __future__ import annotations

from typing import Any

# Keys copied into EvaluationReport task_results.additionalProperties.
ASSIGNMENT_EXPORT_KEYS = (
    "task_title",
    "task_description",
    "acceptance",
    "rubric",
    "prompt",
    "reply",
    "reply_full",
    "reply_preview",
    "progress_trace",
    "chat_trace",
    "assignment",
    "expected_answer",
)


def _default_acceptance(*, suite: str, expected: str, difficulty: str) -> str:
    return (
        f"Suite `{suite}` ({difficulty}): model output must satisfy the task "
        f"expected mode `{expected}`. Partial credit and format checks apply "
        f"when a deterministic scorer is available; otherwise generation success "
        f"is reported as gen_ok only."
    )


def build_chat_trace(
    *,
    prompt: str,
    reply: str,
    model: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build SpanKind-compatible spans for cockpit ``decodeTrace``."""
    spans: list[dict[str, Any]] = []
    if prompt:
        spans.append(
            {
                "kind": "turn",
                "turn": 0,
                "role": "user",
                "content": prompt,
            }
        )
    if tool_calls:
        for i, call in enumerate(tool_calls):
            spans.append(
                {
                    "kind": "tool",
                    "tool_name": str(
                        call.get("name") or call.get("tool_name") or "tool"
                    ),
                    "ok": bool(call.get("ok", True)),
                    "name": str(call.get("name") or f"tool-{i}"),
                }
            )
    if model or reply:
        spans.append(
            {
                "kind": "llm",
                "model": model or "unknown",
                "tokens_in": max(len(prompt) // 4, 0),
                "tokens_out": max(len(reply) // 4, 0),
            }
        )
    if reply:
        spans.append(
            {
                "kind": "turn",
                "turn": 1,
                "role": "assistant",
                "content": reply,
            }
        )
    return spans


def cell_assignment_fields(
    *,
    suite: str,
    task_id: str,
    prompt: str,
    reply: str = "",
    expected: str = "",
    difficulty: str = "unknown",
    title: str | None = None,
    description: str | None = None,
    acceptance: str | None = None,
    model: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
    preview_chars: int = 200,
) -> dict[str, Any]:
    """Return assignment + full I/O + dual-written transcript fields."""
    task_title_v = title or task_id
    task_description_v = description or (
        f"{suite} task `{task_id}` ({difficulty}).\n\n{prompt}".strip()
    )
    acceptance_v = acceptance or _default_acceptance(
        suite=suite, expected=expected or "unspecified", difficulty=difficulty
    )
    reply_full = reply or ""
    reply_preview = reply_full[:preview_chars] if reply_full else ""
    spans = build_chat_trace(
        prompt=prompt,
        reply=reply_full,
        model=model,
        tool_calls=tool_calls,
    )
    return {
        "task_title": task_title_v,
        "task_description": task_description_v,
        "acceptance": acceptance_v,
        # Dual-write alias of acceptance for consumers that expect rubric.
        "rubric": acceptance_v,
        "prompt": prompt,
        "reply": reply_full,
        "reply_full": reply_full,
        "reply_preview": reply_preview,
        "expected_answer": expected,
        "progress_trace": spans,
        "chat_trace": spans,
        "assignment": {
            "title": task_title_v,
            "description": task_description_v,
            "acceptance": acceptance_v,
            "rubric": acceptance_v,
        },
    }


def task_title(cell: dict[str, Any]) -> str:
    """Dual-read ``task_title`` or nested ``assignment.title``."""
    if title := str(cell.get("task_title") or "").strip():
        return title
    assignment = cell.get("assignment") or {}
    if isinstance(assignment, dict):
        return str(assignment.get("title") or "").strip()
    return ""


def task_description(cell: dict[str, Any]) -> str:
    """Dual-read ``task_description`` or nested ``assignment.description``."""
    if desc := str(cell.get("task_description") or "").strip():
        return desc
    assignment = cell.get("assignment") or {}
    if isinstance(assignment, dict):
        return str(assignment.get("description") or "").strip()
    return ""


def acceptance_text(cell: dict[str, Any]) -> str:
    """Dual-read ``acceptance`` → ``rubric`` → nested assignment fields."""
    for key in ("acceptance", "rubric"):
        if text := str(cell.get(key) or "").strip():
            return text
    assignment = cell.get("assignment") or {}
    if isinstance(assignment, dict):
        for key in ("acceptance", "rubric"):
            if text := str(assignment.get(key) or "").strip():
                return text
    return ""


def reply_text(cell: dict[str, Any]) -> str:
    """Prefer ``reply_full`` over truncated ``reply``."""
    if full := str(cell.get("reply_full") or ""):
        return full
    return str(cell.get("reply") or "")


def chat_transcript(cell: dict[str, Any]) -> list[Any]:
    """Dual-read ``progress_trace`` or ``chat_trace`` (prefer non-empty)."""
    progress = cell.get("progress_trace")
    chat = cell.get("chat_trace")
    if isinstance(progress, list) and progress:
        return progress
    if isinstance(chat, list) and chat:
        return chat
    if isinstance(progress, list):
        return progress
    if isinstance(chat, list):
        return chat
    return []


def merge_assignment_into_additional(ap: dict[str, Any], cell: dict[str, Any]) -> None:
    """Copy assignment/transcript export keys from a V5 cell into AP."""
    for key in ASSIGNMENT_EXPORT_KEYS:
        if key in cell and cell[key] is not None:
            ap[key] = cell[key]
