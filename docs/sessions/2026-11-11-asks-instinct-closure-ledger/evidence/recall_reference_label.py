#!/usr/bin/env python3
"""Re-verify the blind reference labelling in recall_reference_labeled.json.

Checks
  1. every idx 0..59 appears exactly once (no dupes, no gaps)
  2. every reference_asks quote is a verbatim substring of that item's text
  3. every turn ordinal is within the window's turn count
  4. no item has empty reference_asks unless every turn in the window is one of the
     recognised non-ask shapes (harness todo nudge / background-task notification /
     redacted placeholder). Anything else in an empty item is a FAIL for review.
  5. matched_register_ask_ids is empty everywhere (this pass is blind)

Reports per-channel totals, total ask count, zero-ask items, and redacted windows.
"""
import json
import re
import sys
from collections import Counter, defaultdict

BASE = ("/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared-space/"
        "feat/researchledger-ingest-v2/wtree/docs/sessions/"
        "2026-11-11-asks-instinct-closure-ledger/evidence")
SHEET = f"{BASE}/recall_reference_sheet.json"
LABELED = f"{BASE}/recall_reference_labeled.json"
EMPTY_OK = f"{BASE}/recall_reference_empty_ok.json"

TURN_RE = re.compile(r"^--- turn (\d+) ---$")
REDACTED_RE = re.compile(r"^turn \d+ x{20,}$")
# Harness todo nudge; matched as a PREFIX because the window often truncates it
# ("you have 2 incomplete todos. continue working, or u").
NUDGE_RE = re.compile(
    r"^you have \d+ incomplete todos?\. continue working, or u",
    re.IGNORECASE)
# Pasted direct message from another agent lane (a report, not an operator ask).
DM_PASTE_RE = re.compile(r"^dm from [a-z0-9_.-]+:", re.IGNORECASE)
BGTASK_RE = re.compile(
    r"^(background task|background task stalled|\*\*background task)", re.IGNORECASE)
BGTASK_MARK = "**background task"


def parse_turns(text):
    bodies, cur, seen = [], [], False
    for line in text.split("\n"):
        if TURN_RE.match(line.strip()):
            if seen:
                bodies.append("\n".join(cur).strip("\n"))
            cur, seen = [], True
            continue
        if seen:
            cur.append(line)
    if seen:
        bodies.append("\n".join(cur).strip("\n"))
    return bodies


def is_system_turn(body):
    b = body.strip()
    low = b.lower()
    if REDACTED_RE.match(low):
        return True
    if NUDGE_RE.match(b):
        return True
    if BGTASK_MARK in low or BGTASK_RE.match(low):
        return True
    if DM_PASTE_RE.match(b):
        return True
    return False


def main():
    sheet = {it["idx"]: it for it in json.load(open(SHEET))["items"]}
    labeled = json.load(open(LABELED))["items"]
    failures = []

    # 1. coverage
    idxs = [it["idx"] for it in labeled]
    dupes = [i for i, c in Counter(idxs).items() if c > 1]
    missing = sorted(set(range(60)) - set(idxs))
    extra = sorted(set(idxs) - set(range(60)))
    if dupes:
        failures.append(f"duplicate idxs: {sorted(dupes)}")
    if missing:
        failures.append(f"missing idxs: {missing}")
    if extra:
        failures.append(f"out-of-range idxs: {extra}")

    per_channel = defaultdict(int)
    zero_items = []
    redacted_items = []
    fragment_items = []
    total = 0
    non_system_empty = []

    for it in labeled:
        idx = it["idx"]
        src = sheet[idx]
        if src["channel"] != it["channel"]:
            failures.append(f"idx {idx}: channel {it['channel']} != sheet {src['channel']}")
        turns = parse_turns(src["text"])
        asks = it["reference_asks"]

        if it.get("matched_register_ask_ids"):
            failures.append(f"idx {idx}: matched_register_ask_ids must be empty (blind pass)")

        if any(is_system_turn(t) for t in turns):
            redacted_items.append(idx)

        # 2/3. quote + turn checks
        seen_turns = set()
        for a in asks:
            q, turn = a["quote"], a["turn"]
            if not isinstance(turn, int) or not (1 <= turn <= len(turns)):
                failures.append(f"idx {idx}: turn {turn} outside 1..{len(turns)}")
                continue
            if turn in seen_turns:
                failures.append(f"idx {idx}: duplicate turn {turn} in reference_asks")
            seen_turns.add(turn)
            if not q or q not in src["text"]:
                failures.append(f"idx {idx} turn {turn}: quote is NOT a verbatim substring: {q[:80]!r}")
                continue
            if q not in turns[turn - 1]:
                failures.append(f"idx {idx} turn {turn}: quote not found in that turn's body")
            if len(q) > 200:
                failures.append(f"idx {idx} turn {turn}: quote longer than 200 chars")
            if not a.get("intent", "").strip():
                failures.append(f"idx {idx} turn {turn}: empty intent")
            if a.get("intent", "").strip().lower() == "fragment":
                fragment_items.append((idx, turn))

        # 4. empty-item justification
        if not asks:
            bad = [i + 1 for i, t in enumerate(turns) if not is_system_turn(t)]
            if bad:
                non_system_empty.append((idx, bad))
        else:
            total += len(asks)
            per_channel[it["channel"]] += len(asks)
        if not asks:
            zero_items.append(idx)

    # Documented human justifications for items whose readable prose contains no ask.
    try:
        justified = {int(k): v for k, v in json.load(open(EMPTY_OK))["items"].items()}
    except FileNotFoundError:
        justified = {}
    for idx, turns_bad in non_system_empty:
        if idx in justified and str(justified[idx]).strip():
            continue
        failures.append(
            f"idx {idx}: reference_asks empty but turns {turns_bad} are not recognised "
            f"non-ask shapes and no justification is recorded in recall_reference_empty_ok.json")

    print("=== recall_reference_label.py verification ===")
    print(f"items: {len(labeled)}")
    print("asks per channel:")
    for ch in ("harness", "imessage", "kcode"):
        n_items = sum(1 for it in labeled if it["channel"] == ch)
        print(f"  {ch:<9} asks={per_channel.get(ch, 0):>3}  (items={n_items})")
    print(f"total asks: {total}")
    print(f"items with zero asks ({len(zero_items)}): {zero_items}")
    print(f"fragment-excluded turns: {fragment_items}")
    print(f"windows containing redacted/system-only turns: {redacted_items}")
    redacted_only = [it["idx"] for it in labeled
                     if parse_turns(sheet[it["idx"]]["text"])
                     and all(is_system_turn(t) for t in parse_turns(sheet[it["idx"]]["text"]))
                     and not it["reference_asks"]]
    print(f"windows with no operator turn at all (redacted/system/DM-paste only): {redacted_only}")
    print(f"empty items justified by hand: {sorted(justified)}")
    print()
    if failures:
        print(f"VERIFICATION: FAIL ({len(failures)} issues)")
        for f in failures:
            print("  -", f)
        return 1
    print("VERIFICATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
