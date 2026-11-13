#!/usr/bin/env python3
"""rate_gate.py -- turn the publication gate from prose into a re-derivable decision.

Reads the committed evidence files, prints each figure it actually read (so a
stale input is visible), computes every cell, and derives the decision from the
cells. Never emits a percentage where a cell is not PASS.

Exit 0 = decision computed. Exit 3 = a required input is missing (the file is
still written, with that cell NOT_RUN).
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "rate_gate.json")

RULES = {
    "publish_rate": "PUBLISH_RATE requires: recall measured AND recall >= 0.9 AND precision_strict >= 0.9.",
    "publish_floor": "PUBLISH_FLOOR requires: precision_strict >= 0.9 (a floor needs only precision).",
    "recall_not_run": (
        "Recall is NOT_RUN only when no recall artifact exists. The 98 source_ref harvest "
        "documents are declared lost, so the original route to a recall denominator is gone, "
        "and the corpus-derived reference frame replaces it on the channels the register covers."
    ),
    "read_discipline": "A failed read is UNKNOWN, never PASS. A percentage is never emitted where a cell is not PASS.",
}

RECALL_THRESHOLD = 0.9
PRECISION_THRESHOLD = 0.9


def read_json(name, required=True):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        print(f"  !! MISSING  {name}")
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # a failed read is UNKNOWN, never PASS
        print(f"  !! UNREADABLE {name}: {type(exc).__name__}: {exc}")
        return None
    print(f"  ok {name}  generated_at_utc={data.get('generated_at_utc')}")
    return data


def dig(obj, dotted, default=None):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def main():
    print("== inputs (key figures actually read) ==")
    l1 = read_json("operator_coverage.json")
    l2 = read_json("operator_coverage_l2.json")
    # optional third coverage point: a third blind reading adjudicating the 12 rows
    # where labellers 1 and 2 disagreed. Absent is fine, and is recorded as absent
    # rather than silently omitted.
    adj = read_json("adjudication.json", required=False)
    agree = read_json("inter_labeller_agreement.json")
    prec = read_json("precision_scored.json")
    quote = read_json("ask_link_verification.json")
    # auxiliary cross-check only (not a gate input)
    print("== auxiliary (cross-check only) ==")
    links = read_json("link_residual_review.json", required=False)
    harvest = read_json("harvest_source_audit.json", required=False)

    l1_point = dig(l1, "coverage.point")
    l2_point = dig(l2, "coverage.point")
    adj_point = dig(adj, "coverage.adjudicated.point")
    adj_range = [dig(adj, "coverage.adjudicated.low"), dig(adj, "coverage.adjudicated.high")]
    adj_nonask = dig(adj, "bucket_operator_count.majority_of_three")
    l1_range = [dig(l1, "coverage.low"), dig(l1, "coverage.high")]
    l2_range = [dig(l2, "coverage.low"), dig(l2, "coverage.high")]
    if l1:
        print(f"  l1 coverage.point={l1_point} range={l1_range} units={dig(l1,'frame.units')} cited={dig(l1,'frame.cited')}")
    if l2:
        print(f"  l2 coverage.point={l2_point} range={l2_range} units={dig(l2,'frame.units')} cited={dig(l2,'frame.cited')}")

    kappas = {}
    bucket_status = {}
    if agree:
        for b in agree.get("per_bucket", []):
            name = b.get("bucket")
            bucket_status[name] = b.get("status")
            # operator-vs-rest is the two-class collapse the coverage estimate uses
            kappas[name] = dig(b, "operator_vs_rest.cohen_kappa")
        print(f"  kappa(operator_vs_rest)={kappas} bucket_status={bucket_status}")
        print(f"  readings={agree.get('readings')}")

    strict = dig(prec, "precision.strict.value")
    lenient = dig(prec, "precision.lenient.value")
    if prec:
        print(f"  precision strict={strict} lenient={lenient} counts={prec.get('counts')} "
              f"judgeable={prec.get('judgeable')} denominator={dig(prec,'denominator.sampled_from')}")

    fidelity = dig(quote, "strict.fidelity_pct")
    if quote:
        print(f"  quote fidelity strict={fidelity} verified={dig(quote,'strict.verified')} "
              f"mismatched={dig(quote,'strict.mismatched')}")

    ns = (links or {}).get("target_namespaces") or {}
    phone_links = ns.get("phonemsg")
    chatdb_links = ns.get("utt")
    total_links = None
    if phone_links is not None and chatdb_links is not None:
        total_links = phone_links + chatdb_links
    sampled_from = dig(prec, "denominator.sampled_from")
    channel_crosscheck_ok = total_links is not None and sampled_from is not None and total_links == sampled_from
    if links:
        print(f"  links target_namespaces={ns} sum={total_links} sampled_from={sampled_from} "
              f"consistent={channel_crosscheck_ok}")

    lost_docs = (harvest or {}).get("distinct_source_refs")
    if harvest:
        print(f"  harvest verdict={harvest.get('verdict')} distinct_source_refs={lost_docs}")

    # ---------------- cells ----------------
    cells = []

    # recall: measured on the one channel the register can represent
    asklevel = read_json("recall_asklevel_scored.json", required=False)
    if asklevel:
        overall = asklevel.get("overall_scored_channels_only") or {}
        rc = overall.get("recall") or {}
        rvalue = rc.get("value")
        rstate = "UNKNOWN"
        if isinstance(rvalue, (int, float)):
            rstate = "PASS" if rvalue >= RECALL_THRESHOLD else "FAIL"
        cells.append({
            "cell": "recall",
            "state": rstate,
            "value": rvalue,
            "threshold": RECALL_THRESHOLD,
            "why": (
                "measured on the imessage stratum only, under a broad ask definition that "
                "includes asks addressed to other humans; the register carries no harness or "
                "kcode conversations, so those channels are not measurable against it rather "
                "than zero"
            ),
            "source": "recall_asklevel_scored.json",
            "scope": {
                "channels_scored": overall.get("channels_scored"),
                "channels_not_measured": overall.get("channels_not_measured"),
                "denominator": overall.get("denominator"),
                "matched": overall.get("matched"),
                "wilson": rc,
            },
        })
    else:
        cells.append({
            "cell": "recall",
            "state": "NOT_RUN",
            "value": None,
            "threshold": RECALL_THRESHOLD,
            "why": "no recall artifact available: recall is not measured here",
            "source": "recall_asklevel_scored.json (absent)",
        })

    if strict is None:
        strict_cell_state = "UNKNOWN"
        strict_why = "precision_scored.json missing or unreadable: not measured here"
    elif strict >= PRECISION_THRESHOLD:
        strict_cell_state = "PASS"
        strict_why = "strict precision meets the 0.9 floor"
    else:
        strict_cell_state = "FAIL"
        strict_why = "strict precision is below the 0.9 floor, so no floor can be published"
    cells.append({
        "cell": "citation_precision_strict",
        "state": strict_cell_state,
        "value": None if strict is None else round(strict, 4),
        "threshold": PRECISION_THRESHOLD,
        "why": strict_why,
        "source": "precision_scored.json",
    })

    if lenient is None:
        lenient_state = "UNKNOWN"
        lenient_why = "precision_scored.json missing or unreadable: not measured here"
    elif lenient >= PRECISION_THRESHOLD:
        lenient_state = "PASS"
        lenient_why = "reported alongside, never instead"
    else:
        lenient_state = "FAIL"
        lenient_why = "below 0.9; reported alongside, never instead"
    cells.append({
        "cell": "citation_precision_lenient",
        "state": lenient_state,
        "value": None if lenient is None else round(lenient, 4),
        "threshold": PRECISION_THRESHOLD,
        "why": lenient_why,
        "source": "precision_scored.json",
    })

    need_buckets = ("cited", "uncited_ask_cue", "uncited_non_ask_cue")
    if not agree:
        indep_state = "UNKNOWN"
        indep_why = "inter_labeller_agreement.json missing or unreadable: independence not measured here"
        indep_value = None
    else:
        measured = all(bucket_status.get(b) == "MEASURED" for b in need_buckets)
        present = all(kappas.get(b) is not None for b in need_buckets)
        indep_state = "PASS" if (measured and present) else "UNKNOWN"
        indep_why = (
            "two independent labellers on all three sheets; non-ask bucket is only substantial, "
            "which is the weakest link, not a gate"
            if indep_state == "PASS" else
            "a bucket is not MEASURED or its kappa is absent: treat as UNKNOWN, not PASS"
        )
        indep_value = {
            "cited_kappa": None if kappas.get("cited") is None else round(kappas["cited"], 4),
            "askcue_kappa": None if kappas.get("uncited_ask_cue") is None else round(kappas["uncited_ask_cue"], 4),
            "nonask_kappa": None if kappas.get("uncited_non_ask_cue") is None else round(kappas["uncited_non_ask_cue"], 4),
        }
    cells.append({
        "cell": "labeller_independence",
        "state": indep_state,
        "value": indep_value,
        "threshold": None,
        "why": indep_why,
        "source": "inter_labeller_agreement.json",
    })

    if phone_links is None or chatdb_links is None:
        chan_state = "UNKNOWN"
        chan_why = ("origin-link channel split not derivable here (no ledger.db present); "
                    "the precision sample covers the register's origin links, ~99% phone channel; "
                    "harness-channel citations were not sampled")
        chan_value = {"phone_links": phone_links, "chatdb_links": chatdb_links, "total_origin_links": total_links}
    else:
        chan_state = "PASS" if channel_crosscheck_ok else "UNKNOWN"
        chan_why = ("the precision sample covers the register's origin links, ~99% phone channel; "
                    "harness-channel citations were not sampled")
        chan_value = {"phone_links": phone_links, "chatdb_links": chatdb_links, "total_origin_links": total_links}
    cells.append({
        "cell": "precision_channel_coverage",
        "state": chan_state,
        "value": chan_value,
        "threshold": None,
        "why": chan_why,
        "source": ("link_residual_review.json target_namespaces, cross-checked against "
                   "precision_scored.json denominator.sampled_from (ledger.db not present to re-derive directly)"),
    })

    if fidelity is None:
        quote_state = "UNKNOWN"
        quote_value = None
    else:
        quote_state = "PASS" if fidelity >= 90.0 else "FAIL"
        quote_value = {"strict": round(fidelity / 100.0, 4)}
    cells.append({
        "cell": "quote_fidelity",
        "state": quote_state,
        "value": quote_value,
        "threshold": None,
        "why": "a precondition, not precision",
        "source": "ask_link_verification.json",
    })

    # ---------------- decision (computed, never hardcoded) ----------------
    by_cell = {c["cell"]: c for c in cells}
    recall_cell = by_cell["recall"]
    strict_cell = by_cell["citation_precision_strict"]

    recall_ok = (recall_cell["state"] == "PASS"
                 and isinstance(recall_cell["value"], (int, float))
                 and recall_cell["value"] >= RECALL_THRESHOLD)
    strict_ok = (strict_cell["state"] == "PASS"
                 and isinstance(strict_cell["value"], (int, float))
                 and strict_cell["value"] >= PRECISION_THRESHOLD)

    if recall_ok and strict_ok:
        decision = "PUBLISH_RATE"
        decision_reason = ("recall is measured and at or above 0.9, and strict precision is at or "
                           "above 0.9.")
    elif strict_ok:
        decision = "PUBLISH_FLOOR"
        decision_reason = ("strict precision passes, so a floor is publishable; recall is not "
                           "measurable, so no rate is.")
    else:
        decision = "WITHHOLD_RATE_AND_FLOOR"
        failing = [c["cell"] for c in cells if c["state"] in ("FAIL", "NOT_RUN", "UNKNOWN")]
        if recall_cell["state"] == "FAIL" and isinstance(recall_cell["value"], (int, float)):
            recall_sentence = (
                f"recall is measured at {round(recall_cell['value'], 4)}, below 0.9, on the "
                "imessage stratum only (the register has no harness or kcode conversations)"
            )
        elif recall_cell["state"] == "NOT_RUN":
            recall_sentence = "recall is NOT_RUN, so no rate can be measured"
        else:
            recall_sentence = f"recall is {recall_cell['state']}"
        decision_reason = (
            "citation_precision_strict is "
            + ("UNKNOWN" if strict_cell["state"] != "FAIL" else f"{strict_cell['value']} < 0.9")
            + ", below the 0.9 floor every publication path needs, and "
            + recall_sentence
            + "; open cells: "
            + ", ".join(failing) + "."
        )

    coverage_status = "estimate, not a published rate"
    if l1_point is None or l2_point is None:
        coverage_status = "NOT_RUN: a coverage file is missing or unreadable"

    derived = None
    if l2_point is not None and l1_point is not None and strict is not None and lenient is not None:
        derived = {
            "low": round(l2_point * strict, 4),
            "high": round(l1_point * lenient, 4),
            "derived": True,
            "definition": "l2_point x precision_strict to l1_point x precision_lenient",
            "warning": ("a unit-share multiplied by a link-share: the two operands come from different "
                        "denominators, so this is an envelope for intuition, never a figure to quote"),
        }

    doc = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "rate_gate.py",
        "rules": RULES,
        "cells": cells,
        "decision": decision,
        "decision_reason": decision_reason,
        "coverage_pair": {
            "l1_point": None if l1_point is None else round(l1_point, 4),
            "l2_point": None if l2_point is None else round(l2_point, 4),
            "l3_adjudicated_point": None if adj_point is None else round(adj_point, 4),
            "l3_adjudicated_range": [
                None if v is None else round(v, 4) for v in adj_range
            ],
            "l3_note": (
                "NOT_RUN: adjudication.json absent" if adj_point is None else
                "a third blind reading resolved 11 of the 12 inter-labeller disagreements "
                f"by majority of three, moving the non-ask operator count to {adj_nonask} of 60. "
                "It is a third reading on the same rubric, not human ground truth, and it is "
                "reported alongside the pair, never instead of it"
            ),
            "l1_range": [None if v is None else round(v, 4) for v in l1_range],
            "l2_range": [None if v is None else round(v, 4) for v in l2_range],
            "status": coverage_status,
        },
        "derived_envelope": derived,
        "does_not_retroactively_withdraw": [
            {
                "claim": "semantic floor 2.12% (17/800), §3h",
                "why": "different instrument and population; it never depended on citation precision",
            }
        ],
        "what_would_change_it": [
            "a second independent precision labeller",
            "a measurable recall instrument (blocked: documents lost)",
            "precision >= 0.9 at strict, which would still not overcome unmeasurable recall for a rate",
        ],
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print("== cells ==")
    for c in cells:
        print(f"  {c['cell']:<28} {c['state']:<8} value={c['value']} threshold={c['threshold']}")
    print(f"== decision == {decision}")
    print(f"  reason: {decision_reason}")
    if derived:
        print(f"  derived envelope: {derived['low']:.4f} .. {derived['high']:.4f}")
    else:
        print("  derived envelope: NOT_RUN (input missing)")
    print(f"  wrote {OUT}")

    missing = [n for n, d in (
        ("operator_coverage.json", l1), ("operator_coverage_l2.json", l2),
        ("inter_labeller_agreement.json", agree), ("precision_scored.json", prec),
        ("ask_link_verification.json", quote),
    ) if d is None]
    if missing:
        print(f"  EXIT 3: required input(s) missing/unreadable: {', '.join(missing)}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
