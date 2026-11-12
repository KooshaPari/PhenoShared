#!/usr/bin/env python3
"""Build a BLIND third-reading sheet for the 12 inter-labeller disagreements.

Why: the published coverage pair (8.07-8.47%) is not driven only by the ask-cue
bucket. Its denominator adds `uncited_non_ask_cue x operator_share`, and that is
precisely the bucket where the two labellers disagree (12 of 60, 10 of which
involve `operator` on one side only). So the pair moves with these 12 rows and a
third reading is worth doing rather than merely listing.

What this script does NOT do: it never writes either labeller's value into the
sheet. `nonask_speaker_key.json` (which holds labeller_1's value, and the channel)
is deliberately not read. The only thing carried across is each row's own clause
text, so the third reader judges words, not votes.

Inputs : nonask_speaker_sheet.json        (clause text, idx)
         inter_labeller_agreement.json    (which idx disagreed; labels discarded)
Output : adjudication_sheet.json          (idx, clause, verdict=null, why="")
         adjudication_key.json            (idx -> l1, l2, and whether each said
                                           operator; withheld from the reader)

Seed: none. The population is the exhaustive disagreement set, not a sample, so
there is nothing to randomise.

Exit codes: 0 written, 2 input missing, 4 disagreement/idx mismatch.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

RUBRIC = (
    "verdict is exactly one of: operator = Koosha's own words (an instruction, "
    "question, ruling, correction, plan, or remark addressed to an agent), including "
    "voice transcription, typos and relayed messages; agent = an AI agent's narration, "
    "plan, self-report, or instruction to another agent, including agent text pasted "
    "inside a human turn; tool = raw tool output, diff, log line, JSON blob, file "
    "listing; system = harness banner, injected prompt, skill or config block, or a "
    "metadata/transcript header with no human voice; peer = a third person's words "
    "(sender header, forwarded or quoted message); other = truly unresolvable. "
    "Judge the words only. Do not default to operator: if there is no human voice in "
    "the clause, it is not operator."
)

CLAUSE_CHARS = 500


def die(code, msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    sheet_path = os.path.join(HERE, "nonask_speaker_sheet.json")
    agree_path = os.path.join(HERE, "inter_labeller_agreement.json")
    for p in (sheet_path, agree_path):
        if not os.path.exists(p):
            die(2, f"missing input {os.path.basename(p)}")

    sheet = json.load(open(sheet_path))
    agree = json.load(open(agree_path))

    items = sheet.get("items") or sheet.get("rows")
    if not items:
        die(2, "nonask_speaker_sheet.json has no items/rows")
    by_idx = {int(it["idx"]): it for it in items}

    bucket = None
    for b in agree["per_bucket"]:
        if b["bucket"] == "uncited_non_ask_cue":
            bucket = b
    if bucket is None:
        die(2, "inter_labeller_agreement.json has no uncited_non_ask_cue bucket")
    dis = bucket["disagreements"]
    if not dis:
        die(4, "no disagreements recorded, nothing to adjudicate")

    rows, key = [], []
    seen = set()
    for r in dis:
        idx = int(r["idx"])
        if idx in seen:
            die(4, f"duplicate idx {idx} in disagreements")
        seen.add(idx)
        it = by_idx.get(idx)
        if it is None:
            die(4, f"disagreement idx {idx} is not in the sheet")
        clause = it.get("clause") or it.get("text") or ""
        rows.append({
            "idx": idx,
            "clause": clause[:CLAUSE_CHARS],
            "verdict": None,
            "why": "",
        })
        key.append({
            "idx": idx,
            "l1": r["l1"],
            "l2": r["l2"],
            "l1_said_operator": r["l1"] == "operator",
            "l2_said_operator": r["l2"] == "operator",
        })

    rows.sort(key=lambda x: x["idx"])
    key.sort(key=lambda x: x["idx"])

    out = {
        "generated_at_utc": now(),
        "script": "make_adjudication_sheet.py",
        "purpose": (
            "third, blind reading of the 12 rows where the two labellers disagreed in the "
            "uncited_non_ask_cue bucket, the bucket whose operator share drives the "
            "coverage denominator"
        ),
        "seed": None,
        "sampling": "exhaustive over the disagreement set, not a sample",
        "n": len(rows),
        "population": {
            "bucket": "uncited_non_ask_cue",
            "paired_rows": bucket.get("n_paired"),
            "disagreements": len(rows),
            "involving_operator": sum(
                1 for k in key if k["l1_said_operator"] != k["l2_said_operator"]
            ),
            "source_sheet": "nonask_speaker_sheet.json",
            "source_agreement": "inter_labeller_agreement.json",
        },
        "instructions": RUBRIC,
        "items": rows,
    }
    keyout = {
        "generated_at_utc": now(),
        "script": "make_adjudication_sheet.py",
        "note": "withheld from the third reader; contains both earlier labellers' values",
        "rows": key,
    }

    json.dump(out, open(os.path.join(HERE, "adjudication_sheet.json"), "w"), indent=1)
    json.dump(keyout, open(os.path.join(HERE, "adjudication_key.json"), "w"), indent=1)

    # Assertions: no labeller value leaked into the sheet.
    leaked = [r["idx"] for r in rows if r.get("verdict") is not None or r.get("why")]
    assert not leaked, leaked
    blob = json.dumps(out)
    for v in ("labeller_1", "labeller_2", "l1", "l2", "operator_share"):
        assert v not in blob, f"leaked key {v}"

    print(f"rows {len(rows)}  involving_operator {out['population']['involving_operator']}")
    print(f"idx {rows[0]['idx']}..{rows[-1]['idx']}")
    print("leak check: no labels in adjudication_sheet.json")
    print("wrote adjudication_sheet.json + adjudication_key.json")


if __name__ == "__main__":
    main()
