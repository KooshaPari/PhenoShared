#!/usr/bin/env python3
"""Claude adapter — wrapper over the proven goal1_normalize adapt_* functions.

Reproduces the exact message pipeline (conversations + design chats + projects +
memories) and the main() message dedupe (content-less skip + conv/role/text-hash
dedupe), so tuple parity with goal1/messages.jsonl is exact by construction.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import goal1_normalize as gn  # noqa: E402


def pipeline_messages(dedupe=True):
    """Return the messages list exactly as goal1_normalize.main() builds it.

    Note: adapt_claude_conversations has a legacy side effect — it rewrites
    goal1/empty_message_report.json. We snapshot that file and restore it if the
    regenerated content is byte-identical, so this adapter stays read-only.
    """
    emr = os.path.join(gn.OUT, "empty_message_report.json")
    pre_bytes = pre_mtime = None
    if os.path.exists(emr):
        pre_bytes = open(emr, "rb").read()
        pre_mtime = os.path.getmtime(emr)

    norm, msgs, log = [], [], {}
    gn.adapt_claude_conversations(norm, msgs, log)
    gn.adapt_claude_design(norm, msgs, log)
    gn.adapt_claude_projects(norm, msgs, log)
    gn.adapt_claude_memories(norm, msgs, log)

    if pre_bytes is not None:
        post = open(emr, "rb").read()
        if post == pre_bytes:
            os.utime(emr, (pre_mtime, pre_mtime))  # restore read-only behavior
        else:
            print("WARNING: empty_message_report.json content changed on re-run; "
                  "keeping the regenerated copy (pre-wipe vs post-wipe text).")
    if not dedupe:
        return msgs, norm, log
    seen = set()
    kept = []
    for m in msgs:
        if not (m["text"] or "").strip():
            continue
        h = gn.fp(m["conv_id"], m["role"], (m["text"] or "")[:2000])
        if h in seen:
            continue
        seen.add(h)
        kept.append(m)
    return kept, norm, log


def iter_messages(raw_dir=None):  # raw_dir unused: paths pinned inside goal1_normalize
    for m in pipeline_messages(dedupe=True)[0]:
        yield m


def iter_conversations(raw_dir=None):
    for r in pipeline_messages(dedupe=False)[1]:
        if r["source"] == "claude":
            yield {"source": r["source"], "conv_id": r["id"], "title": r.get("title"),
                   "created_at": r.get("created_at"), "updated_at": r.get("updated_at"),
                   "model": r.get("model"), "turns": r.get("turns"),
                   "account_uuid": r.get("account_uuid")}
