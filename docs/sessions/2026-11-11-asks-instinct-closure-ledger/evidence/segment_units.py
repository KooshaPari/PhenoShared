#!/usr/bin/env python3
"""Granularity normalisation: segment every channel member into clause-sized units.

WHY. Coverage has been reported as "cited members / union members", but the two sides
have different granularity. A register ask is an extracted intent, typically one
imperative sentence. A harness member is a whole prompt: median a few hundred chars, tail
over 4 KB. A prompt carrying eight asks is one member and can earn one citation, so the
count ratio understates coverage by an unknown amount.

WHAT THIS DOES. Splits each member on structure only -- newlines, sentence terminators,
`;`, dash joins, and list markers -- and keeps units of >= 12 chars. The split contains no
semantic judgement, so the denominator is reproducible without a model. It then recomputes
per-channel unit counts, cross-channel overlap, the union, and citation coverage over units
instead of over members.

TWO DENOMINATORS, because they answer different questions:

  ALL_UNITS   every clause the operator typed. No classification, no judgement, fully
              mechanical. Coverage over this is a LOWER bound on ask coverage, because
              non-ask clauses (status reports, pasted logs, acknowledgements) sit in the
              denominator.
  ASK_UNITS   only units that pass an explicit ask-cue rule set (imperative opener,
              request phrasing, question mark, question word). This tightens the
              denominator, but the rule set is a heuristic, so its error rate is measured
              separately by `validate_ask_rules.py` and must be quoted alongside.

The rules are printed to JSON so a reader can audit them rather than take them on trust.
"""
from __future__ import annotations

import bisect
import json
import re
import sys
import time

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
OUT = f"{BASE}/granularity_units.json"
sys.path.insert(0, BASE)
import union_channels as U  # noqa: E402

MIN_UNIT = 12

# --- structural split, no semantics ------------------------------------------------
SENT = re.compile(r"(?<=[.!?])\s+")
SEMI = re.compile(r"\s*[;]\s*")
DASH = re.compile(r"\s+(?:--|\u2014|\u2013)\s+")
BULLET = re.compile(r"(?:^|\s)(?:\d{1,2}[.)]|[-*\u2022])\s+")

# --- ask cues ----------------------------------------------------------------------
IMPERATIVES = (
    "add", "apply", "archive", "ask", "assume", "audit", "avoid", "back", "be", "begin",
    "build", "bump", "cancel", "change", "check", "cherry-pick", "clean", "clear", "close",
    "collapse", "commit", "compare", "complete", "confirm", "connect", "consolidate",
    "continue", "convert", "copy", "correct", "create", "cut", "debug", "decide", "delete",
    "deploy", "describe", "determine", "disable", "do", "document", "don't", "dont", "drop",
    "enforce", "ensure", "enumerate", "escalate", "exclude", "explain", "export", "extract",
    "fetch", "figure", "find", "finish", "fix", "focus", "fold", "follow", "force", "generate",
    "get", "give", "go", "handle", "hold", "ignore", "implement", "include", "install",
    "investigate", "keep", "kill", "land", "leave", "let", "list", "log", "look", "make",
    "mark", "measure", "merge", "migrate", "mirror", "move", "name", "note", "open",
    "outline", "pick", "plan", "please", "prepare", "preserve", "print", "prioritize",
    "proceed", "produce", "provide", "prune", "publish", "pull", "push", "put", "read",
    "rearm", "rebase", "rebuild", "reconcile", "record", "redo", "reduce", "refactor",
    "regenerate", "reinstall", "reject", "remove", "rename", "reorder", "repair", "replace",
    "reply", "report", "reproduce", "request", "require", "reset", "restart", "restore",
    "restrict", "resume", "retry", "return", "revert", "revisit", "review", "rewrite", "re-run",
    "rerun", "run", "save", "scan", "scope", "search", "send", "set", "setup", "show",
    "simplify", "skip", "split", "start", "stay", "stop", "summarize", "swap", "sync",
    "take", "tell", "test", "think", "throw", "treat", "trim", "try", "turn", "unblock",
    "update", "upgrade", "upload", "use", "validate", "verify", "wait", "watch", "wrap",
    "write", "yield")
