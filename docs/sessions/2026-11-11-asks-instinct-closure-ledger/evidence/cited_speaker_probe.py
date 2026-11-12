#!/usr/bin/env python3
"""Cited-speaker probe: authorship of the distinct cited strings (matched side).

Population = the distinct cited strings derived by running the skeleton's
per-channel citation pass and deduplicating across channels.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"

SHEET = os.path.join(HERE, "cited_speaker_sheet.json")
KEY = os.path.join(HERE, "cited_speaker_key.json")

SEED = 20261116
N_SAMPLE = 60

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)
import union_channels as U            # noqa: E402
import segment_units as SEG           # noqa: E402


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


INSTRUCTIONS = (
    "For each clause set `speaker` to ONE of: operator | agent | tool | system | peer | "
    "other, and give a one-line `why`. operator = Koosha's own words, including text "
    "relayed through an instinct or hermes bridge or quoted behind a `| koosha |` header. "
    "agent = an AI agent's narration, plan, report, or instruction to another agent, "
    "including pasted agent output inside a user turn. peer = a third party. tool = raw "
    "tool output. system = harness banner, injected prompt, config block. other = "
    "unresolvable. Channel is deliberately withheld; judge the text, not the source.")


def populations():
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    H, _ = U.harness()
    members = {"harness": H,
               "imessage": {x for x in U.imessage() if U.keep(x)},
               "kcode": {x for x in U.kcode()[0] if U.keep(x)},
               "phone": U.phone()}

    where: dict[str, set[str]] = {}
    for name, ms in members.items():
        for m in ms:
            for u in SEG.segment(m):
                where.setdefault(u, set()).add(name)

    cited_strings: list[str] = []
    per_channel: dict[str, int] = {}
    for name, ms in members.items():
        units = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited_pos = idx.cite(quotes)          # set of positions
        cited_strings += [units[i] for i in cited_pos]
        per_channel[name] = len(cited_pos)
        print(f"  {name:9s} cited {len(cited_pos):6d}")

    cited_set = sorted(set(cited_strings))
    summed = sum(per_channel.values())
    print(f"  summed per-channel cited: {summed}")
    print(f"  distinct cited:           {len(cited_set)}")
    print(f"  summed - distinct gap:    {summed - len(cited_set)}")

    return cited_set, where, per_channel


def main() -> int:
    cons = json.load(open(os.path.join(HERE, "coverage_consistency.json")))["frame_a_set_union"]
    exp_cited = cons["cited"]

    cited_set, where, per_channel = populations()

    print(f"cited (distinct) : {len(cited_set)} (published {exp_cited})")

    if len(cited_set) != exp_cited:
        raise SystemExit(f"DENOMINATOR DRIFT: cited rebuilt {len(cited_set)} != 1938")

    rng = random.Random(SEED)
    sample = rng.sample(cited_set, N_SAMPLE)

    items, key = [], []
    for k, clause in enumerate(sample):
        items.append({"idx": k, "clause": clause, "speaker": None, "why": ""})
        key.append({"idx": k, "clause": clause, "channels": sorted(where.get(clause, []))})

    meta = {
        "generated_at_utc": _now(),
        "seed": SEED,
        "n": N_SAMPLE,
        "population": len(cited_set),
        "blind_to": ["channel", "declared role"],
        "single_labeller": True,
        "what_this_is_not": "This measures authorship of the matched side only. It does not by itself produce a coverage rate; a rate additionally needs the number of distinct operator-authored units on both sides in one frame.",
    }
    with open(SHEET, "w") as fh:
        json.dump({**meta, "instructions": INSTRUCTIONS, "items": items}, fh, indent=1)
    with open(KEY, "w") as fh:
        json.dump({**meta, "items": key}, fh, indent=1)

    print(f"wrote {SHEET}")
    print(f"wrote {KEY}")
    print("channel composition of the sample (withheld from the sheet):")
    c: Counter = Counter()
    for it in key:
        for ch in (it["channels"] or ["unattributed"]):
            c[ch] += 1
    print("  " + json.dumps(dict(c)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
