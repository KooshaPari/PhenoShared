#!/usr/bin/env python3
"""Ask-level recall against the ask register, with the channel scope made explicit.

The recall reference frame (recall_reference_sheet.py) samples transcript windows from
THREE channels: harness, imessage, kcode. The ask register (asks-ledger/ledger.db) was
built from conversation exports whose conversation_id values are only `phoneconv-*` and
`chatdb`. So two of the three channels cannot be scored against this register at all:
a zero there would be a property of the register's input scope, not a measurement of
retrieval. This script refuses to emit such a zero as if it were recall.

What it measures
  imessage windows: reference asks matched / reference asks, content-matched against the
  register's ask utterances and ask interpretations.

What it refuses to measure
  harness and kcode windows: reported as NOT_MEASURABLE_AGAINST_THIS_REGISTER with the
  observed conversation_id prefixes as evidence.

Matching (only within the scored channel)
  A: normalized containment in either direction, minimum 20 characters.
  B: token Jaccard >= 0.6.
  A reference ask is matched if either rule fires; the firing rule is recorded.

Read-only throughout: ledger.db is opened with URI mode=ro and PRAGMA query_only=1.
No commit, no network, stdlib only.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LEDGER = (
    "/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
    "/asks-ledger/ledger.db"
)
SHEET = os.path.join(BASE, "recall_reference_sheet.json")
KEY = os.path.join(BASE, "recall_reference_key.json")
LABELS = os.path.join(BASE, "recall_reference_labeled.json")
OUT = os.path.join(BASE, "recall_asklevel_scored.json")

MIN_CONTAIN = 20
JACCARD = 0.6
SCORED_CHANNEL = "imessage"

WORD = re.compile(r"[a-z0-9]+")


def norm(s: str) -> str:
    return " ".join(WORD.findall((s or "").lower()))


def toks(s: str) -> set[str]:
    return set(WORD.findall((s or "").lower()))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> dict | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"low": max(0.0, c - h), "high": min(1.0, c + h)}


def open_register():
    if not os.path.exists(LEDGER):
        return None, f"ledger.db not found at {LEDGER}"
    try:
        con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
        con.execute("PRAGMA query_only=1")
        con.execute("select 1 from reg_utterances limit 1").fetchone()
        return con, None
    except Exception as exc:  # noqa: BLE001
        return None, f"ledger.db unreadable read-only: {exc}"


def register_scope(con) -> dict:
    """What the register can and cannot represent."""
    prefixes = {
        r[0]: r[1]
        for r in con.execute(
            "select substr(conversation_id,1,9) as p, count(*) "
            "from reg_utterances group by p"
        )
    }
    asks = con.execute("select count(*) from reg_asks").fetchone()[0]
    utt = con.execute("select count(*) from reg_utterances").fetchone()[0]
    origin = con.execute(
        "select count(*) from reg_ask_messages where relation='origin'"
    ).fetchone()[0]
    return {
        "ledger_db": LEDGER,
        "reg_asks": asks,
        "reg_utterances": utt,
        "origin_links": origin,
        "conversation_prefixes": prefixes,
        "harness_representable": any("harness" in p or "jcode" in p or "kcode" in p for p in prefixes),
    }


def candidates(con) -> list[tuple[str, str, str]]:
    """(ask_id, kind, text) over ask utterances and ask interpretations."""
    out: list[tuple[str, str, str]] = []
    for ask_id, body in con.execute(
        "select m.ask_id, u.body from reg_ask_messages m "
        "join reg_utterances u on u.message_id = m.message_id"
    ):
        if body:
            out.append((ask_id, "utterance", body))
    for ask_id, interp in con.execute("select id, interpretation from reg_asks"):
        if interp:
            out.append((ask_id, "interpretation", interp))
    return out


def match(reference_quote: str, cands: list[tuple[str, str, str]]) -> dict:
    nq = norm(reference_quote)
    tq = toks(reference_quote)
    a_hits, b_hits = [], []
    for ask_id, kind, text in cands:
        nt = norm(text)
        if len(nq) >= MIN_CONTAIN and (nq in nt or (len(nt) >= MIN_CONTAIN and nt in nq)):
            a_hits.append(ask_id)
            continue
        if tq:
            tt = toks(text)
            if tt:
                j = len(tq & tt) / len(tq | tt)
                if j >= JACCARD:
                    b_hits.append((ask_id, round(j, 3)))
    return {
        "rule_a": a_hits,
        "rule_b": [b[0] for b in b_hits],
        "best_b": max((b[1] for b in b_hits), default=None),
    }


def main() -> int:
    for p in (SHEET, KEY, LABELS):
        if not os.path.exists(p):
            print(f"missing input: {p}", file=sys.stderr)
            return 2

    sheet = json.load(open(SHEET))
    key = json.load(open(KEY))
    labels = json.load(open(LABELS))

    items = {i["idx"]: i for i in sheet["items"]}
    keyitems = {i["idx"]: i for i in key["items"]}
    lab = {i["idx"]: i for i in labels["items"]}
    if len(items) != 60 or set(items) != set(lab) or set(items) != set(keyitems):
        print("input shape mismatch", len(items), len(lab), len(keyitems), file=sys.stderr)
        return 5

    con, err = open_register()
    if con is None:
        print(err, file=sys.stderr)
        return 3
    scope = register_scope(con)
    cands = candidates(con)

    per_channel: dict[str, dict] = {}
    unmatched: list[dict] = []
    scored_rows: list[dict] = []

    channels = sorted({i["channel"] for i in items.values()})
    for ch in channels:
        idxs = [k for k, i in items.items() if i["channel"] == ch]
        asks_total = sum(len(lab[k].get("reference_asks") or []) for k in idxs)
        entry = {
            "windows": len(idxs),
            "reference_asks": asks_total,
            "fragments_excluded": 0,
            "denominator": None,
            "matched": 0,
            "by_rule_a": 0,
            "by_rule_b": 0,
            "both": 0,
            "recall": None,
            "measured": False,
        }
        if ch != SCORED_CHANNEL:
            entry["not_measured_reason"] = (
                "the register contains no utterances from this channel: its "
                f"conversation_id prefixes are {sorted(scope['conversation_prefixes'])}. "
                "A zero here would describe the register's input scope, not recall, so it "
                "is not emitted as recall."
            )
            per_channel[ch] = entry
            continue

        entry["measured"] = True
        entry["denominator"] = 0

        for k in idxs:
            item = items[k]
            for a in lab[k].get("reference_asks") or []:
                quote = (a.get("quote") or "").strip()
                if not quote:
                    continue
                if (a.get("intent") or "").strip().lower() == "fragment":
                    entry["fragments_excluded"] += 1
                    continue
                entry["denominator"] += 1
                m = match(quote, cands)
                hit_a = bool(m["rule_a"])
                hit_b = bool(m["rule_b"])
                if hit_a or hit_b:
                    entry["matched"] += 1
                    entry["by_rule_a"] += 1 if hit_a else 0
                    entry["by_rule_b"] += 1 if hit_b else 0
                    entry["both"] += 1 if (hit_a and hit_b) else 0
                else:
                    unmatched.append(
                        {
                            "idx": k,
                            "channel": ch,
                            "turn": a.get("turn"),
                            "quote": quote[:120],
                            "reason": "no register ask within the containment or Jaccard rule",
                            "best_jaccard": m["best_b"],
                        }
                    )
                scored_rows.append(
                    {
                        "idx": k,
                        "turn": a.get("turn"),
                        "quote": quote[:120],
                        "matched": hit_a or hit_b,
                        "rule": "a" if hit_a else ("b" if hit_b else None),
                    }
                )
        entry["measured"] = True
        entry["recall"] = wilson(entry["matched"], entry["denominator"])
        entry["recall"]["value"] = (
            entry["matched"] / entry["denominator"] if entry["denominator"] else None
        )
        per_channel[ch] = entry

    scored = [c for c, e in per_channel.items() if e["measured"]]
    tot_n = sum(per_channel[c]["denominator"] for c in scored)
    tot_k = sum(per_channel[c]["matched"] for c in scored)
    overall = {
        "channels_scored": scored,
        "channels_not_measured": [c for c in per_channel if not per_channel[c]["measured"]],
        "denominator": tot_n,
        "matched": tot_k,
        "recall": wilson(tot_k, tot_n),
    }
    if overall["recall"]:
        overall["recall"]["value"] = tot_k / tot_n if tot_n else None

    doc = {
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "recall_asklevel_match.py",
        "rules": {
            "a": f"normalized containment either direction, min {MIN_CONTAIN} chars",
            "b": f"token jaccard >= {JACCARD}",
            "match": "either rule fires; firing rule recorded per row",
        },
        "register_scope": scope,
        "structural_finding": (
            "the register cannot represent harness or kcode windows: no register utterance "
            "carries a harness conversation id, so recall is measurable only on the imessage "
            "stratum of the frame. A single pooled recall across all 60 windows would be "
            "dominated by channels the register never ingested."
        ),
        "frame": {
            "windows": len(items),
            "population": sheet.get("population"),
            "seed": sheet.get("seed"),
            "reference_asks_total": sum(
                len(v.get("reference_asks") or []) for v in lab.values()
            ),
        },
        "per_channel": per_channel,
        "overall_scored_channels_only": overall,
        "unmatched": unmatched,
        "rows": scored_rows,
        "caveats": [
            "the denominator is a 60-window sample of a 3,337-unit population, and only the "
            "imessage stratum is scorable against this register",
            "the reference inventory is a single model labeller, not a human, so it can miss "
            "asks; that makes measured recall an upper estimate of the denominator's true size",
            "window boundaries can split one ask across two windows",
            "content matching cannot distinguish an ask that the register captured under a "
            "different intent from one it never captured",
        ],
    }

    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)

    print(f"wrote {OUT}")
    print("register scope:", scope["conversation_prefixes"], "asks", scope["reg_asks"])
    for ch, e in per_channel.items():
        r = e.get("recall")
        den = e["denominator"]
        print(
            f"  {ch:9s} windows={e['windows']:2d} asks={e['reference_asks']:3d} "
            f"denom={den if den is not None else '-'} "
            f"matched={e['matched']} measured={e['measured']} "
            f"recall={None if not r else round(r['value'], 4)}"
        )
    r = overall["recall"]
    print(
        f"overall (scored channels only) {tot_k}/{tot_n} = {round(r['value'],4)} "
        f"[{round(r['low'],4)}, {round(r['high'],4)}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
