#!/usr/bin/env python3
"""
STEP 0b — value distributions for LOW-CARDINALITY enum-like fields only
(sender roles, login methods, browser families, model names, message types),
plus monthly message volume timeline. LOCAL ONLY, no network.

Never emits free-text values: a field's values are only listed when the field
has <=50 distinct values AND all values are short (<80 chars) AND the field is
in/near an allowlist of structural fields. Everything else is reported as
"skipped (high-cardinality / free-text)".
"""
import json
import os
import re
from collections import Counter, defaultdict

RAW = os.path.expanduser("~/Exports/claude-20261010/raw")
OUT = os.path.expanduser("~/Exports/analysis/step0")

ALLOW_FIELDS = {
    "sender", "role", "method", "browser_family", "os_family", "device_family",
    "model_type", "model_name", "model", "provider", "type", "file_type",
    "mime_type", "content_type", "search_provider", "language", "site_domain",
    "country", "os_version", "browser_version", "visibility", "is_private",
    "is_starter_project", "stop_reason", "error_type",
}
MAX_DISTINCT = 50
MAX_LEN = 80

def dist(value, path_key, out):
    if path_key not in ALLOW_FIELDS and path_key.split(".")[-1] not in ALLOW_FIELDS:
        return
    if not isinstance(value, (str, bool, int)) or isinstance(value, bool) and value not in (True, False):
        if not isinstance(value, (str, bool)):
            return
    sv = str(value)
    if len(sv) > MAX_LEN:
        return
    c = out[path_key]
    c[sv] += 1
    if len(c) > MAX_DISTINCT:
        c["__overflow__"] = True

def walk(node, key, out, monthly):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, k, out, monthly)
    elif isinstance(node, list):
        for item in node:
            walk(item, key, out, monthly)
    else:
        if key in ALLOW_FIELDS or key.split(".")[-1] in ALLOW_FIELDS:
            dist(node, key.split(".")[-1], out)

def monthly_volume(convos):
    months = Counter()
    for c in convos:
        for m in c.get("chat_messages", []):
            ts = m.get("created_at", "")
            if isinstance(ts, str) and len(ts) >= 7:
                months[ts[:7]] += 1
    return dict(sorted(months.items()))

def main():
    report = {}

    # conversations — enum distributions
    with open(os.path.join(RAW, "conversations-000/conversations.json"), encoding="utf-8") as f:
        convos = json.load(f)

    out = defaultdict(Counter)
    months = Counter()
    sender_by_month = defaultdict(Counter)
    conv_month = Counter()
    for c in convos:
        ca = c.get("created_at", "")
        if isinstance(ca, str) and len(ca) >= 7:
            conv_month[ca[:7]] += 1
        for m in c.get("chat_messages", []):
            s = m.get("sender", "?")
            ts = m.get("created_at", "")
            mm = ts[:7] if isinstance(ts, str) and len(ts) >= 7 else "?"
            months[mm] += 1
            sender_by_month[mm][s] += 1
            walk(m, "", out, None)
    report["conversations_enum_dist"] = {k: dict(v) for k, v in sorted(out.items())
                                         if not v.get("__overflow__")}
    report["conversations_enum_overflow"] = sorted(k for k, v in out.items() if v.get("__overflow__"))
    report["messages_per_month"] = dict(sorted(months.items()))
    report["conversations_per_month"] = dict(sorted(conv_month.items()))

    # login history enums
    with open(os.path.join(RAW, "light_metadata-000/login_history.json"), encoding="utf-8") as f:
        lh = json.load(f)
    lo = defaultdict(Counter)
    for ev in lh.get("login_events", []):
        walk(ev, "", lo, None)
        loc = ev.get("location_info") or {}
        walk(loc.get("country"), "country", lo, None)
    report["login_enum_dist"] = {k: dict(v) for k, v in sorted(lo.items())
                                 if not v.get("__overflow__")}

    # per-sender monthly for gap analysis
    report["sender_per_month"] = {m: dict(c) for m, c in sorted(sender_by_month.items())}

    with open(os.path.join(OUT, "value_distributions.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # md summary
    lines = ["# STEP 0b — enum value distributions + monthly volume (local only)", ""]
    lines.append("## Messages per month (all senders)")
    for m, n in report["messages_per_month"].items():
        lines.append(f"- {m}: {n}")
    lines.append("")
    lines.append("## Conversations created per month")
    for m, n in report["conversations_per_month"].items():
        lines.append(f"- {m}: {n}")
    lines.append("")
    lines.append("## Enum distributions (low-cardinality structural fields)")
    for section in ("conversations_enum_dist", "login_enum_dist"):
        lines.append(f"### {section}")
        for k, v in report[section].items():
            lines.append(f"- `{k}`: " + ", ".join(f"{a}={b}" for a, b in sorted(v.items(), key=lambda x: -x[1])))
    if report["conversations_enum_overflow"]:
        lines.append("")
        lines.append("Skipped (high-cardinality): " + ", ".join(report["conversations_enum_overflow"]))
    with open(os.path.join(OUT, "value_distributions.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("OK -> value_distributions.json/md")

if __name__ == "__main__":
    main()
