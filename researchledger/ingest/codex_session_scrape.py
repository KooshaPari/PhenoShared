#!/usr/bin/env python3
"""
codex_session_scrape.py — full-fidelity scrape of a Codex thread into a resumable pack.

Codex compaction keeps only verbatim user + assistant messages; tool output,
subagent reports, exec commands, typed items, and world state leave the model's
context forever. The rollout JSONL still has all of it. This rebuilds a whole
thread from every segment (resumed forks, compressed, overlapping ordinals),
dedupes by payload hash, and writes reports plus a normalized event stream.
See RESUME_PACK.md (authored per thread) for the narrative index, and
codex_session_report.py / codex_session_items.py for the emitters.

Read-only over ~/.codex. Writes only under --out-dir.

Usage:
  codex_session_scrape.py --thread-id <id> [--out-dir DIR] [--max-text N]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_session_report import write_reports  # noqa: E402
from codex_session_items import accumulate, classify_item, new_store, write_item_reports  # noqa: E402

SESSIONS_DIR = Path.home() / ".codex" / "sessions"
OUT_ROOT = Path.home() / "Exports" / "analysis" / "session-resume"

RE_URL = re.compile(r"https?://[^\s\"'`)\]]+")
RE_PR = re.compile(r"(?:PR|pull request)\s*#?(\d+)", re.IGNORECASE)
RE_BRANCH = re.compile(r"\b(?:feat|fix|chore|docs|test|refactor|audit|revert)/[A-Za-z0-9._/-]+")
RE_SHELL = re.compile(r"exec_command\(\{\s*cmd:\s*\"((?:[^\"\\]|\\.)*)\"", re.DOTALL)
RE_ABS_PATH = re.compile(r"(?:/Users/[A-Za-z0-9._-]+|~/)[A-Za-z0-9._/@+-]*")


# --------------------------------------------------------------------------- io


def open_lines(path: Path) -> Iterator[str]:
    """Yield decoded lines from a plain, gzip, or zstd JSONL file."""
    name = path.name
    if name.endswith(".zst"):
        proc = subprocess.run(["zstd", "-dc", str(path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"zstd failed for {path}: {proc.stderr[:200]!r}")
        yield from proc.stdout.decode("utf-8", "replace").splitlines()
        return
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            yield from fh
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        yield from fh


def find_segments(thread_id: str) -> list[Path]:
    """All rollout files for a thread id, oldest first, no double-compressed copies."""
    hits: list[Path] = []
    for p in SESSIONS_DIR.rglob(f"rollout-*{thread_id}*.jsonl*"):
        if p.name.endswith(".zst.zst"):
            continue
        if p.name.endswith(".zst") and Path(str(p)[:-4]).exists():
            continue  # prefer the decompressed sibling
        hits.append(p)
    return sorted(hits, key=lambda p: p.name)


def record_hash(rec: dict) -> str:
    blob = json.dumps({"t": rec.get("type"), "p": rec.get("payload")},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8", "replace")).hexdigest()


def text_of_content(content) -> str:
    """Concatenate readable text blocks; annotate encrypted/image blocks."""
    if not isinstance(content, list):
        return ""
    out: list[str] = []
    for c in content:
        if not isinstance(c, dict):
            continue
        t = c.get("type", "")
        if t in ("input_text", "output_text", "text"):
            txt = c.get("text") or ""
            if txt:
                out.append(txt)
        elif t == "reasoning_text":
            txt = c.get("text") or ""
            if txt:
                out.append(f"[reasoning] {txt}")
        elif t == "encrypted_content":
            out.append(f"[encrypted {len(c.get('encrypted_content') or '')} chars]")
        elif t == "input_image":
            out.append("[image]")
    return "\n".join(out).strip()


def user_kind(text: str) -> str:
    s = text.lstrip()
    if s.startswith("# AGENTS.md instructions"):
        return "agents_md"
    if s.startswith("<environment_context>"):
        return "environment"
    if s.startswith("<INSTRUCTIONS>"):
        return "instructions"
    if s.startswith("<send_user_message_question_reply>"):
        return "question_reply"
    return "prompt"


def mine(text: str) -> dict:
    """Extract artifact-ish tokens from free text."""
    if not text:
        return {}
    urls = sorted(set(RE_URL.findall(text)))
    prs = sorted(set(RE_PR.findall(text)))
    branches = sorted(set(RE_BRANCH.findall(text)))
    paths = sorted({p.rstrip(".,)`:;") for p in RE_ABS_PATH.findall(text) if len(p) > 8})
    return {"urls": urls[:40], "prs": prs[:20], "branches": branches[:20], "paths": paths[:60]}


# ------------------------------------------------------------------- classify


def classify(rec: dict) -> dict | None:
    """Normalize one rollout record into a flat event, or None to skip noise."""
    t = rec.get("type")
    p = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
    base = {"ts": rec.get("timestamp"), "ord": rec.get("ordinal"), "kind": None}

    if t == "session_meta":
        return {**base, "kind": "session_meta", "data": p}

    if t == "turn_context":
        return {**base, "kind": "turn_context", "data": {
            k: p.get(k) for k in ("turn_id", "root_turn_id", "cwd", "model", "effort",
                                  "approval_policy", "sandbox_policy", "summary")}}

    if t == "world_state":
        state = p.get("state")
        return {**base, "kind": "world_state", "full": p.get("full"),
                "keys": sorted(state.keys()) if isinstance(state, dict) else None,
                "data": state}

    if t == "compacted":
        rc = p.get("retained_context")
        users = rc.get("user_messages", []) if isinstance(rc, dict) else []
        asst = rc.get("assistant_messages", []) if isinstance(rc, dict) else []
        return {**base, "kind": "compaction",
                "window": p.get("window_number"), "window_id": p.get("window_id"),
                "retained_user_count": len(users),
                "retained_assistant_count": len(asst),
                "replacement_items": len(p.get("replacement_history") or []),
                "retained_context": rc}

    if t == "token_usage_record":
        return {**base, "kind": "token_usage", "data": p}

    if t == "event_msg":
        et = p.get("type")
        if et in ("task_started", "task_complete", "turn_aborted", "thread_settings_applied"):
            return {**base, "kind": "turn_event", "event": et, "data": p}
        if et == "token_count":
            return {**base, "kind": "token_count", "data": p}
        if et == "item_completed":
            return classify_item(base["ts"], base["ord"], p)
        return None

    if t != "response_item":
        return None

    pt = p.get("type")
    if pt == "message":
        return {**base, "kind": "message", "role": p.get("role", ""),
                "text": text_of_content(p.get("content"))}
    if pt == "agent_message":
        text = text_of_content(p.get("content"))
        m = re.search(r"Message Type:\s*([A-Z_]+)", text)
        s = re.search(r"Sender:\s*(\S+)", text)
        body = text.split("Payload:", 1)[1].strip() if "Payload:" in text else text
        return {**base, "kind": "agent_message", "mtype": m.group(1) if m else "",
                "sender": s.group(1) if s else "", "author": p.get("author"),
                "recipient": p.get("recipient"), "text": text, "body": body}
    if pt in ("function_call", "custom_tool_call"):
        raw = p.get("arguments", p.get("input", ""))
        args = None
        if isinstance(raw, str):
            try:
                args = json.loads(raw)
            except Exception:
                args = None
        return {**base, "kind": "tool_call", "name": p.get("name", ""),
                "args": args if args is not None else raw,
                "cmds": RE_SHELL.findall(raw) if isinstance(raw, str) else []}
    if pt in ("function_call_output", "custom_tool_call_output"):
        out = p.get("output", "")
        if not isinstance(out, str):
            out = json.dumps(out, ensure_ascii=False)
        return {**base, "kind": "tool_output", "call_id": p.get("call_id"), "text": out}
    if pt == "reasoning":
        parts = [s["text"] if isinstance(s, dict) else s
                 for s in (p.get("summary") or [])]
        parts = [x for x in parts if isinstance(x, str) and x]
        return {**base, "kind": "reasoning", "text": "\n".join(parts)}
    if pt == "configuration_update":
        return {**base, "kind": "config_update", "data": p}
    return None


def parse_cockpit(text: str) -> dict:
    """Pull STATE / PROGRESS / BLOCKERS / NEXT out of an agent report."""
    if not text:
        return {}
    out: dict[str, list[str]] = defaultdict(list)
    cur = None
    for line in text.splitlines():
        s = line.strip()
        head = s.split(":", 1)[0] if ":" in s else ""
        if head in ("SESSION", "STATE", "PROGRESS", "BLOCKERS", "NEXT"):
            cur = head
            rest = s.split(":", 1)[1].strip()
            if rest:
                out[cur].append(rest)
            continue
        if cur and s and not set(s) <= set("="):
            out[cur].append(s)
    return {k: v for k, v in out.items() if v}


# ------------------------------------------------------------------ streaming


def _new_turn(seq: int, e: dict) -> dict:
    d = e["data"]
    return {
        "seq": seq, "turn_id": d.get("turn_id"), "started": e["ts"],
        "started_at": d.get("started_at"),
        "model_context_window": d.get("model_context_window"),
        "trigger": ((d.get("turn_attribution") or {}).get("turn_trigger")),
        "prompts": [], "assistant": [], "agent_msgs": [], "finals": [],
        "tools": Counter(), "cmds": [], "files": set(), "urls": set(),
        "prs": set(), "branches": set(), "cockpit": {}, "model": None,
        "compactions": 0, "world_states": 0, "tokens": {},
    }


def scrape(thread_id: str, out_dir: Path, cap: int) -> dict:
    segments = find_segments(thread_id)
    if not segments:
        raise SystemExit(f"no rollout segments found for thread {thread_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    seg_stats: list[dict] = []
    counts: Counter = Counter()
    dupes = 0

    turns: list[dict] = []
    cur: dict | None = None
    turn_seq = -1
    prompts: list[dict] = []
    asst_msgs: list[dict] = []
    agent_msgs: list[dict] = []
    compactions: list[dict] = []
    user_kinds: Counter = Counter()
    models: Counter = Counter()
    sessions_meta: list[dict] = []
    latest_world: dict | None = None
    thread_usage: dict = {}
    ev_written = 0
    items = new_store()

    with gzip.open(out_dir / "events.jsonl.gz", "wt", encoding="utf-8") as ev:
        for seg in segments:
            n_rec = n_dup = 0
            for line in open_lines(seg):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    counts["bad_json"] += 1
                    continue
                h = record_hash(rec)
                if h in seen:
                    n_dup += 1
                    dupes += 1
                    continue
                seen.add(h)
                n_rec += 1

                e = classify(rec)
                if e is None:
                    continue
                counts[e["kind"]] += 1
                k = e["kind"]

                if k == "session_meta":
                    sessions_meta.append(e["data"])
                    cur = None
                elif k == "turn_event":
                    name = e["event"]
                    if name == "task_started":
                        turn_seq += 1
                        cur = _new_turn(turn_seq, e)
                        turns.append(cur)
                    elif name in ("task_complete", "turn_aborted"):
                        if cur is not None:
                            cur["ended"] = e["ts"]
                            cur["duration_ms"] = e["data"].get("duration_ms")
                            cur["ttft_ms"] = e["data"].get("time_to_first_token_ms")
                            cur["aborted"] = name == "turn_aborted"
                            last = e["data"].get("last_agent_message")
                            if last:
                                cur["last_agent_message"] = last
                                cur["cockpit"] = parse_cockpit(last) or cur["cockpit"]
                            cur = None
                    elif name == "thread_settings_applied":
                        m = (e["data"].get("thread_settings") or {}).get("model")
                        if m:
                            models[m] += 1
                            e["model"] = m
                elif k == "turn_context":
                    m = e["data"].get("model")
                    if m:
                        models[m] += 1
                        if cur is not None and not cur.get("model"):
                            cur["model"] = m
                elif k == "world_state":
                    latest_world = e
                    if cur is not None:
                        cur["world_states"] += 1
                elif k == "item":
                    accumulate(items, e)
                    if cur is not None:
                        if e["item_type"] == "CommandExecution":
                            cmd = e["item"].get("command") or []
                            if isinstance(cmd, list) and cmd:
                                cur["cmds"].append(str(cmd[-1])[:400])
                        for ps in (e["item"].get("item_paths") or []):
                            cur["files"].add(str(ps))
                elif k == "compaction":
                    compactions.append({**e, "turn_seq": turn_seq})
                    if cur is not None:
                        cur["compactions"] += 1
                elif k == "message":
                    txt = e.get("text") or ""
                    role = e.get("role")
                    if role == "user" and txt:
                        item = {"seq": turn_seq, "ts": e["ts"],
                                "kind": user_kind(txt), "text": txt}
                        user_kinds[item["kind"]] += 1
                        prompts.append(item)
                        if cur is not None:
                            cur["prompts"].append(item)
                    elif role == "assistant" and txt:
                        item = {"seq": turn_seq, "ts": e["ts"], "text": txt}
                        asst_msgs.append(item)
                        if cur is not None:
                            cur["assistant"].append(item)
                            cp = parse_cockpit(txt)
                            if cp.get("STATE") or cp.get("NEXT"):
                                cur["cockpit"] = cp
                    if txt and cur is not None:
                        mi = mine(txt)
                        cur["files"].update(mi.get("paths", []))
                        cur["urls"].update(mi.get("urls", []))
                        cur["prs"].update(mi.get("prs", []))
                        cur["branches"].update(mi.get("branches", []))
                elif k == "agent_message":
                    item = {"seq": turn_seq, "ts": e["ts"], "mtype": e.get("mtype"),
                            "sender": e.get("sender"), "author": e.get("author"),
                            "body": e.get("body") or e.get("text") or ""}
                    agent_msgs.append(item)
                    if cur is not None:
                        cur["agent_msgs"].append(item)
                        if item["mtype"] == "FINAL_ANSWER":
                            cur["finals"].append(item)
                elif k == "tool_call":
                    item = {"seq": turn_seq, "ts": e["ts"], "name": e.get("name") or "?",
                            "cmds": e.get("cmds") or []}
                    if cur is not None:
                        cur["tools"][item["name"]] += 1
                        for c in item["cmds"]:
                            cur["cmds"].append(c)
                            mi = mine(c)
                            cur["files"].update(mi.get("paths", []))
                elif k == "token_usage":
                    d = e["data"] or {}
                    tt = d.get("thread_token_usage") or {}
                    if tt:
                        thread_usage = tt
                    tu = d.get("turn_token_usage") or d.get("usage") or {}
                    if cur is not None and tu:
                        cur["tokens"] = tu

                ev.write(json.dumps({**e, "seg": seg.name, "turn": turn_seq},
                                    ensure_ascii=False) + "\n")
                ev_written += 1
            seg_stats.append({"file": str(seg), "records": n_rec, "duplicates": n_dup})

    for t in turns:
        t["files"] = sorted(t["files"])
        t["urls"] = sorted(t["urls"])
        t["prs"] = sorted(t["prs"])
        t["branches"] = sorted(t["branches"])
        t["tools"] = dict(t["tools"])
        t["n_prompts"] = len([p for p in t["prompts"] if p["kind"] == "prompt"])
        t["n_assistant"] = len(t["assistant"])
        t["n_agent_msgs"] = len(t["agent_msgs"])
        t["n_finals"] = len(t["finals"])
        t["cmds"] = t["cmds"][:80]
        t["prompts"] = [{"kind": p["kind"], "ts": p["ts"], "text": p["text"]}
                        for p in t["prompts"]]
        t["assistant"] = [{"ts": a["ts"], "text": a["text"]} for a in t["assistant"]]
        t["agent_msgs"] = [{"ts": a["ts"], "mtype": a["mtype"], "sender": a["sender"]}
                           for a in t["agent_msgs"]]
        t["finals"] = [{"ts": a["ts"], "sender": a["sender"], "body": a["body"]}
                       for a in t["finals"]]

    stats = {
        "thread_id": thread_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "segments": seg_stats,
        "records_kept": sum(s["records"] for s in seg_stats),
        "records_duplicate": dupes,
        "events_written": ev_written,
        "records_skipped": sum(s["records"] for s in seg_stats) - ev_written,
        "event_kinds": dict(counts),
        "turns": len(turns),
        "user_message_kinds": dict(user_kinds),
        "real_prompts": user_kinds.get("prompt", 0),
        "assistant_messages": len(asst_msgs),
        "agent_messages": len(agent_msgs),
        "agent_final_answers": sum(1 for a in agent_msgs if a["mtype"] == "FINAL_ANSWER"),
        "compactions": len(compactions),
        "tool_calls": int(counts.get("tool_call", 0)),
        "models": dict(models),
        "thread_token_usage": thread_usage,
        "first_ts": min((p["ts"] for p in prompts if p["ts"]), default=None),
        "last_ts": max((p["ts"] for p in prompts if p["ts"]), default=None),
        "turns_aborted": sum(1 for t in turns if t.get("aborted")),
        "typed_items": items["counts"],
        "subagents_observed": len({a.get("path") for a in items["agents"] if a.get("path")}),
        "commands_with_exit": len(items["commands"]),
        "mcp_calls": len(items["mcp"]),
    }

    write_reports(out_dir, stats, turns, prompts, asst_msgs, agent_msgs,
                  compactions, sessions_meta, latest_world, cap)
    write_item_reports(
        lambda name, body: (out_dir / name).write_text(body, encoding="utf-8"), items)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Full-fidelity Codex thread scrape.")
    ap.add_argument("--thread-id", required=True)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--max-text", type=int, default=0,
                    help="0 = full text in markdown reports (default).")
    args = ap.parse_args()

    out = args.out_dir or (OUT_ROOT / args.thread_id)
    stats = scrape(args.thread_id, out, args.max_text)
    print(json.dumps({
        "out_dir": str(out),
        "segments": len(stats["segments"]),
        "records_kept": stats["records_kept"],
        "duplicates": stats["records_duplicate"],
        "turns": stats["turns"],
        "real_prompts": stats["real_prompts"],
        "assistant_messages": stats["assistant_messages"],
        "subagent_reports": stats["agent_messages"],
        "final_answers": stats["agent_final_answers"],
        "compactions": stats["compactions"],
        "tool_calls": stats["tool_calls"],
        "models": stats["models"],
        "thread_tokens": stats["thread_token_usage"].get("total_tokens"),
        "subagents_observed": stats["subagents_observed"],
        "typed_items": stats["typed_items"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
