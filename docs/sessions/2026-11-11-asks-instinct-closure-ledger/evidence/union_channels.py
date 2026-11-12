#!/usr/bin/env python3
"""Union of measured channels, with containment-based overlap.

Channels
  harness : jcode + codex occurrence JSONL, filtered to human non-injected
            substantive turns, then distinguished (same filters as
            collapse_intents.py, which published 6,085).
  imessage: chat.db outbound text-bearing, read-only, no copy.
  kcode   : ~/.kcode/sessions/*.json user turns.
  phone   : reg_utterances user bodies (already known to be an iMessage subset).

Overlap method, stated explicitly because it is approximate:
  a member of A overlaps B if its normalized text appears as a substring of the
  concatenated B text. That catches both exact matches and mid-message excerpts.
  The reverse direction is measured separately and reported separately, because
  a short law in one channel can sit inside a long prompt in another and the
  counts are not symmetric. Union is then a coarse count, labelled as such.

Prints aggregates only. Writes union_channels.json.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
JCODE = f"{BASE}/jcode-occurrences.jsonl"
CODEX = f"{BASE}/codex_user_turns_v2.jsonl"
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")
LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")

sys.path.insert(0, BASE)
from recount_imessage_kcode import imessage, kcode, norm, is_noise  # noqa: E402

SUBSTANTIVE = 12

NOISE = [re.compile(p) for p in [
    r"swarm await", r"^\[?auto\]?\b", r"<system-reminder>|system[_ ]reminder",
    r"attached image associated with the preceding|\[image",
    r"environment_context>|<current_date>|<env>",
    r"codex_internal_context|\[internal_context",
    r"agents\.md instructions|<instructions>",
    r"swarm completion report required", r"tool timing:|jcode_progress",
    r"^this session is being continued|conversation summary",
    r"<open_and_recently_viewed_files>|opened file:|edited file:"]]


def keep(n: str) -> bool:
    return len(n) >= SUBSTANTIVE and not any(p.search(n) for p in NOISE)


def harness() -> tuple[set[str], dict]:
    stats = defaultdict(int)
    out: set[str] = set()
    for path in (JCODE, CODEX):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    stats["bad_json"] += 1
                    continue
                stats["rows"] += 1
                if r.get("is_injected"):
                    stats["injected"] += 1
                    continue
                if r.get("is_human") is False:
                    stats["not_human"] += 1
                    continue
                n = norm(r.get("text") or "")
                if not keep(n):
                    stats["filtered"] += 1
                    continue
                out.add(n)
    return out, dict(stats)


def phone() -> set[str]:
    import sqlite3
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    s = {norm(b) for (b,) in con.execute(
        "select body from reg_utterances where role='user'")}
    return {x for x in s if keep(x)}


def contained(a: set[str], blob: str) -> list[str]:
    return [x for x in a if x in blob]


def main() -> int:
    t0 = time.time()
    reg = json.load(open(REGISTER))["records"]
    quotes = sorted({norm(r.get("quote") or "") for r in reg})
    quotes = [q for q in quotes if len(q) >= SUBSTANTIVE]

    H, hstats = harness()
    I = {x for x in imessage() if keep(x)}
    K = {x for x in kcode()[0] if keep(x)}
    P = phone()
    print(f"harness  {len(H)} distinct   {hstats}")
    print(f"imessage {len(I)} distinct")
    print(f"kcode    {len(K)} distinct")
    print(f"phone    {len(P)} distinct")
    print(f"[{time.time()-t0:.0f}s]\n")

    def blob(s: set[str]) -> str:
        return "\n".join(sorted(s))

    blobs = {"harness": blob(H), "imessage": blob(I), "kcode": blob(K), "phone": blob(P)}

    pairs = [("imessage", "harness"), ("kcode", "harness"),
             ("kcode", "imessage"), ("phone", "imessage")]
    ov: dict[str, int] = {}
    for a, b in pairs:
        fwd = contained({"harness": H, "imessage": I, "kcode": K, "phone": P}[a],
                        blobs[b])
        rev = contained({"harness": H, "imessage": I, "kcode": K, "phone": P}[b],
                        blobs[a])
        ov[f"{a}_in_{b}"] = len(fwd)
        ov[f"{b}_in_{a}"] = len(rev)
        print(f"  {a} in {b}: {len(fwd):5d}   {b} in {a}: {len(rev):5d}"
              f"   [{time.time()-t0:.0f}s]")

    # greedy long-first overlap for the union, per unordered pair
    def greedy(a: set[str], b: set[str]) -> int:
        ba = blob(a)
        eaten = 0
        for x in sorted(b, key=len, reverse=True):
            if x in ba:
                eaten += 1
        return eaten

    u_im_h = greedy(H, I)
    u_kc_h = greedy(H, K)
    u_kc_im = greedy(I, K)
    print(f"\ngreedy overlap pairs: im∩harness={u_im_h} kcode∩harness={u_kc_h} "
          f"kcode∩imessage={u_kc_im}  [{time.time()-t0:.0f}s]")

    union = len(H) + len(I) + len(K) - u_im_h - u_kc_h - u_kc_im
    print(f"union = {len(H)} + {len(I)} + {len(K)} - {u_im_h} - {u_kc_h} - {u_kc_im}"
          f" = {union}")

    # citation coverage per channel: a register quote is a substring of the member
    def cited(members: set[str]) -> int:
        n = 0
        for m in members:
            for q in quotes:
                if len(q) <= len(m) and q in m:
                    n += 1
                    break
        return n

    cit = {k: cited(v) for k, v in
           (("harness", H), ("imessage", I), ("kcode", K))}
    print(f"\ncited by a register quote: {cit}  [{time.time()-t0:.0f}s]")
    print(f"register distinct asks: {len(set(quotes))}")
    print(f"citation-based union coverage: "
          f"{sum(cit.values())}/{union} = {sum(cit.values())/union*100:.1f}%")

    out = {
        "channels_distinct": {"harness": len(H), "imessage": len(I),
                              "kcode": len(K), "phone": len(P)},
        "harness_filter_stats": hstats,
        "overlap_substring": ov,
        "overlap_greedy": {"imessage_harness": u_im_h,
                           "kcode_harness": u_kc_h,
                           "kcode_imessage": u_kc_im},
        "union": union,
        "register_distinct_asks": len(set(quotes)),
        "cited_by_channel": cit,
        "citation_based_coverage_pct": round(sum(cit.values()) / union * 100, 1),
        "method": "substring containment both directions; greedy long-first "
                  "pairing; union is a coarse count mixing message and intent "
                  "granularity and must not be read as a precise coverage figure",
    }
    json.dump(out, open(f"{BASE}/union_channels.json", "w"), indent=2)
    print(f"\nwrote {BASE}/union_channels.json  [{time.time()-t0:.0f}s]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
