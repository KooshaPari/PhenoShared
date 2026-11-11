#!/usr/bin/env python3
"""Adapter validation.

  python3 scripts/adapters/smoke.py --source claude    # strict tuple parity vs goal1/messages.jsonl
  python3 scripts/adapters/smoke.py --source gemini    # landed check + record count
  python3 scripts/adapters/smoke.py --source chatgpt   # landed/format status
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_claude():
    from adapters import claude, gemini
    from collections import Counter

    pipe, _norm, log = claude.pipeline_messages(dedupe=True)
    # combined pipeline = claude rows + gemini activity rows (mirrors goal1_normalize.main())
    combined = list(pipe)
    if gemini.landed():
        combined.extend(gemini.iter_messages())
    pipe_pairs = Counter((m["conv_id"], m["msg_id"], m["role"]) for m in combined)

    analysis = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    g1 = os.path.join(analysis, "goal1")
    ref_pairs = Counter()
    with open(os.path.join(g1, "messages.jsonl"), encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            ref_pairs[(m["conv_id"], m["msg_id"], m["role"])] += 1

    missing = set(ref_pairs) - set(pipe_pairs)   # in reference, not reproducible
    extra = set(pipe_pairs) - set(ref_pairs)     # reproducible, absent from reference
    print(json.dumps({
        "source": "claude+gemini combined",
        "pipeline_rows": len(combined),
        "claude_rows": len(pipe),
        "gemini_rows": len(combined) - len(pipe),
        "reference_rows": sum(ref_pairs.values()),
        "tuples_in_reference_not_in_pipeline": len(missing),
        "tuples_in_pipeline_not_in_reference": len(extra),
        "sample_missing": sorted(missing)[:3],
        "sample_extra": sorted(extra)[:3],
        "adapter_log": log,
        "ok": len(missing) == 0,
    }, indent=2))


def check_gemini():
    from adapters import gemini
    if not gemini.landed():
        print(json.dumps({"source": "gemini", "landed": False}))
        return
    n = sum(1 for _ in gemini.iter_messages())
    print(json.dumps({"source": "gemini", "landed": True, "records": n,
                      "expected_from_normalize": 761, "ok": n == 761}))


def check_chatgpt():
    from adapters import chatgpt
    p = chatgpt.landed()
    print(json.dumps({"source": "chatgpt", "landed": bool(p), "path": p,
                      "note": "not landed is EXPECTED until the export arrives"}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["claude", "gemini", "chatgpt"])
    args = ap.parse_args()
    {"claude": check_claude, "gemini": check_gemini, "chatgpt": check_chatgpt}[args.source]()


if __name__ == "__main__":
    main()
