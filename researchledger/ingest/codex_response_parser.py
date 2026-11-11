"""codex_response_parser.py — extract response_item lines into message-shaped dicts.

Pure parsing; no sqlite. Imported by codex_migrate_to_research.py and re-exported
under its public names (`parse_message_content`, `parse_response_item`) so callers
do not need edits.

A response_item line's `payload.type` discriminates one of:

  - "message"             user/assistant/developer text via `content[]`
  - "function_call"       top-level tool call (`name`/`arguments` at payload level)
  - "function_call_output" tool result (`output` at payload level)
  - "custom_tool_call"    openai custom tool call (just `name`)
  - "custom_tool_call_output" openai custom tool call result
  - "reasoning"           standalone reasoning block (uses `summary[]`)
  - "agent_message"       inter-agent (often encrypted; skip when empty)

Other types are skipped. Empty encrypted_content stubs are kept so FTS5 indexes
the line.
"""

from __future__ import annotations

import json


def parse_message_content(content) -> tuple[str, int, int, int, int, int, int, str]:
    """
    Extract text + counters from a response_item payload.content[] array.
    Handles input_text, output_text, reasoning_text, encrypted_content.
    Returns (concatenated_text, n_text, n_tool_use, n_tool_result, n_image, n_reasoning, n_custom, tool_names_csv).
    """
    if not isinstance(content, list):
        return "", 0, 0, 0, 0, 0, 0, ""

    texts: list[str] = []
    n_text = n_tool_use = n_tool_result = n_image = n_reasoning = n_custom = 0
    tool_names: list[str] = []

    for c in content:
        if not isinstance(c, dict):
            continue
        t = c.get("type", "unknown")
        if t == "input_text":
            n_text += 1
            txt = c.get("text", "")
            if txt:
                texts.append(txt)
        elif t == "output_text":
            n_text += 1
            txt = c.get("text", "")
            if txt:
                texts.append(txt)
        elif t == "reasoning_text":
            n_reasoning += 1
            txt = c.get("text", "")
            if txt:
                texts.append(f"<<reasoning>>\n{txt}\n<<end reasoning>>")
        elif t == "encrypted_content":
            # Inter-agent message — we can't decrypt. Keep a stub so FTS5 indexes it.
            n_text += 1
            texts.append(f"<<encrypted_content {len(c.get('encrypted_content', ''))} chars>>")
        else:
            # Unknown block — keep a stub
            texts.append(f"<<{t}>>")

    return ("\n".join(texts).strip(), n_text, n_tool_use, n_tool_result, n_image, n_reasoning, n_custom,
            ",".join(tool_names))


