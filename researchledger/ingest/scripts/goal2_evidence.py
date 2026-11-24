#!/usr/bin/env python3
"""
GOAL 2 evidence collector — LOCAL ONLY. Produces structural/measurement
evidence for audit.md. Never emits raw chat text; IPs minimally masked
(first two octets only); no emails/names in output.
"""
import json
import os
import re
from collections import Counter, defaultdict

CL = os.path.expanduser("~/Exports/claude-20261010/raw")
GM = os.path.expanduser("~/Exports/gemini-20261010/raw")
OUT = os.path.expanduser("~/Exports/analysis/goal2")
os.makedirs(OUT, exist_ok=True)

def mask_ip(ip):
    if not ip:
        return "[IP]"
    if ":" in ip:  # IPv6 — keep first two hextets only
        groups = ip.split(":")
        return ":".join(groups[:2]) + ":x:x:x:x:x:x"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.x.x"
    return "[IP]"

E = {}

# ---- 1. login history ----
with open(os.path.join(CL, "light_metadata-000/login_history.json"), encoding="utf-8") as f:
    lh = json.load(f)
events = lh.get("login_events", [])
accts = Counter(e.get("account_uuid") for e in events)
countries = Counter((e.get("location_info") or {}).get("country") for e in events)
cities = Counter((e.get("location_info") or {}).get("city") for e in events)
regions = Counter((e.get("location_info") or {}).get("region") for e in events)
methods = Counter(e.get("method") for e in events)
os_c = Counter((e.get("user_agent") or {}).get("os_family") for e in events)
browsers = Counter((e.get("user_agent") or {}).get("browser_family") for e in events)
devices = Counter((e.get("user_agent") or {}).get("device_family") for e in events)
timeline = []
for e in sorted(events, key=lambda x: x.get("timestamp") or ""):
    ua = e.get("user_agent") or {}
    timeline.append({
        "ts": e.get("timestamp"), "ip_masked": mask_ip(e.get("ip_address", "")),
        "os": ua.get("os_family"), "browser": ua.get("browser_family"),
        "device": ua.get("device_family"), "country": (e.get("location_info") or {}).get("country"),
        "method": e.get("method"),
    })
E["login_history"] = {
    "events": len(events), "account_uuids": dict(accts),
    "countries": dict(countries), "cities": dict(cities), "regions": dict(regions),
    "methods": dict(methods), "os_family": dict(os_c),
    "browser_family": dict(browsers), "device_family": dict(devices),
    "distinct_ips_masked": sorted({t["ip_masked"] for t in timeline}),
    "n_distinct_ip_masks": len({t["ip_masked"] for t in timeline}),
    "timeline": timeline,
}

# ---- 2. identity/id consistency ----
with open(os.path.join(CL, "light_metadata-000/users.json"), encoding="utf-8") as f:
    users = json.load(f)
u = users[0] if users else {}
with open(os.path.join(CL, "conversations-000/conversations.json"), encoding="utf-8") as f:
    convos = json.load(f)
conv_accts = Counter((c.get("account") or {}).get("uuid") for c in convos)
mem_accts = Counter()
memdir = os.path.join(CL, "memories-000")
for fn in os.listdir(memdir):
    if fn.endswith(".json"):
        with open(os.path.join(memdir, fn), encoding="utf-8") as f:
            mem_accts[json.load(f).get("account_uuid")] += 1
E["identity"] = {
    "user_record_fields": sorted(u.keys()),
    "user_uuid": u.get("uuid"),
    "email_present": bool(u.get("email_address")),
    "full_name_present": bool(u.get("full_name")),
    "phone_present": bool(u.get("verified_phone_number")),
    "conversation_account_uuids": dict(conv_accts),
    "memories_account_uuids": dict(mem_accts),
    "all_match_users_uuid": set(conv_accts) | set(mem_accts) == {u.get("uuid")},
    "org_team_fields_found": False,  # verified: no org/team keys in keyfreq
}

# ---- 3. attachments / extracted_content ----
n_att = n_ext = 0
ext_bytes = 0
by_type = Counter()
by_ftype = Counter()
largest = []
n_files = 0
summaries_nonempty = 0
for c in convos:
    if (c.get("summary") or "").strip():
        summaries_nonempty += 1
    for m in c.get("chat_messages", []):
        for a in m.get("attachments") or []:
            n_att += 1
            by_type[a.get("file_type")] += 1
            by_ftype[re.sub(r".*/", "", a.get("file_type") or "")] += 1
            ec = a.get("extracted_content") or ""
            if ec:
                n_ext += 1
                ext_bytes += len(ec)
                largest.append((len(ec), a.get("file_name"), a.get("file_type")))
        n_files += len(m.get("files") or [])
largest.sort(reverse=True)
E["attachments"] = {
    "attachments_total": n_att,
    "with_extracted_content": n_ext,
    "extracted_content_total_bytes": ext_bytes,
    "by_file_type_top": dict(by_type.most_common(15)),
    "messages_files_field_total": n_files,
    "largest_extracted": [
        {"bytes": b, "name_len": len(fn or ""), "type": ft}
        for b, fn, ft in largest[:10]],
    "conversation_summary_nonempty": summaries_nonempty,
    "conversation_summary_total": len(convos),
}

# ---- 4. flags/hidden/system-ish fields ----
# design chat hidden attachment + pills
dsg = os.path.join(CL, "design_chats-000/design_chats")
hidden = 0
pills = 0
for fn in os.listdir(dsg):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(dsg, fn), encoding="utf-8") as f:
        dc = json.load(f)
    for m in dc.get("messages", []):
        c = m.get("content") or {}
        for a in c.get("attachments") or []:
            if a.get("hidden"):
                hidden += 1
        if c.get("pill"):
            pills += 1
