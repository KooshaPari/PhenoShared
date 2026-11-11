#!/usr/bin/env python3
"""Schema adapters for exports (BRIEF: "Gemini Takeout and ChatGPT exports arrive
later; design for them").

IMPORTANT (validated 2026-10-11): the REFERENCE implementations already exist and
are proven — `scripts/goal1_normalize.py` contains:
    adapt_claude_conversations / adapt_claude_design / adapt_claude_projects
    / adapt_claude_memories   -> produced goal1/messages.jsonl (8,480 rows)
    adapt_gemini              -> parses the LANDED Gemini Takeout export
                                 (HTML activity cells at
                                 ~/Exports/gemini-20261010/raw/Takeout/My Activity/
                                 Gemini Apps/MyActivity.html) — 761 activity rows
    adapt_chatgpt             -> auto-detects ~/Exports/chatgpt-20261010/raw/
                                 conversations.json (mapping-walk); not landed yet

This package is a thin, testable WRAPPER over those functions so future exports
plug into the same pipeline without re-deriving extraction logic. Contract for
every adapter (what downstream stages consume — see goal1/messages.jsonl):

    iter_messages(raw_dir=None) -> dicts with keys
        source, conv_id, msg_id, role, created_at, text
    iter_conversations(raw_dir=None) -> dicts with keys
        source, conv_id, title, created_at, updated_at, model, turns, account_uuid

Run `python3 scripts/adapters/smoke.py --source claude` for the strict parity
check against goal1/messages.jsonl.
"""