def parse_response_item(line: dict) -> dict | None:
    """
    Parse a response_item line into a message dict.
    Returns None if the line should be skipped (e.g., encrypted inter-agent).

    Returned dict keys:
      msg_id, role, content_text, content_json, block_count, text_block_count,
      tool_use_count, tool_result_count, image_block_count, reasoning_block_count,
      custom_tool_call_count, tool_use_names
    """
    p = line.get("payload", {})
    if not isinstance(p, dict):
        return None

    ptype = p.get("type", "?")
    payload_id = p.get("id") or f"line-{line.get('ordinal', '?')}-{line.get('timestamp', '?')}"

    # 'message' type carries user/assistant/developer text via content[] + role
    if ptype == "message":
        role = p.get("role", "")
        content = p.get("content", [])
        text, n_text, n_tool_use, n_tool_result, n_image, n_reasoning, n_custom, tool_names = \
            parse_message_content(content)
        return {
            "msg_id": payload_id,
            "role": role,
            "content_text": text,
            "content_json": json.dumps(content, ensure_ascii=False) if content is not None else None,
            "block_count": len(content) if isinstance(content, list) else 0,
            "text_block_count": n_text,
            "tool_use_count": n_tool_use,
            "tool_result_count": n_tool_result,
            "image_block_count": n_image,
            "reasoning_block_count": n_reasoning,
            "custom_tool_call_count": n_custom,
            "tool_use_names": tool_names,
        }

    if ptype == "function_call":
        # Top-level tool call. name/arguments at payload level.
        name = p.get("name", "")
        args = p.get("arguments", "")
        if isinstance(args, str):
            try:
                args_obj = json.loads(args)
            except json.JSONDecodeError:
                args_obj = None
        else:
            args_obj = args

        # Compact digest
        digest = f"<<function_call {name}>>"
        if isinstance(args_obj, dict):
            for k in ("command", "file_path", "intent", "query", "url"):
                if k in args_obj:
                    v = str(args_obj[k])
                    if len(v) > 200:
                        v = v[:200] + "..."
                    digest = f"<<function_call {name}: {v}>>"
                    break
        elif isinstance(args, str):
            digest = f"<<function_call {name}: {args[:200]!r}>>"

        return {
            "msg_id": payload_id,
            "role": "assistant",  # function_call is from the assistant
            "content_text": digest,
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": 1,
            "text_block_count": 0,
            "tool_use_count": 1,
            "tool_result_count": 0,
            "image_block_count": 0,
            "reasoning_block_count": 0,
            "custom_tool_call_count": 0,
            "tool_use_names": name,
        }

    if ptype == "function_call_output":
        # Top-level tool result. role = tool (implicit).
        output = p.get("output", "")
        if isinstance(output, str):
            if len(output) > 4096:
                output = output[:4096] + "\n... [truncated]"
            text = f"<<function_call_output>>\n{output}\n<<end function_call_output>>"
        else:
            text = f"<<function_call_output (non-string output)>>"
        call_id = p.get("call_id", "")
        return {
            "msg_id": payload_id,
            "role": "tool",
            "content_text": text,
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": 1,
            "text_block_count": 0,
            "tool_use_count": 0,
            "tool_result_count": 1,
            "image_block_count": 0,
            "reasoning_block_count": 0,
            "custom_tool_call_count": 0,
            "tool_use_names": None,
        }

    if ptype == "custom_tool_call":
        name = p.get("name", "")
        return {
            "msg_id": payload_id,
            "role": "assistant",
            "content_text": f"<<custom_tool_call {name}>>",
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": 1,
            "text_block_count": 0,
            "tool_use_count": 0,
            "tool_result_count": 0,
            "image_block_count": 0,
            "reasoning_block_count": 0,
            "custom_tool_call_count": 1,
            "tool_use_names": name,
        }

    if ptype == "custom_tool_call_output":
        output = p.get("output", "")
        if isinstance(output, str):
            if len(output) > 4096:
                output = output[:4096] + "\n... [truncated]"
            text = f"<<custom_tool_call_output>>\n{output}\n<<end custom_tool_call_output>>"
        else:
            text = f"<<custom_tool_call_output (non-string output)>>"
        return {
            "msg_id": payload_id,
            "role": "tool",
            "content_text": text,
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": 1,
            "text_block_count": 0,
            "tool_use_count": 0,
            "tool_result_count": 1,
            "image_block_count": 0,
            "reasoning_block_count": 0,
            "custom_tool_call_count": 0,
            "tool_use_names": None,
        }

    if ptype == "reasoning":
        # Standalone reasoning block (no content array; has summary[])
        summary = p.get("summary", [])
        texts = []
        for s in summary:
            if isinstance(s, dict):
                t = s.get("text", "")
                if t:
                    texts.append(t)
            elif isinstance(s, str):
                texts.append(s)
        full_text = "\n".join(texts)
        return {
            "msg_id": payload_id,
            "role": "assistant",
            "content_text": f"<<reasoning>>\n{full_text}\n<<end reasoning>>" if full_text else "[reasoning block]",
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": 1,
            "text_block_count": 0,
            "tool_use_count": 0,
            "tool_result_count": 0,
            "image_block_count": 0,
            "reasoning_block_count": 1,
            "custom_tool_call_count": 0,
            "tool_use_names": None,
        }

    if ptype == "agent_message":
        # Inter-agent message — usually encrypted. Skip (we can't decrypt).
        # The text may still be readable for some legacy sessions.
        content = p.get("content", [])
        text, _, _, _, _, _, _, _ = parse_message_content(content)
        if not text:
            return None  # skip encrypted inter-agent messages
        return {
            "msg_id": payload_id,
            "role": "developer",  # mark as system-level
            "content_text": text,
            "content_json": json.dumps(p, ensure_ascii=False),
            "block_count": len(content) if isinstance(content, list) else 0,
            "text_block_count": 1 if text else 0,
            "tool_use_count": 0,
            "tool_result_count": 0,
            "image_block_count": 0,
            "reasoning_block_count": 0,
            "custom_tool_call_count": 0,
            "tool_use_names": None,
        }

    # Other types (configuration_update, etc.) — skip
    return None


# ---------------------------------------------------------------------------
# Legacy (2025-era) rollout lines
# ---------------------------------------------------------------------------
# Before Codex wrapped events in `response_item`, rollout lines carried the
# event `type` at the TOP level, e.g.
#     {"type":"message","role":"user","content":[{"type":"input_text",...}]}
#     {"type":"local_shell_call","action":{"type":"exec","command":[...]}}
# These files are decompressed by the migrator but produced zero messages until
# they were adapted into the payload shape parse_response_item() understands.
LEGACY_TOP_LEVEL_TYPES = frozenset({
    "message",
    "function_call",
    "function_call_output",
    "custom_tool_call",
    "custom_tool_call_output",
    "reasoning",
    "local_shell_call",
})


def adapt_legacy_line(line: dict, ordinal: int) -> dict | None:
    """Wrap a legacy top-level-type line so parse_response_item() can read it.

    Returns None for lines that are not legacy message/tool events.
    """
    if not isinstance(line, dict):
        return None
    t = line.get("type")
    if t not in LEGACY_TOP_LEVEL_TYPES:
        return None

    if t == "local_shell_call":
        action = line.get("action") or {}
        payload = {
            "type": "function_call",
            "id": line.get("id") or f"legacy-{ordinal}",
            "name": "local_shell_call",
            "arguments": json.dumps(action, ensure_ascii=False),
            "call_id": line.get("call_id"),
        }
    else:
        payload = dict(line)
        payload.setdefault("id", line.get("id") or f"legacy-{ordinal}")

    return {
        "payload": payload,
        "timestamp": line.get("timestamp", ""),
        "ordinal": line.get("ordinal", ordinal),
    }
