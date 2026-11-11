#!/usr/bin/env python3
"""
Gemini Takeout STEP 0 — LOCAL ONLY. Parses MyActivity.html structure,
inventories media/attachment files, emits record counts, date range, and
field-frequency table. Outputs contain NO prompt/activity text — only
structure, counts, timestamps, and redaction-safe presence flags.
"""
import json
import os
import re
import html as htmllib
from collections import Counter, defaultdict
from datetime import datetime, timezone

GRAW = os.path.expanduser("~/Exports/gemini-20261010/raw")
OUT = os.path.expanduser("~/Exports/analysis/step0")
ACT = os.path.join(GRAW, "Takeout/My Activity/Gemini Apps/MyActivity.html")

RECORD_SPLIT = 'class="outer-cell'
TITLE_RE = re.compile(r'<p class="mdl-typography--title">(.*?)</p>', re.S)
# Date line inside content cell: e.g. "Sep 15, 2026, 7:00:07\u202fPM EDT"
# tz abbreviation captured separately (Python %Z rejects EDT/EST on this box)
DATE_RE = re.compile(
    r'([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2}\s*[AP]M)\s*([A-Z]{2,4})?'
)
PRODUCTS_RE = re.compile(r'<b>Products:</b><br>(.*?)<b>', re.S)
DETAILS_RE = re.compile(r'<b>Details:</b><br>(.*?)<b>', re.S)
WHY_RE = re.compile(r'<b>Why is this here\?</b><br>(.*?)</div>', re.S)
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"')
LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"')

def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = htmllib.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()

def parse_dt(s):
    s = s.replace('\u202f', ' ').replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    try:
        return datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None

def main():
    raw = open(ACT, encoding="utf-8").read()
    parts = raw.split(RECORD_SPLIT)
    body_parts = parts[1:]  # first chunk is head/CSS

    field_presence = Counter()
    dts = []
    products_counter = Counter()
    details_shape = Counter()
    why_present = 0
    media_refs = Counter()
    parse_fail_dates = 0
    titles = Counter()

    records = []
    for chunk in body_parts:
        cell = 'class="' + chunk  # restore
        tm = TITLE_RE.search(cell)
        title = strip_tags(tm.group(1)) if tm else None
        field_presence["title"] += 1 if title else 0
        titles[title or "<missing>"] += 1

        # date: first date-looking match (tz label captured alongside)
        dm = DATE_RE.findall(cell)
        dt = None
        for cand, _tz in dm:
            dt = parse_dt(cand)
            if dt:
                break
        if dt:
            field_presence["time"] += 1
            dts.append(dt)
        else:
            parse_fail_dates += 1

        pm = PRODUCTS_RE.search(cell)
        products = strip_tags(pm.group(1)) if pm else None
        if products:
            field_presence["products"] += 1
            for p in re.split(r'[,\s]+', products):
                p = p.strip()
                if p:
                    products_counter[p] += 1

        dm2 = DETAILS_RE.search(cell)
        if dm2:
            field_presence["details"] += 1
            det = strip_tags(dm2.group(1))
            # shape only: url / text / empty
            if "http" in det:
                details_shape["contains_url"] += 1
            elif det:
                details_shape["text_only"] += 1
            else:
                details_shape["empty"] += 1

        wm = WHY_RE.search(cell)
        if wm:
            why_present += 1
            field_presence["why_is_this_here"] += 1

        for src in IMG_RE.findall(cell):
            media_refs["img_src"] += 1
        for href in LINK_RE.findall(cell):
            if any(href.lower().endswith(ext) for ext in
                   (".png", ".jpg", ".jpeg", ".heic", ".mp4", ".pdf", ".csv",
                    ".xlsx", ".pptx", ".zip", ".cpp", ".html")):
                media_refs["file_link"] += 1

        # structured-field probes (brief's JSON field names)
        low = cell.lower()
        for f in ("safetylabel", "locationinfos", "attachment"):
            if f in low:
                field_presence[f + "_literal_in_record"] += 1

        records.append({"title": title,
                        "time": dt.isoformat() if dt else None})

    # media folder inventory
    media_dir = ACT.rsplit("/", 1)[0]
    media_files = []
    ext_counter = Counter()
    total_media_size = 0
    for fn in sorted(os.listdir(media_dir)):
        fp = os.path.join(media_dir, fn)
        if not os.path.isfile(fp):
            continue
        sz = os.stat(fp).st_size
        ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else "<none>"
        ext_counter[ext] += 1
        total_media_size += sz
        media_files.append({"name": fn, "size": sz, "ext": ext})

    # other Takeout Gemini files
    misc = []
    gdir = os.path.join(GRAW, "Takeout/Gemini")
    for fn in sorted(os.listdir(gdir)):
        fp = os.path.join(gdir, fn)
        sz = os.stat(fp).st_size
        content = open(fp, encoding="utf-8", errors="replace").read() if sz < 10000 else ""
        misc.append({"name": fn, "size": sz, "empty_scaffold": content.strip() == "<div></div>"})

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "myactivity": {
            "path": ACT,
            "size_bytes": os.stat(ACT).st_size,
            "records": len(body_parts),
            "records_dated": len(dts),
            "records_date_parse_fail": parse_fail_dates,
            "date_range": {
                "min": min(dts).isoformat() if dts else None,
                "max": max(dts).isoformat() if dts else None,
            },
            "field_presence": dict(field_presence),
            "title_values": dict(titles.most_common(20)),
            "products_values": dict(products_counter.most_common(30)),
            "details_shape": dict(details_shape),
            "why_is_this_here_present": why_present,
            "media_refs_in_html": dict(media_refs),
        },
        "media_folder": {
            "path": media_dir,
            "file_count": len(media_files),
            "total_bytes": total_media_size,
            "by_extension": dict(ext_counter.most_common()),
        },
        "takeout_gemini_files": misc,
        "notes": [
            "safetyLabel/locationInfos/attachment: brief lists these as JSON My-Activity "
            "fields; this export is HTML. Literal probes per record recorded under "
            "field_presence.*_literal_in_record.",
        ],
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "gemini_inventory.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # md
    a = out["myactivity"]
    m = out["media_folder"]
    lines = ["# Gemini Takeout STEP 0 Inventory (local script, no LLM)", ""]
    lines.append(f"MyActivity.html: {a['size_bytes']:,} bytes")
    lines.append(f"Records: {a['records']} (dated: {a['records_dated']}, date-parse fails: {a['records_date_parse_fail']})")
    lines.append(f"Date range: {a['date_range']['min']} .. {a['date_range']['max']}")
    lines.append("")
    lines.append("## Field presence (per record)")
    for k, v in sorted(a["field_presence"].items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Titles (top)")
    for k, v in a["title_values"].items():
        lines.append(f"- {k!r}: {v}")
    lines.append("")
    lines.append("## Products values")
    for k, v in a["products_values"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Details shape")
    for k, v in a["details_shape"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append(f"## Media folder: {m['file_count']} files, {m['total_bytes']:,} bytes")
    for k, v in m["by_extension"].items():
        lines.append(f"- .{k}: {v}")
    lines.append("")
    lines.append("## Takeout/Gemini files")
    for mm in misc:
        lines.append(f"- {mm['name']}: {mm['size']} bytes, empty_scaffold={mm['empty_scaffold']}")
    with open(os.path.join(OUT, "gemini_inventory.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK: {a['records']} activity records, {m['file_count']} media files -> {OUT}")

if __name__ == "__main__":
    main()