IMPERATIVE_RE = re.compile(r"^(?:%s)\b" % "|".join(
    sorted((re.escape(v) for v in IMPERATIVES), key=len, reverse=True)))
REQUEST_RE = re.compile(
    r"\b(please|can you|could you|would you|will you|i need|i want|i'd like|"
    r"i would like|let's|lets|you should|we should|should be|must|need to|"
    r"have to|is it possible|any way to|why don't you|why not)\b")
QUESTION_WORD_RE = re.compile(r"^(what|why|how|when|where|which|who|is|are|do|does|did|can|could|should|would|will)\b")


def segment(text: str) -> list[str]:
    """Structural split only. No semantic judgement."""
    out: list[str] = []
    for line in text.split("\n"):
        for piece in BULLET.split(line):
            for sent in SENT.split(piece):
                for semi in SEMI.split(sent):
                    for dash in DASH.split(semi):
                        u = dash.strip(" \t-*#>")
                        if len(u) >= MIN_UNIT:
                            out.append(u)
    return out


def is_ask(u: str) -> bool:
    low = u.lower()
    if low.endswith("?"):
        return True
    if REQUEST_RE.search(low):
        return True
    if IMPERATIVE_RE.match(low):
        return True
    if QUESTION_WORD_RE.match(low):
        return True
    return False


class CitedIndex:
    """Map blob offsets back to unit indices so quote scanning is one pass per quote."""

    def __init__(self, units: list[str]):
        self.units = units
        self.starts: list[int] = []
        parts = []
        pos = 0
        for u in units:
            self.starts.append(pos)
            parts.append(u)
            pos += len(u) + 1
        self.blob = "\n".join(parts)

    def cite(self, quotes: list[str]) -> set[int]:
        hit: set[int] = set()
        starts = self.starts
        for q in quotes:
            i = self.blob.find(q)
            while i != -1:
                k = bisect.bisect_right(starts, i) - 1
                if k >= 0:
                    hit.add(k)
                    i = self.blob.find(q, starts[k] + len(self.units[k]))
                else:
                    i = self.blob.find(q, i + 1)
        return hit


