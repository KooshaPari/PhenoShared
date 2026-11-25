# V5 Cell Assignment + Transcript (contract v0.3)

> Status: **enrichment** — assignment brief + chat/tool transcript for cockpit task pages
> Scope: per-cell fields in ablation / stock_vs_ours output and
> `task_results[].additionalProperties` after contract conversion

## Problem

V5 cells carried truncated `reply` (200 chars), no task title/description, no
acceptance/rubric text, and `progress_trace` quality milestones that were not
SpanKind chat/tool turns. Cockpit Canvas-style task pages need an assignment
brief plus an iMessage-like transcript.

## Cell fields (v0.3)

| Field | Type | Meaning |
|-------|------|---------|
| `task_title` | string | Short assignment title (defaults to `task_id`) |
| `task_description` | string | Human-readable task brief |
| `acceptance` | string | Acceptance criteria / contract text |
| `rubric` | string | **Dual-write alias** of `acceptance` |
| `prompt` | string | **Full** user prompt (untruncated) |
| `reply` / `reply_full` | string | **Full** model reply (untruncated) |
| `reply_preview` | string | Optional truncated preview (≤200 chars) |
| `progress_trace` | Span[] | Chat/tool spans (`kind`: turn/llm/tool/…) |
| `chat_trace` | Span[] | **Dual-write alias** of `progress_trace` |
| `assignment` | object | Nested `{title,description,acceptance,rubric}` |

Span shapes match cockpit `decodeTrace` / `SpanKind`
(`turn` \| `llm` \| `tool` \| `verifier` \| `reward` \| `raw`).

## Producer rules

1. Always emit flat fields **and** nested `assignment`.
2. Dual-write `rubric = acceptance` and `chat_trace = progress_trace`.
3. Stop truncating `reply` for contract export; keep `reply_preview` for lists.
4. Include at least user + assistant `turn` spans when prompt/reply exist.

## Consumer rules (cockpit Go dual-read)

1. Prefer flat `task_title` / `task_description`; else nested `assignment.*`.
2. Prefer `acceptance`; else `rubric`; else nested assignment fields.
3. Prefer `reply_full` when present; else `reply`.
4. Prefer non-empty `progress_trace`; else `chat_trace`.

## Helper

`bench/contracts/cell_assignment.py` exports `cell_assignment_fields()`,
`build_chat_trace()`, and dual-read accessors (`task_title`, `acceptance_text`,
`chat_transcript`, `reply_text`).
