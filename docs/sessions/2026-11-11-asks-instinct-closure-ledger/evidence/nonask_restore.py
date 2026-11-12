#!/usr/bin/env python3
"""Restore the non-ask-cue label sheet after a destructive re-run, and attach channel provenance.

WHAT HAPPENED. Pass-1 labels were hand-written into `nonask_label_sheet.json`. Re-running
`nonask_probe.py` to fix a redaction bug regenerated that file and overwrote them. The probe emits a
fresh sheet by design, so this was self-inflicted, not a tool fault. Two facts make a faithful
restoration possible:

  * the sample is deterministic (`seed=20261114`, embedding cache hit), so the same 60 clauses come back
    in the same order;
  * `nonask_scored.json` was preserved from the pass-1 run and records every capture with its idx,
    ask id, rank, cosine, speaker and reason, plus the aggregate label counts.

So the five graded captures are restored from that record, NOT re-judged. The remaining 55 items are
`N` because the preserved counts are M=2, W=3, N=55 and the preserved `captures` array holds exactly
five entries - the arithmetic leaves no room for a sixth judgement.

WHAT IS LOST. Pass-1 per-item speaker attribution. Its aggregate survives (32 agent, 15 operator,
5 system, 4 peer, 2 tool, 2 other) but the item-to-speaker mapping does not. This script therefore
records a second, independent speaker pass (`speaker_pass2`) and keeps the pass-1 aggregate in
`speaker_pass1_aggregate_lost` with its provenance, so the discrepancy is visible rather than smoothed.
Nothing is copied from the aggregate into the per-item field.

CHANNEL IS THE OBJECTIVE PART. `channel` is derived, not judged: the probe's own population build is
re-run here keeping a unit -> channels map, so each sampled clause reports which export it came from.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, "nonask_label_sheet.json")
PRESERVED = os.path.join(HERE, "nonask_pass1_preserved.json")

import union_channels as U          # noqa: E402
import segment_units as SEG         # noqa: E402

# Second speaker pass. `operator` = Koosha's own words, including text relayed through the instinct
# bridge or quoted with a `| koosha |` / `| instinct |` timestamp header. `agent` = an AI agent's
# narration, report, plan, or instruction to another agent. `peer` = a third-party DM. `tool` = raw
# tool output. `system` = harness banner, config block, or injected prompt. `other` = unresolvable.
SPEAKER_PASS2 = {
    0: "agent", 1: "agent", 2: "agent", 3: "operator", 4: "agent", 5: "tool",
    6: "operator", 7: "agent", 8: "agent", 9: "agent", 10: "system", 11: "agent",
    12: "system", 13: "operator", 14: "operator", 15: "operator", 16: "agent", 17: "operator",
    18: "agent", 19: "operator", 20: "agent", 21: "agent", 22: "operator", 23: "operator",
    24: "operator", 25: "agent", 26: "tool", 27: "agent", 28: "operator", 29: "operator",
    30: "agent", 31: "peer", 32: "system", 33: "agent", 34: "agent", 35: "operator",
    36: "agent", 37: "operator", 38: "agent", 39: "operator", 40: "operator", 41: "operator",
    42: "tool", 43: "peer", 44: "agent", 45: "operator", 46: "peer", 47: "system",
    48: "agent", 49: "operator", 50: "operator", 51: "operator", 52: "agent", 53: "agent",
    54: "agent", 55: "operator", 56: "agent", 57: "agent", 58: "agent", 59: "operator",
}


def channel_map() -> dict[str, list[str]]:
    """unit -> sorted list of channels it occurs in, using the probe's own population build."""
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]
    H, _ = U.harness()
    members = {"harness": H,
               "imessage": {x for x in U.imessage() if U.keep(x)},
               "kcode": {x for x in U.kcode()[0] if U.keep(x)},
               "phone": U.phone()}
    where: dict[str, set[str]] = {}
    for name, ms in members.items():
        for m in ms:
            for u in SEG.segment(m):
                where.setdefault(u, set()).add(name)
    return {u: sorted(v) for u, v in where.items()}


def main() -> int:
    sheet = json.load(open(SHEET))
    preserved = json.load(open(PRESERVED))
    cap = {c["idx"]: c for c in preserved["captures"]}

    where = channel_map()
    missing = []
    for it in sheet["items"]:
        idx = it["idx"]
        it["channel"] = where.get(it["clause"], [])
        if not it["channel"]:
            missing.append(idx)
        it["speaker_pass2"] = SPEAKER_PASS2.get(idx, "other")
        if idx in cap:
            c = cap[idx]
            it["grade"] = c["grade"]
            it["captured_by"] = c["ask"]
            it["why"] = c["why"]
        else:
            it["grade"] = "N"
            it["captured_by"] = "NONE"
            it["why"] = "no candidate expresses the same intent (adjacent-but-different treated as none)"

    sheet["labeller"] = preserved["labeller"]
    sheet["labelled_at_utc"] = preserved["labelled_at_utc"]
    sheet["restored_at_utc"] = preserved["restored_at_utc"]
    sheet["restore_note"] = (
        "pass-1 labels were overwritten by re-running nonask_probe.py; the five graded captures are "
        "restored from nonask_pass1_preserved.json (not re-judged) and the 55 N assignments are forced "
        "by the preserved counts M=2/W=3/N=55. Per-item speaker attribution from pass 1 is LOST; "
        "speaker_pass2 is an independent second pass and its aggregate differs from pass 1's."
    )
    sheet["speaker_pass1_aggregate_lost"] = preserved["by_speaker"]
    sheet["channel_rule"] = ("derived, not judged: the sampled clause is looked up in the probe's own "
                             "member sets re-segmented here, so `channel` reports which export(s) it "
                             "came from; a clause can appear in more than one")
    sheet["speaker_rule"] = ("operator = Koosha's own words including text relayed through the instinct "
                             "bridge or quoted under a timestamp header; agent = AI-authored narration, "
                             "report, plan or instruction; peer = third-party DM; tool = raw tool output; "
                             "system = harness banner, config block or injected prompt")

    with open(SHEET, "w") as fh:
        json.dump(sheet, fh, indent=1)

    from collections import Counter
    ch = Counter()
    for it in sheet["items"]:
        ch["+".join(it["channel"]) or "UNMATCHED"] += 1
    print("channel composition:", dict(ch))
    print("unmatched clauses:", missing)
    sp = Counter(it["speaker_pass2"] for it in sheet["items"])
    print("speaker pass 2:", dict(sp))
    print("speaker pass 1 (lost, aggregate only):", {k: v["n"] for k, v in preserved["by_speaker"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
