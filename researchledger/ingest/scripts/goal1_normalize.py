#!/usr/bin/env python3
"""
GOAL 1a — Normalized schema extraction. LOCAL ONLY, no network, no LLM.

Outputs (analysis/goal1/):
  normalized.jsonl   one record per source item:
    {source, record_type, id, title, created_at, updated_at, model, turns,
     attachments:[{name,type,size}], project, account_uuid, fingerprint}
  messages.jsonl     one record per message/activity text unit:
    {source, conv_id, msg_id, role, created_at, text}
  dedupe.json        duplicate report (id-level + content fingerprint)
  adapt_log.json     per-adapter counts + skipped items

Adapters: claude conversations / design_chats / projects / memories,
gemini MyActivity, chatgpt (stub auto-detects ChatGPT export format when it
lands: expects [{title, create_time, update_time, mapping:...}])
"""
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

CL = os.path.expanduser("~/Exports/claude-20261010/raw")
GM = os.path.expanduser("~/Exports/gemini-20261010/raw")
OUT = os.path.expanduser("~/Exports/analysis/goal1")
os.makedirs(OUT, exist_ok=True)

def fp(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", "replace"))
        h.update(b"\x1f")
    return h.hexdigest()[:24]

def iso(s):
    if isinstance(s, str) and len(s) >= 19 and s[4] == "-":
        return s
    return None

# ---------------- adapters ----------------

def msg_text(m):
    """Message text: msg.text, else direct content[].text of type==text blocks."""
    t = (m.get("text") or "").strip()
    if t:
        return m.get("text") or ""
    parts = []
    for b in m.get("content") or []:
        if isinstance(b, dict) and b.get("type") == "text" and (b.get("text") or "").strip():
            parts.append(b.get("text") or "")
    return "\n".join(parts)

def adapt_claude_conversations(norm, msgs, log):
    path = os.path.join(CL, "conversations-000/conversations.json")
    with open(path, encoding="utf-8") as f:
        convos = json.load(f)
    n_msg = 0
    empty_report = {"fully_empty": [], "partially_empty": [],
                    "counts": {"messages_total": 0, "messages_empty": 0,
                               "messages_recovered_via_blocks": 0}}
    for c in convos:
        cid = c.get("uuid")
        ms = c.get("chat_messages", [])
        # model: search message input metadata (best-effort)
        model = None
        for m in ms:
            for blk in m.get("content") or []:
                inp = blk.get("input") if isinstance(blk, dict) else None
                if isinstance(inp, dict):
                    model = (inp.get("model_name") or inp.get("model")
                             or ((inp.get("metadata") or {}).get("model") or {}).get("name")
                             or model)
            if model:
                break
        atts = []
        for m in ms:
            for a in m.get("attachments") or []:
                atts.append({"name": a.get("file_name"), "type": a.get("file_type"),
                             "size": a.get("file_size"),
                             "has_extracted_content": bool(a.get("extracted_content"))})
            for fl in m.get("files") or []:
                atts.append({"name": fl.get("file_name") or fl.get("name"),
                             "type": fl.get("file_type") or fl.get("type"),
                             "size": fl.get("file_size") or fl.get("size"),
                             "has_extracted_content": False})
        texts = [msg_text(m) for m in ms]
        n_empty = sum(1 for t in texts if not t.strip())
        empty_report["counts"]["messages_total"] += len(ms)
        empty_report["counts"]["messages_empty"] += n_empty
        empty_report["counts"]["messages_recovered_via_blocks"] += sum(
            1 for m, t in zip(ms, texts) if t.strip() and not (m.get("text") or "").strip())
        if n_empty == len(ms) and ms:
            empty_report["fully_empty"].append(
                {"uuid": cid, "turns": len(ms), "created_at": c.get("created_at"),
                 "updated_at": c.get("updated_at"), "name_empty": not (c.get("name") or "")})
        elif n_empty:
            empty_report["partially_empty"].append(
                {"uuid": cid, "empty": n_empty, "total": len(ms)})
        first_human = next((t for m, t in zip(ms, texts) if m.get("sender") == "human"), "")
        norm.append({
            "source": "claude", "record_type": "conversation", "id": cid,
            "title": c.get("name"), "created_at": iso(c.get("created_at")),
            "updated_at": iso(c.get("updated_at")), "model": model,
            "turns": len(ms), "attachments": atts, "project": None,
            "account_uuid": (c.get("account") or {}).get("uuid"),
            "summary_field_present": bool(c.get("summary")),
            "fingerprint": fp(c.get("name"), c.get("created_at"), first_human[:400]),
        })
        for m, t in zip(ms, texts):
            msgs.append({"source": "claude", "conv_id": cid, "msg_id": m.get("uuid"),
                         "role": m.get("sender"), "created_at": iso(m.get("created_at")),
                         "text": t})
            n_msg += 1
    log["claude_conversations"] = {"conversations": len(convos), "messages": n_msg}
    with open(os.path.join(OUT, "empty_message_report.json"), "w", encoding="utf-8") as f:
        json.dump(empty_report, f, indent=2, ensure_ascii=False)

def adapt_claude_design(norm, msgs, log):
    d = os.path.join(CL, "design_chats-000/design_chats")
    n = 0
    m0 = len(msgs)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            dc = json.load(f)
        ms = dc.get("messages", [])
        norm.append({
            "source": "claude", "record_type": "design_chat", "id": dc.get("uuid") or fn[:-5],
            "title": dc.get("title"), "created_at": iso(dc.get("created_at")),
            "updated_at": iso(dc.get("updated_at")), "model": None,
            "turns": len(ms),
            "attachments": [{"name": a.get("name"), "type": a.get("type"), "size": None,
                             "has_extracted_content": False}
                            for m in ms for a in (m.get("content") or {}).get("attachments") or []],
            "project": (dc.get("project") or {}).get("name"),
            "account_uuid": None, "summary_field_present": False,
            "fingerprint": fp(dc.get("title"), dc.get("created_at")),
        })
        for m in ms:
            c = m.get("content") or {}
            msgs.append({"source": "claude", "conv_id": dc.get("uuid") or fn[:-5],
                         "msg_id": m.get("uuid"), "role": m.get("role") or c.get("role"),
                         "created_at": iso(m.get("created_at")), "text": c.get("content") or ""})
        n += 1
    log["claude_design_chats"] = {"files": n, "messages": len(msgs) - m0}

def adapt_claude_projects(norm, msgs, log):
    d = os.path.join(CL, "projects-000/projects")
    n = docs = 0
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            p = json.load(f)
        pdocs = p.get("docs") or []
        norm.append({
            "source": "claude", "record_type": "project", "id": p.get("uuid") or fn[:-5],
            "title": p.get("name"), "created_at": iso(p.get("created_at")),
            "updated_at": iso(p.get("updated_at")), "model": None,
            "turns": 0, "attachments": [], "project": p.get("name"),
            "account_uuid": (p.get("creator") or {}).get("uuid"),
            "is_private": p.get("is_private"), "doc_count": len(pdocs),
            "summary_field_present": False,
            "fingerprint": fp(p.get("name"), p.get("created_at")),
        })
        for dd in pdocs:
            msgs.append({"source": "claude", "conv_id": p.get("uuid") or fn[:-5],
                         "msg_id": dd.get("uuid"), "role": "project_doc",
                         "created_at": iso(dd.get("created_at")),
                         "text": dd.get("content") or ""})
        n += 1
        docs += len(pdocs)
    log["claude_projects"] = {"projects": n, "docs": docs}

def adapt_claude_memories(norm, msgs, log):
    d = os.path.join(CL, "memories-000")
    n = 0
    m0 = len(msgs)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            mem = json.load(f)
        files = mem.get("memory_files") or []
        norm.append({
            "source": "claude", "record_type": "memory", "id": fn[:-5],
            "title": None, "created_at": None,
            "updated_at": max((iso(x.get("updated_at")) for x in files
                               if iso(x.get("updated_at"))), default=None),
            "model": None, "turns": 0, "attachments": [],
            "project": None, "account_uuid": mem.get("account_uuid"),
            "memory_file_count": len(files), "summary_field_present": False,
            "fingerprint": fp(mem.get("account_uuid"), fn),
        })
        for mf in files:
            msgs.append({"source": "claude", "conv_id": fn[:-5],
                         "msg_id": mf.get("path"), "role": "memory_file",
                         "created_at": iso(mf.get("updated_at")),
                         "text": mf.get("content") or ""})
        # conversations_memory top-level string
        cm = mem.get("conversations_memory")
        if isinstance(cm, str) and cm.strip():
            msgs.append({"source": "claude", "conv_id": fn[:-5],
                         "msg_id": "conversations_memory", "role": "memory_summary",
                         "created_at": None, "text": cm})
        n += 1
    log["claude_memories"] = {"files": n, "memory_units": sum(
        1 for m in msgs[m0:] if m["role"] in ("memory_file", "memory_summary"))}

DATE_RE = re.compile(r'([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2}\s*[AP]M)')
def _parse_gemini_dt(s):
    s = s.replace("\u202f", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    try:
        return datetime.strptime(s, "%b %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None

def adapt_gemini(norm, msgs, log):
    act = os.path.join(GM, "Takeout/My Activity/Gemini Apps/MyActivity.html")
    raw = open(act, encoding="utf-8").read()
    chunks = raw.split('class="outer-cell')[1:]
    n = 0
    for ch in chunks:
        cell = 'class="' + ch
        # content cell text = title line "Gemini Apps" then content
        m_txt = re.search(
            r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">(.*?)'
            r'<div class="content-cell', cell, re.S)
        body = m_txt.group(1) if m_txt else ""
        # strip the trailing <p></p><br> and date line
        dm = DATE_RE.search(body)
        dt = _parse_gemini_dt(dm.group(1)) if dm else None
        text = re.sub(r"<[^>]+>", "\n", body)
        import html as H
        text = H.unescape(text)
        if dm:
            # remove the date line occurrence
            text = text.replace(dm.group(1), "", 1)
        text = re.sub(r"\n+", "\n", text).strip()
        det = re.search(r'<b>Details:</b><br>(.*?)<b>', cell, re.S)
        url = None
        if det:
            um = re.search(r'href="([^"]+)"', det.group(1))
            url = um.group(1) if um else None
        rid = fp(url or "", dt.isoformat() if dt else "", text[:200])
        norm.append({
            "source": "gemini", "record_type": "activity", "id": rid,
            "title": None, "created_at": dt.isoformat() if dt else None,
            "updated_at": None, "model": None, "turns": 1,
            "attachments": [], "project": None, "account_uuid": None,
            "summary_field_present": False,
            "details_url": url,
            "fingerprint": fp(url or "", dt.isoformat() if dt else ""),
        })
        msgs.append({"source": "gemini", "conv_id": rid, "msg_id": rid,
                     "role": "activity", "created_at": dt.isoformat() if dt else None,
                     "text": text})
        n += 1
    log["gemini_activity"] = {"records": n}

def adapt_chatgpt(norm, msgs, log):
    """Stub: auto-detects ChatGPT export conversations.json if/when it lands."""
    candidates = [
        os.path.expanduser("~/Exports/chatgpt-20261010/raw/conversations.json"),
        os.path.expanduser("~/Exports/chatgpt-20261010/raw/conversations/conversations.json"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        log["chatgpt"] = {"status": "not_present_yet",
                          "expects": candidates[0]}
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not (isinstance(data, list) and data and isinstance(data[0], dict)
            and "mapping" in data[0]):
        log["chatgpt"] = {"status": "present_but_unrecognized_format"}
        return
    n = mcount = 0
    for c in data:
        cid = c.get("id") or fp(c.get("title") or "", str(c.get("create_time")))
        mapping = c.get("mapping") or {}
        ordered = sorted(
            (v.get("message") for v in mapping.values() if v.get("message")),
            key=lambda m: m.get("create_time") or 0)
        texts = []
        for m in ordered:
            cont = m.get("content") or {}
            parts = cont.get("parts") or []
            t = "\n".join(str(p) for p in parts if isinstance(p, str))
            if not t:
                continue
            role = (m.get("author") or {}).get("role")
            texts.append((m.get("id"), role, m.get("create_time"), t))
        norm.append({
            "source": "chatgpt", "record_type": "conversation", "id": cid,
            "title": c.get("title"),
            "created_at": datetime.utcfromtimestamp(c["create_time"]).isoformat() + "Z"
                if c.get("create_time") else None,
            "updated_at": datetime.utcfromtimestamp(c["update_time"]).isoformat() + "Z"
                if c.get("update_time") else None,
            "model": None, "turns": len(texts), "attachments": [],
            "project": None,
            "account_uuid": None, "summary_field_present": False,
            "fingerprint": fp(c.get("title"), str(c.get("create_time")),
                              texts[0][3][:400] if texts else ""),
        })
        for mid, role, ct, t in texts:
            msgs.append({"source": "chatgpt", "conv_id": cid, "msg_id": mid, "role": role,
                         "created_at": datetime.utcfromtimestamp(ct).isoformat() + "Z"
                            if ct else None, "text": t})
            mcount += 1
        n += 1
    log["chatgpt"] = {"status": "adapted", "conversations": n, "messages": mcount}

# ---------------- main ----------------

def main():
    norm, msgs, log = [], [], {}
    adapt_claude_conversations(norm, msgs, log)
    adapt_claude_design(norm, msgs, log)
    adapt_claude_projects(norm, msgs, log)
    adapt_claude_memories(norm, msgs, log)
    adapt_gemini(norm, msgs, log)
    adapt_chatgpt(norm, msgs, log)

    # dedupe
    seen_id, seen_fp, dup_id, dup_fp = {}, {}, [], []
    kept = []
    for r in norm:
        key = (r["source"], r["record_type"], r["id"])
        if key in seen_id:
            dup_id.append({"key": key, "first_title": seen_id[key]})
            continue
        seen_id[key] = r.get("title")
        if r["fingerprint"] in seen_fp:
            dup_fp.append({"fingerprint": r["fingerprint"], "id": r["id"],
                           "dup_of": seen_fp[r["fingerprint"]]})
            continue
        seen_fp[r["fingerprint"]] = r["id"]
        kept.append(r)

    # message-level dupes (same conv+text hash); skip content-less messages
    seen_m, n_dup_m, n_nocontent = set(), 0, 0
    for m in msgs:
        if not (m["text"] or "").strip():
            n_nocontent += 1
            m["_dup"] = True
            continue
        h = fp(m["conv_id"], m["role"], (m["text"] or "")[:2000])
        if h in seen_m:
            n_dup_m += 1
            m["_dup"] = True
        seen_m.add(h)
    msgs_clean = [m for m in msgs if not m.get("_dup")]

    with open(os.path.join(OUT, "normalized.jsonl"), "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "messages.jsonl"), "w", encoding="utf-8") as f:
        for m in msgs_clean:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    dedupe = {"input_records": len(norm), "kept_records": len(kept),
              "dup_by_id": dup_id, "dup_by_fingerprint": dup_fp,
              "input_messages": len(msgs), "dup_messages_dropped": n_dup_m,
              "no_content_messages_skipped": n_nocontent,
              "kept_messages": len(msgs_clean)}
    with open(os.path.join(OUT, "dedupe.json"), "w", encoding="utf-8") as f:
        json.dump(dedupe, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "adapt_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(json.dumps({"records": len(kept), "messages": len(msgs_clean),
                      "dup_id": len(dup_id), "dup_fp": len(dup_fp),
                      "dup_msgs": n_dup_m, "adapters": log}, indent=2))

if __name__ == "__main__":
    main()
