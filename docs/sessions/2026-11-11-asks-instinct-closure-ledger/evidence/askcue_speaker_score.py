#!/usr/bin/env python3
"""Score the ask-cue authorship probe: who composed the 8,819 uncited ask-cue clauses.
WHAT THIS IS. Reads askcue_labels.json (60 clauses labelled by a single reader for
speaker) joined to askcue_speaker_key.json (the withheld channel for each clause),
and reports the operator (Koosha) share of the bucket as a closed Wilson interval,
a speaker x channel cross-tab, an anti-anchor (metadata-only) accuracy, and a
side-by-side against nonask_scored.json.
WHAT THIS IS NOT. This is NOT coverage of intent. Authorship of the bucket is a
different quantity from coverage of intent, and no coverage-of-intent figure may be
derived from this file alone. It is also NOT an independent second-coder result:
one labeller, one pass, n=60.
"""
from __future__ import annotations
import json
import math
import os
import time
HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "askcue_labels.json")
KEY = os.path.join(HERE, "askcue_speaker_key.json")
NONASK = os.path.join(HERE, "nonask_scored.json")
OUT = os.path.join(HERE, "askcue_speaker_scored.json")
Z = 1.96
N_TOTAL = 60
POPULATION = 8819
SEED = 20261115
def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    den = 1.0 + Z * Z / n
    center = p + Z * Z / (2.0 * n)
    margin = Z * math.sqrt(p * (1.0 - p) / n + Z * Z / (4.0 * n * n))
    lo = max(0.0, (center - margin) / den)
    hi = min(1.0, (center + margin) / den)
    return [round(lo, 4), round(hi, 4)]
