#!/usr/bin/env python3
"""Draw a reproducible sample to measure the ask-cue classifier used by segment_units.py.

The classifier gates the TIGHTER denominator (harness ask-units only), so its error rate
must be published next to that figure. Two strata:

  PRED_ASK   units the classifier called asks -> labels estimate PRECISION
  PRED_NOT   units the classifier rejected     -> labels estimate RECALL loss

Randomness is seeded so the sample can be redrawn byte-identically. Labels live in
ask_rule_labels.json, written by hand, and are scored by score_ask_rules.py.
"""
from __future__ import annotations

import json
import random
import sys

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
sys.path.insert(0, BASE)
import union_channels as U  # noqa: E402
from segment_units import is_ask, segment  # noqa: E402

N_ASK = 30
N_NOT = 15
SEED = 23


def main() -> int:
    H, _ = U.harness()
    units: set[str] = set()
    for m in H:
        units.update(segment(m))
    ask = sorted(u for u in units if is_ask(u))
    notask = sorted(u for u in units if not is_ask(u))
    rng = random.Random(SEED)
    rows = ([{"stratum": "PRED_ASK", "text": u} for u in rng.sample(ask, N_ASK)] +
            [{"stratum": "PRED_NOT", "text": u} for u in rng.sample(notask, N_NOT)])
    for r in rows:
        r["excerpt"] = r["text"][:110]
    json.dump({"seed": SEED, "n_ask": N_ASK, "n_not": N_NOT,
               "population": {"pred_ask": len(ask), "pred_not": len(notask)},
               "rows": rows}, open(f"{BASE}/ask_rule_sample.json", "w"), indent=2)
    print(f"population: pred_ask={len(ask)} pred_not={len(notask)}")
    for i, r in enumerate(rows, 1):
        print(f"{i:2d} {r['stratum'][:8]:8s} {r['excerpt']}")
    print(f"\nwrote {BASE}/ask_rule_sample.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
