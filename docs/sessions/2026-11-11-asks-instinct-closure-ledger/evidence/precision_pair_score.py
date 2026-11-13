#!/usr/bin/env python3
"""Score two independent precision labellings against one rubric.

Reads precision_labeled.json (labeller 1) and precision_labeled_l2.json
(labeller 2), validates them, and reports per-labeller precision plus
pair agreement. Writes precision_pair_scored.json.

Deterministic: the only field that differs between runs is generated_at_utc.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
L1_PATH = HERE / "precision_labeled.json"
L2_PATH = HERE / "precision_labeled_l2.json"
OUT_PATH = HERE / "precision_pair_scored.json"

LEGAL = ("supported", "partial", "unsupported", "unresolvable")
CATEGORIES = LEGAL  # kappa is over these four categories
N_EXPECTED = 60
Z95 = 1.959963984540054

DENOMINATOR_NOTE = (
    "denominator is 2,252 origin LINKS, not 1,938 distinct cited units"
)
PAIR_NOTE = (
    "two model labellers on one rubric, not human ground truth, reported "
    "alongside the single-labeller figures never instead of them"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_items(path: Path) -> list[dict]:
    with path.open() as fh:
        doc = json.load(fh)
    items = doc["items"]
    assert isinstance(items, list), f"{path.name}: items is not a list"
    return items


def validate(l1: list[dict], l2: list[dict]) -> None:
    for name, items in (("l1", l1), ("l2", l2)):
        if len(items) != N_EXPECTED:
            _fail(f"{name}: expected {N_EXPECTED} items, got {len(items)}")
        idxs = sorted(it["idx"] for it in items)
        if idxs != list(range(N_EXPECTED)):
            _fail(f"{name}: idx is not exactly 0..{N_EXPECTED - 1}")
        for it in items:
            if it.get("verdict") is None:
                _fail(f"{name}: null verdict at idx {it['idx']}")
            if it["verdict"] not in LEGAL:
                _fail(f"{name}: illegal verdict {it['verdict']!r} at idx {it['idx']}")

    def triples(items: list[dict]) -> list[tuple]:
        return [
            (it["idx"], it["unit_id"], it["ask_id"])
            for it in sorted(items, key=lambda x: x["idx"])
        ]

    if triples(l1) != triples(l2):
        _fail("(idx, unit_id, ask_id) triples differ between labellers")


def _fail(msg: str) -> None:
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    raise SystemExit(5)


def wilson(k: int, n: int) -> dict:
    """Wilson score 95% interval, computed by hand."""
    if n == 0:
        return {"low": None, "high": None}
    p = k / n
    z2 = Z95 * Z95
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (Z95 * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5)) / denom
    low = max(0.0, centre - half)
    high = min(1.0, centre + half)
    return {"low": low, "high": high}


def per_labeller(items: list[dict]) -> dict:
    counts = Counter(it["verdict"] for it in items)
    counts_out = {c: counts.get(c, 0) for c in LEGAL}
    total = len(items)
    judgeable = total - counts_out["unresolvable"]

    k_strict = counts_out["supported"]
    k_lenient = counts_out["supported"] + counts_out["partial"]

    strict_val = k_strict / judgeable if judgeable else None
    lenient_val = k_lenient / judgeable if judgeable else None

    return {
        "counts": counts_out,
        "n": total,
        "judgeable": judgeable,
        "strict": {
            "numerator": k_strict,
            "value": strict_val,
            "wilson": wilson(k_strict, judgeable),
        },
        "lenient": {
            "numerator": k_lenient,
            "value": lenient_val,
            "wilson": wilson(k_lenient, judgeable),
        },
    }


def agreement(l1: list[dict], l2: list[dict]) -> dict:
    by1 = {it["idx"]: it["verdict"] for it in l1}
    by2 = {it["idx"]: it["verdict"] for it in l2}
    idxs = sorted(by1)

    exact = sum(1 for i in idxs if by1[i] == by2[i])
    exact_rate = exact / len(idxs)

    c1 = Counter(by1[i] for i in idxs)
    c2 = Counter(by2[i] for i in idxs)
    n = len(idxs)
    p_e = sum((c1[c] / n) * (c2[c] / n) for c in CATEGORIES)
    p_o = exact_rate
    kappa = (p_o - p_e) / (1.0 - p_e) if p_e != 1.0 else None

    disagreements = sum(1 for i in idxs if by1[i] != by2[i])
    sharp = [
        i
        for i in idxs
        if {by1[i], by2[i]} == {"supported", "unsupported"}
    ]

    return {
        "exact_matches": exact,
        "exact_rate": exact_rate,
        "kappa": kappa,
        "disagreements": disagreements,
        "sharp_idx": sharp,
    }


def main() -> int:
    l1 = load_items(L1_PATH)
    l2 = load_items(L2_PATH)
    validate(l1, l2)

    s1 = per_labeller(l1)
    s2 = per_labeller(l2)
    agree = agreement(l1, l2)

    for block in (s1, s2):
        block["agreement"] = agree
        block["denominator_note"] = DENOMINATOR_NOTE
        block["pair_note"] = PAIR_NOTE

    out = {
        "generated_at_utc": utc_now(),
        "script": "precision_pair_score.py",
        "per_labeller": {"l1": s1, "l2": s2},
        "inputs": {
            "l1": L1_PATH.name,
            "l2": L2_PATH.name,
            "n": N_EXPECTED,
            "categories": list(CATEGORIES),
        },
    }

    with OUT_PATH.open("w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # Human-readable summary
    print("precision_pair_score")
    print(f"  n = {N_EXPECTED}")
    for name, block in (("l1", s1), ("l2", s2)):
        c = block["counts"]
        print(
            f"  {name}: supported={c['supported']} partial={c['partial']} "
            f"unsupported={c['unsupported']} unresolvable={c['unresolvable']} "
            f"judgeable={block['judgeable']}"
        )
        sv, lv = block["strict"], block["lenient"]
        print(
            f"    strict  {sv['value']:.4f} "
            f"[{sv['wilson']['low']:.4f}, {sv['wilson']['high']:.4f}]"
        )
        print(
            f"    lenient {lv['value']:.4f} "
            f"[{lv['wilson']['low']:.4f}, {lv['wilson']['high']:.4f}]"
        )
    print(
        f"  agreement: exact={agree['exact_matches']}/{N_EXPECTED} "
        f"({agree['exact_rate']:.4f})  kappa={agree['kappa']:.3f}  "
        f"disagreements={agree['disagreements']}"
    )
    print(f"  sharp (supported vs unsupported) idx: {agree['sharp_idx']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