def main() -> int:
    if not os.path.exists(LABELS):
        print("labels missing")
        return 2
    labels = json.load(open(LABELS))
    key = json.load(open(KEY))
    key_by_idx = {it["idx"]: it for it in key["items"]}
    items = labels["items"]
    n = len(items)
    # counts per speaker
    counts: dict[str, int] = {}
    for it in items:
        sp = it["speaker"]
        counts[sp] = counts.get(sp, 0) + 1
    speakers_sorted = sorted(counts)
    channels_sorted = sorted({c for it in key["items"] for c in it["channels"]})
    # cross-tab speaker x channel (clause counted in each channel it carries)
    cross: dict[str, dict[str, int]] = {sp: {ch: 0 for ch in channels_sorted}
                                        for sp in speakers_sorted}
    for it in items:
        sp = it["speaker"]
        for ch in key_by_idx[it["idx"]]["channels"]:
            cross[sp][ch] += 1
    # single-channel composition
    single_comp: dict[str, int] = {ch: 0 for ch in channels_sorted}
    combos: dict[str, int] = {}
    for it in key["items"]:
        combo = "+".join(sorted(it["channels"]))
        combos[combo] = combos.get(combo, 0) + 1
        if len(it["channels"]) == 1:
            single_comp[it["channels"][0]] += 1
    # anti-anchor: every channel implies operator
    agree = sum(1 for it in items if it["speaker"] == "operator")
    accuracy = agree / n
    operator_n = counts.get("operator", 0)
    nonop_n = n - operator_n
    # by_speaker breakdown
    by_speaker: dict[str, dict] = {}
    for sp in speakers_sorted:
        sp_channels: dict[str, int] = {ch: 0 for ch in channels_sorted}
        for it in items:
            if it["speaker"] != sp:
                continue
            for ch in key_by_idx[it["idx"]]["channels"]:
                sp_channels[ch] += 1
        by_speaker[sp] = {
            "n": counts[sp],
            "share": round(counts[sp] / n, 4),
            "wilson_95": wilson(counts[sp], n),
            "channels": sp_channels,
        }
    # by_channel breakdown
    by_channel: dict[str, dict] = {}
    for ch in channels_sorted:
        ch_speakers: dict[str, int] = {}
        for it in items:
            if ch not in key_by_idx[it["idx"]]["channels"]:
                continue
            sp = it["speaker"]
            ch_speakers[sp] = ch_speakers.get(sp, 0) + 1
        ch_n = sum(ch_speakers.values())
        by_channel[ch] = {
            "n": ch_n,
            "speakers": ch_speakers,
        }
    # comparison with nonask_scored.json
    comparison = None
    if os.path.exists(NONASK):
        nd = json.load(open(NONASK))
        bsp = nd.get("by_speaker_pass2", {})
        op_n = bsp.get("operator", {}).get("n", 0)
        nn = nd.get("sample_size", 60)
        nonop = nn - op_n
        comparison = {
            "bucket": "DIFFERENT bucket (non-ask-cue), DIFFERENT sample",
            "source": "nonask_scored.json",
            "sample_n": nn,
            "operator_n": op_n,
            "non_operator_n": nonop,
            "non_operator_share": round(nonop / nn, 4),
            "non_operator_wilson_95": wilson(nonop, nn),
            "note": ("reference only; do not pool with the ask-cue bucket above"),
        }
    out = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "labels_file": os.path.basename(LABELS),
        "key_file": os.path.basename(KEY),
        "labeller": labels.get("labeller"),
        "labels_generated_at_utc": labels.get("generated_at_utc"),
        "n": n,
        "counts": {sp: counts[sp] for sp in speakers_sorted},
        "wilson_95_by_speaker": {sp: wilson(counts[sp], n) for sp in speakers_sorted},
        "operator_share": {
            "n": operator_n,
            "of": n,
            "share": round(operator_n / n, 4),
            "wilson_95": wilson(operator_n, n),
        },
        "non_operator_share": {
            "n": nonop_n,
            "of": n,
            "share": round(nonop_n / n, 4),
            "wilson_95": wilson(nonop_n, n),
        },
        "cross_tab_speaker_x_channel": {
            "rows": speakers_sorted,
            "columns": channels_sorted,
            "matrix": cross,
        },
        "single_channel_composition": single_comp,
        "channel_combinations": combos,
        "anti_anchor_check": {
            "prior": "every channel implies operator",
            "accuracy": round(accuracy, 4),
            "agree": agree,
            "n": n,
            "note": ("this is what the metadata-only method would have scored, "
                     "i.e. an upper bound on its usefulness"),
        },
        "by_speaker": by_speaker,
        "by_channel": by_channel,
        "comparison_nonask_scored": comparison,
        "capture_note": ("labels produced by a beam-free subagent against a blind sheet "
                         "(channel withheld); see askcue_speaker_probe.py for instrument"),
        "hard_caveats": {
            "single_labeller": True,
            "not_an_independent_second_coder": True,
            "sample_n": 60,
            "population": 8819,
            "seed": 20261115,
            "measures": "authorship_of_the_bucket, not coverage_of_intent",
            "no_coverage_of_intent_figure_may_be_derived_from_this_file_alone": True,
        },
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    # compact table
    print(f"n={n}  operator={operator_n}/{n} = {operator_n/n:.1%}  "
          f"Wilson95 [{wilson(operator_n,n)[0]:.1%}, {wilson(operator_n,n)[1]:.1%}]")
    print(f"non-operator = {nonop_n}/{n} = {nonop_n/n:.1%}  "
          f"Wilson95 [{wilson(nonop_n,n)[0]:.1%}, {wilson(nonop_n,n)[1]:.1%}]")
    print("counts:")
    for sp in speakers_sorted:
        print(f"  {sp:10s} {counts[sp]:3d}  [{wilson(counts[sp],n)[0]:.1%}, "
              f"{wilson(counts[sp],n)[1]:.1%}]")
    print("cross-tab (speaker x channel):")
    hdr = "  " + " ".join(f"{ch:>9s}" for ch in channels_sorted)
    print(hdr)
    for sp in speakers_sorted:
        print("  " + f"{sp:9s}" + " " + " ".join(f"{cross[sp][ch]:9d}" for ch in channels_sorted))
    print(f"anti-anchor accuracy = {accuracy:.1%} ({agree}/{n})")
    if comparison:
        print(f"nonask (DIFFERENT bucket/sample) non-operator share = "
              f"{comparison['non_operator_share']:.1%}  "
              f"Wilson95 [{comparison['non_operator_wilson_95'][0]:.1%}, "
              f"{comparison['non_operator_wilson_95'][1]:.1%}]")
    print(f"wrote {OUT}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
