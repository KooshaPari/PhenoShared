#!/usr/bin/env python3
"""Derive operator-authored coverage from the three bucket samples -> operator_coverage.json."""
import json, math, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "operator_coverage.json")
Z = 1.959963984540054


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def wilson(k, n, z=Z):
    """Closed-form Wilson score interval; used only to reproduce a reported interval."""
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def main():
    cons, ask, cited, nonask = (load(f) for f in (
        "coverage_consistency.json", "askcue_speaker_scored.json",
        "cited_speaker_scored.json", "nonask_scored.json"))

    fu = cons["frame_a_set_union"]
    frame, cp, up = fu["units"], fu["cited"], fu["uncited"]
    ap, np_ = fu["uncited_ask_cue"], fu["uncited_non_ask_cue"]
    if cp + up != frame:
        raise SystemExit("DRIFT: cited %d + uncited %d != frame %d" % (cp, up, frame))
    if ap + np_ != up:
        raise SystemExit("DRIFT: ask_cue %d + non_ask_cue %d != uncited %d" % (ap, np_, up))

    cs, as_ = cited["operator_share"], ask["operator_share"]

    # nonask_scored.json has no share field: derive from by_speaker_pass2, then flip.
    b2, n = nonask["by_speaker_pass2"], nonask["sample_size"]
    op_n = b2["operator"]["n"]
    nonop_n = sum(v["n"] for k, v in b2.items() if k != "operator")
    if op_n + nonop_n != n:
        raise SystemExit("DRIFT: nonask speakers %d+%d != sample_size %d" % (op_n, nonop_n, n))
    nonop = nonop_n / n
    nonop_ci = wilson(nonop_n, n)
    for doc, lbl in ((ask, "askcue"), (cited, "cited")):
        echo = doc.get("comparison_nonask_scored", {}).get("non_operator_share")
        if echo is not None and abs(echo - round(nonop, 4)) > 1e-9:
            raise SystemExit("DRIFT: %s echo non_operator_share %r != %r" % (lbl, echo, nonop))

    buckets = [
        {"bucket": "cited", "population": cp, "operator_share": cs["share"],
         "wilson_95": cs["wilson_95"],
         "share_source": "cited_speaker_scored.json:operator_share (%d of %d)" % (cs["n"], cs["of"])},
        {"bucket": "uncited_ask_cue", "population": ap, "operator_share": as_["share"],
         "wilson_95": as_["wilson_95"],
         "share_source": "askcue_speaker_scored.json:operator_share (%d of %d)" % (as_["n"], as_["of"])},
        {"bucket": "uncited_non_ask_cue", "population": np_, "operator_share": 1.0 - nonop,
         "wilson_95": [1.0 - nonop_ci[1], 1.0 - nonop_ci[0]],
         "share_source": ("derived from nonask_scored.json:by_speaker_pass2 "
                          "(operator n=%d, non-operator n=%d of sample_size=%d): share = "
                          "1 - %d/%d, interval = [1 - non_op_high, 1 - non_op_low]"
                          % (op_n, nonop_n, n, nonop_n, n)),
         "non_operator_share_as_read": {"value": nonop, "wilson_95_computed": nonop_ci,
                                        "echoed_in_sibling_files": [0.6167, [0.4902, 0.7291]]}},
    ]

    steps = []
    for b in buckets:
        p, s = b["population"], b["operator_share"]
        lo, hi = b["wilson_95"]
        b["operator_units"] = {"point": p * s, "low": p * lo, "high": p * hi}
        steps.append("%s: %d x %r = %.4f" % (b["bucket"], p, s, p * s))
        steps.append("%s: low %d x %r = %.4f ; high %d x %r = %.4f"
                     % (b["bucket"], p, lo, p * lo, p, hi, p * hi))

    tot_p = sum(b["operator_units"]["point"] for b in buckets)
    tot_l = sum(b["operator_units"]["low"] for b in buckets)
    tot_h = sum(b["operator_units"]["high"] for b in buckets)
    ci = [b["operator_units"] for b in buckets]
    steps.append("total point = %.4f + %.4f + %.4f = %.4f"
                 % (ci[0]["point"], ci[1]["point"], ci[2]["point"], tot_p))
    cov = {"point": ci[0]["point"] / tot_p, "low": ci[0]["low"] / tot_h,
           "high": ci[0]["high"] / tot_l}
    steps.append("coverage point = cited_operator %.4f / total %.4f = %r"
                 % (ci[0]["point"], tot_p, cov["point"]))
    steps.append("coverage low  = LOWEST num %.4f / HIGHEST den %.4f = %r"
                 % (ci[0]["low"], tot_h, cov["low"]))
    steps.append("coverage high = HIGHEST num %.4f / LOWEST den %.4f = %r"
                 % (ci[0]["high"], tot_l, cov["high"]))

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "operator_coverage.py",
        "frame": {"name": "frame_a_set_union", "units": frame, "cited": cp, "uncited": up,
                  "uncited_ask_cue": ap, "uncited_non_ask_cue": np_,
                  "identity_checks": {"cited + uncited == units": True,
                                      "uncited_ask_cue + uncited_non_ask_cue == uncited": True}},
        "inputs": {
            "coverage_consistency.json": {
                "frame_a_set_union.units": frame, "frame_a_set_union.cited": cp,
                "frame_a_set_union.uncited": up, "frame_a_set_union.uncited_ask_cue": ap,
                "frame_a_set_union.uncited_non_ask_cue": np_},
            "askcue_speaker_scored.json": {
                "operator_share.share": as_["share"], "operator_share.wilson_95": as_["wilson_95"],
                "operator_share.n": as_["n"], "operator_share.of": as_["of"]},
            "cited_speaker_scored.json": {
                "operator_share.share": cs["share"], "operator_share.wilson_95": cs["wilson_95"],
                "operator_share.n": cs["n"], "operator_share.of": cs["of"]},
            "nonask_scored.json": {
                "by_speaker_pass2.operator.n": op_n,
                "by_speaker_pass2.non_operator.n (sum of agent/tool/system/peer)": nonop_n,
                "sample_size": n,
                "field_used": "by_speaker_pass2 + sample_size (no non_operator_share field present)"},
        },
        "per_bucket": buckets,
        "total_operator_units": {"point": tot_p, "low": tot_l, "high": tot_h},
        "coverage": {"point": cov["point"], "low": cov["low"], "high": cov["high"],
                     "method": "range_from_independent_bounds", "is_confidence_interval": False,
                     "note": "low = lowest numerator over highest denominator; high = highest "
                             "numerator over lowest denominator. Independent bounds only."},
        "steps": steps,
        "caveats": {
            "single_labeller_each_bucket": True,
            "three_samples_not_one": "each bucket share comes from its own n=60 sample; the three intervals are not independent of each other and are not a joint estimate",
            "shares_multiplied_into_populations": "point estimates of a share are applied to a fixed population count; no design effect and no finite-population correction is applied",
            "citation_precision_unmeasured": "the numerator counts units the register matched; the precision of those matches is not measured here, so this is an estimate of coverage, not a published rate",
            "rate_publication_gate": "operator policy: a published rate needs recall AND precision >= 0.9; this file does not meet that gate and must be cited as an estimate with its range",
            "what_would_close_it": "a second independent labeller on all three sheets, plus a measured citation-precision sample",
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")

    for b in buckets:
        u = b["operator_units"]
        print("%-20s pop=%-6d share=%.4f  units point=%.1f low=%.1f high=%.1f"
              % (b["bucket"], b["population"], b["operator_share"],
                 u["point"], u["low"], u["high"]))
    print("total_operator_units point=%.1f low=%.1f high=%.1f" % (tot_p, tot_l, tot_h))
    print("coverage point=%.2f%% range=[%.2f%%, %.2f%%] (range_from_independent_bounds, NOT a CI)"
          % (cov["point"] * 100, cov["low"] * 100, cov["high"] * 100))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
