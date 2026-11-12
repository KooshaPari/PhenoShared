#!/usr/bin/env python3
"""Recall increment: can ANY register ask capture a randomly sampled uncited clause?

WHY. `semantic_coverage_probe.py` established a FLOOR of 17/800 = 2.12% captured
clauses and deliberately withheld the coverage rate, because a floor needs only
precision while a rate needs recall. Its 45 labelled pairs were stratified (top 30
score band, bottom 15), which cannot estimate recall on the population.

WHAT IS DIFFERENT HERE.
  1. The sample is RANDOM and unstratified -- a fresh seed, drawn from the same
     published denominator (asserted against the probe's own 8,819 count, so the
     denominator cannot silently drift).
  2. Each clause is offered the top-K (K=5) retrieved asks, not just top-1, so a
     capture the model ranks second is still reachable. What this measures is
     therefore *capture@5*: recall OF the k=5 retrieval system, not ultimate
     recall. A capture outside the window is uncounted, so the number stays a
     lower bound -- but now a lower bound measured on a random draw rather than on
     a hand-picked band, which is what makes it publishable.
  3. The label sheet is BLINDED: candidates are shuffled and the cosine is removed,
     so the labeller cannot see which ask the model preferred or how strongly.

WHAT IT OUTPUTS. Two files, deliberately split:
  recall_label_sheet.json   -- what a human reads: clause + shuffled candidates.
  recall_candidates.json    -- the same pairs WITH rank and cosine, for the scorer.
If those two were one file the blinding would be theatre.

Read-only throughout: ledger.db mode=ro + query_only, nothing written outside this
session's evidence directory.
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

SHEET = os.path.join(HERE, "recall_label_sheet.json")
PAIRS = os.path.join(HERE, "recall_candidates.json")
PROBE = os.path.join(HERE, "semantic_coverage_probe.json")

SEED = 20261113          # deliberately different from the probe's 20261112
N_SAMPLE = 60
TOPK = 5
QUOTE_CHARS = 130

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)
import union_channels as U          # noqa: E402
import segment_units as SEG         # noqa: E402
import semantic_coverage_probe as SP  # noqa: E402  (reuses embed + clean + model)


def population() -> list[str]:
    """Rebuild the uncited ask-cue population with the published method."""
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    H, _ = U.harness()
    I = {x for x in U.imessage() if U.keep(x)}
    K = {x for x in U.kcode()[0] if U.keep(x)}
    P = U.phone()
    members = {"harness": H, "imessage": I, "kcode": K, "phone": P}

    uncited: list[str] = []
    for name, ms in members.items():
        units = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited = idx.cite(quotes)
        free = [u for i, u in enumerate(units) if i not in cited]
        asklike = [u for u in free if SEG.is_ask(u)]
        uncited.extend(asklike)
        print(f"  {name:9s} uncited ask-cue units: {len(asklike)}")
    return sorted(set(uncited))


def main() -> int:
    t0 = time.time()
    published = json.load(open(PROBE))["population"]
    expected = published["uncited_ask_cue_units_union"]

    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    asks = con.execute(
        "SELECT a.id, a.interpretation, u.body FROM reg_asks a "
        "LEFT JOIN reg_utterances u ON u.id = a.utterance_id").fetchall()
    con.close()

    uncited = population()
    print(f"uncited ask-cue units (union, deduped): {len(uncited)}")
    if len(uncited) != expected:
        raise SystemExit(
            f"DENOMINATOR DRIFT: rebuilt {len(uncited)} but the published probe "
            f"reported {expected}. Refusing to sample a different population.")

    rng = random.Random(SEED)
    sample = rng.sample(uncited, N_SAMPLE)

    A = SP.embed([SP.clean(a[1] or "") or SP.clean(a[2] or "") for a in asks],
                 f"asks_{len(asks)}")
    C = SP.embed(sample, f"recall_{SEED}_{N_SAMPLE}")
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

        # blind copy: shuffle, strip rank and cosine
        blind = [{"ask": c["ask"], "interpretation": c["interpretation"],
                  "quote": c["quote"]} for c in cands]
        random.Random(SEED * 1000 + k).shuffle(blind)
        sheet.append({"idx": k, "clause": clause, "candidates": blind,
                      "captured_by": None,   # <- fill with an ask id, or "NONE"
                      "why": ""})

    for path, body in ((PAIRS, {"generated_at_utc": _now(), "seed": SEED,
                                "n": N_SAMPLE, "topk": TOPK,
                                "population": len(uncited), "pairs": pairs}),
                       (SHEET, {"generated_at_utc": _now(), "seed": SEED,
                                "n": N_SAMPLE, "topk": TOPK,
                                "instructions": ("For each clause set captured_by to the ask id "
                                                 "whose interpretation and quote express the SAME "
                                                 "intent as the clause, or \"NONE\" if no candidate "
                                                 "does. Adjacent-but-different intents are NONE. "
                                                 "Candidates are shuffled: rank is hidden."),
                                "items": sheet})):
        with open(path, "w") as fh:
            json.dump(body, fh, indent=1)
        print(f"wrote {path}")

    print(f"[{time.time() - t0:.0f}s] sample of {N_SAMPLE} from {len(uncited)}")
    return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    raise SystemExit(main())
