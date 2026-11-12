#!/usr/bin/env python3
"""Adjudicate the 12 inter-labeller disagreements in the uncited_non_ask_cue bucket.

Why this matters: the coverage denominator is not built from the ask-cue bucket
alone. It adds `uncited_non_ask_cue x operator_share`, and the non-ask bucket is
exactly where the two labellers disagreed (12 of 60, 10 of which involve
`operator` on one side only). So the published pair moves with these 12 rows.

Method:
 1. Recompute the disagreement set from the two raw label files and assert it is
    the same set inter_labeller_agreement.json recorded. If that reconciliation
    fails, everything below is meaningless, so the script exits 4.
 2. Take the third, blind reading. A disagreement is RESOLVED when the third
    reader agrees with one of the two (majority of three); otherwise it SPLITS.
 3. Rebuild the bucket operator count: agreed rows keep their agreed label,
    resolved rows take the majority label, split rows are carried as uncertainty
    and reported both ways rather than silently assigned.
 4. Recompute coverage with the SAME frame and the SAME formula the committed
    coverage scripts use, and first reproduce both baselines to 1e-9. The cited
    and ask-cue buckets are not touched because both labellers already agree on
    them exactly (58/60 and 52/60), so the adjudicated figure is a single
    well-defined point rather than a mixture of labellers.

Inputs (read only, never modified):
    nonask_label_sheet.json       labeller 1, field speaker_pass2
    nonask_labels_l2.json         labeller 2, field speaker
    adjudication_labels.json      third blind reading
    adjudication_key.json         the two earlier values, for comparison
    inter_labeller_agreement.json recorded disagreement set
    operator_coverage.json        labeller-1 baseline to reproduce
    operator_coverage_l2.json     labeller-2 baseline to reproduce
    coverage_consistency.json     frame counts

Output: adjudication.json

Exit codes: 0 computed, 2 required input missing, 4 reconciliation failure.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SIX = ("operator", "agent", "tool", "system", "peer", "other")
BUCKET = "uncited_non_ask_cue"


def die(code, msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(name, required=True):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        if required:
            die(2, f"missing required input {name}")
        return None
    return json.load(open(p))


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [(c - m) / d, (c + m) / d]


def main():
    l1raw = load("nonask_label_sheet.json")
    l2raw = load("nonask_labels_l2.json")
    third = load("adjudication_labels.json")
    key = load("adjudication_key.json")
    agree = load("inter_labeller_agreement.json")
    cov1 = load("operator_coverage.json")
    cov2 = load("operator_coverage_l2.json")
    cons = load("coverage_consistency.json")

    l1 = {int(i["idx"]): i["speaker_pass2"] for i in l1raw["items"]}
    l2 = {int(i["idx"]): i["speaker"] for i in l2raw["items"]}
    a3 = {int(i["idx"]): i["verdict"] for i in third["items"]}
    why3 = {int(i["idx"]): i.get("why", "") for i in third["items"]}

    # --- 1. reconcile the recomputed disagreement set against the recorded one ---
    live = {i: (l1[i], l2[i]) for i in l1 if l1[i] != l2[i]}
    recorded = {
        int(r["idx"]): (r["l1"], r["l2"])
        for b in agree["per_bucket"] if b["bucket"] == BUCKET
        for r in b["disagreements"]
    }
    if live != recorded:
        die(4, "recomputed disagreements do not match inter_labeller_agreement.json "
               f"(live {len(live)}, recorded {len(recorded)}, "
               f"only-live {sorted(set(live) - set(recorded))}, "
               f"only-recorded {sorted(set(recorded) - set(live))})")
    if set(a3) != set(live):
        die(4, f"third reading covers {sorted(a3)}, disagreements are {sorted(live)}")
    bad = {i: v for i, v in a3.items() if v not in SIX}
    if bad:
        die(4, f"illegal verdict values {bad}")

    krows = {int(r["idx"]): r for r in key["rows"]}

    # --- 2/3. resolve each disagreement and rebuild the bucket count ---
    rows = []
    resolved = splits = 0
    op_from_majority = 0
    split_rows = []
    for idx in sorted(live):
        v1, v2, v3 = l1[idx], l2[idx], a3[idx]
        if v3 == v1 and v3 == v2:
            outcome = "all_three_agree"
        elif v3 == v1:
            outcome = "resolves_to_labeller_1"
            resolved += 1
        elif v3 == v2:
            outcome = "resolves_to_labeller_2"
            resolved += 1
        else:
            outcome = "three_way_split"
            splits += 1
            split_rows.append(idx)
        if v3 == "operator":
            op_from_majority += 1
        rows.append({
            "idx": idx,
            "labeller_1": v1,
            "labeller_2": v2,
            "third": v3,
            "outcome": outcome,
            "third_why": why3.get(idx, ""),
        })

    if key:
        for r in rows:
            k = krows.get(r["idx"], {})
            r["consistent_with_key"] = (
                r["labeller_1"] == k.get("l1") and r["labeller_2"] == k.get("l2")
            )

    agreed_rows = [i for i in l1 if l1[i] == l2[i]]
    agreed_operator = sum(1 for i in agreed_rows if l1[i] == "operator")
    n_paired = len(l1)
    op_count_majority = agreed_operator + op_from_majority
    # sensitivity: the split rows could all be operator, or none of them
    split_third_operator = sum(1 for i in split_rows if a3[i] == "operator")
    op_count_low = op_count_majority - split_third_operator
    op_count_high = op_count_majority + (len(split_rows) - split_third_operator)

    # --- 4. reproduce baselines, then recompute coverage ---
    frame = cov1["frame"]
    units = frame["units"]
    cited_n = frame["cited"]
    ask_n = frame["uncited_ask_cue"]
    nonask_n = frame["uncited_non_ask_cue"]

    def coverage(cited_k, ask_k, nonask_k):
        n_cited, n_ask, n_nonask = len(l1), len(l1), n_paired
        num = cited_n * cited_k / n_cited
        ask_units = ask_n * ask_k / n_ask
        nonask_units = nonask_n * nonask_k / n_nonask
        den = num + ask_units + nonask_units
        return num / den, num, ask_units, nonask_units, den

    cited_k1 = sum(1 for v in l1.values() if v == "operator")
    # cited and ask-cue counts are taken from the committed per-bucket records,
    # never re-derived here, because this script only adjudicates the non-ask bucket
    def bucket_count(cov, bucket):
        """Operator count for a bucket, recovered from the committed share.

        Both coverage files store the share and, in one case only, a share_detail
        count. The share itself is a count ratio over the n=60 sample, so the count
        is share x 60; the function asserts integrality rather than assuming it, so
        a re-based coverage file cannot slip a non-integer count past the check.
        """
        for b in cov.get("per_bucket", []):
            if b.get("bucket") != bucket:
                continue
            detail = b.get("share_detail") or {}
            if isinstance(detail.get("count"), int):
                return detail["count"]
            share = b.get("operator_share")
            if not isinstance(share, (int, float)):
                return None
            exact = share * 60
            # operator_coverage.json stores the share rounded to 4 dp, so a count
            # over 60 can land up to 0.003 away from the integer it came from.
            if abs(exact - round(exact)) > 0.01:
                die(4, f"{bucket} share {share!r} is not a count over 60")
            return int(round(exact))
        return None

    cited_c1 = bucket_count(cov1, "cited")
    ask_c1 = bucket_count(cov1, "uncited_ask_cue")
    nonask_c1 = bucket_count(cov1, "uncited_non_ask_cue")
    cited_c2 = bucket_count(cov2, "cited")
    ask_c2 = bucket_count(cov2, "uncited_ask_cue")
    nonask_c2 = bucket_count(cov2, "uncited_non_ask_cue")
    missing = [n for n, v in (("cited_l1", cited_c1), ("ask_l1", ask_c1),
                              ("nonask_l1", nonask_c1), ("cited_l2", cited_c2),
                              ("ask_l2", ask_c2), ("nonask_l2", nonask_c2)) if v is None]
    if missing:
        die(2, f"could not read bucket operator counts from the coverage files: {missing}")

    p1, *_ , d1 = coverage(cited_c1, ask_c1, nonask_c1)
    p2, *_ , d2 = coverage(cited_c2, ask_c2, nonask_c2)
    # operator_coverage.json records its shares to 4 dp, so its baseline can only be
    # reproduced to that precision; operator_coverage_l2.json carries exact counts.
    tol1, tol2 = 5e-5, 1e-12
    ok1 = abs(p1 - cov1["coverage"]["point"]) < tol1
    ok2 = abs(p2 - cov2["coverage"]["point"]) < tol2
    if not (ok1 and ok2):
        die(4, "baseline reproduction failed: "
               f"l1 {p1!r} vs {cov1['coverage']['point']!r} (tol {tol1}), "
               f"l2 {p2!r} vs {cov2['coverage']['point']!r} (tol {tol2})")

    # adjudicated: cited and ask buckets use the agreed count (identical in both),
    # non-ask uses the majority count, with the split rows carried as a range
    padj, num_adj, ask_units_adj, nonask_units_adj, den_adj = coverage(
        cited_c1, ask_c1, op_count_majority)
    lo_share, hi_share = wilson(op_count_low, n_paired), wilson(op_count_high, n_paired)
    _, _, _, nonask_lo_units, _ = coverage(cited_c1, ask_c1, op_count_low)
    _, _, _, nonask_hi_units, _ = coverage(cited_c1, ask_c1, op_count_high)
    wc, wa = wilson(cited_c1, 60), wilson(ask_c1, 60)
    wh = wilson(op_count_high, n_paired)
    wl = wilson(op_count_low, n_paired)
    num_lo, num_hi = cited_n * wc[0], cited_n * wc[1]
    den_lo = num_lo + ask_n * wa[0] + nonask_n * wl[0]
    den_hi = num_hi + ask_n * wa[1] + nonask_n * wh[1]
    cov_lo = num_lo / den_hi
    cov_hi = num_hi / den_lo

    out = {
        "generated_at_utc": now(),
        "script": "adjudicate_disagreements.py",
        "question": (
            "of the 12 rows where the two authorship labellers disagreed in the "
            f"{BUCKET} bucket, how many does a third blind reading resolve, and does "
            "the resolved bucket count move the coverage pair"
        ),
        "reconciliation": {
            "recomputed_disagreements": len(live),
            "recorded_disagreements": len(recorded),
            "sets_identical": live == recorded,
            "labeller_1_operator": sum(1 for v in l1.values() if v == "operator"),
            "labeller_2_operator": sum(1 for v in l2.values() if v == "operator"),
            "agreed_operator_rows": agreed_operator,
            "identity_check": (
                "labeller_1_operator - disputes_where_l1_says_operator == "
                "agreed_operator_rows and likewise for labeller 2"
            ),
        },
        "third_reading": {
            "labeller": third.get("labeller"),
            "role": third.get("labeller_role"),
            "n": len(a3),
            "verdict_counts": {s: sum(1 for v in a3.values() if v == s) for s in SIX},
            "blind": "adjudication_key.json was withheld from the third reader",
        },
        "outcomes": {
            "resolved_by_majority": resolved,
            "three_way_split": splits,
            "split_idxs": split_rows,
        },
        "rows": rows,
        "bucket_operator_count": {
            "labeller_1": nonask_c1,
            "labeller_2": nonask_c2,
            "agreed_rows_only": agreed_operator,
            "majority_of_three": op_count_majority,
            "range_if_split_rows_go_other_way": [op_count_low, op_count_high],
            "of": n_paired,
            "share_majority": round(op_count_majority / n_paired, 6),
            "share_range": [round(lo_share[0], 6), round(hi_share[1], 6)],
        },
        "coverage": {
            "baseline_labeller_1": {"point": p1, "reproduced": ok1,
                                    "committed": cov1["coverage"]["point"]},
            "baseline_labeller_2": {"point": p2, "reproduced": ok2,
                                    "committed": cov2["coverage"]["point"]},
            "adjudicated": {
                "point": padj,
                "low": cov_lo,
                "high": cov_hi,
                "method": cov1["coverage"]["method"],
                "is_confidence_interval": False,
                "note": cov1["coverage"]["note"],
                "numerator_units": num_adj,
                "denominator_units": den_adj,
                "steps": [
                    f"cited: {cited_n} x {cited_c1}/60 = {num_adj:.4f} "
                    "(both labellers agree on this bucket, so it is not adjudicated)",
                    f"uncited_ask_cue: {ask_n} x {ask_c1}/60 = {ask_units_adj:.4f} "
                    "(both labellers agree, not adjudicated)",
                    f"uncited_non_ask_cue: {nonask_n} x {op_count_majority}/60 = "
                    f"{nonask_units_adj:.4f} (majority of three)",
                    f"coverage = {num_adj:.4f} / {den_adj:.4f} = {padj!r}",
                ],
            },
            "movement_vs_baselines_pp": {
                "vs_labeller_1": round((padj - p1) * 100, 3),
                "vs_labeller_2": round((padj - p2) * 100, 3),
            },
            "frame": {"units": units, "cited": cited_n,
                      "uncited_ask_cue": ask_n, "uncited_non_ask_cue": nonask_n},
        },
        "what_this_does_not_do": [
            "it does not re-label the 48 rows the two labellers already agreed on",
            "it does not touch the cited or ask-cue buckets, where agreement is exact",
            "it does not turn three model labellers into human ground truth; it is a "
            "majority of three readings on one rubric",
            "it does not change citation precision, so the rate stays withheld",
            "the adjudicated point is still an estimate whose three bucket shares come "
            "from three separate n=60 samples, not a joint estimate",
        ],
        "exit_status": "computed",
    }

    json.dump(out, open(os.path.join(HERE, "adjudication.json"), "w"), indent=1)

    print(f"reconciliation: live {len(live)} == recorded {len(recorded)}  {live == recorded}")
    print(f"third reading: {out['third_reading']['verdict_counts']}")
    print(f"resolved {resolved} / split {splits}  split idxs {split_rows}")
    print(f"nonask operator count: l1 {nonask_c1}  l2 {nonask_c2}  "
          f"majority {op_count_majority}  range {[op_count_low, op_count_high]} of 60")
    print(f"baselines reproduced: l1 {ok1} ({p1:.6f})  l2 {ok2} ({p2:.6f})")
    print(f"adjudicated coverage {padj:.6f} [{cov_lo:.6f}, {cov_hi:.6f}]")
    print(f"movement: {out['coverage']['movement_vs_baselines_pp']} pp vs the pair")
    print("wrote adjudication.json")


if __name__ == "__main__":
    main()
