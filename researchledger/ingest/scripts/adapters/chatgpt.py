#!/usr/bin/env python3
"""ChatGPT adapter — wrapper over goal1_normalize.adapt_chatgpt.

The reference implementation already contains the documented ChatGPT export
handling (auto-detected, evidence-driven):
    expects   ~/Exports/chatgpt-20261010/raw/conversations.json (or .../conversations/)
    format    top-level JSON list; per conversation: id/title/create_time/update_time
              + "mapping" node graph; messages sorted by create_time; text from
              content.parts (string parts only); role from author.role
    status    NOT LANDED yet (log["chatgpt"]["status"] == "present_but_unrecognized_format"
              if the file appears but lacks "mapping" — probe before trusting)
When the export lands: run `python3 scripts/adapters/smoke.py --source chatgpt`;
it will report landed/format recognition, then downstream stages run unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import goal1_normalize as gn  # noqa: E402

CANDIDATES = [
    os.path.expanduser("~/Exports/chatgpt-20261010/raw/conversations.json"),
    os.path.expanduser("~/Exports/chatgpt-20261010/raw/conversations/conversations.json"),
]


def landed():
    return next((p for p in CANDIDATES if os.path.exists(p)), None)


def iter_messages(raw_dir=None):
    if not landed():
        raise FileNotFoundError(f"ChatGPT export not present; expects {CANDIDATES[0]}")
    norm, msgs, log = [], [], {}
    gn.adapt_chatgpt(norm, msgs, log)
    if log.get("chatgpt", {}).get("status") not in (None, "ok"):
        raise ValueError(f"ChatGPT export recognized as: {log.get('chatgpt')}")
    for m in msgs:
        if m.get("source") == "chatgpt":
            yield m


def iter_conversations(raw_dir=None):
    norm, _msgs, log = [], [], {}
    gn.adapt_chatgpt(norm, _msgs, log)
    for r in norm:
        if r["source"] == "chatgpt":
            yield {"source": r["source"], "conv_id": r["id"], "title": r.get("title"),
                   "created_at": r.get("created_at"), "updated_at": r.get("updated_at"),
                   "model": r.get("model"), "turns": r.get("turns"),
                   "account_uuid": r.get("account_uuid")}
