#!/usr/bin/env python3
"""Goal 3 step 1 (LOCAL ONLY): extract response-pattern units.

A unit = one human turn + the assistant message it reacts to (the immediately
preceding assistant message in the same conversation). Text is passed through
the same redactor as Goal 1 before being written anywhere. Lexical features
and a heuristic first-pass label are computed locally for tiering analysis.

Output:
  goal3/units_redacted.jsonl  (redacted excerpts + features + heuristic label)
  goal3/heuristic_stats.json  (label counts, coverage, redaction stats)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goal1_redact import redact  # noqa: E402

G1 = "/Users/kooshapari/Exports/analysis/goal1"
G3 = "/Users/kooshapari/Exports/analysis/goal3"

APPROVE = r"\b(yes|yep|yup|yeah|lgtm|ship it|go ahead|do it|looks good|looks great|perfect|great|awesome|sounds good|approved|agreed|nice|cool|fine|banger|w)\b"
REJECT = r"\b(no|nope|stop|halt|revert|undo|cancel|dont|don't|do not|never mind|nevermind|bad idea|wrong approach)\b"
DEFER = r"\b(later|tomorrow|next week|park (it|this)|shelve|not now|come back to|postpone|hold off)\b"
TIGHTEN = r"\b(only|just|minimal|minimally|keep it (small|simple|minimal)|scope (down|creep)|slim|reduce|strip)\b"
REDIRECT = r"^(actually|instead|rather|wait|hold on|change of plan|on second thought|rather than)\b|\b(instead of|rather than|let's do|switch to|go with)\b"
CORRECT = r"\b(no,? (it's|its|this is|that is)|that's wrong|incorrect|not quite|misread|you (misread|missed|mixed up)|typo)\b"
ASK_WHY = r"^(why|how|what if|what's the reason|explain|can you explain|what do you mean|where did you)\b|\?"
THANKS = r"\b(thanks|thank you|ty|appreciate|cheers)\b"
URGENT = r"\b(asap|urgent|immediately|right now|hurry|today|deadline)\b"
FRUSTRATE = r"\b(frustrat|annoy|again\?|seriously|come on|unbelievable|this is (broken|terrible)|wtf|ugh)\b"

NEW_TASK = re.compile(r"^(please\s+)?(can you|could you|make|write|create|build|add|implement|fix|update|run|set up|scaffold|deploy|install|research|find|check|review|edit|refactor|test|commit|push)\b", re.I)


def words(t):
    return re.findall(r"[A-Za-z']+", t.lower())


def features(text):
    t = text.strip()
    tl = t.lower()
    ws = words(t)
    return {
        "wc": len(ws),
        "is_question": bool(re.search(r"\?", t)) or tl.startswith(("why", "how", "what", "can ", "could ", "does ", "is ", "do ")),
        "has_negation": bool(re.search(r"\b(no|not|never|dont|don't|won't|cannot|can't|stop)\b", tl)),
        "starts_redirect": bool(re.match(REDIRECT, tl)),
        "imperative": bool(re.match(NEW_TASK, tl)),
        "approve_cue": bool(re.search(APPROVE, tl)),
        "reject_cue": bool(re.search(REJECT, tl)),
        "defer_cue": bool(re.search(DEFER, tl)),
        "tighten_cue": bool(re.search(TIGHTEN, tl)),
        "correct_cue": bool(re.search(CORRECT, tl)),
        "why_cue": bool(re.search(ASK_WHY, tl)),
        "thanks_cue": bool(re.search(THANKS, tl)),
        "urgent_cue": bool(re.search(URGENT, tl)),
        "frustration_cue": bool(re.search(FRUSTRATE, tl)),
    }


def heuristic_label(f, text, has_prev):
    """First-pass label from lexical cues only (tier-1 proxy)."""
    tl = text.strip().lower()
    if not has_prev:
        return "OPENING"
    if f["wc"] <= 3 and f["thanks_cue"] and not f["imperative"]:
        return "PHATIC"
    if f["reject_cue"] and (f["has_negation"] or tl.startswith(("no", "stop", "cancel", "revert", "undo"))):
        return "REJECT"
    if f["starts_redirect"]:
        return "REDIRECT"
    if f["correct_cue"]:
        return "CORRECT"
    if f["tighten_cue"] and f["wc"] <= 12:
        return "TIGHTEN"
    if f["defer_cue"] and not f["imperative"]:
        return "DEFER"
    if f["imperative"] and not f["approve_cue"]:
        return "NEW_TASK"
    if f["why_cue"] and f["is_question"] and tl.rstrip().endswith("?"):
        return "ASK_WHY"
    if f["approve_cue"] and f["wc"] <= 8 and not f["reject_cue"]:
        return "APPROVE"
    if f["thanks_cue"] and f["wc"] <= 10:
        return "PHATIC"
    if f["wc"] >= 25:
        return "ELABORATE"
    return "UNKNOWN"


def main():
    os.makedirs(G3, exist_ok=True)
    from collections import defaultdict
    stats = defaultdict(int)
    convs = {}
    n_msgs = 0
    with open(os.path.join(G1, "messages.jsonl"), encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            n_msgs += 1
            key = (m.get("source", "claude"), m.get("conv_id", ""))
            convs.setdefault(key, []).append(m)

    units = []
    label_counts = {}
    for (source, conv_id), rows in convs.items():
        rows.sort(key=lambda r: (r.get("created_at") or "", r.get("msg_id") or ""))
        last_assistant = None
        for m in rows:
            role = m.get("role")
            text = m.get("text") or ""
            if role == "assistant":
                if len(text.strip()) >= 20:  # ignore empty/trivial assistant turns
                    last_assistant = text
                continue
            if role != "human":
                continue
            if not text.strip():
                continue
            prev = last_assistant
            feats = features(text)
            label = heuristic_label(feats, text, prev is not None)
            label_counts[label] = label_counts.get(label, 0) + 1
            units.append({
                "unit_id": f"{source}:{conv_id}:{m.get('msg_id', '')[:8]}",
                "source": source,
                "conv_id": conv_id,
                "ts": m.get("created_at"),
                "has_prev_assistant": prev is not None,
                "user_excerpt": text[:500],
                "assistant_prev_excerpt": (prev[:400] if prev else ""),
                "features": feats,
                "heuristic_label": label,
            })

    # Redact every text field in place before writing anything out.
    for u in units:
        u["user_excerpt"] = redact(u["user_excerpt"], stats)
        u["assistant_prev_excerpt"] = redact(u["assistant_prev_excerpt"], stats)

    with open(os.path.join(G3, "units_redacted.jsonl"), "w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")

    hs = {
        "messages_scanned": n_msgs,
        "conversations": len(convs),
        "units": len(units),
        "heuristic_label_counts": dict(sorted(label_counts.items(), key=lambda kv: -kv[1])),
        "share_labeled_non_unknown": round(1 - label_counts.get("UNKNOWN", 0) / max(1, len(units)), 4),
        "share_opening_no_prev": round(label_counts.get("OPENING", 0) / max(1, len(units)), 4),
        "redaction_stats": stats,
    }
    with open(os.path.join(G3, "heuristic_stats.json"), "w", encoding="utf-8") as f:
        json.dump(hs, f, indent=2)
    print(json.dumps({k: v for k, v in hs.items() if k != "redaction_stats"}, indent=2))


if __name__ == "__main__":
    main()