def main() -> int:
    t0 = time.time()
    reg = json.load(open(U.REGISTER))["records"]
    quotes = sorted({U.norm(r.get("quote") or "") for r in reg})
    quotes = [q for q in quotes if len(q) >= MIN_UNIT]
    print(f"register distinct quotes >= {MIN_UNIT} chars: {len(quotes)}")

    H, hstats = U.harness()
    I = {x for x in U.imessage() if U.keep(x)}
    K = {x for x in U.kcode()[0] if U.keep(x)}
    P = U.phone()
    members = {"harness": H, "imessage": I, "kcode": K, "phone": P}
    print(f"members: {[(k, len(v)) for k, v in members.items()]}  [{time.time()-t0:.0f}s]")

    units: dict[str, set[str]] = {}
    for name, ms in members.items():
        s: set[str] = set()
        for m in ms:
            s.update(segment(m))
        units[name] = s
        print(f"  {name:9s} {len(ms):6d} members -> {len(s):7d} distinct units  "
              f"({len(s)/max(len(ms),1):.2f} per member)  [{time.time()-t0:.0f}s]")

    ask_units = {u for u in units["harness"] if is_ask(u)}
    print(f"\nharness ask-cue units: {len(ask_units)} of {len(units['harness'])} "
          f"({len(ask_units)/len(units['harness'])*100:.1f}%)")

    # citation over units
    result = {"min_unit_chars": MIN_UNIT, "per_channel": {}, "ask_rules": {}}

    def blob(s: set[str]) -> str:
        return "\n".join(sorted(s))

    cited: dict[str, int] = {}
    cited_units: dict[str, set[str]] = {}
    for name in members:
        ordered = sorted(units[name])
        idx = CitedIndex(ordered)
        c = idx.cite(quotes)
        cited[name] = len(c)
        cited_units[name] = {ordered[i] for i in c}
        result["per_channel"][name] = {
            "members": len(members[name]),
            "distinct_units": len(units[name]),
            "units_per_member": round(len(units[name]) / max(len(members[name]), 1), 2),
            "cited_units": len(c),
            "coverage_pct": round(len(c) / len(units[name]) * 100, 1),
        }
        print(f"  {name:9s} cited units {len(c):6d} / {len(units[name]):7d} = "
              f"{len(c)/len(units[name])*100:5.1f}%  [{time.time()-t0:.0f}s]")

    # union over units: pairwise greedy containment, same method as union_channels.py
    order = ["harness", "imessage", "kcode", "phone"]
    blobs = {n: blob(units[n]) for n in order}
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]]
    eaten = 0
    pair_overlap = {}
    for a, b in pairs:
        n = sum(1 for x in sorted(units[a], key=len, reverse=True) if x in blobs[b])
        pair_overlap[f"{a}_in_{b}"] = n
        eaten += n
        print(f"  overlap {a} in {b}: {n}  [{time.time()-t0:.0f}s]")
    union = sum(len(units[n]) for n in order) - eaten
    total_cited = sum(cited.values())
    print(f"\nunit union = {sum(len(units[n]) for n in order)} - {eaten} = {union}")
    print(f"cited units = {total_cited}; coverage = "
          f"{total_cited/union*100:.1f}%  [{time.time()-t0:.0f}s]")

    # Tighter denominator: harness restricted to ask-cue units. The numerator MUST be
    # filtered the same way and the overlaps MUST be re-measured on the reduced set;
    # reusing the all-unit numerator or the all-unit overlap count would compare a
    # numerator and a denominator that count different things.
    h_ask_units = units["harness"] & ask_units
    c_ask = cited_units["harness"] & ask_units
    others = [n for n in order if n != "harness"]
    eaten_ask = 0
    for b in others:
        eaten_ask += sum(1 for x in sorted(h_ask_units, key=len, reverse=True)
                         if x in blobs[b])
    for i, a in enumerate(others):
        for b in others[i + 1:]:
            eaten_ask += sum(1 for x in sorted(units[a], key=len, reverse=True)
                             if x in blobs[b])
    union_ask = len(h_ask_units) + sum(len(units[n]) for n in others) - eaten_ask
    print(f"\n[LOWER BOUND] all units: {total_cited}/{union} = "
          f"{total_cited/union*100:.1f}%")
    print(f"[TIGHTER] harness ask-units only: {len(c_ask)}/{union_ask} = "
          f"{len(c_ask)/union_ask*100:.1f}%  (numerator filtered identically)")
    print(f"          harness ask-units {len(h_ask_units)}, of which cited {len(c_ask)}"
          f" = {len(c_ask)/len(h_ask_units)*100:.1f}%")

    result["union_units"] = union
    result["cited_units_total"] = total_cited
    result["coverage_all_units_pct"] = round(total_cited / union * 100, 1)
    result["union_units_harness_ask_only"] = union_ask
    result["cited_units_harness_ask_only"] = len(c_ask)
    result["coverage_harness_ask_only_pct"] = round(len(c_ask) / union_ask * 100, 1)
    result["harness_ask_units_cited_pct"] = round(
        len(c_ask) / max(len(h_ask_units), 1) * 100, 1)
    result["pair_overlap"] = pair_overlap
    result["distinct_quotes_hitting_any_unit"] = len({
        q for q in quotes
        for n in order if q in blobs[n]})
    result["ask_rules"] = {
        "imperative_openers": len(IMPERATIVES),
        "request_phrases": REQUEST_RE.pattern,
        "question_word_openers": QUESTION_WORD_RE.pattern,
        "note": "heuristic; precision and recall measured by validate_ask_rules.py",
    }
    result["method"] = (
        "structural segmentation (newlines, sentence terminators, semicolons, dash joins, "
        "list markers) with no semantic judgement; citation = a register quote appears as "
        "a substring of the unit; overlap = greedy long-first containment; the harness "
        "ask-only figure filters numerator and denominator identically and re-measures "
        "overlap on the reduced set")
    json.dump(result, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}  [{time.time()-t0:.0f}s]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
