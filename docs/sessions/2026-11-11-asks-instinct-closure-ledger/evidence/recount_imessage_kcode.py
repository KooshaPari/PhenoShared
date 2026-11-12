#!/usr/bin/env python3
"""Occurrence-level re-mine of the iMessage and KCode channels.

Both were previously counted as DEDUPED_INPUT (records == distinct), the same
defect that made codex look like 401 records when it was 9,650 occurrences.

iMessage: read-only on chat.db. NO COPY is ever made.
KCode:    ~/.kcode/sessions/*.json, same shape as the jcode store.

Prints aggregates only; never dumps message bodies in bulk.
Writes imessage_kcode_recount.json next to this script.
"""
from __future__ import annotations

import json
import glob
import os
import re
import sqlite3
import sys
from collections import defaultdict

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
CHATDB = "/Users/kooshapari/Library/Messages/chat.db"
KCODE = "/Users/kooshapari/.kcode/sessions"
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")
LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")

WS = re.compile(r"\s+")
FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")
EDGE = " \t\r\n`*_~#>-–—:;,.!?\"'()[]{}<>|/\\"
TOKEN = re.compile(r"[a-z0-9][a-z0-9'_.+/-]*")
NOISE = [re.compile(p) for p in [
    r"swarm await", r"^\[?auto\]?\b", r"<system-reminder>|system[_ ]reminder",
    r"attached image associated with the preceding|\[image",
    r"environment_context>|<current_date>|<env>",
    r"codex_internal_context|\[internal_context",
    r"agents\.md instructions|<instructions>",
    r"swarm completion report required", r"tool timing:|jcode_progress",
    r"^this session is being continued|conversation summary",
    r"<open_and_recently_viewed_files>|opened file:|edited file:"]]
SUBSTANTIVE = 12


def norm(s: str) -> str:
    t = (s or "").strip()
    t = FENCE.sub("", t).lower()
    t = WS.sub(" ", t)
    return t.strip(EDGE)


def toks(n: str) -> frozenset[str]:
    return frozenset(TOKEN.findall(n))


def is_noise(n: str) -> bool:
    return any(p.search(n) for p in NOISE)


def collapse(docs: list[str]) -> dict:
    """exact / prefix-40 / Jaccard-0.8, identical to collapse_intents.py."""
    exact = len(docs)
    pref = len({d[:40] for d in docs})
    buckets: dict[str, list[int]] = defaultdict(list)
    for i, d in enumerate(docs):
        buckets[d[:40]].append(i)
    T = [toks(d) for d in docs]
    p = list(range(len(docs)))

    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            p[rb] = ra

    for mem in buckets.values():
        for i in range(len(mem)):
            a = mem[i]
            if not T[a]:
                continue
            for j in range(i + 1, len(mem)):
                b = mem[j]
                if not T[b]:
                    continue
                inter = len(T[a] & T[b])
                if inter and inter / len(T[a] | T[b]) >= 0.8:
                    union(a, b)
    return {"exact": exact, "prefix40": pref,
            "jaccard80": len({find(i) for i in range(len(docs))})}


def imessage() -> list[str]:
    con = sqlite3.connect(f"file:{CHATDB}?mode=ro", uri=True, timeout=20)
    con.execute("PRAGMA query_only=1")
    rows = con.execute("""
        select text from message
        where is_from_me=1 and text is not null and length(trim(text))>0
    """).fetchall()
    out = []
    for (t,) in rows:
        n = norm(t)
        if len(n) >= SUBSTANTIVE and not is_noise(n):
            out.append(n)
    return out


def blocks_to_text(c) -> str:
    """KCode stores content as a list of typed blocks, not a string."""
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


def kcode() -> list[str]:
    out = []
    files = sorted(glob.glob(os.path.join(KCODE, "*.json")))
    for path in files:
        try:
            d = json.load(open(path, encoding="utf-8", errors="replace"))
        except Exception:
            continue
        msgs = d.get("messages") or d.get("history") or []
        if not isinstance(msgs, list):
            continue
        for m in msgs:
            if not isinstance(m, dict):
                continue
            if (m.get("display_role") or m.get("role")) != "user":
                continue
            # display_role == 'system' marks harness-injected context, not a human turn
            if m.get("display_role") == "system" or m.get("is_injected") is True:
                continue
            n = norm(blocks_to_text(m.get("content") or m.get("text") or ""))
            if len(n) >= SUBSTANTIVE and not is_noise(n):
                out.append(n)
    return out, len(files)


def main() -> int:
    reg = json.load(open(REGISTER))["records"]
    quotes = {norm(r.get("quote") or "") for r in reg}
    quotes = {q for q in quotes if len(q) >= SUBSTANTIVE}

    # phone channel already in ledger.db
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    phone = {norm(b) for (b,) in con.execute(
        "select body from reg_utterances where role='user'")}
    phone = {x for x in phone if len(x) >= SUBSTANTIVE}

    print("== iMessage (read-only, no copy) ==")
    im = imessage()
    im_d = sorted(set(im))
    print(f"  text-bearing outbound, substantive: {len(im)} occurrences, {len(im_d)} distinct")
    print(f"  collapse: {collapse(im_d)}")
    im_cited = [d for d in im_d if any(q in d for q in quotes)]
    print(f"  cited by a register quote: {len(im_cited)} "
          f"({len(im_cited)/len(im_d)*100:.1f}% of distinct)")

    print("\n== KCode ==")
    kc, nfiles = kcode()
    kc_d = sorted(set(kc))
    print(f"  session files read: {nfiles}")
    print(f"  user substantive: {len(kc)} occurrences, {len(kc_d)} distinct")
    print(f"  collapse: {collapse(kc_d) if kc_d else 'none'}")
    kc_cited = [d for d in kc_d if any(q in d for q in quotes)]
    print(f"  cited by a register quote: {len(kc_cited)} "
          f"({len(kc_cited)/len(kc_d)*100:.1f}% of distinct)" if kc_d else "  n/a")

    # cross-channel overlap with phone
    pblob = "\n".join(sorted(phone))
    im_in_phone = [d for d in im_d if d in pblob]
    kc_in_phone = [d for d in kc_d if d in pblob]
    print(f"\n== overlap with the phone channel ({len(phone)} substantive) ==")
    print(f"  iMessage distinct also in phone: {len(im_in_phone)}")
    print(f"  KCode    distinct also in phone: {len(kc_in_phone)}")

    out = {
        "imessage": {
            "text_bearing_outbound_substantive": len(im),
            "distinct": len(im_d),
            "collapse": collapse(im_d),
            "cited_by_register": len(im_cited),
            "also_in_phone_channel": len(im_in_phone),
        },
        "kcode": {
            "session_files": nfiles,
            "user_substantive": len(kc),
            "distinct": len(kc_d),
            "collapse": collapse(kc_d) if kc_d else None,
            "cited_by_register": len(kc_cited),
            "also_in_phone_channel": len(kc_in_phone),
        },
        "phone_channel_distinct": len(phone),
        "register_quotes_used": len(quotes),
    }
    path = f"{BASE}/imessage_kcode_recount.json"
    json.dump(out, open(path, "w"), indent=2)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
