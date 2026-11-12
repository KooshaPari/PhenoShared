#!/usr/bin/env python3
"""Non-ask-cue increment: do the units the ask classifier REJECTED still carry intents
the register holds?

WHY. `recall_probe.py` measured capture@5 = 13.3% on the 8,819 uncited ASK-CUE units and
published union coverage as **at least** 10.7% [9.4-12.9]. It was a lower bound for one
reason only: the 31,023 uncited units the classifier called NOT ask-cue were never probed.
That is the last unmeasured region between 10.7% and "coverage of everything".

Neither answer is comfortable. If these units are also captured at a similar rate, the
published figure rises again. If they are captured at ~0, then 10.7% is close to the whole
truth and the register is simply that incomplete. Either way the bound stops being a bound.

DESIGN. Identical to `recall_probe.py` on purpose -- same retrieval, same K=5, same blind
two-file split -- so the two rates are comparable estimators rather than two different
experiments. Only the population predicate and the seed change.

  population: uncited AND NOT is_ask   (the complement of the previous probe's population)
  seed:       20261114                  (a third seed, not 20261112 or 20261113)

DENOMINATOR DISCIPLINE. The population must reconstruct as the exact complement:
ask-cue (8,819) + non-ask-cue = all uncited (39,842). The script asserts all three numbers
and refuses to sample if any of them drifts, because a rate measured on a silently
different population is exactly the failure this ledger exists to stop repeating.

Read-only: ledger.db mode=ro + query_only=1; nothing written outside this evidence dir.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")

SHEET = os.path.join(HERE, "nonask_label_sheet.json")
PAIRS = os.path.join(HERE, "nonask_candidates.json")
PROBE = os.path.join(HERE, "semantic_coverage_probe.json")
UNION = os.path.join(HERE, "union_channels.json")

SEED = 20261114   # a third seed: not 20261112 (probe) or 20261113 (recall)
N_SAMPLE = 60
TOPK = 5
QUOTE_CHARS = 130

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)
import union_channels as U            # noqa: E402
import segment_units as SEG           # noqa: E402
import semantic_coverage_probe as SP  # noqa: E402


def populations() -> tuple[list[str], list[str], int]:
    """Return (ask_cue, non_ask_cue, all_uncited) with the published method."""
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    H, _ = U.harness()
    I = {x for x in U.imessage() if U.keep(x)}
    K = {x for x in U.kcode()[0] if U.keep(x)}
    P = U.phone()
    members = {"harness": H, "imessage": I, "kcode": K, "phone": P}

    ask_like: list[str] = []
    non_ask: list[str] = []
    free_all: list[str] = []
    for name, ms in members.items():
        units = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited = idx.cite(quotes)
        free = [u for i, u in enumerate(units) if i not in cited]
        free_all.extend(free)
        a = [u for u in free if SEG.is_ask(u)]
        b = [u for u in free if not SEG.is_ask(u)]
        ask_like.extend(a)
        non_ask.extend(b)
        print(f"  {name:9s} free {len(free):6d}  ask-cue {len(a):5d}  non-ask {len(b):6d}")

    return sorted(set(ask_like)), sorted(set(non_ask)), sorted(set(free_all))


def main() -> int:
    t0 = time.time()
    # Expected counts come from coverage_consistency.json (frame A), NOT from the published
    # granularity_units.json: that file's union row mixes a summed numerator with a deduped
    # denominator, and its imessage channel rebuilds 16 units short in this environment. The
    # consistency audit is the authority for the frame these probes sample in.
    cons = json.load(open(os.path.join(HERE, "coverage_consistency.json")))["frame_a_set_union"]
    exp_ask = cons["uncited_ask_cue"]
    exp_non = cons["uncited_non_ask_cue"]
    exp_free = cons["uncited"]

    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    asks = con.execute(
        "SELECT a.id, a.interpretation, u.body FROM reg_asks a "
        "LEFT JOIN reg_utterances u ON u.id = a.utterance_id").fetchall()
    con.close()

    ask_like, non_ask, free_all = populations()
    exp_total = exp_free

    print(f"ask-cue units : {len(ask_like)} (published {exp_ask})")
    print(f"non-ask units : {len(non_ask)}")
    print(f"all uncited   : {len(free_all)} (published {exp_total})")
    print(f"non-ask       : {len(non_ask)} (published {exp_non})")

    if len(ask_like) != exp_ask:
        raise SystemExit(f"DENOMINATOR DRIFT: ask-cue rebuilt {len(ask_like)} != {exp_ask}")
    if len(non_ask) != exp_non:
        raise SystemExit(f"DENOMINATOR DRIFT: non-ask rebuilt {len(non_ask)} != {exp_non}")
    if len(free_all) != exp_total:
        raise SystemExit(f"DENOMINATOR DRIFT: all-uncited rebuilt {len(free_all)} != {exp_total}")
    if len(ask_like) + len(non_ask) != len(free_all):
        raise SystemExit(
            "PARTITION BROKEN: ask-cue + non-ask != all uncited "
            f"({len(ask_like)} + {len(non_ask)} != {len(free_all)}). "
            "A string cannot be both; refusing to sample.")

    rng = random.Random(SEED)
    sample = rng.sample(non_ask, N_SAMPLE)

    A = SP.embed([SP.clean(a[1] or "") or SP.clean(a[2] or "") for a in asks],
                 f"asks_{len(asks)}")
    C = SP.embed(sample, f"nonask_{SEED}_{N_SAMPLE}")
    A = A / np.linalg.norm(A, axis=1, keepdims=True)
    C = C / np.linalg.norm(C, axis=1, keepdims=True)
    sims = C @ A.T

    pairs, sheet = [], []
    for k, clause in enumerate(sample):
        order = np.argsort(-sims[k])[:TOPK]
        cands = [{
            "ask": asks[j][0],
            "interpretation": asks[j][1],
            "quote": (asks[j][2] or "")[:QUOTE_CHARS],
            "rank": r + 1,
            "cosine": round(float(sims[k, j]), 4),
        } for r, j in enumerate(order)]
        pairs.append({"idx": k, "clause": clause, "candidates": cands})

        blind = [{"ask": c["ask"], "interpretation": c["interpretation"],
                  "quote": c["quote"]} for c in cands]
        random.Random(SEED * 1000 + k).shuffle(blind)
        sheet.append({"idx": k, "clause": clause, "candidates": blind,
                      "captured_by": None, "why": ""})

    meta = {"generated_at_utc": _now(), "seed": SEED, "n": N_SAMPLE, "topk": TOPK,
            "population": len(non_ask),
            "partition": {"ask_cue": len(ask_like), "non_ask_cue": len(non_ask),
                          "all_uncited": len(free_all)}}
    with open(PAIRS, "w") as fh:
        json.dump({**meta, "pairs": pairs}, fh, indent=1)
    with open(SHEET, "w") as fh:
        json.dump({**meta,
                   "instructions": ("For each clause set captured_by to the ask id whose "
                                    "interpretation and quote express the SAME intent as the "
                                    "clause, or \"NONE\" if no candidate does. Adjacent-but-"
                                    "different intents are NONE. Candidates are shuffled: "
                                    "rank is hidden."),
                   "items": sheet}, fh, indent=1)
    print(f"wrote {SHEET}\nwrote {PAIRS}")
    print(f"[{time.time() - t0:.0f}s] sample of {N_SAMPLE} from {len(non_ask)}")
    return 0




def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    raise SystemExit(main())
