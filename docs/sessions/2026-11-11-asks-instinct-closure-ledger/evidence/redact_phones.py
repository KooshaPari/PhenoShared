#!/usr/bin/env python3
"""Redact E.164 phone numbers (``+1`` followed by exactly 10 digits) in place.

Reproducible: re-running this on an already-redacted file is a no-op for the
phone patterns (the replacement token contains no digits after ``+1``), and it
prints a count summary without ever printing a phone number.

Usage:
    python3 redact_phones.py [PATH]

Default PATH is ``E-imessage-register.md`` next to this script.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(r"\+1\d{10}")
REPLACEMENT = "<PHONE-REDACTED>"
DEFAULT_TARGET = Path(__file__).resolve().parent / "E-imessage-register.md"


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else DEFAULT_TARGET
    if not target.is_file():
        print(f"target not found: {target}", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8")
    matches = PATTERN.findall(original)
    distinct = len(set(matches))

    redacted = PATTERN.sub(REPLACEMENT, original)
    if redacted != original:
        target.write_text(redacted, encoding="utf-8")

    remaining = len(PATTERN.findall(target.read_text(encoding="utf-8")))

    # Counts only. Never print a matched value.
    print(f"file: {target}")
    print(f"distinct_numbers: {distinct}")
    print(f"occurrences_replaced: {len(matches)}")
    print(f"occurrences_remaining: {remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
