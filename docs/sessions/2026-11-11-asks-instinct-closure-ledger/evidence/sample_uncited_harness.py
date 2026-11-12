#!/usr/bin/env python3
"""Bounded estimate: how much does strict-substring matching understate harness coverage?

A harness member is a whole prompt. A 3,000-character prompt containing ten asks is
one member and can receive only one citation, so the 1.5% harness figure measured by
substring citation is a FLOOR, not an estimate. This samples uncited members and
classifies them, to bound how much the floor misses.

Classification is MY judgement on the printed text, single coder, no second rater.
That makes the result an indicative bound, not a measured rate. It is labelled as
such wherever it is quoted.

Labels
  NEW_ASK    a genuine operator request that the register does not cite
  NOT_ASK    harness artifact: background-task echo, auto-nudge, synthetic probe,
             protocol envelope, recovered-session banner
  NOT_OPS    not operator intent: another agent's DM relayed into the session,
             or the operator quoting a peer's instruction
  ANSWER     a reply to the assistant, not a request
  AMBIGUOUS  too vague to classify from the text

Sample: 15 per length stratum, random.seed(11), strata short(<80), mid(80-399),
long(400+). Re-running reproduces the identical sample.
"""
from __future__ import annotations

import json
import random
import sys

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
sys.path.insert(0, BASE)
import union_channels as U  # noqa: E402

OUT = f"{BASE}/harness_uncited_sample.json"
LABELS = {
    # SHORT
    "S00": ("NOT_ASK", "auto-nudge text, not operator"),
    "S01": ("ANSWER", "response to an approval question"),
    "S02": ("ANSWER", "reply to the assistant"),
    "S03": ("NOT_ASK", "paste marker"),
    "S04": ("AMBIGUOUS", "'all met hroguh wy im needed'"),
    "S05": ("NEW_ASK", "use subagents heavily, fix the remaining 15"),
    "S06": ("NEW_ASK", "proceed and follow the best long-term path"),
    "S07": ("NEW_ASK", "search ~ at full depth for those files"),
    "S08": ("NEW_ASK", "pick the best choice (delegated decision)"),
    "S09": ("NEW_ASK", "what do you need from me"),
    "S10": ("NOT_ASK", "synthetic probe: reply with exactly m3head-ok"),
    "S11": ("NOT_OPS", "peer DM relayed: audit results for all 3 repos"),
    "S12": ("NEW_ASK", "what's next / what's left"),
    "S13": ("NEW_ASK", "async form/inbox entry, what's next"),
    "S14": ("NEW_ASK", "why don't you wake on agent complete"),
    # MID
    "M00": ("NEW_ASK", "worktree ordering: do not remove before merge"),
    "M01": ("NOT_ASK", "synthetic turn-24 probe"),
    "M02": ("NEW_ASK", "path to finish full-forward WBS, use subagents"),
    "M03": ("NOT_OPS", "peer DM relayed: full final report"),
    "M04": ("NEW_ASK", "measure/evaluate project using attached dossier"),
    "M05": ("NEW_ASK", "recovery checks for a worktree with deleted common dir"),
    "M06": ("NOT_ASK", "background-task completion echo"),
    "M07": ("NEW_ASK", "embed a prompt timeline in the html"),
    "M08": ("NOT_ASK", "background-task completion echo"),
    "M09": ("NOT_ASK", "background-task failure echo"),
    "M10": ("NEW_ASK", "define 5 acceptance checks, no live-pass claims"),
    "M11": ("NOT_OPS", "peer DM relayed: research report request"),
    "M12": ("NEW_ASK", "delete/move after full fold into phenoreg+phenoshared"),
    "M13": ("NOT_ASK", "background-task failure echo"),
    "M14": ("NOT_ASK", "recovered-from-crashed-session banner"),
    # LONG
    "L00": ("NOT_OPS", "peer DM relayed: full report to sauropod"),
    "L01": ("NOT_OPS", "status relay about civis PR and a rustsec advisory"),
    "L02": ("NOT_OPS", "coordination from lane B session"),
    "L03": ("NOT_OPS", "peer DM relayed: do not merge egl"),
    "L04": ("ANSWER", "work-node spec echoing a prior intent"),
    "L05": ("NOT_ASK", "background-task stalled echo"),
    "L06": ("NEW_ASK", "tracera repo worktree instruction"),
    "L07": ("NEW_ASK", "read-only provenance check via gh api, max 4 commands"),
    "L08": ("NOT_OPS", "peer ack and self-correction report"),
    "L09": ("NEW_ASK", "phenotype-landing only, preserve others' edits"),
    "L10": ("NOT_OPS", "peer DM relayed: single-character fix report"),
    "L11": ("NEW_ASK", "portfolio full redesign iteration 1"),
    "L12": ("NOT_ASK", "harness protocol envelope (question reply)"),
    "L13": ("NOT_ASK", "background-task completion echo"),
    "L14": ("NEW_ASK", "independent review of artifact.js changes"),
}


def main() -> int:
    reg = json.load(open(U.REGISTER))["records"]
    quotes = [U.norm(r.get("quote") or "") for r in reg]
    quotes = [q for q in quotes if len(q) >= 12]
    H, _ = U.harness()
    uncited = [h for h in H if not any(q in h for q in quotes)]
    short = [h for h in uncited if len(h) < 80]
    mid = [h for h in uncited if 80 <= len(h) < 400]
    long_ = [h for h in uncited if len(h) >= 400]
    random.seed(11)
    buckets = [("S", random.sample(short, 15)),
               ("M", random.sample(mid, 15)),
               ("L", random.sample(long_, 15))]

    rows = []
    for tag, bucket in buckets:
        for i, text in enumerate(bucket):
            key = f"{tag}{i:02d}"
            label, why = LABELS.get(key, ("UNLABELLED", ""))
            rows.append({"id": key, "chars": len(text), "label": label,
                         "reason": why, "excerpt": text[:200]})

    from collections import Counter
    tally = Counter(r["label"] for r in rows)
    n = len(rows)
    new_ask = tally["NEW_ASK"]
    print(f"sample n={n}  {dict(tally)}")
    print(f"NEW_ASK share of uncited: {new_ask}/{n} = {new_ask/n*100:.1f}%")

    cited = len(H) - len(uncited)
    lo = cited / len(H) * 100
    est_new = new_ask / n * len(uncited)
    hi = cited / (cited + est_new) * 100
    print(f"harness coverage floor (strict substring) : {cited}/{len(H)} = {lo:.2f}%")
    print(f"implied uncited NEW_ASK members           : {est_new:.0f}")
    print(f"harness coverage if all NEW_ASK are unseen: {hi:.2f}%  (upper bound)")

    not_ops = tally["NOT_ASK"] + tally["NOT_OPS"] + tally["ANSWER"]
    print(f"\ncorpus contamination: {not_ops}/{n} = {not_ops/n*100:.1f}% of uncited "
          f"members are not operator requests")

    json.dump({
        "sample_n": n, "seed": 11, "strata": "15 per bucket, short<80 / mid 80-399 / long 400+",
        "tally": dict(tally),
        "new_ask_share_pct": round(new_ask / n * 100, 1),
        "harness_distinct": len(H), "harness_cited": cited,
        "coverage_floor_pct": round(lo, 2),
        "coverage_upper_pct": round(hi, 2),
        "implied_uncited_new_asks": round(est_new),
        "contamination_pct": round(not_ops / n * 100, 1),
        "caveat": "single coder, judgement-based; indicative bound, not a measured rate",
        "rows": rows,
    }, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
