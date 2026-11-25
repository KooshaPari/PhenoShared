#!/usr/bin/env python3
"""Gemini adapter — wrapper over goal1_normalize.adapt_gemini.

OBSERVED schema (verified against the landed export, not a guess): the Gemini
Takeout ships activity as HTML, not JSON:
    ~/Exports/gemini-20261010/raw/Takeout/My Activity/Gemini Apps/MyActivity.html
    - records delimited by class="outer-cell"
    - prompt text inside <div class="content-cell ...mdl-typography--body-1">
    - timestamp as "Mon DD, YYYY, H:MM:SS AM/PM" line inside the cell
    - Details: <a href=...> link
Records contain the PROMPT only (no model response) — verified: 761 records in
the Claude export's gemini cross-reference had no response side, which is why
Gemini contributes no Goal-3 reaction labels. If a future Gemini export version
ships JSON responses, extend adapt_gemini; the wrapper contract stays the same.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import goal1_normalize as gn  # noqa: E402


def landed():
    return os.path.exists(os.path.join(
        gn.GM, "Takeout/My Activity/Gemini Apps/MyActivity.html"))


def iter_messages(raw_dir=None):
    if not landed():
        raise FileNotFoundError(f"Gemini export not present under {gn.GM}")
    norm, msgs, log = [], [], {}
    gn.adapt_gemini(norm, msgs, log)
    for m in msgs:
        yield m


def iter_conversations(raw_dir=None):
    # Gemini activity is flat (one record = one unit); no conversation grouping.
    return iter(())
