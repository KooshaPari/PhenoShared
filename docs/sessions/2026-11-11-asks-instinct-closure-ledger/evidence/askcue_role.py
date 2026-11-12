#!/usr/bin/env python3
"""Deterministic role attribution for the 8,819 uncited ask-cue units.

WHY. `nonask_score.py` found that 62-75% of the non-ask-cue bucket is not operator
speech, but said nothing about the ask-cue bucket, which is the one every coverage
figure is actually about. Its speaker mix was never recorded, so no coverage-of-
intent denominator existed.

WHAT. Two of the four channels carry an explicit `role` field in the harvest
(`jcode-occurrences.jsonl`, `codex_user_turns_v2.jsonl`), and the other two are
operator-only by construction (outbound iMessage; `reg_utterances.role='user'`).
So role attribution on the ask-cue population can be computed without labelling.

WHAT THIS MEASURES, AND THE TWO THINGS IT REFUSES TO CLAIM.

  1. `role` is the harness's record of who wrote the turn. It is a proxy for
     operator authorship, not proof: user turns contain pasted agent output, and
     assistant turns quote the operator.
  2. The authorship field is DEGENERATE on this harvest. Measured: both exports
     contain only `role='user'` records (55,122 jcode rows, 9,650 codex rows), and
     the only varying flag is `is_human`, which the published filter uses to drop
     the False rows. After filtering, declared speaker is CONSTANT: 100% operator
     on all 8,819 ask-cue units, so the field has zero discriminating power. On
     the one bucket a human did label, the labeller disagrees on 33 of 60 clauses.
     A per-unit "operator wins" precedence rule would report the same 100% for a
     different reason, so neither rule is used to claim authorship.

The reported frames are therefore: occurrence-level declared-speaker counts (which
show the degeneracy), a three-way unit label (operator / agent / mixed), and a
human cross-check. The honest outcome is a NEGATIVE result: declared speaker cannot
supply a coverage-of-intent denominator.

METHOD. Same population build as `recall_probe.population()` -- same filters, same
cited-exclusion, same `is_ask` -- with per-unit provenance retained, and the total
asserted against the published 8,819 so the denominator cannot drift. Phone
membership is restricted to `role='user'` to match `union_channels.phone()`;
widening it changes the denominator (it also raises the unit count to 10,335, which
the assertion catches).

Read-only. Writes askcue_role.json only.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)

import union_channels as U            # noqa: E402
import segment_units as SEG           # noqa: E402
import recall_probe as RP             # noqa: E402

OUT = os.path.join(HERE, "askcue_role.json")

OPERATOR_ROLES = {"user", "human"}
AGENT_ROLES = {"assistant", "agent", "model"}
TOOL_ROLES = {"tool", "tool_result", "function"}
SYSTEM_ROLES = {"system", "developer"}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify(role: str) -> str:
    r = (role or "").strip().lower()
    if r in OPERATOR_ROLES:
        return "operator"
    if r in AGENT_ROLES:
        return "agent"
    if r in TOOL_ROLES:
        return "tool"
    if r in SYSTEM_ROLES:
        return "system"
    return "other"


def harness_with_roles() -> tuple[dict[str, list[tuple[str, str]]], Counter]:
    """message -> [(channel, declared_speaker)], same filters as `union_channels.harness()`."""
    out: dict[str, list[tuple[str, str]]] = defaultdict(list)
    skipped: Counter = Counter()
    for path, channel in ((U.JCODE, "harness:jcode"), (U.CODEX, "harness:codex")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    skipped["bad_json"] += 1
                    continue
                if r.get("is_injected"):
                    skipped["injected"] += 1
                    continue
                if r.get("is_human") is False:
                    skipped["explicitly_not_human"] += 1
                    continue
                n = U.norm(r.get("text") or "")
                if not U.keep(n):
                    skipped["filtered"] += 1
                    continue
                out[n].append((channel, classify(r.get("role"))))
    return out, skipped


def flat_role(channel: str) -> dict[str, list[tuple[str, str]]]:
    """Channels that are operator-only by construction."""
    if channel == "imessage":
        return {x: [("imessage:outbound", "operator")]
                for x in U.imessage() if U.keep(x)}
    if channel == "kcode":
        return {x: [("kcode:user", "operator")]
                for x in U.kcode()[0] if U.keep(x)}
    if channel == "phone":
        # membership MUST match `union_channels.phone()`, which is role='user' only.
        con = sqlite3.connect(f"file:{U.LEDGER}?mode=ro", uri=True)
        con.execute("PRAGMA query_only=1")
        rows = con.execute(
            "select body, role from reg_utterances where role='user'").fetchall()
        con.close()
        out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for body, role in rows:
            n = U.norm(body or "")
            if U.keep(n):
                out[n].append((f"phone:{role}", classify(role)))
        return out
    raise ValueError(channel)


def _wilson(k: int, n: int, z: float = 1.959963985) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = min(max(k / n, 0.0), 1.0)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    var = p * (1 - p) / n + z * z / (4 * n * n)
    m = z * (var ** 0.5)
    return [round((c - m) / d, 4), round((c + m) / d, 4)]


def main() -> int:
    published = json.load(open(RP.PROBE))["population"]
    expected = published["uncited_ask_cue_units_union"]

    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    harness_units, skipped = harness_with_roles()
    flat = {ch: flat_role(ch) for ch in ("imessage", "kcode", "phone")}

    prov: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for unit, tags in harness_units.items():
        prov[unit].extend(tags)
    for table in flat.values():
        for unit, tags in table.items():
            prov[unit].extend(tags)

    members_by_channel = {
        "harness": set(harness_units),
        "imessage": set(flat["imessage"]),
        "kcode": set(flat["kcode"]),
        "phone": set(flat["phone"]),
    }

    uncited: set[str] = set()
    per_channel_units: Counter = Counter()
    for ch in ("harness", "imessage", "kcode", "phone"):
        units = sorted({u for m in members_by_channel[ch] for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited = idx.cite(quotes)
        free = [u for i, u in enumerate(units) if i not in cited]
        asklike = [u for u in free if SEG.is_ask(u)]
        per_channel_units[ch] = len(asklike)
        uncited.update(asklike)

    print(f"uncited ask-cue units (union, deduped): {len(uncited)}  expected {expected}")
    if len(uncited) != expected:
        raise SystemExit(f"DENOMINATOR DRIFT: {len(uncited)} != {expected}")

    # clause -> the set of (channel, speaker) messages it was cut from
    occ: dict[str, set[tuple[str, str]]] = {}
    for unit, tags in prov.items():
        if len(unit) < SEG.MIN_UNIT:
            continue
        for clause in SEG.segment(unit):
            occ.setdefault(clause, set()).update(tags)

    absent = [u for u in uncited if u not in occ]
    if absent:
        raise SystemExit(f"PROVENANCE GAP: {len(absent)} ask-cue units have no source message")

    def unit_label(u: str) -> str:
        speakers = {s for _c, s in occ[u]}
        speakers.discard("other")
        if not speakers:
            return "unknown"
        if len(speakers) == 1:
            return next(iter(speakers))
        return "mixed"

    unit_labels = Counter(unit_label(u) for u in uncited)

    # The harvest's own role census, BEFORE any filtering. This is the load-bearing
    # evidence: both exports contain only `role='user'` records, so after the published
    # filters every surviving record declares itself an operator turn. The field is
    # therefore CONSTANT on the filtered population and carries no discriminating power.
    census: dict[str, dict[str, int]] = {}
    for path, label in ((U.JCODE, "jcode"), (U.CODEX, "codex")):
        c: Counter = Counter()
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    c["bad_json"] += 1
                    continue
                c[f"role={r.get('role')}|is_human={r.get('is_human')}"] += 1
        census[label] = dict(c)

    # Per-channel declared-speaker counts over the ask-cue population.
    occ_speaker: Counter = Counter()
    occ_channel: Counter = Counter()
    for u in uncited:
        for channel, speaker in occ[u]:
            occ_speaker[speaker] += 1
            occ_channel[f"{channel.split(':')[0]}:{speaker}"] += 1
    total_occ = sum(occ_speaker.values())

    crosscheck = None
    sheet = os.path.join(HERE, "nonask_label_sheet.json")
    if os.path.exists(sheet):
        rows = []
        for item in json.load(open(sheet)).get("items", []):
            clause = item.get("clause") or ""
            rows.append({
                "idx": item.get("idx"),
                "deterministic": unit_label(clause) if clause in occ else "absent",
                "labelled": item.get("speaker_pass2") or item.get("speaker") or "",
            })
        agree = sum(1 for r in rows
                    if (r["deterministic"] == "operator") ==
                       (r["labelled"] in ("operator", "peer")))
        crosscheck = {
            "n": len(rows),
            "operator_agreement": agree,
            "deterministic_labels": dict(Counter(r["deterministic"] for r in rows)),
            "note": ("agreement on the operator/not-operator cut. A clause the human judged "
                     "operator but which also occurs inside an agent message is labelled "
                     "`mixed` here, so it counts as disagreement -- this understates "
                     "agreement and is left that way deliberately."),
        }

    result = {
        "generated_at_utc": _now(),
        "population": {
            "uncited_ask_cue_units_union": len(uncited),
            "asserted_against": expected,
            "per_channel_ask_cue_units_summing_to_more_than_union": dict(per_channel_units),
            "occurrence_pairs": total_occ,
        },
        "unit_labels": dict(unit_labels),
        "harvest_role_census_raw": census,
        "occurrences": {
            "total": total_occ,
            "by_speaker": dict(occ_speaker),
            "by_channel_and_speaker": dict(sorted(occ_channel.items())),
            "operator_share": round(occ_speaker.get("operator", 0) / total_occ, 4)
            if total_occ else 0.0,
            "operator_share_wilson_95": _wilson(occ_speaker.get("operator", 0), total_occ),
        },
        "finding": ("Every harvest record that survives the published filters declares "
                    "itself an operator turn (role='user'), so declared-speaker attribution "
                    "returns 100% operator on all {n} ask-cue units by construction. The "
                    "field is CONSTANT here and carries no discriminating power; a human "
                    "labeller disagrees on {d} of {m} sampled clauses. Coverage of operator "
                    "intent therefore still has no denominator, and the reason is now "
                    "structural rather than merely unsampled.").format(
                        n=len(uncited),
                        d=(crosscheck or {}).get("n", 0) - (crosscheck or {}).get(
                            "operator_agreement", 0),
                        m=(crosscheck or {}).get("n", 0)),
        "method": ("deterministic: the harvest's own `role` field for jcode/codex, and "
                   "operator-only construction for outbound iMessage, kcode user turns and "
                   "reg_utterances.role='user'"),
        "caveat": ("`role` is the harness's record of who wrote the turn, not proof of "
                   "operator authorship: pasted agent output appears inside user turns and "
                   "assistant turns can quote the operator"),
        "rejected_rule": ("neither metadata precedence nor 'operator wins' can be used to "
                          "claim authorship: the surviving harvest is 100% role='user' by "
                          "construction, and a human labeller disagrees on 33 of 60 clauses"),
        "harvest_rows_skipped": dict(skipped),
        "crosscheck_vs_nonask_labels": crosscheck,
        "limitations": [
            "role is a declared field, not an adjudicated one",
            "phone is an iMessage subset, so it cannot rescue the operator share",
            "no adjudication of pasted agent output inside user turns",
            "kcode and iMessage carry no per-message role diversity to measure",
        ],
    }
    with open(OUT, "w") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps({k: result[k] for k in ("unit_labels", "harvest_role_census_raw",
                                             "occurrences", "finding",
                                             "crosscheck_vs_nonask_labels")}, indent=1))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
