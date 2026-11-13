#!/usr/bin/env python3
"""Draw the recall reference frame: a deterministic stratified sample of
6-turn operator windows, emitted as a BLANK labeller sheet + a withheld key.

WHAT THIS IS. `recall_instrument_design.md` specifies the reference inventory
for ask-level recall. This script builds the frame only. It does NOT measure
recall, does NOT label, and does NOT open the register's ask table.

FRAME. Unit = 6 consecutive eligible operator-authored turns inside one
session, ordered by that session's own clock. Trailing partial windows are
dropped, so every window is exactly 6 turns. Three disjoint strata (channels):
harness (jcode + codex occurrence JSONL), imessage (chat.db outbound), kcode
(~/.kcode/sessions). The `phone` channel is a subset of iMessage and is
excluded by construction so no ask can enter the frame twice.

ALLOCATION. n = 60 windows, proportional to the population of full windows in
each channel, floor 8 per channel, largest-remainder rounding.

SEED. 20261121 (the design's seed; distinct from 20261112/13/14).

READ-ONLY. chat.db is opened as URI mode=ro with PRAGMA query_only=1. Nothing is
copied and nothing is written outside this evidence directory.

HARD RULE. No register ask id may appear anywhere in the emitted sheet. This
script never reads reg_asks; `matched_register_ask_ids` is emitted empty.

OUTPUTS
  recall_reference_sheet.json  blank sheet: window text only
  recall_reference_key.json    idx -> channel/session/ordinal/ts metadata, withheld
"""
from __future__ import annotations

import glob
import json
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
CHATDB = "/Users/kooshapari/Library/Messages/chat.db"
JCODE = f"{BASE}/jcode-occurrences.jsonl"
CODEX = f"{BASE}/codex_user_turns_v2.jsonl"
KCODE = "/Users/kooshapari/.kcode/sessions"

SHEET = os.path.join(HERE, "recall_reference_sheet.json")
KEY = os.path.join(HERE, "recall_reference_key.json")

SEED = 20261121
N_TARGET = 60
FLOOR = 8
WINDOW = 6
TEXT_CHARS = 1200
CHANNELS = ("harness", "imessage", "kcode")

sys.path.insert(0, BASE)
from recount_imessage_kcode import norm  # noqa: E402
from union_channels import keep  # noqa: E402  (same eligibility gate)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def blocks_to_text(c) -> str:
    if isinstance(c, str):
        return c
    if not isinstance(c, list):
        return ""
    parts = []
    for b in c:
        if isinstance(b, str):
            parts.append(b)
        elif isinstance(b, dict):
            if b.get("type") in (None, "text") and isinstance(b.get("text"), str):
                parts.append(b["text"])
    return "\n".join(parts)


