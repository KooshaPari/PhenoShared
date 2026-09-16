"""Statistical computation helpers for stock-vs-ours analysis.

This module contains measurement functions for partial credit, format
compliance, intent preservation, and hallucination detection.
"""

from __future__ import annotations

import re


def _measure_partial_credit(reply: str, expected: str) -> float:
    reply_lower = reply.lower()
    if not reply.strip():
        return 0.0
    err_words = ["error", "fail", "cannot", "denied"]
    if any(m in reply_lower for m in err_words):
        return 0.0
    if expected == "match_grid":
        if "[" in reply and "]" in reply:
            if "grid" in reply_lower or "output" in reply_lower:
                return 1.0
            return 0.5
        return 0.0
    if expected == "passes_tests":
        if any(w in reply_lower for w in ["pass", "success", "fixed"]):
            return 1.0
        return 0.5
    if expected == "correct_letter":
        m = re.search(r"\b([A-J])\b", reply.strip())
        if m:
            return 1.0
        return 0.0
    if expected == "ok" or not expected:
        return 1.0
    return 0.0


def _measure_intent_preservation(reply: str) -> float:
    if len(reply) < 2 or len(reply) > 5000:
        return 0.0
    return 1.0


def _measure_format_compliance(reply: str, expected: str) -> float:
    if not reply.strip():
        return 0.0
    if expected in ("ok",):
        return 1.0 if reply.strip() else 0.0
    if expected == "match_grid":
        return 1.0 if "[" in reply and "]" in reply else 0.0
    if expected == "passes_tests":
        return 1.0 if reply.strip() else 0.0
    if expected == "correct_letter":
        return 1.0 if re.search(r"\b[A-J]\b", reply.strip()) else 0.0
    return 0.0


def _measure_hallucination(reply: str, expected: str) -> int:
    if expected in ("ok", "passes_tests", "match_grid"):
        return 0
    m = re.search(r"\b([A-Z])\b", reply)
    if m and m.group(1) not in "ABCDEFGHIJ":
        return 1
    return 0
