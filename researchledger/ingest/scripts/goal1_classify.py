#!/usr/bin/env python3
"""
GOAL 1f — resumable-value vs ephemeral CLASSIFICATION CANDIDATES. LOCAL ONLY.
Heuristic scoring over redacted digests + normalized metadata. Output feeds a
deletion-CANDIDATE REVIEW — never deletion.

Output: analysis/goal1/resumable_vs_ephemeral.json
  {resumable: [{id, source, title_r, created, score, reasons}, ...],
   ephemeral_candidates: [...],
   review_needed: [...], counts: {...}}
"""
import json
import os
import re
from collections import Counter

G1 = os.path.expanduser("~/Exports/analysis/goal1")

RESUMABLE_PAT = re.compile(
    r"\b(spec|requirements?|design|architecture|decision|adr|plan|roadmap|"
    r"setup|configure|configuration|conventions?|guidelines?|onboarding|"
    r"runbook|postmortem|retrospective|summary|report|proposal|thesis|"
    r"resume|cv|portfolio|reference|guide|tutorial|notes|curriculum)\b", re.I)
EPHEMERAL_PAT = re.compile(
    r"\b(debug|error|fix|issue|test this|quick question|what is|what's|who is|"
    r"hello|hi\b|try this|scratch|temp|tmp|one.?off|homework|quiz|exam|"
    r"assignment|generate image|logo|thumbnail|meme|joke|translate|"
    r"rewrite this|convert this)\b", re.I)
DECISION_PAT = re.compile(
    r"\b(decided|will use|going with|chose|choosing|trade.?off|instead of|"
    r"migrat|adopt|standardi[sz]e|final version|approved)\b", re.I)

def score(rec, body):
    reasons = []
    sc = 0
    rt = rec.get("record_type")
    turns = rec.get("turns") or 0
    if rt in ("project", "memory"):
        sc += 3; reasons.append(f"record_type={rt}")
    if rt == "conversation" and turns >= 10:
        sc += 2; reasons.append(f"long-thread({turns} turns)")
    if rec.get("attachments"):
        sc += 1; reasons.append(f"attachments={len(rec['attachments'])}")
    if rec.get("summary_field_present"):
        sc += 1; reasons.append("has_summary")
    if RESUMABLE_PAT.search(body):
        sc += 2; reasons.append("resumable-topic")
    if DECISION_PAT.search(body):
        sc += 1; reasons.append("decision-language")
    if rec.get("record_type") == "activity":
        sc -= 2; reasons.append("single-prompt-activity")
    if EPHEMERAL_PAT.search(body):
        sc -= 2; reasons.append("ephemeral-topic")
    if turns <= 2 and rt == "conversation":
        sc -= 1; reasons.append("short-thread")
    return sc, reasons

def main():
    norm = {}
    with open(os.path.join(G1, "normalized.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            norm[r["id"]] = r

    out = {"resumable": [], "ephemeral_candidates": [], "review_needed": [],
           "content_stripped_review": []}
    counts = Counter()

    # content-stripped conversations always go to review (Goal 2 linkage)
    try:
        emr = json.load(open(os.path.join(G1, "empty_message_report.json")))
        for r in emr.get("fully_empty", []):
            out["content_stripped_review"].append({
                "id": r["uuid"], "title": None, "created": r.get("created_at"),
                "updated": r.get("updated_at"), "turns": r.get("turns"),
                "reason": "content-stripped shell (deletion-candidate review + audit)"})
    except Exception:
        pass

    with open(os.path.join(G1, "digests.jsonl"), encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            rid = d["conv_id"]
            rec = norm.get(rid, {})
            body = (d.get("title_r") or "") + " " + (d.get("digest_r") or "")
            sc, reasons = score(rec, body)
            entry = {"id": rid, "source": d.get("source"),
                     "record_type": d.get("record_type"),
                     "title_r": (d.get("title_r") or "")[:120],
                     "created": d.get("created_at"), "score": sc,
                     "reasons": reasons}
            if sc >= 3:
                out["resumable"].append(entry); counts["resumable"] += 1
            elif sc <= -1:
                out["ephemeral_candidates"].append(entry); counts["ephemeral_candidates"] += 1
            else:
                out["review_needed"].append(entry); counts["review_needed"] += 1

    out["resumable"].sort(key=lambda x: -x["score"])
    out["ephemeral_candidates"].sort(key=lambda x: x["score"])
    out["counts"] = dict(counts)
    out["counts"]["content_stripped_review"] = len(out["content_stripped_review"])
    out["note"] = ("DELETION-CANDIDATE REVIEW INPUT ONLY. Nothing here is "
                   "approved for deletion; no deletion was performed.")

    with open(os.path.join(G1, "resumable_vs_ephemeral.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out["counts"], indent=2))

if __name__ == "__main__":
    main()
