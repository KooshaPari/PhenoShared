#!/usr/bin/env python3
"""Ask-cue authorship probe: who actually composed the 8,819 uncited ask-cue clauses?

WHY. `askcue_role.py` closed the metadata avenue: both harvest exports are user-turn
extracts, so post-filter every record declares itself an operator turn and declared
speaker is constant at 100% operator. A constant field cannot supply the denominator that
every coverage-of-intent statement needs. The only remaining instrument is adjudication by
reading, which is what `nonask_probe.py` did for the other bucket at n=60.

WHAT THIS IS. The same instrument, applied to the population that matters. It produces a
blind label sheet -- clause plus a channel hidden from the labeller -- and a separate key
file for the scorer, so the blinding is real rather than declared.

WHAT THIS IS NOT. This is not an independent second coder. The same reader who labelled the
non-ask sheet labels this one, so the single-labeller limitation in §3i/§3j applies here
unchanged and is repeated in the output rather than left implicit.

DESIGN, identical to `nonask_probe.py` except for the population and the seed:
  population: uncited AND is_ask        (8,819, the ask-cue bucket)
  seed:       20261115                  (a fourth seed, not 20261112/13/14)
  n:          60, no retrieval, no embeddings -- authorship needs the clause alone

DENOMINATOR DISCIPLINE. The population is asserted against `coverage_consistency.json`
frame A, and the partition is re-checked so the bucket cannot silently change size.

Read-only: ledger.db mode=ro + query_only=1; nothing written outside this evidence dir.
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

SHEET = os.path.join(HERE, "askcue_speaker_sheet.json")
KEY = os.path.join(HERE, "askcue_speaker_key.json")

SEED = 20261115   # fourth seed: not 20261112 (probe), 20261113 (recall), 20261114 (nonask)
N_SAMPLE = 60

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)
import union_channels as U            # noqa: E402
import segment_units as SEG           # noqa: E402


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def populations() -> tuple[list[str], list[str], list[str]]:
    """Return (ask_cue, non_ask_cue, all_uncited) and the clause -> channels map."""
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

    ask_like: list[str] = []
    non_ask: list[str] = []
    free_all: list[str] = []
    for name, ms in members.items():
        units = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited = idx.cite(quotes)
        free = [u for i, u in enumerate(units) if i not in cited]
        free_all.extend(free)
        ask_like.extend([u for u in free if SEG.is_ask(u)])
        non_ask.extend([u for u in free if not SEG.is_ask(u)])
        print(f"  {name:9s} free {len(free):6d}")

    return sorted(set(ask_like)), sorted(set(non_ask)), sorted(set(free_all)), where


def main() -> int:
    cons = json.load(open(os.path.join(HERE, "coverage_consistency.json")))["frame_a_set_union"]
    exp_ask = cons["uncited_ask_cue"]
    exp_non = cons["uncited_non_ask_cue"]
    exp_free = cons["uncited"]

    ask_like, non_ask, free_all, where = populations()

    print(f"ask-cue units : {len(ask_like)} (published {exp_ask})")
    print(f"non-ask units : {len(non_ask)} (published {exp_non})")
    print(f"all uncited   : {len(free_all)} (published {exp_free})")

    if len(ask_like) != exp_ask:
        raise SystemExit(f"DENOMINATOR DRIFT: ask-cue rebuilt {len(ask_like)} != {exp_ask}")
    if len(non_ask) != exp_non:
        raise SystemExit(f"DENOMINATOR DRIFT: non-ask rebuilt {len(non_ask)} != {exp_non}")
    if len(free_all) != exp_free:
        raise SystemExit(f"DENOMINATOR DRIFT: all-uncited rebuilt {len(free_all)} != {exp_free}")
    if len(ask_like) + len(non_ask) != len(free_all):
        raise SystemExit("PARTITION BROKEN: ask-cue + non-ask != all uncited")

    rng = random.Random(SEED)
    sample = rng.sample(ask_like, N_SAMPLE)

    items, key = [], []
    for k, clause in enumerate(sample):
        # channel is objective provenance, withheld from the sheet so the speaker judgement
        # cannot anchor on "this came from an agent harness, so it must be agent text"
        items.append({"idx": k, "clause": clause, "speaker": None, "why": ""})
        key.append({"idx": k, "clause": clause, "channels": sorted(where.get(clause, []))})

    meta = {
        "generated_at_utc": _now(),
        "seed": SEED,
        "n": N_SAMPLE,
        "population": len(ask_like),
        "partition": {"ask_cue": len(ask_like), "non_ask_cue": len(non_ask),
                      "all_uncited": len(free_all)},
        "instructions": (
            "For each clause set `speaker` to ONE of: operator | agent | tool | system | peer | "
            "other, and give a one-line `why`. operator = Koosha's own words, including text "
            "relayed through an instinct or hermes bridge or quoted behind a `| koosha |` header. "
            "agent = an AI agent's narration, plan, report, or instruction to another agent, "
            "including pasted agent output inside a user turn. peer = a third party. tool = raw "
            "tool output. system = harness banner, injected prompt, config block. other = "
            "unresolvable. Channel is deliberately withheld; judge the text, not the source."),
        "blind_to": ["channel", "declared role"],
        "single_labeller": True,
    }
    with open(SHEET, "w") as fh:
        json.dump({**meta, "items": items}, fh, indent=1)
    with open(KEY, "w") as fh:
        json.dump({**meta, "note": "channel is objective provenance, read only by the scorer",
                   "items": key}, fh, indent=1)

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
