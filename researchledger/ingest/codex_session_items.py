#!/usr/bin/env python3
"""
codex_session_items.py — recovered structure from Codex `item_completed` records.

The rollout stores two parallel views of a turn:

  1. `response_item` records  — the raw request/response stream (messages, tool
     calls, tool outputs). Text is present, but `spawn_agent` / `send_message`
     arguments are Fernet-encrypted, so agent *instructions* are unreadable.
  2. `event_msg` / `item_completed` records — a typed projection of the same turn:
     `SubAgentActivity`, `CollabAgentToolCall`, `CommandExecution`, `McpToolCall`,
     `Extension`, `ContextCompaction`, `AgentMessage`.

The typed projection is the only readable source for agent topology (who ran,
under which thread id, on which model) and for MCP call arguments and results.
Dropping it as "structural noise" loses real evidence, so it is recovered here.

`Reasoning` and `UserMessage` items are deliberately skipped: their `raw_content`
and `summary_text` are empty in practice, and their text already exists verbatim
in the `response_item` stream.
"""

from __future__ import annotations

INFORMATIVE = {
    "SubAgentActivity",
    "CollabAgentToolCall",
    "CommandExecution",
    "McpToolCall",
    "Extension",
    "ContextCompaction",
    "AgentMessage",
}

CAP = 1200


def _txt(v, cap: int = CAP) -> str:
    s = v if isinstance(v, str) else ("" if v is None else str(v))
    return s if len(s) <= cap else s[:cap] + f" …[+{len(s) - cap}]"


def classify_item(ts: str, ordinal, payload: dict) -> dict | None:
    """Turn one `item_completed` payload into a compact event, or None to skip."""
    item = payload.get("item")
    if not isinstance(item, dict):
        return None
    it = item.get("type")
    if it not in INFORMATIVE:
        return None
    return {"ts": ts, "ord": ordinal, "kind": "item", "item_type": it, "item": item}


def accumulate(store: dict, ev: dict) -> None:
    """Fold one typed item into the report store (capped strings only)."""
    it = ev["item_type"]
    item = ev["item"]
    store["counts"][it] = store["counts"].get(it, 0) + 1

    if it == "SubAgentActivity":
        store["agents"].append({
            "ts": ev["ts"], "kind": item.get("kind"),
            "path": item.get("agent_path"), "thread_id": item.get("agent_thread_id"),
            "model": item.get("model"), "effort": item.get("reasoning_effort"),
        })
    elif it == "CollabAgentToolCall":
        store["collab"].append({
            "ts": ev["ts"], "tool": item.get("tool"), "status": item.get("status"),
            "receivers": item.get("receiver_agents") or item.get("receiver_thread_ids") or [],
        })
    elif it == "CommandExecution":
        cmd = item.get("command") or []
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
        store["commands"].append({
            "ts": ev["ts"], "exit": item.get("exit_code"), "status": item.get("status"),
            "cwd": item.get("cwd"), "cmd": _txt(cmd), "source": item.get("source"),
            "out": _txt(item.get("aggregated_output")),
        })
    elif it == "McpToolCall":
        store["mcp"].append({
            "ts": ev["ts"], "server": item.get("server"), "tool": item.get("tool"),
            "status": item.get("status"),
            "args": _txt(item.get("arguments")), "result": _txt(item.get("result")),
        })
    elif it == "Extension":
        store["extensions"].append({
            "ts": ev["ts"], "kind": item.get("kind"), "action": item.get("action"),
            "query": _txt(item.get("query")),
        })
    elif it == "ContextCompaction":
        store["markers"].append({"ts": ev["ts"], "id": item.get("id")})


def new_store() -> dict:
    return {"counts": {}, "agents": [], "collab": [], "commands": [],
            "mcp": [], "extensions": [], "markers": []}


def write_item_reports(w, store: dict) -> None:
    """Emit subagent_roster.md, mcp_calls.md, and commands.md."""
    # ---- subagent roster
    out = ["# Subagent roster (recovered from typed items)", "",
           "`spawn_agent` / `send_message` arguments are encrypted in this thread, so the "
           "instructions each subagent received are unreadable. This roster is the "
           "readable counterpart: every agent that actually ran, with its thread id, "
           "model, and lifecycle.", ""]
    seen: dict[str, dict] = {}
    for a in store["agents"]:
        key = a.get("path") or a.get("thread_id") or "?"
        row = seen.setdefault(key, {"path": key, "thread_id": a.get("thread_id"),
                                    "model": None, "effort": None,
                                    "started": None, "completed": 0, "interrupted": 0,
                                    "interacted": 0})
        if a.get("model"):
            row["model"] = a["model"]
        if a.get("effort"):
            row["effort"] = a["effort"]
        if a.get("thread_id"):
            row["thread_id"] = a["thread_id"]
        k = a.get("kind") or ""
        if k == "started" and not row["started"]:
            row["started"] = a["ts"]
        elif k == "completed":
            row["completed"] += 1
        elif k == "interrupted":
            row["interrupted"] += 1
        elif k == "interacted":
            row["interacted"] += 1
    out += [f"Agents observed: **{len(seen)}** "
            f"(activity records: {len(store['agents'])})", "",
            "| agent path | thread id | model | effort | first seen | interacted | completed | interrupted |",
            "|---|---|---|---|---|---|---|---|"]
    for key in sorted(seen):
        r = seen[key]
        out.append(f"| `{key}` | {(r['thread_id'] or '-')[:13]} | {r['model'] or '-'} "
                   f"| {r['effort'] or '-'} | {(r['started'] or '-')[:16]} "
                   f"| {r['interacted']} | {r['completed']} | {r['interrupted']} |")
    out.append("")
    w("subagent_roster.md", "\n".join(out) + "\n")

    # ---- mcp calls
    out = ["# MCP tool calls (recovered from typed items)", "",
           "Arguments and results of connector calls, which the response_item stream "
           "does not carry in readable form. This is where PR creation bodies and "
           "GitHub reads actually live.", ""]
    for m in store["mcp"]:
        out += [f"## {(m['ts'] or '')[:19]} · {m['server']}·{m['tool']} · {m['status']}",
                "```", m["args"], "```",
                "result:", "```", m["result"], "```", ""]
    w("mcp_calls.md", "\n".join(out) + "\n")

    # ---- commands with exit codes
    out = ["# Command executions (recovered from typed items)", "",
           "Shell invocations with exit codes and aggregated output. The response_item "
           "stream has the argv but not the exit status.", ""]
    fails = [c for c in store["commands"] if c["exit"] not in (0, None)]
    out += [f"Total: **{len(store['commands'])}** · non-zero exit: **{len(fails)}**", ""]
    for c in store["commands"]:
        flag = "FAIL" if c["exit"] not in (0, None) else "ok"
        out += [f"### {flag} exit={c['exit']} · {(c['ts'] or '')[:19]}",
                "```", c["cmd"], "```"]
        if c["out"]:
            out += ["output:", "```", c["out"], "```"]
    w("commands.md", "\n".join(out) + "\n")

    # ---- extensions / compaction markers
    if store["extensions"] or store["markers"]:
        out = ["# Other typed items", "",
               f"Extension items: {len(store['extensions'])} · "
               f"ContextCompaction markers: {len(store['markers'])}", ""]
        for e in store["extensions"]:
            out.append(f"- {(e['ts'] or '')[:19]} {e['kind']} {e['action']} "
                       f"`{(e['query'] or '')[:120]}`")
        for m in store["markers"]:
            out.append(f"- compaction marker {(m['ts'] or '')[:19]} {m['id']}")
        w("other_items.md", "\n".join(out) + "\n")
