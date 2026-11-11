#!/usr/bin/env python3
"""Acceptance test for the cockpit artifact.

This does NOT inspect the artifact for plausible-looking numbers. It performs the
acceptance workflow end to end:

    frozen source JSON  ->  independent re-derivation  ->  compare to the numbers
                                                            RENDERED IN THE HTML

The artifact is treated as an opaque delivered product: its numbers are scraped out
of the markup and checked against a from-scratch derivation.

Exit 0 = every rendered count agrees with the source.
Exit 1 = at least one disagreement (printed).

Usage: python3 verify-artifact.py [--artifact PATH] [--frozen PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys

DEFAULT_ARTIFACT = "/Users/kooshapari/Exports/analysis/session-20261028-cockpit.html"
DEFAULT_FROZEN = "/Users/kooshapari/.jcode/scratch/cockpit-NBTp5M/session.frozen.json"
EXPECTED_SHA = "e41f3f7340ea7ece3fc033bbdeef3034ff2acda653c8664cd4b34dd31a1f2535"

MARKERS = [
    "You have", "incomplete todo", "[auto]", "[Scheduled", "Scheduled task",
    "<system-reminder>", "Swarm await", "Background task stalled", "DM from",
    "File activity", "Tool output missing",
]


def txt(m) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def derive(frozen_path: str) -> dict:
    """Re-derive every count from the frozen source, from scratch."""
    import hashlib

    raw = open(frozen_path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw)
    msgs = doc["messages"]

    user = [m for m in msgs if m.get("role") == "user"]
    tool = [m for m in user if "tool_duration_ms" in m]
    relayed = [m for m in user if "tool_duration_ms" not in m and "display_role" in m]
    cand = [m for m in user if "tool_duration_ms" not in m and "display_role" not in m]

    by_marker: dict[str, int] = {}
    marker_ids = set()
    for m in cand:
        t = txt(m)
        for mk in MARKERS:
            if mk in t:
                by_marker[mk] = by_marker.get(mk, 0) + 1
                marker_ids.add(id(m))
                break

    shape = []
    for m in cand:
        if id(m) in marker_ids:
            continue
        c = m.get("content")
        if isinstance(c, list) and c and all(
            isinstance(x, dict) and x.get("type") == "tool_result" for x in c
        ):
            shape.append(m)
    shape_ids = {id(m) for m in shape}

    rest = [m for m in cand if id(m) not in marker_ids and id(m) not in shape_ids]
    acks = [m for m in rest if len(txt(m).strip()) < 20]
    subs = [m for m in rest if len(txt(m).strip()) >= 20]

    per_day: dict[str, int] = {}
    for m in subs:
        d = m["timestamp"][:10]
        per_day[d] = per_day.get(d, 0) + 1

    return {
        "sha256": sha,
        "bytes": len(raw),
        "messages": len(msgs),
        "user": len(user),
        "tool": len(tool),
        "relayed": len(relayed),
        "candidates": len(cand),
        "partition_gap": len(user) - (len(tool) + len(relayed) + len(cand)),
        "assistant": len([m for m in msgs if m.get("role") == "assistant"]),
        "relayed_system": sum(1 for m in relayed if m.get("display_role") == "system"),
        "relayed_background": sum(
            1 for m in relayed if m.get("display_role") == "background_task"
        ),
        "marker_total": len(marker_ids),
        "by_marker": by_marker,
        "shape_total": len(shape),
        "keystrokes": len(rest),
        "acks": len(acks),
        "subs": len(subs),
        "per_day": per_day,
        "per_day_sum": sum(per_day.values()),
    }


def scrape(html: str) -> dict:
    """Pull the rendered count cells out of the HTML table."""
    out: dict[str, int | None] = {}
    # rows look like: <tr><td>LABEL</td><td class="num">VALUE</td>...
    # VALUE may be wrapped in <b>.
    for label, key in [
        ("Total records in transcript", "messages"),
        ("user-role records", "user"),
        ("Tool results", "tool"),
        ("Relayed / background", "relayed"),
        ("Operator-candidate", "candidates"),
        ("Machine text, no key", "marker_total"),
        ("Machine, tool-result shape", "shape_total"),
        ("Operator keystrokes", "keystrokes"),
        ("Short acks", "acks"),
        ("Substantive prompts", "subs"),
    ]:
        # Keep the window inside one row (rows are newline-separated) so a label that
        # fails to find its own value cannot silently borrow the NEXT row's number.
        pat = (
            re.escape(label)
            + r"[^\n]{0,300}?<td class=\"num\">\s*(?:<b>)?\s*([\d,]+)\s*(?:</b>)?\s*</td>"
        )
        m = re.search(pat, html, re.S)
        out[key] = int(m.group(1).replace(",", "")) if m else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=DEFAULT_ARTIFACT)
    ap.add_argument("--frozen", default=DEFAULT_FROZEN)
    a = ap.parse_args()

    d = derive(a.frozen)
    html = open(a.artifact, encoding="utf-8", errors="replace").read()
    s = scrape(html)

    checks: list[tuple[str, object, object]] = [
        ("frozen sha256 matches expected", d["sha256"], EXPECTED_SHA),
        ("partition closes (gap == 0)", d["partition_gap"], 0),
        ("rendered total records", s["messages"], d["messages"]),
        ("rendered user-role", s["user"], d["user"]),
        ("rendered tool results", s["tool"], d["tool"]),
        ("rendered relayed", s["relayed"], d["relayed"]),
        ("rendered candidates", s["candidates"], d["candidates"]),
        ("rendered marker total", s["marker_total"], d["marker_total"]),
        ("rendered tool-result shape", s["shape_total"], d["shape_total"]),
        ("rendered keystrokes", s["keystrokes"], d["keystrokes"]),
        ("rendered short acks", s["acks"], d["acks"]),
        ("rendered substantive", s["subs"], d["subs"]),
        ("ladder: cand = marker+shape+keys",
         d["candidates"], d["marker_total"] + d["shape_total"] + d["keystrokes"]),
        ("ladder: keys = acks+subs", d["keystrokes"], d["acks"] + d["subs"]),
        ("ladder: user = tool+relayed+cand",
         d["user"], d["tool"] + d["relayed"] + d["candidates"]),
        ("ladder: user+assistant = messages",
         d["messages"], d["user"] + d["assistant"]),
        ("relayed split sums to relayed",
         d["relayed"], d["relayed_system"] + d["relayed_background"]),
        ("per-day sum == substantive", d["per_day_sum"], d["subs"]),
        ("source hash rendered in artifact", "e41f3f73" in html, True),
    ]

    width = max(len(n) for n, _, _ in checks)
    failures = 0
    print(f"artifact : {a.artifact}")
    print(f"frozen   : {a.frozen}")
    print(f"sha256   : {d['sha256']}")
    print(f"bytes    : {d['bytes']:,}   messages: {d['messages']:,}")
    print()
    for name, got, want in checks:
        ok = got == want
        if not ok:
            failures += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  got={got!r}  want={want!r}")

    print()
    print("derived ladder:")
    print(f"  messages {d['messages']:,} = user {d['user']:,} + assistant {d['assistant']:,}")
    print(f"  user {d['user']:,} = tool {d['tool']:,} + relayed {d['relayed']} + candidates {d['candidates']}")
    print(f"  relayed {d['relayed']} = system {d['relayed_system']} + background_task {d['relayed_background']}")
    print(f"  candidates {d['candidates']} = marker {d['marker_total']} + shape {d['shape_total']} + keystrokes {d['keystrokes']}")
    print(f"  keystrokes {d['keystrokes']} = acks {d['acks']} + substantive {d['subs']}")
    print(f"  markers: {d['by_marker']}")
    print(f"  per-day: {dict(sorted(d['per_day'].items()))} (sum {d['per_day_sum']})")
    print()
    if failures:
        print(f"RESULT: FAIL — {failures} check(s) disagree")
        return 1
    print(f"RESULT: PASS — all {len(checks)} checks agree with the frozen source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
