"""Standalone 12-case test for canonical_attrs._tool_names_to_array.

This is a focused unit test for the shared helper consolidated out of the four
private copies in jcode/kcode/codex/cursor_build_canonical.py. It is a plain
script (not a pytest file) so `pytest tests/ -q` stays at the original 6-pass
count and this test runs separately on demand.

Run from /Users/kooshapari/Exports/analysis with:

    python3 test_canonical_attrs_12case.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sure the analysis dir is on sys.path so `import canonical_attrs` works
# whether the script is invoked from there or from somewhere else.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from canonical_attrs import _tool_names_to_array  # noqa: E402


# (label, input, expected_output)
CASES = [
    # Sentinel values
    ("None -> None",                          None,                None),
    ("empty string -> []",                    "",                  []),
    ("whitespace string -> []",               "   ",               []),
    ("question mark -> []",                   "?",                 []),
    # Single CSV value
    ("single name -> single list",            "bash",              ["bash"]),
    # Multiple CSV values
    ("multiple CSV -> multiple list",         "bash,bash,read",    ["bash", "bash", "read"]),
    # CSV with whitespace around commas
    ("CSV with whitespace -> trimmed list",   " bash , bash ,read ", ["bash", "bash", "read"]),
    # Pass-through list
    ("list input -> pass through",            ["bash", "read"],    ["bash", "read"]),
    # JSON-array STRING inputs
    ("JSON array string (no spaces) -> list", '["bash","read"]',   ["bash", "read"]),
    ("JSON array string (with spaces)",       '["bash", "read"]',  ["bash", "read"]),
    # JSON-like but not parseable as a list-of-strings -> comma split
    ("JSON array of ints -> comma split",     "[1,2]",             ["[1", "2]"]),
    # Garbage starting with '[' but invalid -> comma split
    ("garbage starting with '[' -> split",    "not-json[",         ["not-json["]),
]


def main() -> int:
    failures: list[str] = []
    for label, inp, expected in CASES:
        got = _tool_names_to_array(inp)
        if got != expected:
            failures.append(
                f"  FAIL {label!r}: input={inp!r} expected={expected!r} got={got!r}"
            )
        else:
            print(f"  PASS {label}")
    print()
    print(f"Ran {len(CASES)} cases; {len(failures)} failed.")
    for line in failures:
        print(line)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())