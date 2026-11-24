#!/usr/bin/env python3
"""
codex_session_report.py — markdown/JSON emitters for a scraped Codex thread.

Imported by codex_session_scrape.py. Pure rendering: takes already-extracted
lists and writes the human-readable pack. No filesystem reads.
"""

from __future__ import annotations

import json
from pathlib import Path

TAG = {
    "prompt": "PROMPT",
    "question_reply": "Q-REPLY",
    "agents_md": "INJECTED:agents_md",
    "environment": "INJECTED:env",
    "instructions": "INJECTED:instructions",
}


def short(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n].rstrip() + f" …[+{len(s) - n} chars]"


def write_reports(out_dir: Path, stats: dict, turns: list[dict], prompts: list[dict],
                  asst_msgs: list[dict], agent_msgs: list[dict], compactions: list[dict],
                  sessions_meta: list[dict], latest_world: dict | None, cap: int) -> None:
    def w(name: str, body: str) -> None:
        (out_dir / name).write_text(body, encoding="utf-8")

    w("MANIFEST.json", json.dumps({
        "thread_id": stats["thread_id"],
        "generated_at": stats["generated_at"],
        "source_segments": stats["segments"],
        "session_meta": sessions_meta[:2],
        "counts": {k: stats[k] for k in (
            "records_kept", "records_duplicate", "turns", "assistant_messages",
            "agent_messages", "agent_final_answers", "compactions", "tool_calls")},
        "event_kinds": stats["event_kinds"],
    }, indent=2, ensure_ascii=False)[:200000] + "\n")
    w("stats.json", json.dumps(stats, indent=2, ensure_ascii=False) + "\n")

    with (out_dir / "turns.jsonl").open("w", encoding="utf-8") as fh:
        for t in turns:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    _write_turn_table(w, stats, turns)
    _write_objectives(w, turns)
    _write_prompts(w, prompts, cap)
    _write_assistant(w, asst_msgs, cap)
    _write_agents(w, agent_msgs, cap)
    _write_state(w, turns)
    _write_compactions(w, out_dir, compactions)
    _write_context_loss(w, turns, compactions)
    _write_artifacts(w, turns)

    if latest_world:
        (out_dir / "latest_world_state.json").write_text(
            json.dumps(latest_world, indent=2, ensure_ascii=False)[:400000] + "\n",
            encoding="utf-8")


