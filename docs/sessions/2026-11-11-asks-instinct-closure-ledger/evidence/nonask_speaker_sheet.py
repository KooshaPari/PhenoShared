"""Emit a BLIND speaker-only sheet for the non-ask bucket.

The non-ask sheet (`nonask_label_sheet.json`) was built for a capture task, so its
`speaker_pass2` field is already filled. A second independent labeller must not see it,
or the exercise measures agreement with a prompt rather than agreement between coders.

This script therefore emits two files from the SAME 60 sampled clauses:

  nonask_speaker_sheet.json  idx, clause, speaker=null, why=""   (give this to the labeller)
  nonask_speaker_key.json    idx, clause, channels               (withhold; objective metadata)

It copies clause strings unchanged from the source sheet and writes nothing else.
Re-running is idempotent. It does NOT assign labels.
"""

import json
from datetime import datetime, timezone

SRC = "nonask_label_sheet.json"
SHEET = "nonask_speaker_sheet.json"
KEY = "nonask_speaker_key.json"

INSTRUCTIONS = (
    "Label each clause with exactly ONE speaker: operator | agent | tool | system | peer | other.\n"
    " - operator = Koosha's own words: an instruction, question, ruling, correction, or remark\n"
    "   addressed to an agent, including instinct-bridge relays, a '| koosha |' header, typos,\n"
    "   and voice-transcribed text.\n"
    " - agent = an AI agent's narration, plan, self-report, or instruction to another agent,\n"
    "   including agent output pasted inside a user turn.\n"
    " - tool = raw tool output, diff, log line, JSON blob of tool results, file listing.\n"
    " - system = harness banner, injected prompt, skill or config block, metadata header with\n"
    "   no human voice.\n"
    " - peer = a third party's words (a person who is not Koosha).\n"
    " - other = genuinely unresolvable.\n"
    "Do NOT default to operator. If the text has no human voice, it is not operator.\n"
    "Channel and provenance are withheld from this sheet on purpose; judge the words only."
)

with open(SRC, encoding="utf-8") as fh:
    src = json.load(fh)

items = src["items"]
sheet, key = [], []
for it in items:
    sheet.append({"idx": it["idx"], "clause": it["clause"], "speaker": None, "why": ""})
    ch = it.get("channel")
    if isinstance(ch, str):
        ch = [c.strip() for c in ch.strip("[]").replace("'", "").split(",") if c.strip()]
    key.append({"idx": it["idx"], "clause": it["clause"], "channels": ch or []})

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
meta = {
    "generated_at_utc": now,
    "source": SRC,
    "bucket": "uncited_non_ask_cue",
    "seed": src.get("seed"),
    "n": len(items),
    "population": src.get("population"),
    "blind_to": ["channel", "capture outcome", "first labeller's labels"],
    "purpose": "second independent labeller on the non-ask bucket",
    "what_this_is_not": (
        "This measures authorship of the bucket. It does not by itself produce a coverage rate."
    ),
}

with open(SHEET, "w", encoding="utf-8") as fh:
    json.dump({**meta, "instructions": INSTRUCTIONS, "items": sheet}, fh, indent=1,
              ensure_ascii=False)
with open(KEY, "w", encoding="utf-8") as fh:
    json.dump({**meta, "items": key}, fh, indent=1, ensure_ascii=False)

print(f"wrote {SHEET} and {KEY}: n={len(items)} population={meta['population']} seed={meta['seed']}")