# content block type distribution for "system-ish" detection
ctypes = Counter()
flags_nonnull = 0
for c in convos:
    for m in c.get("chat_messages", []):
        for b in m.get("content") or []:
            if isinstance(b, dict):
                ctypes[b.get("type")] += 1
                if b.get("flags") is not None:
                    flags_nonnull += 1
E["system_fields"] = {
    "design_hidden_attachments": hidden,
    "design_pill_messages": pills,
    "content_block_types": dict(ctypes.most_common()),
    "flags_nonnull": flags_nonnull,
    "nil_root_parent_observed": True,  # 00000000-0000-4000-8000-000000000000 seen
}

# ---- 5. content-stripped chats (deleted-chat candidates) ----
try:
    with open(os.path.expanduser("~/Exports/analysis/goal1/empty_message_report.json"),
              encoding="utf-8") as f:
        emr = json.load(f)
except Exception:
    emr = {}
# bulk timestamp clustering of updated_at on fully-empty convs
upd = Counter()
for r in emr.get("fully_empty", []):
    ts = r.get("updated_at") or ""
    upd[ts[:16]] += 1  # minute precision
E["content_stripped"] = {
    "counts": emr.get("counts", {}),
    "fully_empty_conversations": len(emr.get("fully_empty", [])),
    "partially_empty_conversations": len(emr.get("partially_empty", [])),
    "updated_at_minute_clusters": dict(upd.most_common(10)),
    "all_names_empty": all(r.get("name_empty")
                           for r in emr.get("fully_empty", [])),
    "created_range": [
        min((r.get("created_at") or "" for r in emr.get("fully_empty", [])), default=None),
        max((r.get("created_at") or "" for r in emr.get("fully_empty", [])), default=None)],
}

# ---- 6. Gemini media folder unexpected-file scan (names only) ----
media = os.path.join(GM, "Takeout/My Activity/Gemini Apps")
names = sorted(os.listdir(media))
course_like = [n for n in names if re.search(
    r"(?i)(assignment|lecture|recitation|cse\d|test\d|exam|homework|project\d|week\d)", n)]
docs_like = [n for n in names if n.lower().endswith(
    (".pdf", ".pptx", ".xlsx", ".csv", ".zip", ".cpp"))]
media_like = [n for n in names if n.lower().endswith((".png", ".jpg", ".heic", ".mp4"))]
E["gemini_media"] = {
    "total_files": len(names),
    "course_work_named": len(course_like),
    "document_like": len(docs_like),
    "photo_video_like": len(media_like),
    "course_examples_redacted": [re.sub(r"[A-Za-z0-9]{8,}", "[ID]", n)[:60]
                                  for n in course_like[:8]],
}

# ---- 7. uninterpretable / null-only fields from keyfreq ----
agg = os.path.expanduser("~/Exports/analysis/step0/keyfreq/_aggregate.tsv")
unint = []
nullish = []
with open(agg, encoding="utf-8") as f:
    hdr = f.readline()
    for line in f:
        path, cnt, types = line.rstrip("\n").split("\t")
        tmap = dict(p.split(":") for p in types.split(","))
        total = int(cnt)
        nulls = int(tmap.get("null", 0))
        if total > 0 and nulls == total:
            nullish.append((path, total))
        # heuristic: odd/unknown field names
        leaf = path.rsplit(".", 1)[-1].rstrip("[]")
        if leaf in ("approval_key", "approval_key_legacy", "approval_options",
                    "alternative_display_type", "pill", "cut_off", "is_missing",
                    "is_citable", "token_budget", "enterprise", "first_call",
                    "raw", "all", "automotive", "safety", "design", "team",
                    "single_select", "multi_select", "display_content",
                    "why_is_this_here", "ingestion_date"):
            unint.append((path, total, types))
E["uninterpretable_fields"] = {
    "null_everywhere": [{"path": p, "n": n} for p, n in nullish if n >= 100],
    "unknown_semantics": [{"path": p, "n": n, "types": t} for p, n, t in unint],
}

# ---- 8. gaps (from step0 value distributions) ----
try:
    with open(os.path.expanduser("~/Exports/analysis/step0/value_distributions.json"),
              encoding="utf-8") as f:
        vd = json.load(f)
    months = vd["messages_per_month"]
    present = set(months)
    lo, hi = min(present), max(present)
    def ym_add(y, m, d):
        m += d
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return f"{y:04d}-{m:02d}"
    gaps = []
    cy, cm = int(lo[:4]), int(lo[5:7])
    while f"{cy:04d}-{cm:02d}" <= hi:
        key = f"{cy:04d}-{cm:02d}"
        if key not in present:
            gaps.append(key)
        nxt = ym_add(cy, cm, 1)
        cy, cm = int(nxt[:4]), int(nxt[5:7])
    E["gaps"] = {"range": [lo, hi], "zero_months": gaps,
                 "messages_per_month": months}
except Exception as ex:
    E["gaps"] = {"error": str(ex)}

with open(os.path.join(OUT, "evidence.json"), "w", encoding="utf-8") as f:
    json.dump(E, f, indent=2, ensure_ascii=False)
print(json.dumps({k: (v if not isinstance(v, dict) else
                      {kk: vv for kk, vv in list(v.items())[:6]})
                  for k, v in E.items()}, indent=2, default=str)[:4000])