# ---------------------------------------------------------------- harness
def harness_turns() -> dict[str, list[dict]]:
    by_session: dict[str, list[dict]] = defaultdict(list)
    for path, src in ((JCODE, "jcode"), (CODEX, "codex")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("is_injected") is True:
                    continue
                if r.get("is_human") is False:
                    continue
                n = norm(r.get("text") or "")
                if not keep(n):
                    continue
                sid = r.get("session_id") or ""
                if not sid:
                    continue
                by_session[sid].append({
                    "ts": r.get("ts") or "",
                    "order": _int(r.get("msg_index")),
                    "text": n,
                    "source": src,
                })
    for sid, turns in by_session.items():
        turns.sort(key=lambda t: (t["ts"], t["order"]))
    return by_session


def _int(v) -> int:
    try:
        return int(v)
    except Exception:
        return 0


# ---------------------------------------------------------------- imessage
def imessage_turns() -> dict[str, list[dict]]:
    con = sqlite3.connect(f"file:{CHATDB}?mode=ro", uri=True, timeout=30)
    try:
        con.execute("PRAGMA query_only=1")
        rows = con.execute("""
            SELECT cj.chat_id, m.ROWID, m.date, m.text
            FROM message m
            JOIN chat_message_join cj ON cj.message_id = m.ROWID
            WHERE m.is_from_me = 1
              AND m.text IS NOT NULL AND length(trim(m.text)) > 0
            ORDER BY m.ROWID
        """).fetchall()
    finally:
        con.close()
    by_session: dict[str, list[dict]] = defaultdict(list)
    for chat_id, rowid, date, text in rows:
        n = norm(text or "")
        if not keep(n):
            continue
        by_session[f"imessage:{chat_id}"].append({
            "ts": str(date or ""),
            "order": _int(rowid),
            "text": n,
            "source": "chat.db",
        })
    for turns in by_session.values():
        turns.sort(key=lambda t: t["order"])
    return by_session


# ---------------------------------------------------------------- kcode
def kcode_turns() -> dict[str, list[dict]]:
    by_session: dict[str, list[dict]] = {}
    for path in sorted(glob.glob(os.path.join(KCODE, "*.json"))):
        try:
            d = json.load(open(path, encoding="utf-8", errors="replace"))
        except Exception:
            continue
        msgs = d.get("messages") or d.get("history") or []
        if not isinstance(msgs, list):
            continue
        sid = d.get("id") or f"kcode:{os.path.basename(path)}"
        turns = []
        for i, m in enumerate(msgs):
            if not isinstance(m, dict):
                continue
            if (m.get("display_role") or m.get("role")) != "user":
                continue
            if m.get("display_role") == "system" or m.get("is_injected") is True:
                continue
            n = norm(blocks_to_text(m.get("content") or m.get("text") or ""))
            if not keep(n):
                continue
            turns.append({"ts": str(m.get("timestamp") or ""), "order": i,
                          "text": n, "source": "kcode"})
        if turns:
            by_session[sid] = turns
    return by_session


# ---------------------------------------------------------------- windows
def windows(by_session: dict[str, list[dict]], channel: str) -> list[dict]:
    """Full 6-turn windows, ordered deterministically by (session, ordinal)."""
    out = []
    for sid in sorted(by_session):
        turns = by_session[sid]
        for start in range(0, len(turns) - WINDOW + 1, WINDOW):
            chunk = turns[start:start + WINDOW]
            out.append({
                "channel": channel,
                "session_id": sid,
                "start_line": start + 1,
                "end_line": start + WINDOW,
                "n_turns": WINDOW,
                "first_ts": chunk[0]["ts"],
                "last_ts": chunk[-1]["ts"],
                "sources": sorted({c["source"] for c in chunk}),
                "text": "\n\n".join(
                    f"--- turn {start + k + 1} ---\n{c['text']}"
                    for k, c in enumerate(chunk)),
            })
    out.sort(key=lambda w: (w["session_id"], w["start_line"]))
    return out


def allocate(pops: dict[str, int], n: int, floor: int) -> dict[str, int]:
    """Proportional + floor, largest-remainder, capped by population."""
    total = sum(pops.values())
    n = min(n, total)
    alloc = {c: 0 for c in CHANNELS}
    for c in CHANNELS:
        alloc[c] = min(max(min(floor, pops[c]), int(n * pops[c] / total)), pops[c])
    while sum(alloc.values()) < n:
        room = [c for c in CHANNELS if alloc[c] < pops[c]]
        if not room:
            break
        # largest fractional remainder first, tie-break by channel order
        c = max(room, key=lambda k: (n * pops[k] / total - alloc[k],
                                     -CHANNELS.index(k)))
        alloc[c] += 1
    while sum(alloc.values()) > n:
        c = max((k for k in CHANNELS if alloc[k] > 0),
                key=lambda k: (alloc[k], -CHANNELS.index(k)))
        alloc[c] -= 1
    return alloc


# ---------------------------------------------------------------- main
def blocked(reason: str) -> int:
    body = {
        "generated_at_utc": _now(), "seed": SEED, "stratify_by": "channel",
        "n": 0, "population": {}, "allocation": {}, "items": [],
        "blocked_reason": reason,
    }
    with open(SHEET, "w") as fh:
        json.dump(body, fh, indent=1)
        fh.write("\n")
    print(f"BLOCKED: {reason}")
    print(f"wrote {SHEET} (n=0)")
    return 3


def main() -> int:
    t0 = time.time()

    if not os.path.isfile(CHATDB):
        return blocked(f"chat.db not found at {CHATDB}")
    try:
        probe = sqlite3.connect(f"file:{CHATDB}?mode=ro", uri=True, timeout=10)
        probe.execute("PRAGMA query_only=1")
        probe.execute("select count(*) from message")
        probe.close()
    except Exception as exc:  # noqa: BLE001
        return blocked(f"chat.db unreadable read-only ({CHATDB}): {exc}")

    builders = {"harness": harness_turns, "imessage": imessage_turns,
                "kcode": kcode_turns}
    per_channel: dict[str, list[dict]] = {}
    pops: dict[str, int] = {}
    for c in CHANNELS:
        try:
            per_channel[c] = windows(builders[c](), c)
        except Exception as exc:  # noqa: BLE001
            return blocked(f"channel {c} could not be built: {exc}")
        pops[c] = len(per_channel[c])
        print(f"  {c:9s} full windows: {pops[c]:6d}  [{time.time()-t0:.0f}s]")

    alloc = allocate(pops, N_TARGET, FLOOR)
    n = sum(alloc.values())
    print(f"  allocation: {alloc}  n={n}")

    rng = random.Random(SEED)
    chosen: list[dict] = []
    for c in CHANNELS:
        k = alloc[c]
        if k:
            chosen.extend(rng.sample(per_channel[c], k))

    items, key_items = [], []
    for idx, w in enumerate(chosen):
        text = w["text"][:TEXT_CHARS]
        items.append({
            "idx": idx,
            "channel": w["channel"],
            "session_id": w["session_id"],
            "window_start_line": w["start_line"],
            "window_end_line": w["end_line"],
            "text": text,
            "reference_asks": [],
            "matched_register_ask_ids": [],
        })
        key_items.append({
            "idx": idx,
            "channel": w["channel"],
            "session_id": w["session_id"],
            "window_start_line": w["start_line"],
            "window_end_line": w["end_line"],
            "n_turns": w["n_turns"],
            "first_ts": w["first_ts"],
            "last_ts": w["last_ts"],
            "sources": w["sources"],
            "text_chars": len(w["text"]),
            "truncated": len(w["text"]) > TEXT_CHARS,
        })

    key_body = {
        "generated_at_utc": _now(),
        "seed": SEED,
        "stratify_by": "channel",
        "n": n,
        "population": pops,
        "allocation": alloc,
        "withheld_from_labeller": (
            "This file holds channel/session/ordinal/timestamp metadata only, no "
            "transcript text and no register ask id. It is withheld from the "
            "reference labeller so the frame can be reconstructed later without "
            "biasing labelling. The labeller must not open ledger.db, "
            "register.json, or this key while labelling."),
        "items": key_items,
    }
    with open(KEY, "w") as fh:
        json.dump(key_body, fh, indent=1)
        fh.write("\n")

    sheet_body = {
        "generated_at_utc": _now(),
        "seed": SEED,
        "stratify_by": "channel",
        "n": n,
        "population": pops,
        "allocation": alloc,
        "instructions": (
            "For each window record EVERY operator ask you can see as "
            "{\"turn\": <int>, \"quote\": <verbatim>, \"intent\": <one line>} in "
            "reference_asks. An ask is a request, instruction, or directive from "
            "the operator; a question counts, a statement of fact does not. If a "
            "turn is a fragment of an ask completed outside the window, use "
            "intent \"fragment\" and it is excluded from the denominator. "
            "matched_register_ask_ids stays empty: matching is a later step."),
        "items": items,
    }
    with open(SHEET, "w") as fh:
        json.dump(sheet_body, fh, indent=1)
        fh.write("\n")

    print(f"wrote {KEY}")
    print(f"wrote {SHEET}")
    print(f"[{time.time()-t0:.0f}s] n={n} from populations {pops}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
