#!/usr/bin/env python3
"""Smoke test for verifier.risky_action gate."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verifier.risky_action import check_proposal


def main() -> int:
    blocked = check_proposal('{"command": "rm -rf /tmp/x"}')
    benign = check_proposal('{"result": "ok"}')
    print("blocked:", blocked.to_dict())
    print("benign:", benign.to_dict())
    if blocked.ok:
        print("FAIL: expected rm -rf to be blocked")
        return 1
    if not benign.ok:
        print("FAIL: expected benign JSON to pass")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
