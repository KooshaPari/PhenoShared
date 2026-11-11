#!/usr/bin/env python3
"""
STEP 0 inventory — LOCAL ONLY. No network, no LLM. Reads raw export JSON files,
emits file inventory, record counts, date ranges, and full JSON key-frequency
tables at every nesting level.

Outputs (under analysis/step0/):
  inventory.json        machine-readable full inventory
  inventory.md          human-readable summary
  keyfreq/<name>.tsv    per-file key-frequency table (path pattern, count, types)
  keyfreq/_aggregate.tsv aggregated across all files

Privacy: outputs contain only structure (key names, counts, types, min/max
timestamps) — never message bodies or other content values.
"""
import json
import os
import re
import sys
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone

RAW = os.path.expanduser("~/Exports/claude-20261010/raw")
OUT = os.path.expanduser("~/Exports/analysis/step0")
KF = os.path.join(OUT, "keyfreq")

ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)
DATEONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Values that must never be echoed into outputs
def looks_like_content_key(k: str) -> bool:
    return k.lower() in {
        "text", "content", "body", "message", "prompt", "completion",
        "input", "output", "title", "name", "summary", "description",
    }

def classify(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        if ISO_RE.match(v):
            return "timestamp"
        if DATEONLY_RE.match(v):
            return "date"
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__

def walk(node, path, freq, dates, counter, depth=0, max_depth=40):
    """freq: path_pattern -> (Counter of types, occurrence count)
       dates: path_pattern -> [min_iso, max_iso]"""
    t = classify(node)
    freq[path][1] += 1
    freq[path][0][t] += 1

    if t in ("timestamp", "date") and isinstance(node, str):
        cur = dates.get(path)
        if cur is None:
            dates[path] = [node, node]
        else:
            if node < cur[0]:
                cur[0] = node
            if node > cur[1]:
                cur[1] = node
        return

    if depth >= max_depth:
        return

    if isinstance(node, dict):
        for k, v in counter(node):
            vt = classify(v)
            # record scalar timestamp fields too
            if vt in ("timestamp", "date") and isinstance(v, str):
                p = f"{path}.{k}"
                freq[p][1] += 1
                freq[p][0][vt] += 1
                cur = dates.get(p)
                if cur is None:
                    dates[p] = [v, v]
                else:
                    if v < cur[0]:
                        cur[0] = v
                    if v > cur[1]:
                        cur[1] = v
                continue
            walk(v, f"{path}.{k}", freq, dates, counter, depth + 1, max_depth)
    elif isinstance(node, list):
        for item in node:
            walk(item, f"{path}[]", freq, dates, counter, depth + 1, max_depth)

def counter(d):
    return d.items()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        head = f.read(1)
        f.seek(0)
        if head == "[" or head == "{":
            return json.load(f), "json"
        # JSONL fallback
        rows = []
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows, "jsonl"

def top_level_counts(obj):
    """Record counts: list -> 1 collection of N; dict -> per-key list lengths."""
    counts = {}
    if isinstance(obj, list):
        counts["<root array>"] = len(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list):
                counts[k] = len(v)
            elif isinstance(v, dict):
                counts[k] = 1
    return counts

def main():
    os.makedirs(KF, exist_ok=True)
    files = []
    for dirpath, dirnames, filenames in os.walk(RAW):
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            if not fn.endswith(".json"):
                # still inventory non-json files
                st = os.stat(fp)
                files.append({"path": os.path.relpath(fp, RAW), "size": st.st_size,
                              "kind": "non-json"})
                continue
            st = os.stat(fp)
            files.append({"path": os.path.relpath(fp, RAW), "size": st.st_size,
                          "kind": "json"})

    inv = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "raw_root": RAW, "files": [], "notes": []}

    agg_freq = defaultdict(lambda: [Counter(), 0])

    for meta in files:
        rel = meta["path"]
        fp = os.path.join(RAW, rel)
        entry = {"path": rel, "size_bytes": meta["size"]}
        if meta["kind"] != "json":
            entry["note"] = "not JSON — not parsed"
            inv["files"].append(entry)
            continue
        try:
            obj, fmt = load_json(fp)
        except Exception as e:
            entry["error"] = f"parse failed: {type(e).__name__}: {e}"
            inv["files"].append(entry)
            continue
        entry["format"] = fmt
        entry["top_type"] = type(obj).__name__
        entry["record_counts"] = top_level_counts(obj)

        freq = defaultdict(lambda: [Counter(), 0])
        dates = {}
        walk(obj, "$", freq, dates, counter)

        # per-file key frequency table
        name = rel.replace("/", "__").replace(".json", "") + ".tsv"
        with open(os.path.join(KF, name), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["path_pattern", "occurrences", "value_types"])
            for p in sorted(freq):
                types, cnt = freq[p]
                w.writerow([p, cnt, ",".join(f"{k}:{v}" for k, v in sorted(types.items()))])
                agg_freq[p][1] += cnt
                agg_freq[p][0].update(types)

        # date ranges: overall + notable fields
        all_min, all_max = None, None
        for lo, hi in dates.values():
            if all_min is None or lo < all_min:
                all_min = lo
            if all_max is None or hi > all_max:
                all_max = hi
        entry["date_range"] = {"min": all_min, "max": all_max}
        entry["date_fields"] = {p: {"min": v[0], "max": v[1]}
                                for p, v in sorted(dates.items())}
        entry["key_patterns"] = len(freq)
        inv["files"].append(entry)

    # aggregate table
    with open(os.path.join(KF, "_aggregate.tsv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["path_pattern", "occurrences", "value_types"])
        for p in sorted(agg_freq):
            types, cnt = agg_freq[p]
            w.writerow([p, cnt, ",".join(f"{k}:{v}" for k, v in sorted(types.items()))])

    # detect expected-but-missing dirs
    expected = ["conversations-000", "design_chats-000", "light_metadata-000",
                "projects-000", "memories-000"]
    present = set(os.listdir(RAW))
    inv["present_dirs"] = sorted(present)
    inv["missing_expected_dirs"] = [d for d in expected if d not in present]

    with open(os.path.join(OUT, "inventory.json"), "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=2, ensure_ascii=False)

    # human summary
    lines = []
    lines.append("# STEP 0 Inventory (local script, no LLM, no network)")
    lines.append(f"Generated: {inv['generated_utc']}")
    lines.append(f"Raw root: {RAW}")
    lines.append("")
    lines.append(f"Present dirs: {', '.join(inv['present_dirs'])}")
    if inv["missing_expected_dirs"]:
        lines.append(f"MISSING (noted per brief): {', '.join(inv['missing_expected_dirs'])}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("| file | size | records | date range | key patterns |")
    lines.append("|---|---:|---|---|---:|")
    for e in inv["files"]:
        rc = e.get("record_counts", {})
        rc_s = "; ".join(f"{k}={v}" for k, v in rc.items()) or e.get("note") or e.get("error", "-")
        dr = e.get("date_range", {})
        dr_s = f"{dr.get('min','-')} .. {dr.get('max','-')}" if dr else "-"
        lines.append(f"| {e['path']} | {e['size_bytes']:,} | {rc_s} | {dr_s} | {e.get('key_patterns','-')} |")
    lines.append("")
    lines.append("## Date fields (per file, path -> min/max)")
    for e in inv["files"]:
        df = e.get("date_fields")
        if not df:
            continue
        lines.append(f"### {e['path']}")
        for p, mm in df.items():
            lines.append(f"- `{p}`: {mm['min']} .. {mm['max']}")
    lines.append("")
    lines.append("Full key-frequency tables: analysis/step0/keyfreq/*.tsv")
    with open(os.path.join(OUT, "inventory.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"OK: {len(inv['files'])} files inventoried -> {OUT}")
    print(f"missing: {inv['missing_expected_dirs']}")

if __name__ == "__main__":
    main()
