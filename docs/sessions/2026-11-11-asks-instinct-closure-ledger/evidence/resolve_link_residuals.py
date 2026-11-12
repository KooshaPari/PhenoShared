#!/usr/bin/env python3
"""Resolve the residual of the ask->message link test: the 19 paraphrase mismatches,
the 7 unlinked asks, and the mixed namespace inside `reg_ask_messages.message_id`.

Supersedes the four untestable-link claims carried earlier.

What the earlier measurement got wrong, in two places:

1. `reg_ask_messages.message_id` is a MIXED-NAMESPACE column. 2,229 rows hold a
   `phonemsg-<ULID>` that joins `reg_utterances.message_id`; 23 hold a `UTT-NNNNNN`
   that joins `reg_utterances.id`. Resolving only through message_id reports those 23
   as absent. There are in fact ZERO link targets absent from reg_utterances.
2. The 7 legitimately unlinked asks are not a defect either: `reg_asks.source_missing`
   is 1 for exactly those 7 and 0 for the other 2,252. Link presence and the register's
   own flag agree perfectly.

Verdicts on the 19 residual mismatches are MY reading of the quote against the full
body, single coder. They are recorded per row rather than summarised, so the reading can
be checked. In every case the link is correct and the quote is a paraphrase or is
degraded by speech-to-text.
"""
from __future__ import annotations

import json
import sqlite3
import sys

LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
VERIF = ("/Users/kooshapari/CodeProjects/temp/asks-coverage"
         "/ask_link_verification.json")
OUT = ("/Users/kooshapari/CodeProjects/temp/asks-coverage"
       "/link_residual_review.json")

# ASK -> (verdict, why). Link is CORRECT in all 19; the label names the damage mode.
VERDICTS = {
    "ASK-000279": ("CORRECT_PARAPHRASE", "755-char multi-topic utterance; one ask extracted"),
    "ASK-000626": ("CORRECT_PARAPHRASE", "'every deploy should work this way'"),
    "ASK-000700": ("CORRECT_ASR", "'automatic feedupdate to dataset every 48hrs'"),
    "ASK-000705": ("CORRECT_ASR", "'rebasingreplacive' = rebasing/replacive, spaces lost"),
    "ASK-000718": ("CORRECT_ASR", "'cloudlocal' for cloud/local"),
    "ASK-000721": ("CORRECT_ASR", "'altnertivecomplementary' for alternative/complementary"),
    "ASK-000724": ("CORRECT_ASR", "'blockstatus' for block/status"),
    "ASK-001166": ("CORRECT_PARAPHRASE", "'no to swap m3 ref' read as leave the hardcoded ref"),
    "ASK-001463": ("CORRECT_PARAPHRASE", "long utterance; asks for a state block per program"),
    "ASK-001753": ("CORRECT_ASR", "'Desk allowed aga8n exam doje' = desk allowed again, exam done"),
    "ASK-001787": ("CORRECT_PARAPHRASE", "'Cloud/web state, 9:58:' with a full status block"),
    "ASK-001836": ("CORRECT_PARAPHRASE", "'fan out agents to properly accelerate batch work on the 9x'"),
    "ASK-001906": ("CORRECT_PARAPHRASE", "445-char utterance; 'tabs were added to kooshapri.com remove; dash only' reordered"),
    "ASK-001939": ("CORRECT_ASR", "'and apperclip' = apperclip for paperclip"),
    "ASK-001956": ("CORRECT_PARAPHRASE", "'how to access hermesor use its uiagent or cli'"),
    "ASK-002097": ("CORRECT_ASR", "'discord state'"),
    "ASK-002161": ("CORRECT_ASR", "'token plan ( claude openai minimax sub) to ocgo equiv'"),
    "ASK-002184": ("CORRECT_PARAPHRASE", "'what is with all items paused and not acitively running'"),
    "ASK-002232": ("CORRECT_ASR", "'what's nxy' = what's next"),
}


def main() -> int:
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    cur = con.cursor()

    con.execute("pragma table_info(reg_utterances)")  # table exists
    by_mid = {m: b for m, b in cur.execute(
        "select message_id, body from reg_utterances")}
    by_id = {u: b for u, b in cur.execute(
        "select id, body from reg_utterances")}
    interp = {a: i for a, i in cur.execute(
        "select id, interpretation from reg_asks")}
    missing = {a: int(s) for a, s in cur.execute(
        "select id, source_missing from reg_asks")}

    links: dict[str, list[str]] = {}
    for a, m in cur.execute("select ask_id, message_id from reg_ask_messages"):
        links.setdefault(a, []).append(m)

    asks = sorted(missing)
    unlinked = [a for a in asks if a not in links]

    ns = {"phonemsg": 0, "utt": 0, "absent": 0}
    absent_targets = []
    for a, ms in links.items():
        for m in ms:
            if m in by_mid:
                ns["phonemsg"] += 1
            elif m in by_id:
                ns["utt"] += 1
            else:
                ns["absent"] += 1
                absent_targets.append({"ask": a, "target": m})

    residual = json.load(open(VERIF))["fold"]["mismatched_asks"]
    rows = []
    for a in residual:
        verdict, why = VERDICTS.get(a, ("UNREVIEWED", ""))
        target = links.get(a, [""])[0]
        rows.append({
            "ask": a, "target": target, "verdict": verdict, "why": why,
            "interpretation": interp.get(a, "")[:300],
            "body_excerpt": (by_mid.get(target) or by_id.get(target) or "")[:400],
        })

    wrong = [r for r in rows if r["verdict"].startswith("WRONG")]
    out = {
        "asks_total": len(asks),
        "asks_linked": len(asks) - len(unlinked),
        "asks_unlinked": len(unlinked),
        "unlinked_asks": unlinked,
        "unlinked_all_flagged_source_missing":
            all(missing.get(a) == 1 for a in unlinked),
        "source_missing_1_total": sum(1 for v in missing.values() if v == 1),
        "target_namespaces": ns,
        "absent_targets": absent_targets,
        "fold_residual_mismatches": len(residual),
        "residual_reviewed": len(rows),
        "wrong_links_found": len(wrong),
        "rows": rows,
        "caveat": "verdicts are single-coder reading of quote vs full body",
    }

    print(f"asks {out['asks_total']}  linked {out['asks_linked']}  "
          f"unlinked {out['asks_unlinked']}")
    print(f"target namespaces: {ns}   absent targets: {ns['absent']}")
    print(f"unlinked asks all carry source_missing=1: "
          f"{out['unlinked_all_flagged_source_missing']}  "
          f"(source_missing=1 total {out['source_missing_1_total']})")
    print(f"fold residual mismatches {len(residual)}, reviewed {len(rows)}, "
          f"wrong links found {len(wrong)}")
    from collections import Counter
    print(f"verdicts: {dict(Counter(r['verdict'] for r in rows))}")

    json.dump(out, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