def _write_turn_table(w, stats: dict, turns: list[dict]) -> None:
    lines = ["# Turn index", "",
             f"Thread `{stats['thread_id']}` — {stats['turns']} turns, "
             f"{stats['records_kept']} records, {stats['compactions']} compactions, "
             f"{stats['real_prompts']} operator prompts.", "",
             "| # | started | dur | model | prompts | asst | finals | tools | cmp | next |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for t in turns:
        nxt = "; ".join((t.get("cockpit") or {}).get("NEXT", [])[:1])
        dur = f"{round((t.get('duration_ms') or 0) / 1000)}s"
        lines.append(
            f"| {t['seq']} | {(t.get('started') or '')[5:16]} | {dur} | {t.get('model') or '-'} "
            f"| {t['n_prompts']} | {t['n_assistant']} | {t['n_finals']} "
            f"| {sum(t['tools'].values())} | {t.get('compactions', 0)} | {short(nxt, 70)} |")
    w("turns.md", "\n".join(lines) + "\n")


def _write_objectives(w, turns: list[dict]) -> None:
    """Operator intent ledger: only real prompts and question replies."""
    out = ["# Operator intent ledger", "",
           "Every real operator message in order. Terse entries (`go`, `.`, `proc`) mean "
           "\"continue the current authorized work\".", ""]
    for t in turns:
        real = [p for p in t["prompts"] if p["kind"] in ("prompt", "question_reply")]
        if not real:
            continue
        out.append(f"## turn {t['seq']} · {t.get('started')} · {t.get('model') or '-'}")
        for p in real:
            body = " ".join(p["text"].split())
            out.append(f"- **{TAG.get(p['kind'], p['kind'])}**: {body}")
        ck = (t.get("cockpit") or {})
        for k in ("BLOCKERS", "NEXT"):
            if ck.get(k):
                out.append(f"- _{k}_: {'; '.join(ck[k][:2])}")
        out.append("")
    w("objectives.md", "\n".join(out) + "\n")


def _write_prompts(w, prompts: list[dict], cap: int) -> None:
    out = ["# User messages (verbatim)", "",
           "`PROMPT` = real operator message. `Q-REPLY` = answer to an agent question.",
           "`INJECTED:*` = harness-injected context, kept for completeness.", ""]
    for p in prompts:
        body = p["text"] if cap == 0 else short(p["text"], cap)
        out += [f"### turn {p['seq']} · {p['ts']} · {TAG.get(p['kind'], p['kind'])}",
                "```", body, "```", ""]
    w("user_prompts.md", "\n".join(out) + "\n")


def _write_assistant(w, asst_msgs: list[dict], cap: int) -> None:
    out = ["# Root assistant messages (verbatim, chronological)", ""]
    for a in asst_msgs:
        body = a["text"] if cap == 0 else short(a["text"], cap)
        out += [f"### turn {a['seq']} · {a['ts']}", "```", body, "```", ""]
    w("assistant_messages.md", "\n".join(out) + "\n")


def _write_agents(w, agent_msgs: list[dict], cap: int) -> None:
    out = ["# Inter-agent reports (verbatim)", "",
           "FINAL_ANSWER = completed subagent report (carries the evidence).",
           "MESSAGE = in-flight or status note.", ""]
    for a in agent_msgs:
        body = a["body"] if cap == 0 else short(a["body"], cap)
        out += [f"### turn {a['seq']} · {a['ts']} · {a['mtype'] or '?'} · {a.get('sender') or '?'}",
                "```", body, "```", ""]
    w("subagent_reports.md", "\n".join(out) + "\n")


def _write_state(w, turns: list[dict]) -> None:
    out = ["# Cockpit state timeline", "",
           "The agent's own STATE / PROGRESS / BLOCKERS / NEXT at the end of each turn.", ""]
    for t in turns:
        cp = t.get("cockpit") or {}
        if not cp:
            continue
        out.append(f"## turn {t['seq']} · {t.get('started') or ''}")
        for k in ("SESSION", "STATE", "PROGRESS", "BLOCKERS", "NEXT"):
            if cp.get(k):
                out.append(f"**{k}:**")
                for ln in cp[k][:12]:
                    out.append(f"- {ln}")
        out.append("")
    w("state_timeline.md", "\n".join(out) + "\n")


def _write_compactions(w, out_dir: Path, compactions: list[dict]) -> None:
    out = ["# Compactions (context resets)", "",
           "A compaction keeps only verbatim user + assistant messages. Tool output, "
           "subagent reports, exec commands, and world state are permanently dropped "
           "from the model's context at each window. The rollout retains them; this "
           "pack restores them.", ""]
    cdir = out_dir / "compactions"
    cdir.mkdir(exist_ok=True)
    for c in compactions:
        rc = c.get("retained_context") or {}
        users = rc.get("user_messages", []) if isinstance(rc, dict) else []
        asst = rc.get("assistant_messages", []) if isinstance(rc, dict) else []
        out += [f"## window {c.get('window')} · {c.get('ts')} · turn {c.get('turn_seq')}",
                f"- retained user messages: {len(users)}",
                f"- retained assistant messages: {len(asst)}",
                f"- replacement history items: {c.get('replacement_items')}", ""]
        body = [f"# Compaction window {c.get('window')} — retained context",
                f"ts: {c.get('ts')}  turn: {c.get('turn_seq')}",
                "", "## Retained user messages", ""]
        for u in users:
            body.append(f"- [{u.get('order')}] {u.get('text')}")
        body += ["", "## Retained assistant messages", ""]
        for a in asst:
            body.append(f"- [{a.get('order')}] {short(a.get('text') or '', 400)}")
        (cdir / f"window_{str(c.get('window')).zfill(2)}.md").write_text(
            "\n".join(body) + "\n", encoding="utf-8")
    w("compactions.md", "\n".join(out) + "\n")


def _write_context_loss(w, turns: list[dict], compactions: list[dict]) -> None:
    """Quantify what each compaction dropped, as a span between consecutive resets."""
    if not compactions:
        w("context_loss.md", "# Context loss\n\nNo compactions recorded.\n")
        return
    marks = sorted(((c.get("turn_seq") if c.get("turn_seq") is not None else 0), c) for c in compactions)
    rows = []
    prev = -1
    for seq, c in marks:
        span = [t for t in turns if prev < t["seq"] <= seq]
        rows.append({
            "window": c.get("window"),
            "ts": (c.get("ts") or "")[:16],
            "from_turn": prev + 1,
            "to_turn": seq,
            "turns": len(span),
            "finals": sum(t["n_finals"] for t in span),
            "tools": sum(sum(t["tools"].values()) for t in span),
            "assistant": sum(t["n_assistant"] for t in span),
            "agent_msgs": sum(t["n_agent_msgs"] for t in span),
            "retained_u": c.get("retained_user_count"),
            "retained_a": c.get("retained_assistant_count"),
        })
        prev = seq
    tot = {k: sum(r[k] for r in rows) for k in ("finals", "tools", "agent_msgs")}
    out = ["# Context loss — what each compaction dropped", "",
           "A compaction keeps a fixed handful of user + assistant messages and drops "
           "everything else. Each row counts the material written since the previous "
           "reset, i.e. exactly what left the model's context at that moment.", "",
           "| # | when | turns | retained u/a | finals dropped | tool calls dropped | agent msgs dropped |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        span_lbl = (f"{r['from_turn']}" if r["from_turn"] == r["to_turn"]
                    else f"{r['from_turn']}-{r['to_turn']}")
        out.append(f"| {r['window']} | {r['ts']} | {span_lbl} "
                   f"| {r['retained_u']}/{r['retained_a']} | {r['finals']} | {r['tools']} "
                   f"| {r['agent_msgs']} |")
    out.append(f"| **total** | | | | **{tot['finals']}** | **{tot['tools']}** "
               f"| **{tot['agent_msgs']}** |")
    out += ["", "Restored by this pack: `subagent_reports.md` (all agent messages), "
            "`events.jsonl.gz` (all tool calls and outputs), `state_timeline.md` "
            "(per-turn cockpit state).", ""]
    w("context_loss.md", "\n".join(out) + "\n")


def _write_artifacts(w, turns: list[dict]) -> None:
    files, urls, prs, branches, cmds = set(), set(), set(), set(), []
    for t in turns:
        files.update(t["files"])
        urls.update(t["urls"])
        prs.update(t["prs"])
        branches.update(t["branches"])
        cmds.extend(t["cmds"])
    w("artifacts.json", json.dumps({
        "paths": sorted(files)[:2000],
        "urls": sorted(urls)[:500],
        "prs": sorted(prs)[:100],
        "branches": sorted(branches)[:100],
        "commands_sample": cmds[:400],
        "commands_total": len(cmds),
    }, indent=2, ensure_ascii=False) + "\n")
